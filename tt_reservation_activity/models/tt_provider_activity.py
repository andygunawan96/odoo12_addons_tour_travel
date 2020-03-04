from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime


class TtProviderActivity(models.Model):
    _name = 'tt.provider.activity'
    _rec_name = 'pnr'
    _order = 'visit_date'
    _description = 'Rodex Model'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.activity', 'Order Number', ondelete='cascade')
    balance_due = fields.Float('Balance Due')
    activity_id = fields.Many2one('tt.master.activity', 'Activity')
    activity_product_id = fields.Many2one('tt.master.activity.lines', 'Activity Product')
    activity_product = fields.Char('Product Type')
    activity_product_uuid = fields.Char('Product Type Uuid')
    visit_date = fields.Datetime('Visit Date')

    sid_issued = fields.Char('SID Issued')#signature generate sendiri

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_activity_booking_id', 'Cost Service Charges')

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
    ticket_ids = fields.One2many('tt.ticket.activity', 'provider_id', 'Ticket Number')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    # is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    def action_reverse_ledger_from_button(self):
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

        # if not self.is_ledger_created:
        #     raise UserError("This Provider Ledger is not Created.")

        ##fixme salahhh, ini ke reverse semua provider bukan provider ini saja
        for rec in self.booking_id.ledger_ids:
            if rec.pnr == self.pnr and not rec.is_reversed:
                rec.reverse_ledger()

        self.write({
            'state': 'fail_refunded',
            # 'is_ledger_created': False,
            'refund_uid': self.env.user.id,
            'refund_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid':self.env.user.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_booked_api_activity(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data.get('code') and provider_data['code'] or '',
                'pnr2': provider_data.get('uuid') and provider_data['uuid'] or '',
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
            for rec2 in rec.cost_service_charge_ids:
                rec2.sudo().write({
                    'description': provider_data['code']
                })

    def action_issued_api_activity(self,context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'sid_issued': context['signature'],
                'balance_due': 0
            })

    def action_failed_booked_api_activity(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked'
            })

    def action_failed_issued_api_activity(self):
        for rec in self:
            rec.write({
                'state': 'fail_issued'
            })

    def action_expired(self):
        self.state = 'cancel2'

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_ticket_api(self,passengers):
        ticket_list = []
        ticket_found = []
        ticket_not_found = []
        for psg in passengers:
            psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower() ==
                                                                ('%s%s' % (psg.get('first_name', ''),
                                                                           psg.get('last_name', ''))).lower().replace(' ',''))

            if not psg_obj:
                psg_obj = self.booking_id.passenger_ids.filtered(lambda x: x.name.replace(' ', '').lower()*2 ==
                                                                           ('%s%s' % (psg.get('first_name', ''),
                                                                                      psg.get('last_name',
                                                                                              ''))).lower().replace(' ',''))
            if psg_obj:
                ticket_list.append((0, 0, {
                    'pax_type': psg.get('pax_type'),
                    'ticket_number': psg.get('ticket_number'),
                    'passenger_id': psg_obj.id
                }))
                ticket_found.append(psg_obj.id)
            else:
                ticket_not_found.append(psg)

        psg_with_no_ticket = self.booking_id.passenger_ids.filtered(lambda x: x.id not in ticket_found)
        for idx, psg in enumerate(ticket_not_found):
            ticket_list.append((0, 0, {
                'pax_type': psg.get('pax_type'),
                'ticket_number': psg.get('ticket_number'),
                'passenger_id': psg_with_no_ticket[idx].id
            }))

        self.write({
            'ticket_ids': ticket_list
        })

    def update_ticket_api(self,passengers):##isi ticket number
        ticket_not_found = []
        for psg in passengers:
            ticket_found = False
            for ticket in self.ticket_ids:
                psg_name = ticket.passenger_id.name.replace(' ','').lower()
                if ('%s%s' % (psg['first_name'], psg['last_name'])).replace(' ','').lower() in [psg_name, psg_name*2]:
                    ticket.write({
                        'ticket_number': psg.get('ticket_number','')
                    })
                    ticket_found = True
                    break
            if not ticket_found:
                ticket_not_found.append(psg)

        for psg in ticket_not_found:
            self.write({
                'ticket_ids': [(0,0,{
                    'ticket_number': psg.get('ticket_number'),
                    'pax_type': psg.get('pax_type'),
                })]
            })

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['pax_count'] = 0
            scs['passenger_activity_ids'] = []
            scs['total'] = 0
            scs['currency_id'] = currency_obj.get_id('IDR')
            scs['foreign_currency_id'] = currency_obj.get_id('IDR')
            scs['provider_activity_booking_id'] = self.id
            if scs['charge_code'] != 'disc':
                for psg in self.ticket_ids:
                    if scs['pax_type'] == psg.pax_type and scs['sku_id'] == psg.ticket_number:
                        scs['passenger_activity_ids'].append(psg.passenger_id.id)
                        scs['pax_count'] += 1
                        scs['total'] += scs['amount']
            # scs.pop('currency')
            # scs.pop('foreign_currency')
                scs.pop('sku_id')
            else:
                for psg in self.ticket_ids:
                    scs['passenger_activity_ids'].append(psg.passenger_id.id)
                    scs['pax_count'] += 1
                    scs['total'] += scs['amount']
            scs['passenger_activity_ids'] = [(6,0,scs['passenger_activity_ids'])]
            scs['description'] = self.pnr and self.pnr or ''
            if scs['total'] != 0:
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
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created
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

    def action_create_ledger(self,issued_uid, pay_method=None):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid)

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
            'arrival_date': self.arrival_date,
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
        }

        return res

    def get_carrier_name(self):
        return []
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
