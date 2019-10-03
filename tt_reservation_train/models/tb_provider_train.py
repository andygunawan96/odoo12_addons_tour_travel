from odoo import api, fields, models, _
from .tt_reservation_train import BOOKING_STATE, JOURNEY_DIRECTION
from datetime import datetime

class TransportBookingProvider(models.Model):
    _name = 'tt.tb.provider.train'
    _rec_name = 'pnr'
    # _order = 'sequence'
    _order = 'departure_date'

    pnr = fields.Char('PNR')
    provider = fields.Char('Provider')
    state = fields.Selection(BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.train', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')

    direction = fields.Selection(JOURNEY_DIRECTION, string='Direction')
    # origin_id = fields.Many2one('tt.destinations', 'Origin')
    # destination_id = fields.Many2one('tt.destinations', 'Destination')
    departure_date = fields.Datetime('Departure Date')
    return_date = fields.Datetime('Return Date')
    origin = fields.Char('Origin')
    destination = fields.Char('Destination')

    journey_ids = fields.One2many('tt.tb.journey.train', 'provider_booking_id', string='Journeys')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_train_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    total = fields.Monetary(string='Total', readonly=True)
    total_fare = fields.Monetary(string='Total Fare', compute=False, readonly=True)
    total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    promotion_code = fields.Char(string='Promotion Code')

    # sid_connector = fields.Char('SID Connector', readonly=True)
    # sid = fields.Char('Session ID', readonly=True)

    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    #
    # refund_uid = fields.Many2one('res.users', 'Refund By')
    # refund_date = fields.Datetime('Refund Date')

    ticket_ids = fields.One2many('tt.tb.ticket.train', 'provider_id', 'Ticket Number')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    def action_booked(self, pnr, api_context):
        for rec in self:
            rec.write({
                'pnr': pnr,
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
        self.env.cr.commit()

    def action_set_as_booked(self):
        self.write({
            'state': 'booked',
        })
        self.booking_id.action_check_provider_state()
        self.booking_id.message_post(body=_("PNR set as BOOKED: {} (Provider : {})".format(self.pnr, self.provider)))

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
            provider_obj = self.env['tt.tb.provider.train'].browse(provider_id)
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

        # self.ticket_ids.unlink()

        [self.ticket_ids.create({
            'passenger_id': rec['id'],
            'provider_id': self.id,
            'ticket_number': rec['ticket_number']
        }) for rec in passenger_list]

    @api.one
    def _create_service_charge(self, service_charge_summary):
        if not service_charge_summary:
            pass
        for rec in self.cost_service_charge_ids:
            if rec.charge_type != 'VOUCHER':
                rec.sudo().unlink()
        # self.cost_service_charge_ids.sudo().unlink()
        service_chg_obj = self.env['tt.service.charge']
        # Update Service Charge - Provider
        for scs in service_charge_summary:
            for val in scs['service_charges']:
                if val['amount']:
                    val['provider_train_booking_id'] = self.id
                    service_chg_obj.create(val)
            self._compute_total()

    @api.depends('cost_service_charge_ids')
    def _compute_total(self):
        for rec in self:
            total = 0
            total_orig = 0
            for sc in rec.cost_service_charge_ids:
                if sc.charge_code.find('r.ac') < 0:
                    total += sc.total
                # total_orig adalah NTA
                total_orig += sc.total
            rec.write({
                'total': total,
                'total_orig': total_orig
            })

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