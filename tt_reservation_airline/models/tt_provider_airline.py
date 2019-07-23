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

    def action_failed_booked_api_airline(self):
        for rec in self:
            rec.write({
                'state': 'fail_booking'
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

    def action_issued_provider_api(self, provider_id, api_context):
        try:
            # ## UPDATED by Samvi 2018/07/24
            # ## Terdetect sebagai administrator jika sudo
            # provider_obj = self.env['tt.tb.provider'].sudo().browse(provider_id)
            provider_obj = self.env['tt.provider.airline'].browse(provider_id)
            if not provider_obj:
                return {
                    'error_code': -1,
                    'error_msg': '',
                }
            provider_obj.action_issued(api_context)
            return {
                'error_code': 0,
                'error_msg': '',
            }
        except Exception as e:
            return {
                'error_code': -1,
                'error_msg': str(e)
            }

    @api.one
    def create_ticket_number(self, passenger_ids):
        # Variable name adalah first_name + last_name yang disambung semua tanpa spasi
        # Case nya bisa first_name = Budi Satria last_name Gunawan
        # atau first_name = Budi last_name Satria Gunawan
        passenger_list = []
        for rec in self.booking_id.passenger_ids:
            value = {
                'id': rec.id,
                'name': '{}{}'.format(''.join(rec.first_name.split(' ')).lower(), ''.join(rec.last_name.split(' ')).lower()),
            }
            passenger_list.append(value)

        for psg_data in passenger_ids:
            psg_data['name'] = '{}{}'.format(''.join(psg_data['first_name'].split(' ')).lower(), ''.join(psg_data['last_name'].split(' ')).lower())
            for psg_list in passenger_list:
                if not psg_list.get('ticket_number', False) and psg_list['name'] == psg_data['name']:
                    psg_list['ticket_number'] = psg_data.pop('ticket_number')
                    break

        self.ticket_ids.unlink()

        [self.ticket_ids.create({
            'passenger_id': rec['id'],
            'provider_id': self.id,
            'ticket_number': rec['ticket_number']
        }) for rec in passenger_list]

    @api.one
    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']

        for scs in service_charge_vals:
            scs['currency_id'] = currency_obj.get_id(scs.pop('currency'))
            scs['foreign_currency_id'] = currency_obj.get_id(scs.pop('foreign_currency'))
            scs['provider_airline_booking_id'] = self.id
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
            self.env.cr.commit()

    def action_create_ledger_api(self):
        try:
            # ## UPDATED by Samvi 2018/07/24
            # ## Terdetect sebagai administrator jika sudo
            # provider_obj = self.env['tt.tb.provider'].sudo().browse(provider_id)

            self.action_create_ledger()
            return {
                'error_code': 0,
                'error_msg': ''
            }
        except Exception as e:
            return {
                'error_code': -1,
                'error_msg': str(e)
            }

    def to_dict(self):
        journey_list = []
        for rec in self.journey_ids:
            journey_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id.code,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'balance_due': self.balance_due,
            'direction': self.direction,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'return_date': self.return_date,
            'sid_issued': self.sid_issued and self.sid_issued or '',
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': []
        }

        return res