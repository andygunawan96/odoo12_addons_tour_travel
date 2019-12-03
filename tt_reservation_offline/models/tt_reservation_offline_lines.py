from odoo import models, fields, api, _

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('paid', 'Validate'),
    ('posted', 'Done'),
    ('refund', 'Refund'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
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

    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)],
                                                    'confirm': [('readonly', False)],
                                                    'paid': [('readonly', False)]})

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

    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True,
                               states={'draft': [('required', False)],
                                       'confirm': [('readonly', False)]})
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True,
                                 states={'draft': [('required', False)],
                                         'confirm': [('readonly', False)]})
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Class', states={'draft': [('required', False)],
                                                                           'confirm': [('readonly', False)]})
    subclass = fields.Char('SubClass', states={'draft': [('required', False)],
                                               'confirm': [('readonly', False)]})

    # Hotel / Activity / Cruise
    visit_date = fields.Date('Visit Date', readonly=True, states={'draft': [('readonly', False)],
                                                                  'confirm': [('readonly', False)]})
    check_in = fields.Date('Check In', readonly=True, states={'draft': [('readonly', False)],
                                                              'confirm': [('readonly', False)]})
    check_out = fields.Date('Check Out', readonly=True, states={'draft': [('readonly', False)],
                                                                'confirm': [('readonly', False)]})
    hotel_name = fields.Char('Name', readonly=True, states={'draft': [('readonly', False)],
                                                            'confirm': [('readonly', False)]})
    room = fields.Char('Room Type', readonly=True, states={'draft': [('readonly', False)],
                                                           'confirm': [('readonly', False)]})
    meal_type = fields.Char('Meal Type', states={'draft': [('readonly', False)],
                                                 'confirm': [('readonly', False)]})
    activity_name = fields.Char('Activity Name', readonly=True,
                                states={'draft': [('readonly', False)],
                                        'confirm': [('readonly', False)]})
    activity_package = fields.Char('Activity Package', readonly=True,
                                   states={'draft': [('readonly', False)],
                                           'confirm': [('readonly', False)]})
    activity_timeslot = fields.Char('Timeslot')
    cruise_name = fields.Char('Cruise Name', readonly=True, states={'draft': [('readonly', False)],
                                                                    'confirm': [('readonly', False)]})
    departure_location = fields.Char('Departure Location', readonly=True, states={'draft': [('readonly', False)],
                                                                                  'confirm': [('readonly', False)]})
    arrival_location = fields.Char('Arrival Location', readonly=True, states={'draft': [('readonly', False)],
                                                                              'confirm': [('readonly', False)]})

    description = fields.Text('Description')

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id',
                                              'Cost Service Charges')

    @api.onchange('transaction_type', 'booking_id.provider_type_id')
    def onchange_domain(self):
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

    # @api.depends('activity_name')
    # @api.onchange('activity_name')
    # def get_activity_package(self):
    #     for rec in self:
    #         rec.activity_package = ''
    #         if rec.activity_name:
    #             return {'domain': {
    #                 'activity_package': [('activity_id', '=', rec.activity_name.id)]
    #             }}

    # @api.depends('activity_package')
    # @api.onchange('activity_package')
    # def get_activity_timeslot(self):
    #     for rec in self:
    #         rec.activity_timeslot = ''
    #         if rec.activity_package:
    #             return {'domain': {
    #                 'activity_timeslot': [('product_type_id', '=', rec.activity_package.id)]
    #             }}

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
            passengers += str(psg_count) + '. ' + (rec.passenger_id.name if rec.passenger_id else '') + ' \n'
        return passengers

    def get_meal_type(self):
        if self.meal_type:
            return dict(self._fields['meal_type'].selection).get(self.meal_type)

    def get_all_line_airline_train_description(self):
        vals = ''
        for rec in self.booking_id.line_ids:
            vals += rec.origin_id.name + ' - ' if rec.origin_id else ' - '
            vals += rec.destination_id.name + ' \n' if rec.destination_id else ' \n'
            vals += str(rec.departure_date) + ' - ' if rec.departure_date else ' - '
            vals += str(rec.return_date) + ' \n' if rec.return_date else ' \n'
            vals += rec.carrier_id.name + ' ' if rec.carrier_id else ' '
            vals += rec.carrier_code + ' ' if rec.carrier_code else ' '
            vals += rec.carrier_number + ' \n' if rec.carrier_number else ' \n'
        return vals

    def get_line_airline_train_description(self):
        vals = ''
        vals += self.origin_id.name + ' - ' if self.origin_id else ' - '
        vals += self.destination_id.name + ' \n' if self.destination_id else ' \n'
        vals += str(self.departure_date) + ' - ' if self.departure_date else ' - '
        vals += str(self.return_date) + ' \n' if self.return_date else ' \n'
        vals += self.carrier_id.name + ' ' if self.carrier_id else ' '
        vals += self.carrier_code + ' ' if self.carrier_code else ' '
        vals += self.carrier_number + ' \n' if self.carrier_number else ' \n'
        return vals

    def get_line_hotel_description(self):
        vals = ''
        vals += 'Hotel : ' + self.hotel_name + '\n' if self.hotel_name else 'Hotel : ' + '\n'
        vals += 'Room : ' + self.room + ' (' + self.meal_type + ') ' + str(self.obj_qty) + 'x\n' if self.room else 'Room : ' + '\n'
        vals += 'Date : ' + str(self.check_in) + ' - ' if self.check_in else 'Date : - '
        vals += str(self.check_out) + '\n' if self.check_out else '\n'
        vals += 'Passengers : \n' + str(self.get_passengers_list())
        vals += 'Description : ' + self.description if self.description else 'Description : '
        return vals

    def get_all_line_hotel_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Hotel : ' + line.hotel_name + '\n' if line.hotel_name else 'Hotel : ' + '\n'
            vals += 'Room : ' + line.room + ' (' + line.meal_type + ') ' + str(line.obj_qty) + 'x\n' if line.room else 'Room : ' + '\n'
            vals += 'Date : ' + str(line.check_in) + ' - ' if line.check_in else 'Date : - '
            vals += str(line.check_out) + '\n' if line.check_out else '\n'
            vals += 'Passengers : \n' + str(self.get_passengers_list())
            vals += 'Description : ' + line.description if line.description else 'Description : '
        return vals

    def get_line_activity_description(self):
        vals = ''
        vals += 'Activity : ' + self.activity_name + '\n' if self.activity_name else 'Activity : ' + '\n'
        vals += 'Package : ' + self.activity_package + str(self.obj_qty) + 'x\n' if self.activity_package else 'Package : ' + '\n'
        vals += 'Date : ' + str(self.check_in) + '\n' if self.check_in else 'Date : ' + '\n'
        vals += 'Passengers : \n' + str(self.get_passengers_list())
        vals += 'Description : ' + self.description if self.description else 'Description : '
        return vals

    def get_all_line_activity_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Activity : ' + line.activity_name + '\n' if line.activity_name else 'Activity : ' + '\n'
            vals += 'Package : ' + line.activity_package + str(line.obj_qty) + 'x\n' if line.activity_package else 'Package : ' + '\n'
            vals += 'Date : ' + str(line.check_in) + '\n' if line.check_in else 'Date : ' + '\n'
            vals += 'Passengers : \n' + str(self.get_passengers_list())
            vals += 'Description : ' + line.description if line.description else 'Description : '
        return vals

    def get_line_cruise_description(self, line):
        vals = ''
        vals += 'Cruise : ' + line.cruise_name + '\n' if line.cruise_name else 'Cruise : ' + '\n'
        vals += 'Room : ' + line.room + ' ' + str(line.obj_qty) + 'x\n' if line.room else 'Room : ' + '\n'
        vals += 'Date : ' + str(line.check_in) + ' - ' if line.check_in else 'Date : ' + ' - '
        vals += str(line.check_out) + '\n' if line.check_out else '' + '\n'
        vals += 'Passengers : \n' + str(self.get_passengers_list())
        vals += 'Description : ' + line.description if line.description else 'Description : '

    def get_all_line_cruise_description(self):
        vals = ''
        for line in self.booking_id.line_ids:
            vals += 'Cruise : ' + line.cruise_name + '\n' if line.cruise_name else 'Cruise : ' + '\n'
            vals += 'Room : ' + line.room + ' ' if line.room else 'Room : '
            vals += str(line.obj_qty) + 'x\n' if line.obj_qty else '0x\n'
            vals += 'Date : ' + str(line.check_in) + ' - ' if line.check_in else 'Date : ' + ' - '
            vals += str(line.check_out) + '\n' if line.check_out else '' + '\n'
            vals += 'Passengers : \n' + str(self.get_passengers_list())
            vals += 'Description : ' + line.description if line.description else 'Description : '
        return vals

    def get_line_description(self):
        vals = ''
        if self.booking_id.provider_type_id_name == 'airline' or self.booking_id.provider_type_id_name == 'train':
            # vals = self.get_all_line_airline_train_description()
            vals = self.get_line_airline_train_description()
        # elif self.booking_id.provider_type_id_name == 'hotel':
        #     if self.booking_id.description:
        #         vals = 'Description : ' + self.booking_id.description
        elif self.booking_id.provider_type_id_name == 'activity':
            vals = self.get_line_activity_description()
        elif self.booking_id.provider_type_id_name == 'cruise':
            vals = self.get_all_line_cruise_description()
        return vals
