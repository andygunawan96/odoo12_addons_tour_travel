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

CLASS_OF_SERVICE_TRAIN = [
    ('eko', 'Ekonomi'),
    ('bus', 'Bisnis'),
    ('eks', 'Eksekutif')
]

MEAL_TYPE = [
    ('room_only', 'Room Only'),
    ('with_breakfast', 'With Breakfast')
]


class IssuedOfflineLines(models.Model):
    _name = 'tt.reservation.offline.lines'
    _description = 'Rodex Model'

    pnr = fields.Char('PNR', readonly=True, states={'confirm': [('readonly', False)]})

    booking_id = fields.Many2one('tt.reservation.offline', 'Reservation Offline')
    obj_qty = fields.Integer('Qty', readonly=True, states={'draft': [('readonly', False)],
                                                           'confirm': [('readonly', False)]}, default=1)
    state = fields.Selection(STATE, string='State', default='draft', related='booking_id.state')
    transaction_type = fields.Many2one('tt.provider.type', 'Service Type', related='booking_id.provider_type_id')
    transaction_name = fields.Char('Service Name', readonly=True, related='booking_id.provider_type_id_name')
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
    provider = fields.Char('Provider', readonly=True, required=False, states={'draft': [('required', False)],
                                                                              'confirm': [('readonly', False)]})

    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True)
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Class')
    subclass = fields.Char('SubClass')

    # Hotel / Activity / Cruise
    visit_date = fields.Datetime('Visit Date', readonly=True, states={'draft': [('readonly', False)],
                                                                      'confirm': [('readonly', False)]})
    check_in = fields.Date('Check In', readonly=True, states={'draft': [('readonly', False)],
                                                              'confirm': [('readonly', False)]})
    check_out = fields.Date('Check Out', readonly=True, states={'draft': [('readonly', False)],
                                                                'confirm': [('readonly', False)]})
    hotel_name = fields.Char('Name', readonly=True, states={'draft': [('readonly', False)],
                                                            'confirm': [('readonly', False)]})
    room = fields.Char('Room', readonly=True, states={'draft': [('readonly', False)],
                                                      'confirm': [('readonly', False)]})
    activity_name = fields.Many2one('tt.master.activity', 'Activity Name', readonly=True,
                                    states={'draft': [('readonly', False)],
                                            'confirm': [('readonly', False)]})
    activity_package = fields.Many2one('tt.master.activity.lines', 'Activity Package', readonly=True,
                                       states={'draft': [('readonly', False)],
                                               'confirm': [('readonly', False)]})
    cruise_name = fields.Char('Cruise Name', readonly=True, states={'draft': [('readonly', False)],
                                                                    'confirm': [('readonly', False)]})
    departure_location = fields.Char('Departure Location', readonly=True, states={'draft': [('readonly', False)],
                                                                                  'confirm': [('readonly', False)]})
    arrival_location = fields.Char('Arrival Location', readonly=True, states={'draft': [('readonly', False)],
                                                                              'confirm': [('readonly', False)]})

    description = fields.Text('Description')
    meal_type = fields.Selection(MEAL_TYPE, 'Meal Type')

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id',
                                              'Cost Service Charges')

    @api.onchange('transaction_type', 'booking_id.provider_type_id')
    def onchange_domain(self):
        print('Provider Type ID : ' + str(self.booking_id.provider_type_id_name))
        booking_type = self.booking_id.provider_type_id.code

        return {'domain': {
            'carrier_id': [('provider_type_id', '=', self.booking_id.provider_type_id.id)],
            'origin_id': [('provider_type_id', '=', self.booking_id.provider_type_id.id)],
            'destination_id': [('provider_type_id', '=', self.booking_id.provider_type_id.id)],
            'provider_id': [('provider_type_id', '=', self.booking_id.provider_type_id.id)]
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

    def get_passengers_list(self):
        passengers = ''
        psg_count = 0
        for rec in self.booking_id.passenger_ids:
            psg_count += 1
            passengers += str(psg_count) + '. ' + rec.passenger_id.name + ' \n'
        return passengers

    def get_meal_type(self):
        if self.meal_type:
            return dict(self._fields['meal_type'].selection).get(self.meal_type)

    def get_all_line_airline_train_description(self):
        vals = ''
        for rec in self.booking_id.line_ids:
            vals += rec.origin_id.name + ' - ' + rec.destination_id.name + ' \n' + str(rec.departure_date) + ' ' + \
                    str(rec.return_date) + ' \n' + rec.carrier_id.name + ' ' + rec.carrier_code + ' ' + \
                    rec.carrier_number + ' \n'
        return vals

    def get_line_hotel_description(self, line):
        vals = ''
        vals += 'Hotel : ' + line.hotel_name + '\n' + 'Room : ' + line.room + ' (' + line.get_meal_type() + ') ' \
                + str(line.obj_qty) + 'x\n' + 'Date : ' + str(line.check_in) + ' - ' + str(line.check_out) + '\n' + \
                'Passengers : \n' + str(self.get_passengers_list()) + 'Description : ' + line.description
        return vals

    def get_all_line_hotel_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Hotel : ' + line.hotel_name + '\n' + 'Room : ' + line.room + ' (' + line.get_meal_type() + \
                    ') ' + str(line.obj_qty) + 'x\n' + 'Date : ' + str(line.check_in) + ' - ' + str(line.check_out) + \
                    '\n' + 'Passengers : \n' + str(self.get_passengers_list()) + 'Description : ' + line.description
        return vals

    def get_line_activity_description(self, line):
        vals = ''
        vals += 'Activity : ' + line.activity_name + '\n' + 'Package : ' + line.activity_package + \
                ' ' + str(line.obj_qty) + 'x\n' + 'Date : ' + str(line.check_in) + '\n' \
                + 'Passengers : \n' + str(self.get_passengers_list()) + 'Description : ' + (line.description or '')
        return vals

    def get_all_line_activity_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Activity : ' + line.activity_name.name + '\n' + 'Package : ' + line.activity_package.name + \
                    ' ' + str(line.obj_qty) + 'x\n' + 'Date : ' + str(line.check_in) + '\n' \
                    + 'Passengers : \n' + str(self.get_passengers_list()) + 'Description : ' + (line.description or '')
        return vals

    def get_line_cruise_description(self, line):
        vals = ''
        vals += 'Cruise : ' + line.cruise_name + '\n' + 'Room : ' + line.room + ' ' + str(line.obj_qty) + 'x\n' + \
                'Date : ' + str(line.check_in) + ' - ' + str(line.check_out) + '\n' + 'Passengers : \n' + \
                str(self.get_passengers_list()) + 'Description : ' + (line.description or '')

    def get_all_line_cruise_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Cruise : ' + line.cruise_name + '\n' + 'Room : ' + line.room + ' ' + str(line.obj_qty) + 'x\n' + \
                    'Date : ' + str(line.check_in) + ' - ' + str(line.check_out) + '\n' + 'Passengers : \n' + \
                    str(self.get_passengers_list()) + 'Description : ' + (line.description or '')
        return vals

    def get_line_description(self):
        vals = ''
        if self.booking_id.provider_type_id_name == 'airline' or self.booking_id.provider_type_id_name == 'train':
            vals = self.get_all_line_airline_train_description()
        elif self.booking_id.provider_type_id_name == 'hotel':
            vals = 'Description : ' + self.booking_id.description
        elif self.booking_id.provider_type_id_name == 'activity':
            vals = self.get_all_line_activity_description()
        elif self.booking_id.provider_type_id_name == 'cruise':
            vals = self.get_all_line_cruise_description()
        return vals
