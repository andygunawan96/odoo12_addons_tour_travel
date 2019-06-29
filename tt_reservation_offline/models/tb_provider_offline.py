from odoo import api, fields, models, _


class ProviderOffline(models.Model):
    _name = 'tt.tb.provider.offline'

    _rec_name = 'pnr'
    # _order = 'sequence'
    # _order = 'departure_date'

    pnr = fields.Char('PNR')
    provider = fields.Char('Provider')
    # state = fields.Selection(BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('issued.offline', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')

    # direction = fields.Selection(JOURNEY_DIRECTION, string='Direction')
    # origin_id = fields.Many2one('tt.destinations', 'Origin')
    # destination_id = fields.Many2one('tt.destinations', 'Destination')
    # departure_date = fields.Datetime('Departure Date')
    # return_date = fields.Datetime('Return Date')
    # origin = fields.Char('Origin')
    # destination = fields.Char('Destination')

    # journey_ids = fields.One2many('tt.tb.journey.train', 'provider_booking_id', string='Journeys')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    total = fields.Monetary(string='Total', readonly=True)
    total_fare = fields.Monetary(string='Total Fare', compute=False, readonly=True)
    total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    promotion_code = fields.Char(string='Promotion Code')

    # sid_connector = fields.Char('SID Connector', readonly=True)
    # sid = fields.Char('Session ID', readonly=True)

    # Booking Progress
    # booked_uid = fields.Many2one('res.users', 'Booked By')
    # booked_date = fields.Datetime('Booking Date')
    confirm_uid = fields.Many2one('res.users', 'Confirmed By')
    confirm_date = fields.Datetime('Confirm Date')
    sent_uid = fields.Many2one('res.users', 'Sent By')
    sent_date = fields.Datetime('Sent Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    #
    # refund_uid = fields.Many2one('res.users', 'Refund By')
    # refund_date = fields.Datetime('Refund Date')

    # ticket_ids = fields.One2many('tt.tb.ticket.train', 'provider_id', 'Ticket Number')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    def action_confirm(self):
        for rec in self:
            rec.write({
                'state': 'confirm',
                'confirm_date': fields.Datetime.now(),
            })
        self.env.cr.commit()

    @api.depends('cost_service_charge_ids')
    def _compute_total(self):
        for rec in self:
            total = 0
            total_orig = 0
            for sc in self.cost_service_charge_ids:
                if sc.charge_code.find('r.ac') < 0:
                    total += sc.total
                    # total_orig adalah NTA
                    total_orig += sc.total
                rec.write({
                    'total': total,
                    'total_orig': total_orig
                })
