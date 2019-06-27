from odoo import api, fields, models, _
import datetime

TRANSPORT_TYPE = [('airline', 'Airline'),
                  ('train', 'Train'),
                  ('ship', 'Ship'),
                  ('cruise', 'Cruise'),
                  ('car', 'Car/Rent'),
                  ('bus', 'Bus')]


class Routes(models.Model):
    _name = 'tt.routes'

    name = fields.Char('Name', help="Usage for flight number, train name", required=True)
    # route_number = fields.Char('Route Number', required=True)
    # type = fields.Selection(TRANSPORT_TYPE, string='Route Type')
    provider_type_id = fields.Many2one(comodel_name='tt.provider.type', string='Provider Type')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Transport Carrier Code', help='or Flight Code', index=True)
    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True)
    operating_airline_code = fields.Char('Operated By')
    code_share = fields.Char('Codeshare', help='Y if this flight is a codeshare (that is, not operated by'
                                              'Airline, but another carrier), empty otherwise.')

    origin_id = fields.Many2one('tt.destinations', string='Origin', required=True, ondelete='restrict')
    origin = fields.Char('Origin IATA Code', related='origin_id.code', store=True)
    origin_timezone_hour = fields.Float('Origin Timezone Hour',related='origin_id.timezone_hour')
    origin_terminal = fields.Char('Terminal Number')
    destination_id = fields.Many2one('tt.destinations', string='Destination', store=True)
    destination = fields.Char('Destination IATA Code', related='destination_id.code')
    destination_timezone_hour = fields.Float('Origin Timezone Hour', related='destination_id.timezone_hour')
    destination_terminal = fields.Char('Terminal Number')

    leg_ids = fields.One2many('tt.routes.leg', 'route_id', 'Legs')

    #analyze later
    # stops = fields.Integer('Stops', help='Number of stops on this flight (0 for direct')
    # equipment_type = fields.Char('Equipment', help='3-letter codes for plane type(s) generally used on this'
    #                                           'flight, separated by spaces')

    departure_time = fields.Char('Departure Time')
    arrival_time = fields.Char('Arrival Time')
    elapsed_time = fields.Char('Elapsed Time')

    # transport_type = fields

    def get_route(self, carrier_code, carrier_number, origin, destination):
        route = self.search([('carrier_code', '=', carrier_code),('carrier_number', '=', carrier_number)])
        if not route:
            return False
        elif len(route) > 1:
            return route.filtered(lambda x: x.origin == origin and x.destination == destination)
        else:
            return route[0]

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'carrier_code': self.carrier_code.to_dict(),
            'carrier_code_str': self.carrier_code,
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code,
            'code_share': self.code_share,
            'origin': self.origin_id.to_dict(),
            'origin_str': self.origin,
            'origin_timezone_hour': self.origin_timezone_hour,
            'origin_terminal': self.origin_terminal,
            'destination': self.destination_id.to_dict(),
            'destination_str': self.destination,
            'destination_timezone_hour': self.destination_timezone_hour,
            'destination_terminal': self.destination_terminal,
            'departure_time': self.departure_time,
            'arrival_time': self.arrival_time,
        }

    # def get_route(self,):


class RoutesLeg(models.Model):
    _name = 'tt.routes.leg'

    route_id = fields.Many2one(comodel_name='tt.routes', string='Route')
    origin_id = fields.Many2one('tt.destinations', string='Origin', required=True, ondelete='restrict')
    origin = fields.Char('Origin IATA Code', related='origin_id.code', store=True)
    origin_timezone_hour = fields.Float('Origin Timezone Hour', related='origin_id.timezone_hour')
    origin_terminal = fields.Char('Terminal Number')
    destination_id = fields.Many2one('tt.destinations', string='Destination', store=True)
    destination = fields.Char('Destination IATA Code', related='destination_id.code')
    destination_timezone_hour = fields.Float('Origin Timezone Hour', related='destination_id.timezone_hour')
    destination_terminal = fields.Char('Terminal Number')
    departure_time = fields.Char('Departure Time')
    arrival_time = fields.Char('Arrival Time')
    elapsed_time = fields.Char('Elapsed Time')
