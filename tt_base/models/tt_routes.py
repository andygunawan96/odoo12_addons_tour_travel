from odoo import api, fields, models, _
import datetime
from ...tools.api import Response
import traceback

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

    def get_route_data(self):
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'origin_utc': self.origin_timezone_hour and self.origin_timezone_hour or 0,
            'destination_utc': self.destination_timezone_hour and self.destination_timezone_hour or 0,
            'origin_terminal': self.origin_terminal and self.origin_terminal or '',
            'destination_terminal': self.destination_terminal and self.destination_terminal or '',
            'departure_time': self.departure_time,
            'arrival_time': self.arrival_time,
            'operating_airline_code': self.operating_airline_code and self.operating_airline_code or '',
        }
        return res

    def get_all_routes_api(self, _provider_type, context):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id)])
            response = [rec.get_route_data() for rec in routes_obj]
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def get_all_routes_api_by_code(self, _provider_type, context):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id)])
            response = {}
            for rec in routes_obj:
                code = '%s%s%s' % (rec.carrier_code, rec.carrier_number, rec.origin)
                response[code] = rec.get_route_data()
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def get_routes_api_by_code(self, _carrier_codes, _provider_type, context):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id),
                                             ('carrier_code', 'in', _carrier_codes)])
            response = {}
            for rec in routes_obj:
                code = '%s%s%s' % (rec.carrier_code, rec.carrier_number, rec.origin)
                response[code] = rec.get_route_data()
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def update_route_api(self, req_data, context):
        try:
            _obj = self.sudo().search([('carrier_code', '=', req_data['carrier_code']),
                                       ('carrier_number', '=', req_data['carrier_number']),
                                       ('origin', '=', req_data['origin'])])
            if not _obj:
                _obj = self.sudo().create(req_data)

            _obj.write(req_data)
            return Response().get_no_error()
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)
