from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...tools import variables

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
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
                                                    'validate': [('readonly', False)]})

    booking_id = fields.Many2one('tt.reservation.offline', 'Reservation Offline')
    obj_qty = fields.Integer('Qty', readonly=False, default=1)
    state = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state')
    state_offline = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state_offline')
    transaction_type = fields.Selection('tt.provider.type', 'Service Type', related='booking_id.offline_provider_type')
    transaction_name = fields.Char('Service Name', readonly=True, related='booking_id.provider_type_id_name')
    provider_id = fields.Many2one('tt.provider', 'Provider ID', readonly=False)

    # Airplane / Train
    departure_date = fields.Char('Departure Date', readonly=False)
    return_date = fields.Char('Return Date', readonly=False)
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=False)
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=False)

    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', readonly=False)
    provider = fields.Char('Provider', readonly=False, required=False, states={'draft': [('required', False)],
                                                                              'confirm': [('readonly', False)]})

    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True, readonly=False)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True, readonly=False)
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Class', readonly=False)
    subclass = fields.Char('SubClass', readonly=False)

    # Hotel / Activity / Cruise
    visit_date = fields.Char('Visit Date', readonly=False)
    check_in = fields.Char('Check In', readonly=False)
    check_out = fields.Char('Check Out', readonly=False)
    hotel_name = fields.Char('Name', readonly=False)
    room = fields.Char('Room Type', readonly=False)
    meal_type = fields.Char('Meal Type', readonly=False)
    activity_name = fields.Char('Activity Name', readonly=False)
    activity_package = fields.Char('Activity Package', readonly=False)
    activity_timeslot = fields.Char('Timeslot', readonly=False)
    cruise_name = fields.Char('Cruise Name', readonly=False)
    departure_location = fields.Char('Departure Location', readonly=False)
    arrival_location = fields.Char('Arrival Location', readonly=False)

    description = fields.Text('Description', readonly=False)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id',
                                              'Cost Service Charges')

    @api.onchange('booking_id.offline_provider_type')
    def onchange_domain(self):
        provider_type_id = self.env['tt.provider.type'].search([('code', '=', self.booking_id.offline_provider_type)], limit=1)
        return {'domain': {
            'carrier_id': [('provider_type_id', '=', provider_type_id.id)],
            'origin_id': [('provider_type_id', '=', provider_type_id.id)],
            'destination_id': [('provider_type_id', '=', provider_type_id.id)],
            'provider_id': [('provider_type_id', '=', provider_type_id.id)]
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
            passengers += str(psg_count) + '. ' + (rec.first_name if rec.first_name else '') + ' ' +\
                          (rec.last_name if rec.last_name else '') + ' \n'
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
        vals += 'Room : ' + (self.room if self.room else '') + ' (' + (self.meal_type if self.meal_type else '') + ') ' + str(self.obj_qty) + 'x\n'
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

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot delete a line. You have to set state to draft.'))
        return super(IssuedOfflineLines, self).unlink()
