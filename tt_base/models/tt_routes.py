from odoo import api, fields, models, _
from datetime import datetime
from ...tools.api import Response
from ...tools import ERR
import logging
import traceback
from ...tools.db_connector import GatewayConnector

_logger = logging.getLogger(__name__)
_gw_con = GatewayConnector()


class Routes(models.Model):
    _name = 'tt.routes'
    _description = 'Rodex Model'

    name = fields.Char('Name', help="Usage for flight number, train name", compute='_compute_name', store=True)
    provider_type_id = fields.Many2one(comodel_name='tt.provider.type', string='Provider Type', required=True)
    carrier_id = fields.Many2one('tt.transport.carrier', 'Transport Carrier Code', help='or Flight Code', index=True, required=True)
    carrier_name = fields.Char('Carrier Name', related='carrier_id.name', store=True)
    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True, required=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True, required=True)
    operating_airline_code = fields.Char('Operated By', default='')
    origin_id = fields.Many2one('tt.destinations', string='Origin')
    origin = fields.Char('Origin IATA Code', related='origin_id.code', index=True, store=True)
    origin_utc = fields.Float('Origin Timezone Hour', related='origin_id.timezone_hour', store=True)
    destination_id = fields.Many2one('tt.destinations', string='Destination', store=True)
    destination = fields.Char('Destination IATA Code', related='destination_id.code', index=True, store=True)
    destination_utc = fields.Float('Origin Timezone Hour', related='destination_id.timezone_hour', store=True)
    departure_time = fields.Char('Departure Time', required=True)
    arrival_time = fields.Char('Arrival Time', required=True)

    @api.depends('carrier_name', 'carrier_code', 'carrier_number')
    def _compute_name(self):
        for rec in self:
            data = rec.get_data()
            rec.name = '{carrier_name} - {carrier_code} {carrier_number}'.format(**data)

    def get_data(self):
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'origin_utc': self.origin_utc and self.origin_utc or 0,
            'destination_utc': self.destination_utc and self.destination_utc or 0,
            'departure_time': self.departure_time,
            'arrival_time': self.arrival_time,
            'carrier_name': self.carrier_name,
            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code and self.operating_airline_code or '',
        }
        return res

    def update_route_api(self, req_data, provider_type):
        try:
            schedules = req_data.get('schedules', [])
            provider_type_obj = self.env['tt.provider.type'].sudo().search([('code', '=', provider_type)], limit=1)
            if not provider_type_obj:
                raise Exception('Provider Type Object not found, %s' % provider_type)
            for sch in schedules:
                if len(sch['journey_list']) > 1 or not sch['journeys']:
                    continue
                provider = sch['provider']
                journey_data = sch['journey_list'][0]
                schedule_env = self.env['tt.routes.schedule'].sudo()
                schedule_obj = schedule_env.search([('origin', '=', journey_data['origin']),
                                                   ('destination', '=', journey_data['destination']),
                                                   ('departure_date', '=', journey_data['departure_date']),
                                                   ('provider_type_id', '=', provider_type_obj.id),
                                                   ('provider', '=', provider)], limit=1)
                if not schedule_obj:
                    schedule_obj = schedule_env.create({
                        'provider_type_id': provider_type_obj.id
                    })

                for journey in sch['journeys']:
                    journey_env = self.env['tt.routes.journey'].sudo()
                    journey_obj = journey_env.search([('route_code', '=', journey['route_code']),
                                                      ('schedule_id', '=', schedule_obj.id)], limit=1)
                    if not journey_obj:
                        journey_obj = journey_env.create({
                            'schedule_id': schedule_obj.id,
                            'route_code': journey['route_code'],
                            'journey_code': journey['journey_code'],
                        })
                    for seg in journey['segments']:
                        seg_env = self.env['tt.routes.segment'].sudo()
                        seg_obj = seg_env.search([('route_code', '=', seg['route_code']),
                                                  ('journey_id', '=', journey_obj.id)], limit=1)
                        if not seg_obj:
                            seg_obj = seg_env.create({
                                'journey_id': journey_obj.id,
                                'route_code': seg['route_code'],
                                'segment_code': seg['segment_code'],
                            })
                        for leg in seg['legs']:
                            leg_env = self.env['tt.routes.leg'].sudo()
                            leg_obj = leg_env.search([('route_code', '=', leg['route_code']),
                                                      ('segment_id', '=', seg_obj.id)], limit=1)
                            if not leg_obj:
                                route_obj = self.sudo().search([('carrier_code', '=', leg['carrier_code']),
                                                                ('carrier_number', '=', leg['carrier_number']),
                                                                ('origin', '=', leg['origin']),
                                                                ('destination', '=', leg['destination'])], limit=1)
                                if not route_obj:
                                    carrier_env = self.carrier_id.with_context(active_test=False).sudo()
                                    carrier_obj = carrier_env.search([('code', '=', leg['carrier_code'])], limit=1)
                                    if not carrier_obj:
                                        carrier_values = {
                                            'name': leg['carrier_code'],
                                            'code': leg['carrier_code'],
                                            'provider_type_id': provider_type_obj.id
                                        }
                                        carrier_obj = carrier_env.create(carrier_values)

                                    destination_env = self.origin_id.with_context(active_test=False).sudo()
                                    origin_obj = destination_env.search([('code', '=', leg['origin'])], limit=1)
                                    if not origin_obj:
                                        origin_values = {
                                            'name': leg['origin'],
                                            'code': leg['origin'],
                                            'provider_type_id': provider_type_obj.id,
                                            'timezone_hour': leg.get('origin_utc', 0),
                                            'city': ''
                                        }
                                        origin_obj = destination_env.create(origin_values)

                                    destination_obj = destination_env.search([('code', '=', leg['destination'])], limit=1)
                                    if not destination_obj:
                                        destination_values = {
                                            'name': leg['destination'],
                                            'code': leg['destination'],
                                            'provider_type_id': provider_type_obj.id,
                                            'timezone_hour': leg.get('destination_utc', 0),
                                            'city': ''
                                        }
                                        destination_obj = destination_env.create(destination_values)

                                    route_values = {
                                        'carrier_id': carrier_obj.id,
                                        'origin_id': origin_obj.id,
                                        'destination_id': destination_obj.id,
                                        'carrier_code': leg['carrier_code'],
                                        'carrier_number': leg['carrier_number'],
                                        'operating_airline_code': leg['operating_airline_code'],
                                        'departure_time': datetime.strptime(leg['departure_date'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M'),
                                        'arrival_time': datetime.strptime(leg['arrival_date'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M'),
                                        'provider_type_id': provider_type_obj.id,
                                    }
                                    route_obj = self.sudo().create(route_values)
                                leg_values = {
                                    'route_id': route_obj.id,
                                    'origin_terminal': leg.get('origin_terminal', ''),
                                    'destination_terminal': leg.get('destination_terminal', ''),
                                    'departure_date': leg['departure_date'],
                                    'arrival_date': leg['arrival_date'],
                                    'provider': leg['provider'],
                                    'segment_id': seg_obj.id
                                }
                                leg_obj = leg_env.create(leg_values)
                            try:
                                if leg_obj.leg_code != leg['leg_code'] or leg_obj.origin_terminal != leg['origin_terminal'] or leg_obj.destination_terminal != leg['destination_terminal']:
                                    leg_obj.write({
                                        'departure_date': leg['departure_date'],
                                        'arrival_date': leg['arrival_date'],
                                        'origin_terminal': leg.get('origin_terminal', ''),
                                        'destination_terminal': leg.get('destination_terminal', ''),
                                        'leg_code': leg['leg_code'],
                                        'route_code': leg['route_code'],
                                    })
                            except:
                                _logger.error('Error Update Leg, %s' % traceback.format_exc())

                        for fare in seg['fares']:
                            fare_env = self.env['tt.routes.fare'].sudo()
                            fare_obj = fare_env.search([('class_of_service', '=', fare['class_of_service']), ('segment_id', '=' , seg_obj.id)], limit=1)
                            if not fare_obj:
                                fare_values = {
                                    'cabin_class': fare['cabin_class'],
                                    'class_of_service': fare['class_of_service'],
                                    'available_count': fare['available_count'],
                                    'fare_name': fare['fare_name'],
                                    'fare_class': fare['fare_class'],
                                    'fare_code': fare['fare_code'],
                                    'fare_basis_code': fare['fare_basis_code'],
                                    'segment_id': seg_obj.id
                                }
                                fare_obj = fare_env.create(fare_values)

                            if fare_obj.fare_basis_code != fare['fare_basis_code'] or fare_obj.fare_code != fare['fare_code'] or fare_obj.available_count != fare['available_count']:
                                fare_obj.write({
                                    'fare_basis_code': fare['fare_basis_code'],
                                    'fare_code': fare['fare_code'],
                                    'available_count': fare['available_count'],
                                })

                            fare_pax_env = self.env['tt.routes.pax.fare'].sudo()
                            for sc_sum in fare['service_charge_summary']:
                                fare_pax_obj = fare_pax_env.search([('pax_type', '=', sc_sum['pax_type']),
                                                                    ('fare_id', '=', fare_obj.id)], limit=1)
                                sc_env = self.env['tt.routes.service.charge'].sudo()
                                if not fare_pax_obj:
                                    fare_pax_obj = fare_pax_env.create({
                                        'pax_type': sc_sum['pax_type'],
                                        'fare_id': fare_obj.id,
                                        'fare_amount': sc_sum['total_fare'],
                                        'tax_amount': sc_sum['total_tax'],
                                        'total_amount': sc_sum['total_price'],
                                    })
                                    for sc in sc_sum['service_charges']:
                                        sc_env.create({
                                            'charge_code': sc['charge_code'],
                                            'charge_type': sc['charge_type'],
                                            'currency': sc['currency'],
                                            'amount': sc['amount'],
                                            'foreign_currency': sc['foreign_currency'],
                                            'foreign_amount': sc['foreign_amount'],
                                            'pax_type': sc['pax_type'],
                                            'pax_fare_id': fare_pax_obj.id,
                                        })

                                if fare_pax_obj.total_amount == sc_sum['total_price']:
                                    continue

                                fare_pax_obj.service_charge_ids.unlink()
                                for sc in sc_sum['service_charges']:
                                    sc_env.create({
                                        'charge_code': sc['charge_code'],
                                        'charge_type': sc['charge_type'],
                                        'currency': sc['currency'],
                                        'amount': sc['amount'],
                                        'foreign_currency': sc['foreign_currency'],
                                        'foreign_amount': sc['foreign_amount'],
                                        'pax_type': sc['pax_type'],
                                        'pax_fare_id': fare_pax_obj.id,
                                    })
                                try:
                                    fare_pax_obj.write({
                                        'fare_amount': sc_sum['total_fare'],
                                        'tax_amount': sc_sum['total_tax'],
                                        'total_amount': sc_sum['total_price'],
                                    })
                                except:
                                    _logger.error('Error Update Fare Pax, %s' % traceback.format_exc())

                            # FIXME
                            # fare_detail_env = fare_obj.fare_detail_ids.sudo()
                            # for det in fare['fare_details']:
                            #     fare_detail_env.create({
                            #         'detail_code': det['detail_code'],
                            #         'detail_type': det['detail_type'],
                            #         'amount': det['amount'],
                            #         'unit': det['unit'],
                            #         'detail_name': det['detail_name'],
                            #         'fare_id': fare_obj.id,
                            #     })
                        if not seg_obj.destination or seg_obj.segment_code != seg['segment_code']:
                            try:
                                seg_obj._compute_data()
                            except:
                                _logger.error('Error Compute Data Segment, %s' % traceback.format_exc())
                    if not journey_obj.destination or journey_obj.journey_code != journey['journey_code']:
                        try:
                            journey_obj._compute_data()
                        except:
                            _logger.error('Error Compute Data Journey, %s' % traceback.format_exc())
                if not schedule_obj.schedule_code:
                    try:
                        schedule_obj._compute_data()
                    except:
                        _logger.error('Error Compute Data Schedule, %s' % traceback.format_exc())
            return ERR.get_no_error()
        except Exception as e:
            _logger.error('Error Update Routes API, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message='Error Update Routes API')

    def get_route_schedule_api(self, req_data, provider_type):
        try:
            schedules = []
            for rec_id, rec in enumerate(req_data['journey_list']):
                schedule_code = '%s,%s,%s,%s,%s' % (rec['origin'], rec['destination'], rec['departure_date'], provider_type, req_data['provider'])
                schedule_obj = self.env['tt.routes.schedule'].sudo().search([('schedule_code', '=', schedule_code)], limit=1)
                if not schedule_obj:
                    raise Exception('Schedule not found, %s' % schedule_code)
                schedule_values = schedule_obj.get_data(False)
                for journey in schedule_obj.journey_ids:
                    if not req_data['carrier_codes'] or any(rec in journey.carrier_code_list for rec in req_data['carrier_codes']):
                        schedule_values['journeys'].append(journey.get_data())
                schedules.append(schedule_values)
            response = {
                'schedules': schedules
            }
            return ERR.get_no_error(response)
        except Exception as e:
            _logger.error('Error Get Route Schedule API, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message='Error Get Route Schedule API')

    def get_segment_route_api(self, req_data, provider_type):
        try:
            param = [
                ('origin', '=', req_data['origin']),
                ('destination', '=', req_data['destination']),
                ('carrier_code', '=', req_data['carrier_code']),
                ('carrier_number', '=', req_data['carrier_number']),
                ('departure_date', '=', req_data['departure_date']),
                ('arrival_date', '=', req_data['arrival_date']),
                ('provider', '=', req_data['provider']),
            ]
            segment_obj = None
            segment_env = self.env['tt.routes.segment'].sudo()
            for i in range(1):
                segment_obj = segment_env.search(param, limit=1)
                if segment_obj:
                    break
                param.pop()
            if not segment_obj:
                raise Exception('Segment Route Not Found')
            legs = [leg.get_data() for leg in segment_obj.leg_ids]
            segment = segment_obj.get_data(False)
            segment.update({'legs': legs})
            return ERR.get_no_error(segment)
        except Exception as e:
            _logger.error('Error Get Segment Route API, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message='Error Get Segment Route API')


class RoutesLeg(models.Model):
    _name = 'tt.routes.leg'
    # _rec_name = 'Leg'
    # _description = 'Leg'
    _order = 'departure_date'

    name = fields.Char('Name', compute='_compute_name', store=True)
    route_id = fields.Many2one('tt.routes', required=True)
    carrier_name = fields.Char('Carrier Name', related='route_id.carrier_name', store=True)
    carrier_code = fields.Char('Carrier Code', related='route_id.carrier_code', store=True)
    carrier_number = fields.Char('Carrier Number', related='route_id.carrier_number', store=True)
    operating_airline_code = fields.Char('Operating Airline Code', related='route_id.operating_airline_code', store=True)
    origin = fields.Char('Origin', related='route_id.origin', store=True)
    origin_utc = fields.Float('Origin UTC', related='route_id.origin_utc', store=True)
    destination = fields.Char('Destination', related='route_id.destination', store=True)
    destination_utc = fields.Float('Destination UTC', related='route_id.destination_utc', store=True)
    origin_terminal = fields.Char('Origin Terminal', default='')
    destination_terminal = fields.Char('Destination Terminal', default='')
    departure_date = fields.Char('Departure Date', required=True, help='Format YYYY-mm-dd HH:MM:SS')
    departure_time = fields.Char('Departure Time', related='route_id.departure_time', store=True)
    arrival_date = fields.Char('Arrival Date', required=True, help='Format YYYY-mm-dd HH:MM:SS')
    arrival_time = fields.Char('Arrival Time', related='route_id.arrival_time', store=True)
    leg_code = fields.Char('Leg Code', default='')
    route_code = fields.Char('Route Code', default='')
    provider = fields.Char('Provider', required=True)
    segment_id = fields.Many2one('tt.routes.segment', 'Segment', ondelete='cascade')

    @api.depends('carrier_code', 'carrier_number', 'origin', 'destination', 'departure_date')
    def _compute_name(self):
        for rec in self:
            data = rec.get_data()
            rec.name = '{carrier_code} {carrier_number} - {origin} {destination} - {departure_date}'.format(**data)

    def get_data(self):
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'origin_utc': self.origin_utc and self.origin_utc or 0,
            'destination_utc': self.destination_utc and self.destination_utc or 0,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code,
            'origin_terminal': self.origin_terminal,
            'destination_terminal': self.destination_terminal,
            'provider': self.provider,
        }
        return res


class RoutesSegment(models.Model):
    _name = 'tt.routes.segment'
    # _rec_name = 'Segment'
    # _description = 'Segment'

    name = fields.Char('Name', compute='_compute_name', store=True)
    leg_ids = fields.One2many('tt.routes.leg', 'segment_id', 'Legs')
    fare_ids = fields.One2many('tt.routes.fare', 'segment_id', 'Fares')
    carrier_name = fields.Char('Carrier Name', related='leg_ids.carrier_name', store=True)
    carrier_code = fields.Char('Carrier Code', related='leg_ids.carrier_code', store=True)
    carrier_number = fields.Char('Carrier Number', related='leg_ids.carrier_number', store=True)
    operating_airline_code = fields.Char('Operating Airline Code', related='leg_ids.operating_airline_code', store=True)
    provider = fields.Char('Provider', related='leg_ids.provider', store=True)
    origin = fields.Char('Origin', compute='_compute_data', store=True)
    origin_terminal = fields.Char('Origin Terminal')
    origin_utc = fields.Float('Origin UTC')
    departure_date = fields.Char('Departure Date')
    destination = fields.Char('Destination')
    destination_terminal = fields.Char('Destination Terminal')
    destination_utc = fields.Float('Destination UTC')
    arrival_date = fields.Char('Arrival Date')
    segment_code = fields.Char('Segment Code', default='')
    route_code = fields.Char('Route Code', default='')
    journey_id = fields.Many2one('tt.routes.journey', 'Journey', ondelete='cascade')

    @api.depends('carrier_code', 'carrier_number', 'origin', 'destination', 'departure_date')
    def _compute_name(self):
        for rec in self:
            data = rec.get_data(False)
            rec.name = '{carrier_code} {carrier_number} - {origin} {destination} - {departure_date}'.format(**data)

    def get_data(self, is_child=True):
        legs = []
        fares = []
        if is_child:
            legs = [rec.get_data() for rec in self.leg_ids]
            fares = [rec.get_data() for rec in self.fare_ids]
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'origin_utc': self.origin_utc and self.origin_utc or 0,
            'destination_utc': self.destination_utc and self.destination_utc or 0,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'carrier_code': self.carrier_code,
            'carrier_number': self.carrier_number,
            'operating_airline_code': self.operating_airline_code,
            'origin_terminal': self.origin_terminal,
            'destination_terminal': self.destination_terminal,
            'segment_code': self.segment_code and self.segment_code or '',
            'provider': self.provider and self.provider or '',
            'legs': legs,
            'fares': fares,
        }
        return res

    @api.depends('leg_ids')
    def _compute_data(self):
        for rec in self:
            values = {
                'origin': '',
                'origin_terminal': '',
                'origin_utc': '',
                'departure_date': '',
                'destination': '',
                'destination_terminal': '',
                'destination_utc': '',
                'arrival_date': '',
            }
            if rec.leg_ids:
                values = {
                    'origin': rec.leg_ids[0].origin,
                    'origin_terminal': rec.leg_ids[0].origin_terminal,
                    'origin_utc': rec.leg_ids[0].origin_utc,
                    'departure_date': rec.leg_ids[0].departure_date,
                    'destination': rec.leg_ids[-1].destination,
                    'destination_terminal': rec.leg_ids[-1].destination_terminal,
                    'destination_utc': rec.leg_ids[-1].destination_utc,
                    'arrival_date': rec.leg_ids[-1].arrival_date,
                }
            rec.update(values)


class RoutesJourney(models.Model):
    _name = 'tt.routes.journey'

    name = fields.Char('Name', compute='_compute_name', store=True)
    segment_ids = fields.One2many('tt.routes.segment', 'journey_id', 'Segments')
    provider = fields.Char('Provider', related='segment_ids.provider', store=True)
    origin = fields.Char('Origin', compute='_compute_data', store=True)
    origin_terminal = fields.Char('Origin Terminal')
    origin_utc = fields.Float('Origin UTC')
    departure_date = fields.Char('Departure Date')
    destination = fields.Char('Destination')
    destination_terminal = fields.Char('Destination Terminal')
    destination_utc = fields.Float('Destination UTC')
    arrival_date = fields.Char('Arrival Date')
    journey_code = fields.Char('Journey Code')
    route_code = fields.Char('Route Code')
    carrier_code_list = fields.Char('Carrier Code List')
    operating_airline_code_list = fields.Char('Operating Airline Code List')
    schedule_id = fields.Many2one('tt.routes.schedule', 'Schedule', ondelete='cascade')

    @api.depends('origin', 'destination', 'departure_date')
    def _compute_name(self):
        for rec in self:
            data = rec.get_data(False)
            rec.name = '{origin} {destination} - {departure_date}'.format(**data)

    def get_data(self, is_child=True):
        segments = [rec.get_data() for rec in self.segment_ids] if is_child else []
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'origin_utc': self.origin_utc and self.origin_utc or 0,
            'destination_utc': self.destination_utc and self.destination_utc or 0,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'origin_terminal': self.origin_terminal,
            'destination_terminal': self.destination_terminal,
            'journey_code': self.journey_code and self.journey_code or '',
            'provider': self.provider and self.provider or '',
            'segments': segments
        }
        return res

    @api.depends('segment_ids')
    def _compute_data(self):
        for rec in self:
            values = {
                'origin': '',
                'origin_terminal': '',
                'origin_utc': '',
                'departure_date': '',
                'destination': '',
                'destination_terminal': '',
                'destination_utc': '',
                'arrival_date': '',
                'carrier_code_list': '',
                'operating_airline_code_list': '',
            }
            if rec.segment_ids:
                carrier_code_list = []
                operating_airline_code_list = []
                for seg in rec.segment_ids:
                    if seg.carrier_code and seg.carrier_code not in carrier_code_list:
                        carrier_code_list.append(seg.carrier_code)
                    if seg.operating_airline_code and seg.operating_airline_code not in operating_airline_code_list:
                        operating_airline_code_list.append(seg.operating_airline_code)
                values = {
                    'origin': rec.segment_ids[0].origin,
                    'origin_terminal': rec.segment_ids[0].origin_terminal,
                    'origin_utc': rec.segment_ids[0].origin_utc,
                    'departure_date': rec.segment_ids[0].departure_date,
                    'destination': rec.segment_ids[-1].destination,
                    'destination_terminal': rec.segment_ids[-1].destination_terminal,
                    'destination_utc': rec.segment_ids[-1].destination_utc,
                    'arrival_date': rec.segment_ids[-1].arrival_date,
                    'carrier_code_list': ','.join(carrier_code_list),
                    'operating_airline_code_list': ','.join(operating_airline_code_list),
                }
            rec.update(values)


class RoutesSchedule(models.Model):
    _name = 'tt.routes.schedule'

    name = fields.Char('Name', default='')
    journey_ids = fields.One2many('tt.routes.journey', 'schedule_id', 'Journeys')
    schedule_code = fields.Char('Schedule Code', default='')
    origin = fields.Char('Origin', related='journey_ids.origin', store=True)
    destination = fields.Char('Destination', related='journey_ids.destination', store=True)
    departure_date = fields.Char('Departure Date', compute='_compute_departure_date', store=True)
    provider = fields.Char('Provider', related='journey_ids.provider', store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

    @api.depends('journey_ids', 'origin', 'destination')
    def _compute_data(self):
        for rec in self:
            values = {
                'name': '',
                'schedule_code': '',
                'departure_date': '',
            }
            if rec.journey_ids:
                departure_date = str(rec.journey_ids[0].departure_date)[:10]
                values = {
                    'name': '%s %s - %s' % (rec.origin, rec.destination, departure_date),
                    'schedule_code': '%s,%s,%s,%s,%s' % (rec.origin, rec.destination, departure_date, rec.provider_type_id.code, rec.provider),
                    'departure_date': departure_date,
                }
            rec.update(values)

    def get_data(self, is_child=True):
        journeys = [rec.get_data() for rec in self.journey_ids] if is_child else []
        res = {
            'origin': self.origin,
            'destination': self.destination,
            'departure_date': self.departure_date,
            'schedule_code': self.schedule_code and self.schedule_code or '',
            'provider': self.provider,
            'journeys': journeys
        }
        return res


class RoutesFare(models.Model):
    _name = 'tt.routes.fare'

    name = fields.Char('Name', compute='_compute_name', store=True)
    cabin_class = fields.Char('Cabin Class', default='')
    class_of_service = fields.Char('Class of Service', default='')
    fare_code = fields.Char('Fare Code', default='')
    fare_basis_code = fields.Char('Fare Basis Code', default='')
    available_count = fields.Integer('Available Count', default=-1)
    fare_class = fields.Char('Fare Class', default='')
    fare_name = fields.Char('Fare Name', default='')
    segment_id = fields.Many2one('tt.routes.segment', 'Segment', ondelete='cascade')
    fare_detail_ids = fields.One2many('tt.routes.fare.detail', 'fare_id', 'Fare Details')
    pax_fare_ids = fields.One2many('tt.routes.pax.fare', 'fare_id', 'Pax Fares')

    def _compute_name(self):
        for rec in self:
            temp = rec.get_data(False)
            rec.name = '{class_of_service}'.format(**temp)

    def get_data(self, is_child=True):
        fare_details = []
        pax_fares = []
        if is_child:
            fare_details = [rec.get_data() for rec in self.fare_detail_ids]
            pax_fares = [rec.get_data() for rec in self.pax_fare_ids]
        res = {
            'cabin_class': self.cabin_class and self.cabin_class or '',
            'class_of_service': self.class_of_service and self.class_of_service or '',
            'fare_code': self.fare_code and self.fare_code or '',
            'fare_basis_code': self.fare_basis_code and self.fare_basis_code or '',
            'available_count': self.available_count,
            'fare_class': self.fare_class and self.fare_class or '',
            'fare_name': self.fare_name and self.fare_name or '',
            'fare_details': fare_details,
            'pax_fares': pax_fares,
        }
        return res


class RoutesFareDetail(models.Model):
    _name = 'tt.routes.fare.detail'

    name = fields.Char('Name', compute='_compute_name', store=True)
    detail_code = fields.Char('Detail Code', default='')
    detail_type = fields.Char('Detail Type', default='')
    amount = fields.Char('Detail Amount', default='')
    unit = fields.Char('Unit', default='')
    description = fields.Char('Description', default='')
    detail_name = fields.Char('Detail Name', default='')
    fare_id = fields.Many2one('tt.routes.fare', 'Fare', ondelete='cascade')

    def _compute_name(self):
        for rec in self:
            temp = rec.get_data()
            rec.name = '{detail_code}-{detail_type}'.format(**temp)

    def get_data(self):
        res = {
            'detail_code': self.detail_code and self.detail_code or '',
            'detail_type': self.detail_type and self.detail_type or '',
            'amount': self.amount,
            'unit': self.unit and self.unit or '',
            'description': self.description and self.description or '',
            'detail_name': self.detail_name and self.detail_name or '',
        }
        return res


class RoutesPaxFare(models.Model):
    _name = 'tt.routes.pax.fare'

    name = fields.Char('Name', compute='_compute_name', store=True)
    pax_type = fields.Char('Pax Type', default='')
    fare_amount = fields.Float('Fare Amount', default=0)
    tax_amount = fields.Float('Tax Amount', default=0)
    total_amount = fields.Float('Total Amount', default=0)
    fare_id = fields.Many2one('tt.routes.fare', 'Fare', ondelete='cascade')
    service_charge_ids = fields.One2many('tt.routes.service.charge', 'pax_fare_id', 'Service Charges')

    def _compute_name(self):
        for rec in self:
            temp = rec.get_data(False)
            rec.name = '{pax_type}'.format(**temp)

    def get_data(self, is_child=True):
        service_charges = [rec.get_data() for rec in self.service_charge_ids] if is_child else []
        res = {
            'pax_type': self.pax_type and self.pax_type or '',
            'fare_amount': self.fare_amount and self.fare_amount or '',
            'tax_amount': self.tax_amount and self.tax_amount or '',
            'total_amount': self.total_amount and self.total_amount or '',
            'service_charges': service_charges
        }
        return res


class RoutesServiceCharge(models.Model):
    _name = 'tt.routes.service.charge'

    name = fields.Char('Name', compute='_compute_name', store=True)
    charge_code = fields.Char('Charge Code', default='')
    charge_type = fields.Char('Charge Type', default='')
    currency = fields.Char('Currency', default='')
    amount = fields.Float('Amount', default=0)
    foreign_currency = fields.Char('Foreign Currency', default='')
    foreign_amount = fields.Float('Foreign Amount', default=0)
    pax_type = fields.Char('Pax Type', default='')
    pax_fare_id = fields.Many2one('tt.routes.pax.fare', 'Pax Fare', ondelete='cascade')

    def _compute_name(self):
        for rec in self:
            temp = rec.get_data()
            rec.name = '{charge_type}-{charge_code}'.format(**temp)

    def get_data(self):
        res = {
            'charge_code': self.charge_code and self.charge_code or '',
            'charge_type': self.charge_type and self.charge_type or '',
            'currency': self.currency and self.currency or '',
            'amount': self.amount,
            'foreign_currency': self.foreign_currency and self.foreign_currency or '',
            'foreign_amount': self.foreign_amount,
            'pax_type': self.pax_type and self.pax_type or '',
        }
        return res
