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
    _description = 'Issued Offline Lines'

    pnr = fields.Char('PNR',required=True)

    booking_id = fields.Many2one('tt.reservation.offline', 'Reservation Offline')
    obj_qty = fields.Integer('Qty', readonly=False, default=1)
    state = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state')
    state_offline = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state_offline')
    transaction_type = fields.Selection('tt.provider.type', 'Service Type', related='booking_id.offline_provider_type')
    transaction_name = fields.Char('Service Name', readonly=True, related='booking_id.provider_type_id_name')
    provider_id = fields.Many2one('tt.provider', 'Provider ID', readonly=False, domain="['|', ('provider_type_id.code', '=', transaction_type), ('provider_type_id.code', '=', 'offline')]")
    provider_name = fields.Char('Provider Name', compute='compute_provider_name', store=True)
    provider_type = fields.Char('Provider Type', related='provider_id.provider_type_id.code')

    # Airplane / Train
    departure_date = fields.Char('Departure Date', readonly=False)
    departure_hour = fields.Char('Departure Hour', readonly=False)
    departure_minute = fields.Char('Departure Minute', readonly=False)
    return_date = fields.Char('Return Date', readonly=False)
    arrival_date = fields.Char('Arrival Date', readonly=False)
    return_hour = fields.Char('Return Hour', readonly=False)
    return_minute = fields.Char('Return Minute', readonly=False)
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=False, domain="[('provider_type_id.code', '=', transaction_type)]")
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=False, domain="[('provider_type_id.code', '=', transaction_type)]")

    carrier_id = fields.Many2one('tt.transport.carrier', 'Carrier', readonly=False, domain="[('provider_type_id.code', '=', transaction_type)]")
    provider = fields.Char('Provider', readonly=False, required=False, states={'draft': [('required', False)],
                                                                               'pending': [('readonly', False)],
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
    cruise_package = fields.Char('Cruise Package', readonly=False)
    departure_location = fields.Char('Departure Location', readonly=False)
    arrival_location = fields.Char('Arrival Location', readonly=False)

    description = fields.Text('Description', readonly=False)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id',
                                              'Cost Service Charges')

    @api.onchange('provider_id')
    def compute_provider_name(self):
        for rec in self:
            if rec.provider_id.id != rec.env.ref('tt_reservation_offline.tt_provider_rodextrip_other').id:
                rec.provider_name = rec.provider_id.name

    @api.onchange('carrier_id')
    def set_provider(self):
        for rec in self:
            rec.provider = rec.carrier_id.name

    def action_create_ledger(self, use_point=False):
        if not self.is_ledger_created:
            self.write({
                'is_ledger_created': True
            })
            return self.env['tt.ledger'].action_create_ledger(self, use_point=use_point)

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
            vals += str(rec.arrival_date) + ' \n' if rec.arrival_date else ' \n'
            vals += rec.carrier_id.name + ' ' if rec.carrier_id else ' '
            vals += rec.carrier_code + ' ' if rec.carrier_code else ' '
            vals += rec.carrier_number + ' \n' if rec.carrier_number else ' \n'
        return vals

    def get_line_airline_train_description(self):
        vals = ''
        vals += self.origin_id.name + ' - ' if self.origin_id else ' - '
        vals += self.destination_id.name + ' \n' if self.destination_id else ' \n'
        vals += self.departure_date + ' ' if self.departure_date else ' '
        vals += self.departure_hour + ':' if self.departure_hour else ' '
        vals += self.departure_minute + ' - ' if self.departure_minute else ' - '
        vals += self.arrival_date + ' ' if self.arrival_date else ' '
        vals += self.return_hour + ':' if self.return_hour else ' '
        vals += self.return_minute + ' \n' if self.return_minute else ' \n'
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
        # vals += 'Passengers : \n' + str(self.get_passengers_list())
        # vals += 'Description : ' + self.description if self.description else 'Description : '
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

    def get_line_cruise_description(self):
        vals = ''
        vals += 'Cruise : ' + self.cruise_package + '\n' if self.cruise_package else 'Cruise : ' + '\n'
        vals += 'Room : ' + self.room + ' ' + str(self.obj_qty) + 'x\n' if self.room else 'Room : ' + '\n'
        vals += 'Date : ' + str(self.check_in) + ' - ' if self.check_in else 'Date : ' + ' - '
        vals += str(self.check_out) + '\n' if self.check_out else '' + '\n'
        vals += 'Passengers : \n' + str(self.get_passengers_list()) + '\n'
        vals += 'Description : ' + self.description if self.description else 'Description : '
        vals += '\n\n'
        return vals

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

    def get_other_line_description(self):
        vals = ''
        vals += 'Description : ' + self.description if self.description else 'Description : '
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
            vals = self.get_line_cruise_description()
        else:
            vals = self.get_other_line_description()
        return vals

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state_offline != 'draft':
                raise UserError(_('You cannot delete a line. You have to set state to draft.'))
        return super(IssuedOfflineLines, self).unlink()

    def to_dict(self):
        if self.transaction_type in ['airline', 'train']:
            return {
                'pnr': self.pnr if self.pnr else '',
                'origin': self.origin_id.name if self.origin_id.name else '',
                'destination': self.destination_id.name if self.destination_id.name else '',
                'departure_date': (self.departure_date if self.departure_date else '') + ' ' + (self.departure_hour if self.departure_hour else '') + ':' + (self.departure_minute if self.departure_minute else ''),
                'arrival_date': (self.arrival_date if self.arrival_date else '') + ' ' + (self.return_hour if self.return_hour else '') + ':' + (self.return_minute if self.return_minute else ''),
                'carrier': self.carrier_id.name if self.carrier_id.name else '',
                'carrier_code': self.carrier_code if self.carrier_code else '',
                'carrier_number': self.carrier_number if self.carrier_number else '',
                'class': dict(self._fields['class_of_service'].selection).get(self.class_of_service) if self.class_of_service else '',
                'subclass': self.subclass if self.subclass else '',
            }
        elif self.transaction_type == 'activity':
            return {
                'pnr': self.pnr if self.pnr else '',
                'activity_name': self.activity_name if self.activity_name else '',
                'activity_package': self.activity_package if self.activity_package else '',
                'visit_date': self.visit_date if self.visit_date else '',
                'description': self.description if self.description else '',
            }
        elif self.transaction_type == 'hotel':
            return {
                'pnr': self.pnr if self.pnr else '',
                'hotel_name': self.hotel_name if self.hotel_name else '',
                'room': self.room if self.room else '',
                'check_in': self.check_in if self.check_in else '',
                'check_out': self.check_out if self.check_out else '',
                'description': self.description if self.description else '',
            }
        elif self.transaction_type == 'cruise':
            return {
                'pnr': self.pnr if self.pnr else '',
                'carrier': self.carrier_id.name if self.carrier_id.name else '',
                'cruise_package': self.cruise_package if self.cruise_package else '',
                'departure_location': self.departure_location if self.departure_location else '',
                'arrival_location': self.arrival_location if self.arrival_location else '',
                'room': self.room if self.room else '',
                'check_in': self.check_in if self.check_in else '',
                'check_out': self.check_out if self.check_out else '',
                'description': self.description if self.description else ''
            }
        else:
            return {
                'pnr': self.pnr if self.pnr else '',
                'description': self.description if self.description else ''
            }
