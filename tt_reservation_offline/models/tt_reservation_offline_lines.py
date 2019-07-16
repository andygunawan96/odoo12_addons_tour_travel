from odoo import models, fields, api, _

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Request'),
    ('valid', 'Validated'),
    ('final', 'Finalization'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
]

TRANSACTION_TYPE = [
    ('airline', 'Airline'),
    ('train', 'Train'),
    ('ship', 'Ship'),
    # ('visa', 'Visa'),
    ('cruise', 'Cruise'),
    ('car', 'Car/Rent'),
    ('bus', 'Bus'),
    ('tour', 'Tours'),
    ('merchant', 'Merchandise'),
    ('others', 'Other(s)'),
    # ('passport', 'Passport'),
    ('activity', 'Activity'),
    ('travel_doc', 'Travel Doc.'),
    ('hotel', 'Hotel')
]

CLASS_OF_SERVICE = [
    ('eco', 'Economy'),
    ('pre', 'Premium Economy'),
    ('bus', 'Bussiness')
]


class IssuedOfflineLines(models.Model):
    _name = 'tt.reservation.offline.lines'

    pnr = fields.Char('PNR', readonly=True, states={'confirm': [('readonly', False)]})

    booking_id = fields.Many2one('tt.reservation.offline', 'Reservation Offline')
    obj_qty = fields.Integer('Qty', readonly=True, states={'draft': [('readonly', False)],
                                                           'confirm': [('readonly', False)]}, default=1)
    state = fields.Selection(STATE, string='State', default='draft', related='booking_id.state')
    transaction_type = fields.Many2one('tt.provider.type', 'Service Type', related='booking_id.provider_type_id')
    transaction_name = fields.Char('Service Name', readonly=True, related='booking_id.provider_type_name')
    provider_id = fields.Many2one('tt.provider', 'Provider ID', readonly=True, states={'confirm': [('readonly', False)]})

    # Airplane / Train
    departure_date = fields.Datetime('Departure Date', readonly=True, states={'draft': [('readonly', False)],
                                                                              'confirm': [('readonly', False)]})
    return_date = fields.Datetime('Return Date', readonly=True, states={'draft': [('readonly', False)],
                                                                        'confirm': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)],
                                                                                    'confirm': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True,
                                     states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    provider = fields.Char('Provider', readonly=True, required=True, states={'draft': [('readonly', False)],
                                                                             'confirm': [('readonly', False)]})

    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True)
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Class')
    subclass = fields.Char('SubClass')

    # Hotel / Activity
    visit_date = fields.Datetime('Visit Date', readonly=True, states={'draft': [('readonly', False)],
                                                                      'confirm': [('readonly', False)]})
    check_in = fields.Date('Check In', readonly=True, states={'draft': [('readonly', False)],
                                                              'confirm': [('readonly', False)]})
    check_out = fields.Date('Check Out', readonly=True, states={'draft': [('readonly', False)],
                                                                'confirm': [('readonly', False)]})
    obj_name = fields.Char('Name', related='provider', store=True)
    obj_subname = fields.Char('Room/Package', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})

    description = fields.Text('Description')

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id',
                                              'Cost Service Charges')

    @api.onchange('transaction_type', 'booking_id.provider_type_id')
    def onchange_domain(self):
        booking_type = self.booking_id.provider_type_id.code

        return {'domain': {
            'carrier_id': [('transport_type', '=', booking_type)]
        }}

    @api.onchange('carrier_id')
    def set_provider(self):
        for rec in self:
            rec.provider = rec.carrier_id.name

    def action_create_ledger(self):
        if not self.is_ledger_created:
            self.write({
                'is_ledger_created': True
            })
            self.env['tt.ledger'].action_create_ledger(self)
            self.env.cr.commit()

    def get_pnr_list(self):
        pnr_seen = set()
        pnr_uniq = []

        for prov in self:
            if prov.pnr not in pnr_seen:
                pnr_uniq.append(prov.pnr)
                pnr_seen.add(prov.pnr)

        pnr_to_str = ''
        for rec in pnr_uniq:
            pnr_to_str += rec + ' '
        return pnr_to_str

    def get_provider_list(self):
        provider_seen = set()
        provider_uniq = []

        for prov in self:
            if prov.provider not in provider_seen:
                provider_uniq.append(prov.provider)
                provider_seen.add(prov.provider)

        provider_to_str = ''
        for rec in provider_uniq:
            provider_to_str += rec + ' '
        return provider_to_str
