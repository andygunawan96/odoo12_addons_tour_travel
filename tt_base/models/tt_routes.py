from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from ...tools.api import Response
from ...tools import ERR
import logging
import traceback
from ...tools.timer import Timer

_logger = logging.getLogger(__name__)
_UPDATE_TIME = 300 # 5 x 60 seconds


class Routes(models.Model):
    _name = 'tt.routes'
    _inherit = 'tt.history'
    _description = 'Routes Model'

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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 424')
        return super(Routes, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 425')
        return super(Routes, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 426')
        return super(Routes, self).unlink()

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
            for i in range(2):
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

    def get_schedule_update_permission_api(self, req_data, provider_type):
        try:
            schedule_env = self.env['tt.routes.schedule'].sudo()
            is_permitted = False
            for rec in req_data['journey_list']:
                schedule_code = '%s,%s,%s,%s,%s' % (rec['origin'], rec['destination'], rec['departure_date'], provider_type, req_data['provider'])
                schedule_obj = schedule_env.search([('schedule_code', '=', schedule_code)], limit=1)
                if not schedule_obj:
                    is_permitted = True
                    break
                last_update = schedule_obj.write_date + timedelta(seconds=_UPDATE_TIME)
                if datetime.now() > last_update:
                    is_permitted = True
                    break
            payload = {'is_permitted': is_permitted}
            return ERR.get_no_error(payload)
        except Exception as e:
            _logger.error('Error Get Schedule Update Permission API, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message='Error Get Schedule Update Permission API')

    def get_fare_detail_api(self, req_data, provider_type):
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
            class_of_service = req_data['class_of_service']
            segment_obj = None
            segment_env = self.env['tt.routes.segment'].sudo()
            for i in range(2):
                segment_obj = segment_env.search(param, limit=1)
                if segment_obj:
                    break
                param.pop()
            if not segment_obj:
                raise Exception('Segment Route Not Found')
            legs = [leg.get_data() for leg in segment_obj.leg_ids]
            fares = [fare.get_data() for fare in segment_obj.fare_ids if fare.class_of_service == class_of_service]
            segment = segment_obj.get_data(False)
            segment.update({
                'legs': legs,
                'fares': fares,
            })
            return ERR.get_no_error(segment)
        except Exception as e:
            _logger.error('Error Get Fare Detail Route API, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message='Error Get Fare Detail Route API')


class RoutesLeg(models.Model):
    _name = 'tt.routes.leg'
    # _rec_name = 'Leg'
    _description = 'Routes Leg'
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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 427')
        return super(RoutesLeg, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 428')
        return super(RoutesLeg, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 429')
        return super(RoutesLeg, self).unlink()

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
    _description = 'Routes Segment'

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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 430')
        return super(RoutesSegment, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 431')
        return super(RoutesSegment, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 432')
        return super(RoutesSegment, self).unlink()

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
    _description = 'Routes Journey'

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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 433')
        return super(RoutesJourney, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 434')
        return super(RoutesJourney, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 435')
        return super(RoutesJourney, self).unlink()

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
    _description = 'Routes Schedule'

    name = fields.Char('Name', default='')
    journey_ids = fields.One2many('tt.routes.journey', 'schedule_id', 'Journeys')
    schedule_code = fields.Char('Schedule Code', default='')
    origin = fields.Char('Origin', related='journey_ids.origin', store=True)
    destination = fields.Char('Destination', related='journey_ids.destination', store=True)
    departure_date = fields.Char('Departure Date', compute='_compute_departure_date', store=True)
    provider = fields.Char('Provider', related='journey_ids.provider', store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 436')
        return super(RoutesSchedule, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 437')
        return super(RoutesSchedule, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 438')
        return super(RoutesSchedule, self).unlink()

    def test_button(self):
        import json
        import copy
        schedule_id = 146
        departure_date = '2019-12-30'
        # res = self.env.cr.execute("select test_function(%s)", (schedule_id,))
        # res = self.env.cr.dictfetchall()
        # print("TRIAL HERE : %s" % json.dumps(res))
        # temp = res
        _TIMER = Timer('Execute SQL')
        self.env.cr.execute('''
            SELECT 
                -- Schedule
                sch.id schedule_id,
                sch.schedule_code schedule_schedule_code,
                sch.origin schedule_origin,
                sch.destination schedule_destination,
                sch.departure_date schedule_departure_date,
                -- Journey
                jr.id journey_id,
                jr.origin journey_origin,
                jr.origin_terminal journey_origin_terminal,
                jr.origin_utc journey_origin_utc,
                jr.destination journey_destination,
                jr.destination_terminal journey_destination_terminal,
                jr.destination_utc journey_destination_utc,
                jr.departure_date journey_departure_date,
                jr.arrival_date journey_arrival_date,
                jr.journey_code journey_journey_code,
                jr.route_code journey_route_code,
                jr.provider journey_provider,
                -- Segment
                sg.id segment_id,
                sg.origin segment_origin,
                sg.origin_terminal segment_origin_terminal,
                sg.origin_utc segment_origin_utc,
                sg.destination segment_destination,
                sg.destination_terminal segment_destination_terminal,
                sg.destination_utc segment_destination_utc,
                sg.departure_date segment_departure_date,
                sg.arrival_date segment_arrival_date,
                sg.carrier_code segment_carrier_code,
                sg.operating_airline_code segment_operating_airline_code,
                sg.carrier_number segment_carrier_number,
                sg.segment_code segment_segment_code,
                sg.route_code segment_route_code,
                sg.provider segment_provider,
                -- Leg
                lg.id leg_id,
                lg.origin leg_origin,
                lg.origin_terminal leg_origin_terminal,
                lg.origin_utc leg_origin_utc,
                lg.destination leg_destination,
                lg.destination_terminal leg_destination_terminal,
                lg.destination_utc leg_destination_utc,
                lg.departure_date leg_departure_date,
                lg.arrival_date leg_arrival_date,
                lg.carrier_code leg_carrier_code,
                lg.operating_airline_code leg_operating_airline_code,
                lg.carrier_number leg_carrier_number,
                lg.leg_code leg_leg_code,
                lg.route_code leg_route_code,
                lg.provider leg_provider,
                -- Fare
                fr.id fare_id,
                fr.class_of_service fare_class_of_service,
                fr.cabin_class fare_cabin_class,
                fr.fare_code fare_fare_code,
                fr.fare_basis_code fare_fare_basis_code,
                fr.available_count fare_available_count,
                fr.fare_class fare_fare_class,
                fr.fare_name fare_fare_name,
                -- Pax Fare
                pf.id paxfare_id,
                pf.pax_type paxfare_pax_type,
                pf.fare_amount paxfare_fare_amount,
                pf.tax_amount paxfare_tax_amount,
                pf.total_amount paxfare_total_amount,
                -- Service Charge
                sc.id servicecharge_id,
                sc.charge_code servicecharge_charge_code,
                sc.charge_type servicecharge_charge_type,
                sc.currency servicecharge_currency,
                sc.amount servicecharge_amount
            FROM tt_routes_schedule sch
            LEFT JOIN tt_routes_journey jr ON jr.schedule_id=sch.id
            LEFT JOIN tt_routes_segment sg ON sg.journey_id=jr.id
            LEFT JOIN tt_routes_leg lg ON lg.segment_id=sg.id
            LEFT JOIN tt_routes_fare fr ON fr.segment_id=sg.id
            LEFT JOIN tt_routes_pax_fare pf ON pf.fare_id=fr.id
            LEFT JOIN tt_routes_service_charge sc ON sc.pax_fare_id=pf.id
            WHERE sch.departure_date='%s';
        ''' % departure_date)
        res = self.env.cr.dictfetchall()
        schedule_dict = {}

        def extract_data(data):
            extract_result = {}
            for key, val in data.items():
                temp = key.split('_')
                extract_key = temp[0]
                data_key = '_'.join(temp[1:])
                if not extract_result.get(extract_key):
                    extract_result[extract_key] = {}
                extract_result[extract_key][data_key] = val
            return extract_result

        def set_data(_data, _key, _obj):
            obj_id = _data[_key]['id']
            dict_name = '%s_dict' % _key
            if not _obj.get(dict_name):
                _obj[dict_name] = {}
            if not _obj[dict_name].get(obj_id):
                _obj[dict_name][obj_id] = _data[_key]
            res_obj = _obj[dict_name][obj_id]
            return res_obj

        def key_parser(_key):
            lib = {
                'schedule': 'schedules',
                'journey': 'journeys',
                'segment': 'segments',
                'leg': 'legs',
                'fare': 'fares',
                'paxfare': 'pax_fares',
                'servicecharge': 'service_charges',
            }
            return lib[_key]

        def get_data(data_dict):
            for data_key, data_val in copy.deepcopy(data_dict).items():
                if not data_val:
                    data_dict[data_key] = ''
                if '_dict' not in data_key:
                    continue
                data_dict.pop(data_key)
                temp_list = [value_val for value_val in data_val.values()]
                temp_list.sort(key=lambda i: i['id'])
                for temp_rec in temp_list:
                    temp_rec = get_data(temp_rec)
                label = key_parser(data_key.split('_')[0])
                data_dict[label] = temp_list

            return data_dict

        for rec in res:
            rec_data = extract_data(rec)
            keys = ['schedule', 'journey', 'segment', 'fare', 'paxfare', 'servicecharge']
            payload_obj = schedule_dict
            for key in keys:
                payload_obj = set_data(rec_data, key, payload_obj)
                if key == 'segment':
                    set_data(rec_data, 'leg', payload_obj)

        payload = get_data(schedule_dict)
        _TIMER.stop()

        _TIMER2 = Timer('Odoo Object')
        odoo_data = self.search([('departure_date', '=', departure_date)])
        test2 = [rec.get_data() for rec in odoo_data]
        test2_res = {
            'schedules': test2
        }
        _TIMER2.stop()
        # print('TRIAL HERE : %s' % json.dumps(schedule_dict))
        # print('TRIAL 2 HERE : %s' % json.dumps(payload))
        # _file = open('/var/log/tour_travel/test.txt', 'w')
        # _file.write(json.dumps(payload))
        # _file.close()

        # _file2 = open('/var/log/tour_travel/test2.txt', 'w')
        # _file2.write(json.dumps(test2_res))
        # _file2.close()
        # print('DONE')

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
    _description = 'Routes Fare'

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

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 439')
        return super(RoutesFare, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 440')
        return super(RoutesFare, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 441')
        return super(RoutesFare, self).unlink()

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
    _description = 'Routes Fare Detail'

    name = fields.Char('Name', compute='_compute_name', store=True)
    detail_code = fields.Char('Detail Code', default='')
    detail_type = fields.Char('Detail Type', default='')
    amount = fields.Char('Detail Amount', default='')
    unit = fields.Char('Unit', default='')
    description = fields.Char('Description', default='')
    detail_name = fields.Char('Detail Name', default='')
    fare_id = fields.Many2one('tt.routes.fare', 'Fare', ondelete='cascade')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 442')
        return super(RoutesFareDetail, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 443')
        return super(RoutesFareDetail, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 444')
        return super(RoutesFareDetail, self).unlink()

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
    _description = 'Routes Pax Fare'

    name = fields.Char('Name', compute='_compute_name', store=True)
    pax_type = fields.Char('Pax Type', default='')
    fare_amount = fields.Float('Fare Amount', default=0)
    tax_amount = fields.Float('Tax Amount', default=0)
    total_amount = fields.Float('Total Amount', default=0)
    fare_id = fields.Many2one('tt.routes.fare', 'Fare', ondelete='cascade')
    service_charge_ids = fields.One2many('tt.routes.service.charge', 'pax_fare_id', 'Service Charges')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 445')
        return super(RoutesPaxFare, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 446')
        return super(RoutesPaxFare, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 447')
        return super(RoutesPaxFare, self).unlink()

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
    _description = 'Routes Service Charge'

    name = fields.Char('Name', compute='_compute_name', store=True)
    charge_code = fields.Char('Charge Code', default='')
    charge_type = fields.Char('Charge Type', default='')
    currency = fields.Char('Currency', default='')
    amount = fields.Float('Amount', default=0)
    foreign_currency = fields.Char('Foreign Currency', default='')
    foreign_amount = fields.Float('Foreign Amount', default=0)
    pax_type = fields.Char('Pax Type', default='')
    pax_fare_id = fields.Many2one('tt.routes.pax.fare', 'Pax Fare', ondelete='cascade')

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 448')
        return super(RoutesServiceCharge, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 449')
        return super(RoutesServiceCharge, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 450')
        return super(RoutesServiceCharge, self).unlink()

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
