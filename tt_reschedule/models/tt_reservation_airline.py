from odoo import api,models,fields, _
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback

_logger = logging.getLogger(__name__)


class ReservationAirline(models.Model):

    _inherit = "tt.reservation.airline"

    reschedule_ids = fields.One2many('tt.reschedule', 'res_id', 'After Sales', readonly=True)

    def create_reschedule_airline_api(self, vals, context):
        try:
            airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)
            if airline_obj:
                airline_obj = airline_obj[0]
                passenger_list = []
                for rec in airline_obj.passenger_ids:
                    passenger_list.append(rec.id)
                old_segment_list = []
                for rec in airline_obj.segment_ids:
                    old_segment_list.append(rec.id)
                new_segment_list = []
                for rec in vals['segments']:
                    temp_carrier_id = rec.get('carrier_code') and self.env['tt.transport.carrier'].sudo().search([('code', '=', rec['carrier_code'])], limit=1) or []
                    if temp_carrier_id:
                        temp_carrier_id = temp_carrier_id[0]
                    temp_provider_id = rec.get('provider_code') and self.env['tt.provider'].sudo().search([('code', '=', rec['provider_code'])], limit=1) or []
                    if temp_provider_id:
                        temp_provider_id = temp_provider_id[0]
                    temp_origin_id = rec.get('origin') and self.env['tt.destinations'].sudo().search([('code', '=', rec['origin'])], limit=1) or []
                    if temp_origin_id:
                        temp_origin_id = temp_origin_id[0]
                    temp_destination_id = rec.get('destination') and self.env['tt.destinations'].sudo().search([('code', '=', rec['destination'])], limit=1) or []
                    if temp_destination_id:
                        temp_destination_id = temp_destination_id[0]
                    new_seg_obj = self.env['tt.segment.reschedule'].sudo().create({
                        'segment_code': rec.get('segment_code', ''),
                        'pnr': rec.get('pnr', ''),
                        'fare_code': rec.get('fare_code', ''),
                        'carrier_id': temp_carrier_id.id,
                        'carrier_code': rec.get('carrier_code', ''),
                        'carrier_number': rec.get('carrier_number', ''),
                        'provider_id': temp_provider_id.id,
                        'origin_id': temp_origin_id.id,
                        'destination_id': temp_destination_id.id,
                        'origin_terminal': rec.get('origin_terminal', ''),
                        'destination_terminal': rec.get('destination_terminal', ''),
                        'departure_date': rec.get('departure_date', ''),
                        'arrival_date': rec.get('arrival_date', ''),
                        'class_of_service': rec.get('class_of_service', ''),
                        'cabin_class': rec.get('cabin_class', ''),
                        'sequence': rec.get('sequence', 0),
                    })
                    new_segment_list.append(new_seg_obj.id)

                res_vals = {
                    'agent_id': airline_obj.agent_id.id,
                    'customer_parent_id': airline_obj.customer_parent_id.id,
                    'booker_id': airline_obj.booker_id.id,
                    'currency_id': airline_obj.currency_id.id,
                    'service_type': airline_obj.provider_type_id.id,
                    'referenced_pnr': airline_obj.pnr,
                    'old_segment_ids': [(6, 0, old_segment_list)],
                    'new_segment_ids': [(6, 0, new_segment_list)],
                    'passenger_ids': [(6, 0, passenger_list)],
                    'res_model': airline_obj._name,
                    'res_id': airline_obj.id,
                    'notes': vals.get('notes') and vals['notes'] or '',
                    'created_by_api': True,
                }
                res_obj = self.env['tt.reschedule'].create(res_vals)
                res_obj.confirm_reschedule_from_button()
                final_res = {
                    'reschedule_number': res_obj.name
                }
                return ERR.get_no_error(final_res)
            else:
                raise RequestException(1001, additional_message="Airline reservation %s is not found in our system." % (vals['order_number']))
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1030)

    def update_reschedule_airline_api(self, vals, context):
        pass

    def test_get_reschedule_airline(self):
        vals = {
            'order_number': 'AL.20012224115'
        }
        context = {
            'co_uid': self.env.user.id,
            'co_agent_id': self.env.user.agent_id.id,
        }
        self.get_reschedule_airline_api(vals, context)

    def test_create_reschedule_airline(self):
        segment_list = [
            {
                'segment_code': 'SQ,933,CGK,2020-05-12 15:30:00,HKG,2020-05-12 17:45:00,amadeus',
                'pnr': 'TLHKL2',
                'fare_code': '1~0~E',
                'carrier_code': 'SQ',
                'carrier_number': '933',
                'provider_code': 'amadeus',
                'origin': 'CGK',
                'destination': 'HKG',
                'origin_terminal': 'Soekarno-Hatta Terminal 1',
                'destination_terminal': 'Chep Lap Kok Terminal 2',
                'departure_date': '2020-05-12 15:30:00',
                'arrival_date': '2020-05-12 17:45:00',
                'class_of_service': 'E1',
                'cabin_class': 'Economy',
                'sequence': 1,
            },
            {
                'segment_code': 'SQ,930,SIN,2020-05-17 07:50:00,SUB,2020-05-17 09:15:00,amadeus',
                'pnr': 'TLHKL3',
                'fare_code': '1~0~E',
                'carrier_code': 'SQ',
                'carrier_number': '930',
                'provider_code': 'amadeus',
                'origin': 'HKG',
                'destination': 'SIN',
                'origin_terminal': 'Chep Lap Kok Terminal 2',
                'destination_terminal': 'Changi Terminal 2',
                'departure_date': '2020-05-17 07:50:00',
                'arrival_date': '2020-05-17 09:15:00',
                'class_of_service': 'E2',
                'cabin_class': 'Economy',
                'sequence': 2,
            },
        ]
        vals = {
            'order_number': 'AL.20012224115',
            'segments':segment_list,
            'notes': 'Test Notes'
        }
        context = {
            'co_uid': self.env.user.id,
            'co_agent_id': self.env.user.agent_id.id,
        }
        self.create_reschedule_airline_api(vals, context)

    def get_reschedule_airline_api(self, vals, context):
        try:
            rs_list = []
            airline_obj = self.env['tt.reservation.airline'].search([('name', '=', vals['order_number'])], limit=1)
            if airline_obj:
                for rec in airline_obj.reschedule_ids:
                    rs_list.append(rec.get_reschedule_data())
            else:
                raise RequestException(1001, additional_message="Airline reservation %s is not found in our system." % (vals['order_number']))
            return ERR.get_no_error(rs_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1030)
