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
    provider_type_id = fields.Many2one(comodel_name='tt.provider.type', string='Provider Type', required=True)
    carrier_id = fields.Many2one('tt.transport.carrier', 'Transport Carrier Code', help='or Flight Code', index=True, required=True)
    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True, required=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True, required=True)
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

    departure_time = fields.Char('Departure Time', required=True)
    arrival_time = fields.Char('Arrival Time', required=True)
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

    def get_object(self):
        res = {
            'name': self.name,
            'provider_type_id': self.provider_type_id and self.provider_type_id.id,
            'carrier_id': self.carrier_id and self.carrier_id.id,
            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code,
            'code_share': self.code_share,
            'origin_id': self.origin_id and self.origin_id.id,
            'origin': self.origin,
            'origin_timezone_hour': self.origin_timezone_hour,
            'origin_terminal': self.origin_terminal,
            'destination_id': self.destination_id and self.destination_id.id,
            'destination': self.destination,
            'destination_timezone_hour': self.destination_timezone_hour,
            'destination_terminal': self.destination_terminal,
            'departure_time': self.departure_time,
            'arrival_time': self.arrival_time,
        }
        return res

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'carrier_code': self.carrier_code.to_dict(),
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code,
            'code_share': self.code_share,
            'origin': self.origin_id.to_dict(),
            'origin_timezone_hour': self.origin_timezone_hour,
            'origin_terminal': self.origin_terminal,
            'destination': self.destination_id.to_dict(),
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

    def get_all_routes_api(self, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id)])
            response = [rec.get_route_data() for rec in routes_obj]
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def get_all_routes_api_by_code(self, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id)])
            response = {}
            for rec in routes_obj:
                code = '%s%s%s%s' % (rec.carrier_code, rec.carrier_number, rec.origin, rec.destination)
                response[code] = rec.get_route_data()
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def get_routes_api_by_code(self, _carrier_codes, _provider_type):
        try:
            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', _provider_type)], limit=1)
            routes_obj = self.sudo().search([('provider_type_id', '=', provider_obj.id),
                                             ('carrier_code', 'in', _carrier_codes)])
            response = {}
            for rec in routes_obj:
                code = '%s%s%s%s' % (rec.carrier_code, rec.carrier_number, rec.origin, rec.destination)
                response[code] = rec.get_route_data()
            return Response().get_no_error(response)
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def update_route_api(self, req_data, provider_type):
        try:
            mandatory_fields = ['origin', 'destination', 'departure_time', 'arrival_time', 'carrier_code', 'carrier_number']

            keys = [rec for rec in req_data.keys()]
            diff_fields = list(set(mandatory_fields).difference(keys))
            if diff_fields:
                raise Exception('Missing Mandatory fields')

            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            _obj = self.sudo().search([('carrier_code', '=', req_data['carrier_code']),
                                       ('carrier_number', '=', req_data['carrier_number']),
                                       ('origin', '=', req_data['origin']), ('destination', '=', req_data['destination']),
                                       ('provider_type_id', '=', provider_obj.id)])

            if not _obj:
                raise Exception('Data not Found')

            _obj.write(req_data)
            return Response().get_no_error()
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def create_route_api(self, req_data, provider_type):
        try:
            mandatory_fields = ['origin', 'destination', 'departure_time', 'arrival_time', 'carrier_code', 'carrier_number']

            keys = [rec for rec in req_data.keys()]
            diff_fields = list(set(mandatory_fields).difference(keys))
            if diff_fields:
                raise Exception('Missing Mandatory fields')

            provider_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            _obj = self.sudo().search([('carrier_code', '=', req_data['carrier_code']),
                                       ('carrier_number', '=', req_data['carrier_number']),
                                       ('origin', '=', req_data['origin']), ('destination', '=', req_data['destination']),
                                       ('provider_type_id', '=', provider_obj.id)])

            if _obj:
                raise Exception('Data already exist')

            origin_id = self.env['tt.destinations'].sudo().get_id(req_data['origin'], provider_obj)
            if not origin_id:
                origin_values = {
                    'name': req_data['origin'],
                    'code': req_data['origin'],
                    'provider_type_id': provider_obj.id,
                    'timezone_hour': req_data.get('origin_timezone_hour', 0),
                }
                origin_obj = self.env['tt.destinations'].sudo().create(origin_values)
                origin_id = origin_obj.id

            destination_id = self.env['tt.destinations'].sudo().get_id(req_data['destination'], provider_obj)
            if not destination_id:
                destination_values = {
                    'name': req_data['destination'],
                    'code': req_data['destination'],
                    'provider_type_id': provider_obj.id,
                    'timezone_hour': req_data.get('destination_timezone_hour', 0),
                }
                destination_obj = self.env['tt.destinations'].sudo().create(destination_values)
                destination_id = destination_obj.id

            carrier_id = self.env['tt.transport.carrier'].sudo().get_id(req_data['carrier_code'], provider_obj)
            if not carrier_id:
                carrier_values = {
                    'name': req_data['carrier_code'],
                    'code': req_data['carrier_code'],
                    'provider_type_id': provider_obj.id,
                }
                carrier_obj = self.env['tt.destinations'].sudo().create(carrier_values)
                carrier_id = carrier_obj.id

            req_data.update({
                'origin_id': origin_id,
                'destination_id': destination_id,
                'carrier_id': carrier_id,
                'provider_type_id': provider_obj.id,
            })
            req_data['name'] = '{carrier_code} {carrier_number} - {origin}'.format(**req_data)
            data = self.sudo().create(req_data)
            data.merge_route()
            return Response().get_no_error()
        except Exception as e:
            error_msg = '%s, %s' % (str(e), traceback.format_exc())
            return Response().get_error(error_msg, 500)

    def merge_route(self):
        _obj = self.sudo().search([('carrier_code', '=', self.carrier_code),
                                   ('carrier_number', '=', self.carrier_number)])
        if len(_obj) <= 1:
            return True

        _obj = sorted(_obj, key=lambda i: i.departure_time)
        del_ids = []
        for idx, rec in enumerate(_obj):
            if idx < 1:
                continue
            temp = _obj[idx-1]
            if temp.origin == rec.origin:
                values = {
                    'name': rec.name,
                    'provider_type_id': rec.provider_type_id and rec.provider_type_id.id,
                    'carrier_id': rec.carrier_id and rec.carrier_id.id,
                    'carrier_code': rec.carrier_code,
                    'carrier_number': rec.carrier_number,
                    'operating_airline_code': rec.operating_airline_code,
                    'code_share': rec.code_share,
                    'origin_id': temp.destination_id and temp.destination_id.id,
                    'origin': temp.destination,
                    'origin_timezone_hour': temp.destination_timezone_hour,
                    'origin_terminal': temp.destination_terminal,
                    'destination_id': rec.destination_id and rec.destination_id.id,
                    'destination': rec.destination,
                    'destination_timezone_hour': rec.destination_timezone_hour,
                    'destination_terminal': rec.destination_terminal,
                    'departure_time': temp.arrival_time,
                    'arrival_time': rec.arrival_time,
                }
            elif temp.destination == rec.destination:
                values = {
                    'name': rec.name,
                    'provider_type_id': rec.provider_type_id and rec.provider_type_id.id,
                    'carrier_id': rec.carrier_id and rec.carrier_id.id,
                    'carrier_code': rec.carrier_code,
                    'carrier_number': rec.carrier_number,
                    'operating_airline_code': rec.operating_airline_code,
                    'code_share': rec.code_share,
                    'origin_id': temp.origin_id and temp.origin_id.id,
                    'origin': temp.origin,
                    'origin_timezone_hour': temp.origin_timezone_hour,
                    'origin_terminal': temp.origin_terminal,
                    'destination_id': rec.origin_id and rec.origin_id.id,
                    'destination': rec.origin,
                    'destination_timezone_hour': rec.origin_timezone_hour,
                    'destination_terminal': rec.origin_terminal,
                    'departure_time': temp.departure_time,
                    'arrival_time': rec.departure_time,
                }
            else:
                continue

            del_ids.append(rec)
            self.sudo().create(values)

        for rec in del_ids:
            rec.unlink()
