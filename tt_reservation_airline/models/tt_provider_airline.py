from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime


class TtProviderAirline(models.Model):
    _name = 'tt.provider.airline'
    _rec_name = 'pnr'
    _order = 'departure_date'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    balance_due = fields.Float('Balance Due')
    direction = fields.Selection(variables.JOURNEY_DIRECTION, string='Direction')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Char('Departure Date')
    return_date = fields.Char('Return Date')

    sid_issued = fields.Char('SID Issued')#signature generate sendiri

    journey_ids = fields.One2many('tt.journey.airline', 'provider_booking_id', string='Journeys')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_airline_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    # total = fields.Monetary(string='Total', readonly=True)
    # total_fare = fields.Monetary(string='Total Fare', compute="_compute_provider_total_fare", readonly=True)
    # total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    promotion_code = fields.Char(string='Promotion Code')


    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Char('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    #
    # refund_uid = fields.Many2one('res.users', 'Refund By')
    # refund_date = fields.Datetime('Refund Date')

    ticket_ids = fields.One2many('tt.ticket.airline', 'provider_id', 'Ticket Number')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    def action_booked_api_airline(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'pnr2': provider_data['pnr2'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
                'hold_date': datetime.strptime(provider_data['hold_date'],"%Y-%m-%d %H:%M:%S"),
                'balance_due': provider_data['balance_due']
            })

    def action_issued_api_airline(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature']
            })

    def action_failed_booked_api_airline(self):
        for rec in self:
            rec.write({
                'state': 'fail_booking'
            })

    def action_failed_issued_api_airline(self):
        for rec in self:
            rec.write({
                'state': 'fail_issued'
            })

    def action_set_as_booked(self):
        self.write({
            'state': 'booked',
        })
        # self.booking_id.action_check_provider_state()

    def action_issued(self, api_context=None):
        if not api_context: #Jika dari Backend, TIDAK ada api_context
            api_context = {
                'co_uid': self.env.user.id,
            }
        # self._validate_issued(api_context=api_context)
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_uid': api_context['co_uid'],
                'issued_date': fields.Datetime.now(),
            })
            rec.booking_id.action_check_provider_state(api_context)

    def create_ticket_api(self,passengers):
        ticket_list = []
        for psg in passengers:
            psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() ==
                                                                ('%s%s' % (psg.get('first_name', ''),
                                                                           psg.get('last_name', ''))).lower())

            if not psg_obj:
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower()*2 ==
                                                                           ('%s%s' % (psg.get('first_name', ''),
                                                                                      psg.get('last_name',
                                                                                              ''))).lower())
            ticket_list.append((0, 0, {
                'pax_type': psg.get('pax_type'),
                'ticket_number': psg.get('ticket_number'),
                'passenger_id': psg_obj.id
            }))
        self.write({
            'ticket_ids': ticket_list
        })

    def update_ticket_api(self,passengers):##isi ticket number
        for psg in passengers:
            for ticket in self.ticket_ids:
                psg_name = ticket.passenger_id.name.replace(' ','').lower()
                if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ', '').lower() in [psg_name,psg_name*2]:
                    ticket.write({
                        'ticket_number': psg.get('ticket_number','')
                    })
                    break

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['pax_count'] = 0
            scs['passenger_airline_ids'] = []
            scs['total'] = 0
            scs['currency_id'] = currency_obj.get_id(scs.get('currency'))
            scs['foreign_currency_id'] = currency_obj.get_id(scs.get('foreign_currency'))
            scs['provider_airline_booking_id'] = self.id
            for psg in self.ticket_ids:
                if scs['pax_type'] == psg.pax_type:
                    scs['passenger_airline_ids'].append(psg.passenger_id.id)
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
            scs.pop('currency')
            scs.pop('foreign_currency')
            scs['passenger_airline_ids'] = [(6,0,scs['passenger_airline_ids'])]
            scs['description'] = self.pnr
            service_chg_obj.create(scs)

        # "sequence": 1,
        # "charge_code": "fare",
        # "charge_type": "FARE",
        # "currency": "IDR",
        # "amount": 4800000,
        # "foreign_currency": "IDR",
        # "foreign_amount": 4800000,
        # "pax_count": 3,
        # "pax_type": "ADT",
        # "total": 14400000

    def delete_service_charge(self):
        for rec in self.cost_service_charge_ids:
            rec.unlink()
    # @api.depends('cost_service_charge_ids')
    # def _compute_total(self):
    #     for rec in self:
    #         total = 0
    #         total_orig = 0
    #         for sc in rec.cost_service_charge_ids:
    #             if sc.charge_code.find('r.ac') < 0:
    #                 total += sc.total
    #             # total_orig adalah NTA
    #             total_orig += sc.total
    #         rec.write({
    #             'total': total,
    #             'total_orig': total_orig
    #         })

    def action_create_ledger(self):
        if not self.is_ledger_created:
            self.write({'is_ledger_created': True})
            self.env['tt.ledger'].action_create_ledger(self)

    def to_dict(self):
        journey_list = []
        for rec in self.journey_ids:
            journey_list.append(rec.to_dict())
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'balance_due': self.balance_due,
            'direction': self.direction,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'return_date': self.return_date,
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
        }

        return res

    # def get_cost_service_charges(self):
    #     sc_value = {}
    #     for p_sc in self.cost_service_charge_ids:
    #         p_charge_type = p_sc.charge_type
    #         p_pax_type = p_sc.pax_type
    #         if p_charge_type == 'RAC' and p_sc.charge_code !=  'rac':
    #             continue
    #         if not sc_value.get(p_pax_type):
    #             sc_value[p_pax_type] = {}
    #         if not sc_value[p_pax_type].get(p_charge_type):
    #             sc_value[p_pax_type][p_charge_type] = {}
    #             sc_value[p_pax_type][p_charge_type].update({
    #                 'amount': 0,
    #                 'foreign_amount': 0
    #             })
    #         sc_value[p_pax_type][p_charge_type].update({
    #             'charge_code': p_sc.charge_code,
    #             'currency': p_sc.currency_id.name,
    #             'pax_count': p_sc.pax_count,
    #             'total': p_sc.total,
    #             'foreign_currency': p_sc.foreign_currency_id.name,
    #             'amount': sc_value[p_pax_type][p_charge_type]['amount'] + p_sc.amount,
    #             'foreign_amount': sc_value[p_pax_type][p_charge_type]['foreign_amount'] + p_sc.foreign_amount,
    #         })
    #     return sc_value
