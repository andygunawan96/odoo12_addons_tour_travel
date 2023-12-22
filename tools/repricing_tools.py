import logging, traceback
import json, copy
from datetime import datetime, timedelta
from math import ceil, floor
from odoo.http import request
from .destination_tools import DestinationToolsV2 as DestinationTools
from decimal import Decimal
from . import util


_logger = logging.getLogger(__name__)
FORMAT_DATETIME = '%Y-%m-%d %H:%M:%S'


class RepricingTools(object):
    def __init__(self, provider_type, provider='', origin='', origin_country='', destination='', destination_country='', carrier_code_list=[], context=None, is_filter=False, is_set_pricing=False, **kwargs):
        self.provider_type = provider_type
        self.provider = provider
        self.origin = origin
        self.origin_country = origin_country
        self.destination = destination
        self.origin_country = destination_country
        self.carrier_code_list = carrier_code_list
        self.context = context
        self.is_filter = is_filter
        self.pricing_providers = self.get_and_update_provider_repricing_data()
        self.pricing_agents = self.get_and_update_agent_repricing_data()
        self.destination_tools = DestinationTools(provider_type)
        self.provider_pricing_dict = {}
        self.agent_pricing_dict = {}
        self._do_config()

    def _do_config(self):
        agent_type_code = ''
        agent_id = ''
        if self.context:
            agent_type_code = self.context['co_agent_type_code']
            agent_id = self.context['co_agent_id']

        if self.is_filter:
            self.filter_pricing_providers(provider=self.provider, carrier_code_list=self.carrier_code_list, agent_type_code=agent_type_code, agent_id=agent_id)
            self.filter_pricing_agents(provider=self.provider, origin=self.origin, destination=self.destination, carrier_code_list=self.carrier_code_list, agent_type_code=agent_type_code, agent_id=agent_id)

    def validate(self):
        if not self.provider_type:
            err_msg = 'Provider type for repricing is mandatory'
            _logger.error(err_msg)
            raise Exception(err_msg)
        return True

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        if not agent_data:
            res = round(data)
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def get_datetime_now(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def get_and_update_provider_repricing_data(self):
        self.validate()
        res = request.env['tt.pricing.provider'].sudo().get_pricing_provider_api(self.provider_type)
        if res['error_code'] != 0:
            _logger.error('Error Get Pricing Provider Data Backend, %s' % res['error_msg'])
            return []

        new_data = res['response']['pricing_providers']
        return new_data

    def get_and_update_agent_repricing_data(self):
        self.validate()
        res = request.env['tt.pricing.agent'].sudo().get_pricing_agent_api(self.provider_type)
        if res['error_code'] != 0:
            _logger.error('Error Get Pricing Agent Data Backend, %s' % res['error_msg'])
            return []

        new_data = res['response']['pricing_agents']
        return new_data

    def filter_pricing_providers(self, provider='', carrier_code_list=[], agent_type_code='', agent_id='', **kwargs):
        result = []
        for rec in self.pricing_providers:
            is_provider = False
            is_carrier = False
            is_agent_type = False
            is_agent = False

            if rec['provider_access_type'] == 'all':
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'allow' and provider and provider in rec['providers']:
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'restrict' and provider and provider not in rec['providers']:
                is_provider = True

            if rec['carrier_access_type'] == 'all':
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'allow' and carrier_code_list and any(carrier_code in rec['carrier_codes'] for carrier_code in carrier_code_list):
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'restrict' and carrier_code_list and not any(carrier_code in rec['carrier_codes'] for carrier_code in carrier_code_list):
                is_carrier = True

            if rec['agent_type_access_type'] == 'all':
                is_agent_type = True
            elif rec['agent_types'] and rec['agent_type_access_type'] == 'allow' and agent_type_code and agent_type_code in rec['agent_types']:
                is_agent_type = True
            elif rec['agent_types'] and rec['agent_type_access_type'] == 'restrict' and agent_type_code and agent_type_code not in rec['agent_types']:
                is_agent_type = True

            if rec['agent_access_type'] == 'all':
                is_agent = True
            elif rec['agent_ids'] and rec['agent_access_type'] == 'allow' and agent_id and agent_id in rec['agent_ids']:
                is_agent = True
            elif rec['agent_ids'] and rec['agent_access_type'] == 'restrict' and agent_id and agent_id not in rec['agent_ids']:
                is_agent = True

            if not is_provider or not is_carrier or not is_agent_type or not is_agent:
                continue
            result.append(rec)
        self.pricing_providers = result
        return result

    def filter_pricing_agents(self, provider='', origin='', destination='', carrier_code_list=[], agent_type_code='', agent_id='', **kwargs):
        result = []
        for rec in self.pricing_agents:
            if not rec['agent_type_id']:
                continue
            if not rec['provider_type'] == self.provider_type or not rec['agent_type_id']['code'] == agent_type_code:
                continue

            is_provider = False
            is_carrier = False
            is_origin = False
            is_destination = False
            is_agent = False

            origin_country_code = self.destination_tools.get_destination_country_code(origin)
            destination_country_code = self.destination_tools.get_destination_country_code(destination)

            if rec['provider_access_type'] == 'all':
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'allow' and provider and provider in rec['providers']:
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'restrict' and provider and provider not in rec['providers']:
                is_provider = True

            if rec['carrier_access_type'] == 'all':
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'allow' and carrier_code_list and any(carrier_code in rec['carrier_codes'] for carrier_code in carrier_code_list):
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'restrict' and carrier_code_list and not any(carrier_code in rec['carrier_codes'] for carrier_code in carrier_code_list):
                is_carrier = True

            if rec['agent_access_type'] == 'all':
                is_agent = True
            elif rec['agents'] and rec['agent_access_type'] == 'allow' and agent_id and agent_id in rec['agents']:
                is_agent = True
            elif rec['agents'] and rec['agent_access_type'] == 'restrict' and agent_id and agent_id not in rec['agents']:
                is_agent = True

            if rec['origin_type'] == 'all':
                is_origin = True
            elif rec['origin_codes'] and rec['origin_type'] == 'allow' and origin and origin in rec['origin_codes']:
                is_origin = True
            elif rec['origin_codes'] and rec['origin_type'] == 'restrict' and origin and origin not in rec['origin_codes']:
                is_origin = True
            elif rec['origin_country_codes'] and rec['origin_type'] == 'allow' and origin_country_code and origin_country_code in rec['origin_country_codes']:
                is_origin = True
            elif rec['origin_country_codes'] and rec['origin_type'] == 'restrict' and origin_country_code and origin_country_code not in rec['origin_country_codes']:
                is_origin = True

            if rec['destination_type'] == 'all':
                is_destination = True
            elif rec['destination_codes'] and rec['destination_type'] == 'allow' and destination and destination in rec['destination_codes']:
                is_destination = True
            elif rec['destination_codes'] and rec['destination_type'] == 'restrict' and destination and destination not in rec['destination_codes']:
                is_destination = True
            elif rec['destination_country_codes'] and rec['destination_type'] == 'allow' and destination_country_code and destination_country_code in rec['destination_country_codes']:
                is_destination = True
            elif rec['destination_country_codes'] and rec['destination_type'] == 'restrict' and destination_country_code and destination_country_code not in rec['destination_country_codes']:
                is_destination = True

            if is_provider and is_carrier and is_origin and is_destination and is_agent:
                result.append(rec)
        self.pricing_agents = result
        return result

    def get_key_name(self, pricing_type='', provider_pricing_type='', provider='', origin='', destination='', carrier_code='', class_of_service='', charge_code_list=[], agent_type_code='', agent_id='', pricing_date=''):
        charge_code_str = ''.join(charge_code_list) if charge_code_list else ''
        result = '%s%s%s%s%s%s%s%s%s%s%s' % (pricing_type, provider_pricing_type, provider, origin, destination, carrier_code, class_of_service, charge_code_str, agent_type_code, agent_id, pricing_date[:10])
        return result

    def get_provider_pricing(self, pricing_type, provider_pricing_type, provider='', carrier_code='',
                             agent_type_code='', agent_id='', origin='', origin_country='', destination='', destination_country='', class_of_service='',
                             charge_code_list=[], is_retrieved=False, pricing_date=None, **kwargs):
        if not pricing_date:
            pricing_date = self.get_datetime_now()

        data_temp_key = self.get_key_name(pricing_type, provider_pricing_type, provider, origin and origin or origin_country, destination and destination or destination_country, carrier_code, class_of_service, charge_code_list, agent_type_code, agent_id, pricing_date)
        if data_temp_key in self.provider_pricing_dict:
            return self.provider_pricing_dict[data_temp_key]

        for rec in self.pricing_providers:
            if rec['provider_pricing_type'] != provider_pricing_type:
                continue
            if not (pricing_type == 'sale' and rec['is_sale']) and not (
                    pricing_type == 'commission' and rec['is_commission']) and not (
                    pricing_type == 'provider' and rec['is_provider_commission']):
                continue

            is_provider = False
            is_carrier = False
            is_agent_type = False
            is_agent = False

            if rec['provider_access_type'] == 'all':
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'allow' and provider and provider in rec['providers']:
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'restrict' and provider and provider not in rec['providers']:
                is_provider = True

            if rec['carrier_access_type'] == 'all':
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'allow' and carrier_code and carrier_code in rec['carrier_codes']:
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'restrict' and carrier_code and carrier_code not in rec['carrier_codes']:
                is_carrier = True

            if rec['agent_type_access_type'] == 'all':
                is_agent_type = True
            elif rec['agent_types'] and rec['agent_type_access_type'] == 'allow' and agent_type_code and agent_type_code in rec['agent_types']:
                is_agent_type = True
            elif rec['agent_types'] and rec['agent_type_access_type'] == 'restrict' and agent_type_code and agent_type_code not in rec['agent_types']:
                is_agent_type = True

            if rec['agent_access_type'] == 'all':
                is_agent = True
            elif rec['agent_ids'] and rec['agent_access_type'] == 'allow' and agent_id and agent_id in rec['agent_ids']:
                is_agent = True
            elif rec['agent_ids'] and rec['agent_access_type'] == 'restrict' and agent_id and agent_id not in rec['agent_ids']:
                is_agent = True

            if not is_provider or not is_carrier or not is_agent_type or not is_agent:
                continue

            for line in rec['line_ids']:
                if (line['active'] and (line.get('is_no_expiration', False) or line['date_from'] < pricing_date < line['date_to'])) or (is_retrieved and (line['date_from'] < pricing_date < line['date_to'])):
                    is_origin = False
                    is_destination = False
                    is_class_of_service = False
                    is_charge_code = False

                    origin_country_code = self.destination_tools.get_destination_country_code(origin)
                    destination_country_code = self.destination_tools.get_destination_country_code(destination)

                    if not origin_country_code and origin_country:
                        origin_country_code = origin_country

                    if not destination_country_code and destination_country:
                        destination_country_code = destination_country

                    if line['origin_type'] == 'all':
                        is_origin = True
                    elif line['origin_codes'] and line['origin_type'] == 'allow' and origin and origin in line['origin_codes']:
                        is_origin = True
                    elif line['origin_codes'] and line['origin_type'] == 'restrict' and origin and origin not in line['origin_codes']:
                        is_origin = True
                    elif line['origin_country_codes'] and line['origin_type'] == 'allow' and origin_country_code and origin_country_code in line['origin_country_codes']:
                        is_origin = True
                    elif line['origin_country_codes'] and line['origin_type'] == 'restrict' and origin_country_code and origin_country_code not in line['origin_country_codes']:
                        is_origin = True

                    if line['destination_type'] == 'all':
                        is_destination = True
                    elif line['destination_codes'] and line['destination_type'] == 'allow' and destination and destination in line['destination_codes']:
                        is_destination = True
                    elif line['destination_codes'] and line['destination_type'] == 'restrict' and destination and destination not in line['destination_codes']:
                        is_destination = True
                    elif line['destination_country_codes'] and line['destination_type'] == 'allow' and destination_country_code and destination_country_code in line['destination_country_codes']:
                        is_destination = True
                    elif line['destination_country_codes'] and line['destination_type'] == 'restrict' and destination_country_code and destination_country_code not in line['destination_country_codes']:
                        is_destination = True

                    if line['charge_code_type'] == 'all':
                        is_charge_code = True
                    elif line['charge_codes'] and line['charge_code_type'] == 'allow' and charge_code_list and any(s_code in line['charge_codes'] for s_code in charge_code_list):
                        is_charge_code = True
                    elif line['charge_codes'] and line['charge_code_type'] == 'restrict' and charge_code_list and all(s_code not in line['charge_codes'] for s_code in charge_code_list):
                        is_charge_code = True

                    if line['class_of_service_type'] == 'all':
                        is_class_of_service = True
                    elif line['class_of_services'] and line['class_of_service_type'] == 'allow' and class_of_service and class_of_service in line['class_of_services']:
                        is_class_of_service = True
                    elif line['class_of_services'] and line['class_of_service_type'] == 'restrict' and class_of_service and class_of_service not in line['class_of_services']:
                        is_class_of_service = True

                    if is_origin and is_destination and is_charge_code and is_class_of_service:
                        self.provider_pricing_dict[data_temp_key] = line
                        return line
        return {}

    # def get_provider_pricing(self, pricing_type='', provider_pricing_type='', provider='', carrier_code='',
    #                          agent_type_code='', agent_id='', origin='', destination='', class_of_service='',
    #                          charge_code_list=[], journey_count=0, segment_count=0, pax_count=0,
    #                          is_retrieved=False, pricing_date=None, is_separate_journey=False, **kwargs):
    #     pass

    def get_agent_pricing(self, origin='', origin_country='', destination='', destination_country='', charge_code_list=[], class_of_service='', provider='',
                          carrier_code='', agent_type_code='', agent_id='', **kwargs):

        data_temp_key = self.get_key_name(provider=provider, origin=origin, destination=destination,
                                          carrier_code=carrier_code, class_of_service=class_of_service,
                                          charge_code_list=charge_code_list, agent_type_code=agent_type_code,
                                          agent_id=agent_id)
        if data_temp_key in self.agent_pricing_dict:
            return self.agent_pricing_dict[data_temp_key]

        for rec in self.pricing_agents:
            if not rec['agent_type_id']:
                continue
            if not rec['provider_type'] == self.provider_type or not rec['agent_type_id']['code'] == agent_type_code:
                continue

            is_provider = False
            is_carrier = False
            is_origin = False
            is_destination = False
            is_class_of_service = False
            is_charge_code = False
            is_agent = False

            origin_country_code = self.destination_tools.get_destination_country_code(origin)
            destination_country_code = self.destination_tools.get_destination_country_code(destination)

            if not origin_country_code and origin_country:
                origin_country_code = origin_country

            if not destination_country_code and destination_country:
                destination_country_code = destination_country

            if rec['provider_access_type'] == 'all':
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'allow' and provider and provider in rec['providers']:
                is_provider = True
            elif rec['providers'] and rec['provider_access_type'] == 'restrict' and provider and provider not in rec['providers']:
                is_provider = True

            if rec['carrier_access_type'] == 'all':
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'allow' and carrier_code and carrier_code in rec['carrier_codes']:
                is_carrier = True
            elif rec['carrier_codes'] and rec['carrier_access_type'] == 'restrict' and carrier_code and carrier_code not in rec['carrier_codes']:
                is_carrier = True

            if rec['agent_access_type'] == 'all':
                is_agent = True
            elif rec['agents'] and rec['agent_access_type'] == 'allow' and agent_id and agent_id in rec['agents']:
                is_agent = True
            elif rec['agents'] and rec['agent_access_type'] == 'restrict' and agent_id and agent_id not in rec['agents']:
                is_agent = True

            if rec['origin_type'] == 'all':
                is_origin = True
            elif rec['origin_codes'] and rec['origin_type'] == 'allow' and origin and origin in rec['origin_codes']:
                is_origin = True
            elif rec['origin_codes'] and rec['origin_type'] == 'restrict' and origin and origin not in rec['origin_codes']:
                is_origin = True
            elif rec['origin_country_codes'] and rec['origin_type'] == 'allow' and origin_country_code and origin_country_code in rec['origin_country_codes']:
                is_origin = True
            elif rec['origin_country_codes'] and rec['origin_type'] == 'restrict' and origin_country_code and origin_country_code not in rec['origin_country_codes']:
                is_origin = True

            if rec['destination_type'] == 'all':
                is_destination = True
            elif rec['destination_codes'] and rec['destination_type'] == 'allow' and destination and destination in rec['destination_codes']:
                is_destination = True
            elif rec['destination_codes'] and rec['destination_type'] == 'restrict' and destination and destination not in rec['destination_codes']:
                is_destination = True
            elif rec['destination_country_codes'] and rec['destination_type'] == 'allow' and destination_country_code and destination_country_code in rec['destination_country_codes']:
                is_destination = True
            elif rec['destination_country_codes'] and rec['destination_type'] == 'restrict' and destination_country_code and destination_country_code not in rec['destination_country_codes']:
                is_destination = True

            if rec['charge_code_type'] == 'all':
                is_charge_code = True
            elif rec['charge_codes'] and rec['charge_code_type'] == 'allow' and charge_code_list and any(s_code in rec['charge_codes'] for s_code in charge_code_list):
                is_charge_code = True
            elif rec['charge_codes'] and rec['charge_code_type'] == 'restrict' and charge_code_list and all(s_code not in rec['charge_codes'] for s_code in charge_code_list):
                is_charge_code = True

            if rec['class_of_service_type'] == 'all':
                is_class_of_service = True
            elif rec['class_of_services'] and rec['class_of_service_type'] == 'allow' and class_of_service and class_of_service in rec['class_of_services']:
                is_class_of_service = True
            elif rec['class_of_services'] and rec['class_of_service_type'] == 'restrict' and class_of_service and class_of_service not in rec['class_of_services']:
                is_class_of_service = True

            if is_provider and is_carrier and is_origin and is_destination and is_charge_code and is_class_of_service and is_agent:
                self.agent_pricing_dict[data_temp_key] = rec
                return rec
        return {}

    def calculate_provider_pricing_by_fare(self, fare_amount, tax_amount, pax_type, pricing_obj, is_calculate_amount, is_margin_amount, is_reverse_amount, **kwargs):
        '''
        :param pricing_type: sale / commission
        '''
        total_amount = fare_amount + tax_amount

        up_fare = 0.0
        if pax_type != 'INF' or (pax_type == 'INF' and pricing_obj['is_compute_infant_basic']):
            up_fare = fare_amount * pricing_obj['basic_amount'] / 100 if pricing_obj['basic_amount_type'] == 'percentage' else pricing_obj['basic_amount']
        calc_fare = fare_amount + up_fare

        up_tax = 0.0
        if pax_type != 'INF' or (pax_type == 'INF' and pricing_obj['is_compute_infant_tax']):
            up_tax = tax_amount * pricing_obj['tax_amount'] / 100 if pricing_obj['tax_amount_type'] == 'percentage' else pricing_obj['tax_amount']
        calc_tax = tax_amount + up_tax

        total_calc = calc_fare + calc_tax
        up_total_calc = 0.0
        if pax_type != 'INF' or (pax_type == 'INF' and pricing_obj['is_compute_infant_after_tax']):
            up_total_calc = total_calc * pricing_obj['after_tax_amount'] / 100 if pricing_obj['after_tax_amount_type'] == 'percentage' else pricing_obj['after_tax_amount']

        grand_total = total_calc + up_total_calc
        calc_amount = grand_total - total_amount

        up_margin = 0
        if pax_type != 'INF' or (pax_type == 'INF' and pricing_obj['is_compute_infant_upsell']):
            if pricing_obj['lower_amount'] and grand_total < pricing_obj['lower_margin']:
                up_margin = grand_total * pricing_obj['lower_amount'] / 100 if pricing_obj['lower_amount_type'] == 'percentage' else pricing_obj['lower_amount']
            elif pricing_obj['upper_amount'] and grand_total >= pricing_obj['upper_margin']:
                up_margin = grand_total * pricing_obj['upper_amount'] / 100 if pricing_obj['upper_amount_type'] == 'percentage' else pricing_obj['upper_amount']

        result_amount = 0.0
        if is_calculate_amount:
            result_amount += calc_amount
        if is_margin_amount:
            result_amount += up_margin
        if is_reverse_amount:
            result_amount = -result_amount
        return result_amount

    def calculate_provider_pricing_by_criteria(self, pricing_obj, pax_type, route_total, segment_total, pax_total, is_reverse_amount=False, **kwargs):
        flag_list = []

        # multiply_val = 1
        # if route_total > 0:
        #     multiply_val *= route_total
        #     flag_list.append(True)
        # if segment_total > 0:
        #     multiply_val *= segment_total
        #     flag_list.append(True)
        # if pax_total > 0:
        #     multiply_val *= pax_total
        #     flag_list.append(True)

        if pax_type == 'INF' and not pricing_obj['is_compute_infant_fee']:
            multiply_val = 0
        elif pricing_obj['is_per_pax']:
            flag_list.append(True)
            multiply_val = pax_total
            if pricing_obj['is_per_route']:
                multiply_val *= route_total
            if pricing_obj['is_per_segment']:
                multiply_val *= segment_total
        elif pax_type == 'ADT' and (pricing_obj['is_per_route'] or pricing_obj['is_per_segment']):
            flag_list.append(True)
            multiply_val = 1
            if pricing_obj['is_per_route']:
                multiply_val *= route_total
            if pricing_obj['is_per_segment']:
                multiply_val *= segment_total
        else:
            multiply_val = 0

        result_amount = pricing_obj['fee_amount'] * multiply_val if flag_list else 0
        if is_reverse_amount:
            result_amount = -result_amount
        return result_amount

    # TODO Note : This is Primary function
    # TODO USAGE Example
    '''
        1. pricing_tools = RepricingTools('airline')
        2. additional_list = pricing_tool.get_service_charge_pricing(
                fare_amount=150000,
                tax_amount=50000,
                roc_amount=50000,
                rac_amount=-50000, -> nilai minus
                currency='IDR',
                provider='amadeus',
                origin='',
                origin_country='',
                destination='',
                destination_country='',
                carrier_code='',
                class_of_service='',
                charge_code_list=[],
                route_count=1,
                segment_count=1,
                pax_count=2,
                pax_type='ADT',
                agent_type_code='japro',
                agent_id=2,
                is_pricing=False, --> True (Pricing dari rule Pricing Provider) / False (Pricing dari input roc_amount, rac_amount)
                is_commission=True,
                is_retrieved=False,
                pricing_date='',
                show_upline_commission=True,
                user_info=[]
            )
        3. additional_list -> list of service charges
    '''
    def get_service_charge_pricing(
            self,
            fare_amount=0,
            tax_amount=0,
            roc_amount=0,
            rac_amount=0,
            currency='',
            provider='',
            origin='',
            origin_country='',
            destination='',
            destination_country='',
            carrier_code='',
            class_of_service='',
            charge_code_list=[],
            route_count=0,
            segment_count=0,
            pax_count=0,
            pax_type='',
            agent_type_code='',
            agent_id='',
            is_pricing=True,
            is_commission=True,
            is_retrieved=False,
            pricing_date='',
            user_info=None,
            show_upline_commission=True,
            **kwargs):

        service_charge_result = []
        total_amount = fare_amount + tax_amount
        grand_total = total_amount * pax_count

        if is_pricing:
            # Sale pricing obj
            sale_main_pricing_obj = self.get_provider_pricing('sale', 'main', provider, carrier_code, agent_type_code, agent_id, origin, origin_country, destination, destination_country, class_of_service, charge_code_list, is_retrieved, pricing_date)
            sale_append_pricing_obj = self.get_provider_pricing('sale', 'append', provider, carrier_code, agent_type_code, agent_id, origin, origin_country, destination, destination_country, class_of_service, charge_code_list, is_retrieved, pricing_date)
            for idx, pricing_obj in enumerate([sale_main_pricing_obj, sale_append_pricing_obj]):
                if not pricing_obj:
                    continue

                code = 'roc' if idx == 0 else 'rocapp'
                is_calculate_amount = True
                is_margin_amount = True
                is_reverse_amount = False

                charge_amount = self.calculate_provider_pricing_by_fare(fare_amount, tax_amount, pax_type, pricing_obj, is_calculate_amount, is_margin_amount, is_reverse_amount)
                if not pricing_obj['is_override_pricing']:
                   charge_amount += roc_amount
                   roc_amount = 0

                # if charge_amount != 0:
                #     charge_values = {
                #         'charge_type': 'ROC',
                #         'charge_code': 'roc',
                #         'amount': charge_amount,
                #         'pax_type': pax_type,
                #         'pax_count': pax_count,
                #     }
                #     service_charge_result.append(charge_values)

                fee_amount = self.calculate_provider_pricing_by_criteria(pricing_obj, pax_type, route_count, segment_count, pax_count, is_reverse_amount)
                if fee_amount == 0:
                    if charge_amount != 0:
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'ROC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'currency': currency,
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'total': round_charge_amount * pax_count,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        service_charge_result.append(charge_values)
                        grand_total += (round_charge_amount * pax_count)
                else:
                    if pricing_obj['is_per_pax']:
                        fee_amount /= pax_count
                        charge_amount += fee_amount
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'ROC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'currency': currency,
                            'total': round_charge_amount * pax_count,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        service_charge_result.append(charge_values)
                        grand_total += (round_charge_amount * pax_count)
                    else:
                        charge_amount = (charge_amount * pax_count) + fee_amount
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'ROC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': 1,
                            'currency': currency,
                            'total': round_charge_amount,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        service_charge_result.append(charge_values)
                        grand_total += round_charge_amount

                # if charge_amount != 0:
                #     charge_values = {
                #         'charge_type': 'ROC',
                #         'charge_code': 'rofc',
                #         'amount': charge_amount,
                #         'pax_type': pax_type,
                #         'pax_count': pax_count_2,
                #     }
                #     service_charge_result.append(charge_values)
        elif roc_amount != 0:
            round_roc_amount = self.round(roc_amount)
            charge_values = {
                'charge_type': 'ROC',
                'charge_code': 'roc',
                'amount': round_roc_amount,
                'pax_type': pax_type,
                'pax_count': pax_count,
                'currency': currency,
                'total': round_roc_amount * pax_count,
                'foreign_amount': round_roc_amount,
                'foreign_currency': currency,
            }
            service_charge_result.append(charge_values)
            grand_total += (round_roc_amount * pax_count)

        if user_info:
            round_grand_total = self.round(grand_total, user_info[0]['agent_type_id'])
            diff_grand_total = round_grand_total - grand_total
            if diff_grand_total != 0:
                charge_values = {
                    'charge_type': 'ROC',
                    'charge_code': 'rocround',
                    'amount': diff_grand_total,
                    'pax_type': pax_type,
                    'pax_count': 1,
                    'currency': currency,
                    'total': diff_grand_total,
                    'foreign_amount': diff_grand_total,
                    'foreign_currency': currency,
                }
                service_charge_result.append(charge_values)

        if not is_commission:
            return service_charge_result

        # Agent Pricing
        agent_pricing_obj = self.get_agent_pricing(origin, origin_country, destination, destination_country, charge_code_list, class_of_service, provider, carrier_code, agent_type_code, agent_id)

        # Commission pricing obj
        com_main_pricing_obj = self.get_provider_pricing('commission', 'main', provider, carrier_code, agent_type_code, agent_id, origin, origin_country, destination, destination_country, class_of_service, charge_code_list, is_retrieved, pricing_date)
        com_append_pricing_obj = self.get_provider_pricing('commission', 'append', provider, carrier_code, agent_type_code, agent_id, origin, origin_country, destination, destination_country, class_of_service, charge_code_list, is_retrieved, pricing_date)

        for idx, pricing_obj in enumerate([com_main_pricing_obj, com_append_pricing_obj]):
            code = 'rac' if idx == 0 else 'racapp'
            charge_values = {}

            if is_pricing:
                if not pricing_obj:
                    continue


                is_calculate_amount = False
                is_margin_amount = True
                is_reverse_amount = True

                charge_amount = self.calculate_provider_pricing_by_fare(fare_amount, tax_amount, pax_type, pricing_obj,
                                                                        is_calculate_amount, is_margin_amount,
                                                                        is_reverse_amount)
                if not pricing_obj['is_override_pricing']:
                    charge_amount += rac_amount
                    rac_amount = 0

                # if charge_amount != 0:
                #     charge_values = {
                #         'charge_type': 'RAC',
                #         'charge_code': 'rac',
                #         'amount': charge_amount,
                #         'pax_type': pax_type,
                #         'pax_count': pax_count,
                #     }
                #     service_charge_result.append(charge_values)

                fee_amount = self.calculate_provider_pricing_by_criteria(pricing_obj, pax_type, route_count, segment_count, pax_count, is_reverse_amount)
                if fee_amount == 0:
                    if charge_amount != 0:
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'RAC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'currency': currency,
                            'total': round_charge_amount * pax_count,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        # service_charge_result.append(charge_values)
                else:
                    if pricing_obj['is_per_pax']:
                        fee_amount /= pax_count
                        charge_amount += fee_amount
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'RAC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'currency': currency,
                            'total': round_charge_amount * pax_count,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        # service_charge_result.append(charge_values)
                    else:
                        charge_amount = (charge_amount * pax_count) + fee_amount
                        round_charge_amount = self.round(charge_amount)
                        charge_values = {
                            'charge_type': 'RAC',
                            'charge_code': code,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': 1,
                            'currency': currency,
                            'total': round_charge_amount,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        # service_charge_result.append(charge_values)

                # if charge_amount != 0:
                #     charge_values = {
                #         'charge_type': 'RAC',
                #         'charge_code': 'rafc',
                #         'amount': charge_amount,
                #         'pax_type': pax_type,
                #         'pax_count': pax_count_2,
                #     }
                #     service_charge_result.append(charge_values)
            elif rac_amount != 0:
                # Asumsi rac amount dari connector bernilai negatif
                round_charge_amount = self.round(rac_amount)
                charge_values = {
                    'charge_type': 'RAC',
                    'charge_code': 'rac',
                    'amount': round_charge_amount,
                    'pax_type': pax_type,
                    'pax_count': pax_count,
                    'currency': currency,
                    'total': round_charge_amount * pax_count,
                    'foreign_amount': round_charge_amount,
                    'foreign_currency': currency,
                }
                code = 'rac'
                rac_amount = 0

            if not charge_values:
                continue

            if code != 'rac':
                service_charge_result.append(charge_values)
                continue

            charge_values['amount'] *= -1
            pax_total = charge_values['pax_count']
            pax_amount = charge_values['amount']
            total_commission = pax_amount * pax_total
            agent_fee_amount = self.calculate_provider_pricing_by_criteria(agent_pricing_obj, pax_type, route_count, segment_count, pax_total, is_reverse_amount=False)

            if total_commission < agent_fee_amount:
                agent_fee_amount = total_commission

            if agent_fee_amount != 0 and user_info and show_upline_commission:
                fee_agent_id = user_info[-1]['id']
                if agent_pricing_obj['fee_charge_type'] == 'parent' and len(user_info) >= 2:
                    fee_agent_id = user_info[1]['id']
                elif agent_pricing_obj['fee_charge_type'] == 'ho':
                    fee_agent_id = user_info[-1]['id']

                if agent_pricing_obj['is_per_pax']:
                    round_charge_amount = -self.round(agent_fee_amount / pax_total)
                    agent_fee_values = {
                        'charge_type': 'RAC',
                        'charge_code': 'racfee',
                        'amount': round_charge_amount,
                        'pax_type': pax_type,
                        'pax_count': pax_total,
                        'commission_agent_id': fee_agent_id,
                        'currency': currency,
                        'total': round_charge_amount * pax_total,
                        'foreign_amount': round_charge_amount,
                        'foreign_currency': currency,
                    }
                else:
                    round_charge_amount = -self.round(agent_fee_amount)
                    agent_fee_values = {
                        'charge_type': 'RAC',
                        'charge_code': 'racfee',
                        'amount': round_charge_amount,
                        'pax_type': pax_type,
                        'pax_count': 1,
                        'commission_agent_id': fee_agent_id,
                        'currency': currency,
                        'total': round_charge_amount,
                        'foreign_amount': round_charge_amount,
                        'foreign_currency': currency,
                    }
                service_charge_result.append(agent_fee_values)

            nett_commission = total_commission - agent_fee_amount
            temp_commission = nett_commission

            if agent_pricing_obj['commission_charge_type'] == 'fare':
                agent_rac = fare_amount * agent_pricing_obj['basic_amount'] / 100 if agent_pricing_obj['basic_amount_type'] == 'percentage' else agent_pricing_obj['basic_amount']
            elif agent_pricing_obj['commission_charge_type'] == 'total':
                agent_rac = total_amount * agent_pricing_obj['basic_amount'] / 100 if agent_pricing_obj['basic_amount_type'] == 'percentage' else agent_pricing_obj['basic_amount']
            else:
                agent_rac = nett_commission * agent_pricing_obj['basic_amount'] / 100 if agent_pricing_obj['basic_amount_type'] == 'percentage' else agent_pricing_obj['basic_amount']
                agent_rac /= pax_count

            temp_commission -= (agent_rac * pax_count)
            round_charge_amount = -self.round(agent_rac)
            rac_values = {
                'charge_type': 'RAC',
                'charge_code': 'rac',
                'amount': round_charge_amount,
                'pax_type': pax_type,
                'pax_count': pax_count,
                'currency': currency,
                'total': round_charge_amount * pax_count,
                'foreign_amount': round_charge_amount,
                'foreign_currency': currency,
            }
            service_charge_result.append(rac_values)

            if not user_info or not show_upline_commission:
                continue

            # Menghitung terlebih dahulu jumlah komisi yang didapat oleh agent upline
            calc_agent_commission_dict = {}
            for agent_type, line in agent_pricing_obj['line_dict'].items():
                if not agent_type in calc_agent_commission_dict:
                    calc_agent_commission_dict[agent_type] = 0

                if agent_pricing_obj['commission_charge_type'] == 'fare':
                    com_amount = fare_amount * line['basic_amount'] / 100 if line['basic_amount_type'] == 'percentage' else line['basic_amount']
                elif agent_pricing_obj['commission_charge_type'] == 'total':
                    com_amount = total_amount * line['basic_amount'] / 100 if line['basic_amount_type'] == 'percentage' else line['basic_amount']
                else:
                    com_amount = nett_commission * line['basic_amount'] / 100 if line['basic_amount_type'] == 'percentage' else line['basic_amount']
                    com_amount /= pax_count

                temp_commission -= (com_amount * pax_count)
                calc_agent_commission_dict[agent_type] = com_amount

            agent_lvl_com_amount = temp_commission / agent_pricing_obj['loop_level'] if agent_pricing_obj['loop_level'] > 0 and temp_commission > 0 else 0
            agent_lvl_com_amount /= pax_count

            # Menghitung jumlah agent di upline, berfungsi saat agent lvl commission
            agent_count_dict = {}
            base_agent_type = ''
            upline_total_commission = nett_commission - (agent_rac * pax_count)
            for idx, rec in enumerate(user_info):
                if idx == 0:
                    # index 0 adalah user itu sendiri, jadi di skip
                    base_agent_type = rec['agent_type_id']['code']
                    continue

                rec_agent_type = rec['agent_type_id']['code']
                if not rec_agent_type in agent_count_dict:
                    agent_count_dict[rec_agent_type] = 0
                agent_count_dict[rec_agent_type] += 1

                if rec_agent_type == base_agent_type:
                    if agent_count_dict[rec_agent_type] <= agent_pricing_obj['loop_level']and agent_lvl_com_amount > 0:
                        if agent_lvl_com_amount <= 0 or upline_total_commission < agent_lvl_com_amount:
                            continue

                        upline_total_commission -= (agent_lvl_com_amount * pax_count)
                        round_charge_amount = -self.round(agent_lvl_com_amount)
                        com_values = {
                            'charge_type': 'RAC',
                            'charge_code': 'rac%s' % idx,
                            'amount': round_charge_amount,
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'commission_agent_id': rec['id'],
                            'currency': currency,
                            'total': round_charge_amount * pax_count,
                            'foreign_amount': round_charge_amount,
                            'foreign_currency': currency,
                        }
                        service_charge_result.append(com_values)
                else:
                    if not rec_agent_type in calc_agent_commission_dict:
                        continue

                    agent_com_amount = calc_agent_commission_dict[rec_agent_type]
                    if agent_com_amount <= 0 or upline_total_commission < agent_com_amount:
                        continue

                    upline_total_commission -= (agent_com_amount * pax_count)
                    round_charge_amount = -self.round(agent_com_amount)
                    com_values = {
                        'charge_type': 'RAC',
                        'charge_code': 'rac%s' % idx,
                        'amount': round_charge_amount,
                        'pax_type': pax_type,
                        'pax_count': pax_count,
                        'commission_agent_id': rec['id'],
                        'currency': currency,
                        'total': round_charge_amount * pax_count,
                        'foreign_amount': round_charge_amount,
                        'foreign_currency': currency,
                    }
                    service_charge_result.append(com_values)

            if upline_total_commission > 0:
                round_charge_amount = -self.round(upline_total_commission / pax_count)
                com_values = {
                    'charge_type': 'RAC',
                    'charge_code': 'racdiff',
                    'amount': round_charge_amount,
                    'pax_type': pax_type,
                    'pax_count': pax_count,
                    'commission_agent_id': user_info[-1]['id'],
                    'currency': currency,
                    'total': round_charge_amount * pax_count,
                    'foreign_amount': round_charge_amount,
                    'foreign_currency': currency,
                }
                service_charge_result.append(com_values)

        return service_charge_result

    def add_service_charge_detail_airline(self, fare_data={}, currency='', provider='', origin='', destination='', carrier_code='', class_of_service='',
                                          charge_code_list=[], route_count=0, segment_count=0, agent_type_code='', agent_id='',
                                          is_commission=True, is_retrieved=False, pricing_date='', user_info=None, **kwargs):
        '''
            :param pricing_type = 'sale' / 'commission'
                untuk menentukan charge type/charge code nya "ROC"/"roc", atau "RAC"/"rac"

            # Structure
                base_dict = {
                    pax_type: {
                        pax_count: {
                            charge_type.lower(): total_base_amount
                        }
                    }
                }

            # Example
                base_dict = {
                    "ADT": {
                        3: {
                            "fare": 150000,
                            "tax": 100000,
                            "roc": 50000
                        },
                        1: {
                            "roc": 300000
                            "rac": 230000
                        }
                    }
                }
        '''
        service_charge_result = []
        base_dict = {}
        # for scs in fare_data['service_charges_summary']:
        # base_fare = 0.0
        # base_tax = 0.0
        # base_roc = 0.0
        # base_rac = 0.0
        # for sc in scs['service_charges']:
        is_charge_code_list = False if not charge_code_list else True
        for sc in fare_data['service_charges']:
            # if sc['charge_type'] == 'FARE':
            #     base_fare += sc['amount']
            # elif sc['charge_type'] == 'ROC':
            #     base_roc += sc['amount']
            # elif sc['charge_type'] == 'RAC':
            #     base_rac += sc['amount']
            # else:
            #     base_tax += sc['amount']
            pax_type = sc['pax_type']
            pax_count = sc['pax_count']
            charge_type = sc['charge_type'].lower()
            charge_code = sc['charge_code']
            if not is_charge_code_list:
                charge_code_list.append(charge_code)

            base_amount = sc['amount']
            # if charge_type == 'rac' and charge_code != 'rac':
            #     continue
            if pax_type not in base_dict:
                base_dict[pax_type] = {}
            if pax_count not in base_dict[pax_type]:
                base_dict[pax_type][pax_count] = {}
            if charge_type not in base_dict[pax_type][pax_count]:
                base_dict[pax_type][pax_count][charge_type] = 0.0
            base_dict[pax_type][pax_count][charge_type] += base_amount

        is_route_charged = False
        for pax_type, pax_type_val in base_dict.items():
            for pax_count, pax_count_val in pax_type_val.items():
                '''
                    January 27, 2021 - SAM
                    Antisipasi apabila terdapat detail harga yang tidak sesuai standard
                    Contoh apabila dari connector memberikan upsell atau komisi dengan jumlah pax yang tidak sesuai
                    jumlah pax : 3
                    komisi yang di dapat bundle jadi jumlah pax 1
                    Jika ada case demikian, maka tidak akan dipricing
                    Asumsi tidak terdapat fare / tax pada data dengan jumlah pax tersebut

                    Pada Type RAC akan diproses untuk dibagikan ke upline agent
                '''
                is_pricing_valid = True if 'fare' in pax_count_val or 'tax' in pax_count_val else False
                fare_amount = pax_count_val['fare'] if 'fare' in pax_count_val else 0.0
                tax_amount = pax_count_val['tax'] if 'tax' in pax_count_val else 0.0
                roc_amount = pax_count_val['roc'] if 'roc' in pax_count_val else 0.0
                rac_amount = pax_count_val['rac'] if 'rac' in pax_count_val else 0.0

                route_value = 0
                if pax_type == 'ADT' and not is_route_charged:
                    route_value = route_count
                    is_route_charged = True

                values = {
                    'fare_amount': fare_amount,
                    'tax_amount': tax_amount,
                    'roc_amount': roc_amount,
                    'rac_amount': rac_amount,
                    'currency': currency,
                    'provider': provider,
                    'pax_type': pax_type,
                    'pax_count': pax_count,
                    'charge_code_list': charge_code_list,
                    'origin': origin,
                    'destination': destination,
                    'carrier_code': carrier_code,
                    'class_of_service': class_of_service,
                    'route_count': route_value,
                    'segment_count': segment_count,
                    'agent_type_code': agent_type_code,
                    'agent_id': agent_id,
                    'is_pricing': is_pricing_valid,
                    'user_info': user_info,
                    'is_commission': is_commission,
                    'is_retrieved': is_retrieved,
                    'pricing_date': pricing_date,
                }

                results = self.get_service_charge_pricing(**values)
                service_charge_result += results
        return service_charge_result


class ProviderPricing(object):
    def __init__(self, provider_type):
        self.provider_type = provider_type
        self.data = {}
        self.do_config()

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        # June 27, 2023 - SAM
        # Karena mostly data decimal 2 terbanyak, sementara hardcode untuk default 2 decimal di belakang koma
        data_with_two_dec = float(data) * 100
        data_round = round(data_with_two_dec)
        data = data_round / 100
        if not agent_data:
            # res = round(data)
            res = data
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def do_config(self):
        data = self.get_backend_data()
        if not data:
            return False

        for provider_type, rec in data.get('provider_pricing_data', {}).items():
            if self.provider_type == provider_type:
                self.data = rec
        return True

    def get_backend_data(self):
        try:
            payload = request.env['tt.provider.pricing'].sudo().get_provider_pricing_api()
        except Exception as e:
            _logger.error('Error Get Provider Pricing Backend Data, %s' % str(e))
            payload = {}
        return payload

    def get_pricing_data(self, agent_id, agent_type_code, provider_code, carrier_code, origin_code, origin_city, origin_country, destination_code, destination_city, destination_country, class_of_service_list, charge_code_list, tour_code_list, pricing_datetime, departure_date_list, currency_code_list, total_amount, **kwargs):
        # if self.is_data_expired():
        #     self.do_config()
        if not self.data:
            return {}
        provider_pricing_list = []
        if kwargs['context'].get('co_ho_id'):
            if self.data.get(str(kwargs['context']['co_ho_id'])):
                provider_pricing_list = self.data[str(kwargs['context']['co_ho_id'])]['provider_pricing_list']
            else:
                provider_pricing_list = []
        for rec_idx, rec in enumerate(provider_pricing_list):
            if rec['state'] == 'disable':
                continue

            is_provider = False
            is_carrier = False
            is_agent = False
            is_agent_type = False

            provider_data = rec['provider']
            if provider_data['access_type'] == 'all':
                is_provider = True
            elif not provider_code:
                pass
            elif provider_data['access_type'] == 'allow' and provider_code in provider_data['provider_code_list']:
                is_provider = True
            elif provider_data['access_type'] == 'restrict' and provider_code not in provider_data['provider_code_list']:
                is_provider = True

            carrier_data = rec['carrier']
            if carrier_data['access_type'] == 'all':
                is_carrier = True
            elif not carrier_code:
                pass
            elif carrier_data['access_type'] == 'allow' and carrier_code in carrier_data['carrier_code_list']:
                is_carrier = True
            elif carrier_data['access_type'] == 'restrict' and carrier_code not in carrier_data['carrier_code_list']:
                is_carrier = True

            agent_data = rec['agent']
            if agent_data['access_type'] == 'all':
                is_agent = True
            elif not agent_id:
                pass
            elif agent_data['access_type'] == 'allow' and agent_id in agent_data['agent_id_list']:
                is_agent = True
            elif agent_data['access_type'] == 'restrict' and agent_id not in agent_data['agent_id_list']:
                is_agent = True

            agent_type_data = rec['agent_type']
            if agent_type_data['access_type'] == 'all':
                is_agent_type = True
            elif not agent_type_code:
                pass
            elif agent_type_data['access_type'] == 'allow' and agent_type_code in agent_type_data['agent_type_code_list']:
                is_agent_type = True
            elif agent_type_data['access_type'] == 'restrict' and agent_type_code not in agent_type_data['agent_type_code_list']:
                is_agent_type = True

            result_list = [is_provider, is_carrier, is_agent, is_agent_type]
            if not all(res for res in result_list):
                continue

            for rule_idx, rule in enumerate(rec['rule_list']):
                if rule['state'] == 'disable':
                    continue
                if rule['set_expiration_date']:
                    if pricing_datetime < rule['date_from'] or pricing_datetime > rule['date_to']:
                        continue

                is_origin = False
                is_destination = False
                is_class_of_service = False
                is_charge_code = False
                is_tour_code = False
                is_dot = False
                is_currency = False
                is_total_amount = False
                if not rule.get('currency_code'):
                    is_currency = True
                elif rule['currency_code'] and rule['currency_code'] in currency_code_list:
                    is_currency = True
                if not is_currency:
                    continue

                route_data_origin = rule['route']['origin']
                if route_data_origin['access_type'] == 'all':
                    is_origin = True
                elif route_data_origin['access_type'] == 'allow':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True
                elif route_data_origin['access_type'] == 'restrict':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code not in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city not in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country not in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True

                route_data_destination = rule['route']['destination']
                if route_data_destination['access_type'] == 'all':
                    is_destination = True
                elif route_data_destination['access_type'] == 'allow':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True
                elif route_data_destination['access_type'] == 'restrict':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code not in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city not in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country not in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True

                cos_data = rule['route']['class_of_service']
                if cos_data['access_type'] == 'all':
                    is_class_of_service = True
                elif not class_of_service_list:
                    pass
                elif cos_data['access_type'] == 'allow' and any(class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True
                elif cos_data['access_type'] == 'restrict' and not any(class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True

                charge_code_data = rule['route']['charge_code']
                if charge_code_data['access_type'] == 'all':
                    is_charge_code = True
                elif not charge_code_list:
                    pass
                elif charge_code_data['access_type'] == 'allow' and any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True
                elif charge_code_data['access_type'] == 'restrict' and not any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True

                tour_code_data = rule['route']['tour_code']
                if tour_code_data['access_type'] == 'all':
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_any' and tour_code_list:
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_blank' and not tour_code_list:
                    is_tour_code = True
                elif not tour_code_list:
                    pass
                elif tour_code_data['access_type'] == 'allow' and any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'restrict' and not any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True

                dot_data = rule['route']['date_of_travel']
                if dot_data['access_type'] == 'all':
                    is_dot = True
                elif not departure_date_list:
                    pass
                elif dot_data['access_type'] == 'allow' and all(dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in departure_date_list):
                    is_dot = True
                elif dot_data['access_type'] == 'restrict' and not all(dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in departure_date_list):
                    is_dot = True

                total_data = util.get_tree_data(rule, ['route', 'total'])
                if not total_data or total_data['access_type'] == 'all':
                    is_total_amount = True
                elif total_data['access_type'] == 'less':
                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            is_total_amount = True
                    else:
                        if total_amount < less_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'greater':
                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            is_total_amount = True
                    else:
                        if total_amount > greater_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'between':
                    less_flag = greater_flag = False

                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            less_flag = True
                    else:
                        if total_amount < less_amount:
                            less_flag = True

                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            greater_flag = True
                    else:
                        if total_amount > greater_amount:
                            greater_flag = True

                    if less_flag and greater_flag:
                        is_total_amount = True

                result_2_list = [is_origin, is_destination, is_class_of_service, is_charge_code, is_tour_code, is_dot, is_total_amount]
                if not all(res for res in result_2_list):
                    continue

                pricing_data = copy.deepcopy(rec)
                if 'rule_list' in pricing_data:
                    pricing_data.pop('rule_list')

                rule.update({
                    'pricing_id': rec['id'],
                    'parent_data': pricing_data,
                    'rule_id': rule['id'],
                    'pricing_index': rec_idx,
                    'rule_index': rule_idx
                })
                return rule
        return {}

    def calculate_price(self, price_data, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        is_infant = True if pax_type == 'INF' else False
        total_amount = fare_amount + tax_amount
        final_fare_amount = fare_amount
        final_tax_amount = tax_amount
        if 'fare' in price_data:
            fare_data = price_data['fare']
            if not is_infant or (is_infant and fare_data.get('is_infant', False)):
                if fare_data['percentage']:
                    final_fare_amount = final_fare_amount * (100 + fare_data['percentage']) / 100
                if fare_data['amount']:
                    final_fare_amount += fare_data['amount']
        if 'tax' in price_data:
            tax_data = price_data['tax']
            if not is_infant or (is_infant and tax_data.get('is_infant', False)):
                if tax_data['percentage']:
                    final_tax_amount = final_tax_amount * (100 + tax_data['percentage']) / 100
                if tax_data['amount']:
                    final_tax_amount += tax_data['amount']

        final_total_amount = final_fare_amount + final_tax_amount
        if 'total' in price_data:
            total_data = price_data['total']
            if not is_infant or (is_infant and total_data.get('is_infant', False)):
                if total_data['percentage']:
                    final_total_amount = final_total_amount * (100 + total_data['percentage']) / 100
                if total_data['amount']:
                    final_total_amount += total_data['amount']
        if 'upsell_by_percentage' in price_data:
            upsell_data = price_data['upsell_by_percentage']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                has_minimum = upsell_data.get('has_minimum', True)
                has_maximum = upsell_data.get('has_maximum', False)
                add_amount = final_total_amount * upsell_data['percentage'] / 100
                if has_minimum and add_amount < upsell_data['minimum']:
                    add_amount = upsell_data['minimum']
                if has_maximum and add_amount > upsell_data['maximum']:
                    add_amount = upsell_data['maximum']
                final_total_amount += add_amount

        if 'upsell_by_amount' in price_data:
            upsell_data = price_data['upsell_by_amount']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                multiply_amount = 1
                flag = False
                if 'is_route' in upsell_data and upsell_data['is_route']:
                    multiply_amount *= route_count
                    flag = True
                if 'is_segment' in upsell_data and upsell_data['is_segment']:
                    multiply_amount *= segment_count
                    flag = True
                if not flag and not upsell_by_amount_charge:
                    multiply_amount = 0
                add_amount = upsell_data['amount'] * multiply_amount
                final_total_amount += add_amount

        upsell_amount = final_total_amount - total_amount

        payload = {
            'upsell_amount': round(upsell_amount),
        }
        return payload

    def get_ticketing_calculation(self, rule_obj, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        sales_data = rule_obj['ticketing']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_data = rule_obj['ticketing']['nta']
        nta_res = self.calculate_price(nta_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        nta_total_amount = fare_amount + tax_amount + nta_res['upsell_amount']

        nta_agent_data = rule_obj['ticketing']['nta_agent']
        nta_agent_res = self.calculate_price(nta_agent_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        nta_agent_total_amount = fare_amount + tax_amount + nta_agent_res['upsell_amount']

        # total_commission_amount = sales_total_amount - nta_total_amount
        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount

        # July 25, 2023 - SAM
        # October 18, 2023 - SAM
        tax_ho_commission_amount = 0.0
        if rule_obj['ticketing'].get('ho_commission', {}):
            com_data = rule_obj['ticketing']['ho_commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0 and ho_commission_amount > 0 and com_tax_percentage > 0:
                com_tax_charge = (ho_commission_amount * com_tax_percentage) / 100
                tax_ho_commission_amount += com_tax_charge
            if com_tax_amount != 0 and com_tax_amount > 0:
                tax_ho_commission_amount += com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            if com_rounding < 0:
                temp = tax_ho_commission_amount / digit
                tax_ho_commission_amount = round(temp) * digit
            else:
                temp = tax_ho_commission_amount * digit
                tax_ho_commission_amount = round(temp) / digit

        tax_total_commission_amount = 0.0
        if rule_obj['ticketing'].get('commission', {}):
            com_data = rule_obj['ticketing']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            calc_commission_amount = total_commission_amount
            if tax_ho_commission_amount > 0:
                calc_commission_amount -= tax_ho_commission_amount
            if com_tax_percentage != 0 and calc_commission_amount > 0 and com_tax_percentage < 0:
                com_tax_charge = (calc_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
                # total_commission_amount = total_commission_amount + com_tax_charge
            if com_tax_amount != 0 and com_tax_amount < 0:
                tax_total_commission_amount += com_tax_amount
                # total_commission_amount = total_commission_amount + com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = total_commission_amount / digit
            # total_commission_amount = ceil(temp) * digit
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            # nta_agent_total_amount = sales_total_amount - total_commission_amount
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit

        # END

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ticketing',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'pax_type': pax_type,
            'route_count': route_count,
            'segment_count': segment_count,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'nta_agent_amount': nta_agent_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
            'tax_ho_commission_amount': tax_ho_commission_amount,
        }
        return payload

    def get_ancillary_calculation(self, rule_obj, fare_amount, tax_amount, **kwargs):
        sales_data = rule_obj['ancillary']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_data = rule_obj['ancillary']['nta']
        nta_res = self.calculate_price(nta_data, fare_amount, tax_amount)
        nta_total_amount = fare_amount + tax_amount + nta_res['upsell_amount']

        nta_agent_data = rule_obj['ancillary']['nta_agent']
        nta_agent_res = self.calculate_price(nta_agent_data, fare_amount, tax_amount)
        nta_agent_total_amount = fare_amount + tax_amount + nta_agent_res['upsell_amount']

        # total_commission_amount = sales_total_amount - nta_total_amount
        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount
        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ancillary',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
        }
        return payload

    def get_reservation_calculation(self, rule_obj, total_amount, route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        sales_data = rule_obj['reservation']['sales']
        sales_res = self.calculate_price(sales_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = total_upsell_amount

        nta_data = rule_obj['reservation']['nta']
        nta_res = self.calculate_price(nta_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        nta_total_amount = nta_res['upsell_amount']

        nta_agent_data = rule_obj['reservation']['nta_agent']
        nta_agent_res = self.calculate_price(nta_agent_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        nta_agent_total_amount = nta_agent_res['upsell_amount']

        # total_commission_amount = sales_total_amount - nta_total_amount
        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount

        # July 25, 2023 - SAM
        # if total_commission_amount > 0 and rule_obj['reservation'].get('commission', {}):
        #     com_data = rule_obj['reservation']['commission']
        #     com_tax_percentage = com_data.get('tax_percentage', 0)
        #     com_tax_amount = com_data.get('tax_amount', 0)
        #     com_rounding = com_data.get('rounding', 0)
        #     if com_tax_percentage != 0:
        #         com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
        #         total_commission_amount = total_commission_amount + com_tax_charge
        #     if com_tax_amount != 0:
        #         total_commission_amount = total_commission_amount + com_tax_amount
        #     if com_rounding > 0:
        #         digit = 1
        #         for i in range(com_rounding):
        #             digit *= 10
        #         temp = total_commission_amount / digit
        #         total_commission_amount = ceil(temp) * digit
        # END

        # October 18, 2023 - SAM
        tax_ho_commission_amount = 0.0
        if rule_obj['reservation'].get('ho_commission', {}):
            com_data = rule_obj['reservation']['ho_commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0 and ho_commission_amount > 0 and com_tax_percentage > 0:
                com_tax_charge = (ho_commission_amount * com_tax_percentage) / 100
                tax_ho_commission_amount += com_tax_charge
            if com_tax_amount != 0 and com_tax_amount > 0:
                tax_ho_commission_amount += com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            if com_rounding < 0:
                temp = tax_ho_commission_amount / digit
                tax_ho_commission_amount = round(temp) * digit
            else:
                temp = tax_ho_commission_amount * digit
                tax_ho_commission_amount = round(temp) / digit

        tax_total_commission_amount = 0.0
        if rule_obj['reservation'].get('commission', {}):
            com_data = rule_obj['reservation']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            calc_commission_amount = total_commission_amount
            if tax_ho_commission_amount > 0:
                calc_commission_amount -= tax_ho_commission_amount
            if com_tax_percentage != 0 and calc_commission_amount > 0 and com_tax_percentage < 0:
                com_tax_charge = (calc_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
                # total_commission_amount = total_commission_amount + com_tax_charge
            if com_tax_amount != 0 and com_tax_amount < 0:
                tax_total_commission_amount += com_tax_amount
                # total_commission_amount = total_commission_amount + com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = total_commission_amount / digit
            # total_commission_amount = ceil(temp) * digit
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            # nta_agent_total_amount = sales_total_amount - total_commission_amount
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit

        # END

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'reservation',
            'route_count': route_count,
            'segment_count': segment_count,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'nta_agent_amount': nta_agent_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
            'tax_ho_commission_amount': tax_ho_commission_amount,
        }
        return payload

    def get_less_calculation(self, rule_obj, pax_type, **kwargs):
        less_data = rule_obj['less']
        less_percentage = less_data['percentage']
        less_tour_code = less_data.get('tour_code', '')
        if pax_type == 'INF' and not less_data.get('is_infant', False):
            less_percentage = 0

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'less',
            'pax_type': pax_type,
            'less_percentage': less_percentage,
            'less_tour_code': less_tour_code,
        }
        return payload


class AgentPricing(object):
    def __init__(self, agent_type):
        self.agent_type = agent_type
        self.data = {}
        self.do_config()

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        # June 27, 2023 - SAM
        # Karena mostly data decimal 2 terbanyak, sementara hardcode untuk default 2 decimal di belakang koma
        data_with_two_dec = float(data) * 100
        data_round = round(data_with_two_dec)
        data = data_round / 100
        if not agent_data:
            # res = round(data)
            res = data
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def do_config(self):
        data = self.get_backend_data()
        if not data:
            return False

        self.data = data.get('agent_pricing_data', {})
        # for agent_type, rec in data.get('agent_pricing_data', {}).items():
        #     if self.agent_type == agent_type:
        #         self.data = rec
        return True

    def get_backend_data(self):
        try:
            payload = request.env['tt.agent.pricing'].sudo().get_agent_pricing_api()
        except Exception as e:
            _logger.error('Error Get Agent Pricing Backend Data, %s' % str(e))
            payload = {}
        return payload

    def get_pricing_data(self, provider_type_code, agent_id, provider_code, carrier_code, origin_code, origin_city, origin_country, destination_code, destination_city, destination_country, class_of_service_list, charge_code_list, tour_code_list, pricing_datetime, departure_date_list, currency_code_list, total_amount, **kwargs):
        # if self.is_data_expired():
        #     self.do_config()
        if not self.data:
            return {}

        agent_pricing_data = []
        if kwargs['context'].get('co_ho_id'):
            if self.data.get(str(kwargs['context']['co_ho_id'])):
                agent_pricing_data = self.data[str(kwargs['context']['co_ho_id'])]['agent_pricing_list']
            else:
                agent_pricing_data = []
        for rec_idx, rec in enumerate(agent_pricing_data):
            if rec['state'] == 'disable':
                continue

            is_agent_type = False
            is_provider_type = False
            is_agent = False
            is_provider = False
            is_carrier = False
            agent_type_data = rec['agent_type']
            if agent_type_data['access_type'] == 'all':
                is_agent_type = True
            elif not self.agent_type:
                pass
            elif agent_type_data['access_type'] == 'allow' and self.agent_type in agent_type_data['agent_type_code_list']:
                is_agent_type = True
            elif agent_type_data['access_type'] == 'restrict' and self.agent_type not in agent_type_data['agent_type_code_list']:
                is_agent_type = True

            provider_type_data = rec['provider_type']
            if provider_type_data['access_type'] == 'all':
                is_provider_type = True
            elif not provider_type_code:
                pass
            elif provider_type_data['access_type'] == 'allow' and provider_type_code in provider_type_data['provider_type_code_list']:
                is_provider_type = True
            elif provider_type_data['access_type'] == 'restrict' and provider_type_code not in provider_type_data['provider_type_code_list']:
                is_provider_type = True

            agent_data = rec['agent']
            if agent_data['access_type'] == 'all':
                is_agent = True
            elif not agent_id:
                pass
            elif agent_data['access_type'] == 'allow' and agent_id in agent_data['agent_id_list']:
                is_agent = True
            elif agent_data['access_type'] == 'restrict' and agent_id not in agent_data['agent_id_list']:
                is_agent = True

            provider_data = rec['provider']
            if provider_data['access_type'] == 'all':
                is_provider = True
            elif not provider_code:
                pass
            elif provider_data['access_type'] == 'allow' and provider_code in provider_data['provider_code_list']:
                is_provider = True
            elif provider_data['access_type'] == 'restrict' and provider_code not in provider_data['provider_code_list']:
                is_provider = True

            carrier_data = rec['carrier']
            if carrier_data['access_type'] == 'all':
                is_carrier = True
            elif not carrier_code:
                pass
            elif carrier_data['access_type'] == 'allow' and carrier_code in carrier_data['carrier_code_list']:
                is_carrier = True
            elif carrier_data['access_type'] == 'restrict' and carrier_code not in carrier_data['carrier_code_list']:
                is_carrier = True

            result_list = [is_agent_type, is_provider_type, is_agent, is_provider, is_carrier]
            if not all(res for res in result_list):
                continue

            for rule_idx, rule in enumerate(rec['rule_list']):
                if rule['state'] == 'disable':
                    continue

                if rule['set_expiration_date']:
                    if pricing_datetime < rule['date_from'] or pricing_datetime > rule['date_to']:
                        continue

                is_origin = False
                is_destination = False
                is_class_of_service = False
                is_charge_code = False
                is_tour_code = False
                is_dot = False
                is_currency = False
                is_total_amount = False
                if not rule.get('currency_code'):
                    is_currency = True
                elif rule['currency_code'] and rule['currency_code'] in currency_code_list:
                    is_currency = True
                if not is_currency:
                    continue

                route_data_origin = rule['route']['origin']
                if route_data_origin['access_type'] == 'all':
                    is_origin = True
                elif route_data_origin['access_type'] == 'allow':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True
                elif route_data_origin['access_type'] == 'restrict':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code not in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city not in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country not in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True

                route_data_destination = rule['route']['destination']
                if route_data_destination['access_type'] == 'all':
                    is_destination = True
                elif route_data_destination['access_type'] == 'allow':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True
                elif route_data_destination['access_type'] == 'restrict':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code not in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city not in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country not in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True

                cos_data = rule['route']['class_of_service']
                if cos_data['access_type'] == 'all':
                    is_class_of_service = True
                elif not class_of_service_list:
                    pass
                elif cos_data['access_type'] == 'allow' and any(
                        class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True
                elif cos_data['access_type'] == 'restrict' and not any(
                        class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True

                charge_code_data = rule['route']['charge_code']
                if charge_code_data['access_type'] == 'all':
                    is_charge_code = True
                elif not charge_code_list:
                    pass
                elif charge_code_data['access_type'] == 'allow' and any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True
                elif charge_code_data['access_type'] == 'restrict' and not any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True

                tour_code_data = rule['route']['tour_code']
                if tour_code_data['access_type'] == 'all':
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_any' and tour_code_list:
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_blank' and not tour_code_list:
                    is_tour_code = True
                elif not tour_code_list:
                    pass
                elif tour_code_data['access_type'] == 'allow' and any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'restrict' and not any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True

                dot_data = rule['route']['date_of_travel']
                if dot_data['access_type'] == 'all':
                    is_dot = True
                elif not departure_date_list:
                    pass
                elif dot_data['access_type'] == 'allow' and all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True
                elif dot_data['access_type'] == 'restrict' and not all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True

                total_data = util.get_tree_data(rule, ['route', 'total'])
                if not total_data or total_data['access_type'] == 'all':
                    is_total_amount = True
                elif total_data['access_type'] == 'less':
                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            is_total_amount = True
                    else:
                        if total_amount < less_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'greater':
                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            is_total_amount = True
                    else:
                        if total_amount > greater_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'between':
                    less_flag = greater_flag = False

                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            less_flag = True
                    else:
                        if total_amount < less_amount:
                            less_flag = True

                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            greater_flag = True
                    else:
                        if total_amount > greater_amount:
                            greater_flag = True

                    if less_flag and greater_flag:
                        is_total_amount = True

                result_2_list = [is_origin, is_destination, is_class_of_service, is_charge_code, is_tour_code, is_dot, is_total_amount]
                if not all(res for res in result_2_list):
                    continue

                pricing_data = copy.deepcopy(rec)
                if 'rule_list' in pricing_data:
                    pricing_data.pop('rule_list')

                rule.update({
                    'pricing_id': rec['id'],
                    'parent_data': pricing_data,
                    'rule_id': rule['id'],
                    'pricing_index': rec_idx,
                    'rule_index': rule_idx
                })
                return rule
        return {}

    def calculate_price(self, price_data, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        is_infant = True if pax_type == 'INF' else False
        total_amount = fare_amount + tax_amount
        final_fare_amount = fare_amount
        final_tax_amount = tax_amount
        if 'fare' in price_data:
            fare_data = price_data['fare']
            if not is_infant or (is_infant and fare_data.get('is_infant', False)):
                if fare_data['percentage']:
                    final_fare_amount = final_fare_amount * (100 + fare_data['percentage']) / 100
                if fare_data['amount']:
                    final_fare_amount += fare_data['amount']
        if 'tax' in price_data:
            tax_data = price_data['tax']
            if not is_infant or (is_infant and tax_data.get('is_infant', False)):
                if tax_data['percentage']:
                    final_tax_amount = final_tax_amount * (100 + tax_data['percentage']) / 100
                if tax_data['amount']:
                    final_tax_amount += tax_data['amount']

        final_total_amount = final_fare_amount + final_tax_amount
        if 'total' in price_data:
            total_data = price_data['total']
            if not is_infant or (is_infant and total_data.get('is_infant', False)):
                if total_data['percentage']:
                    final_total_amount = final_total_amount * (100 + total_data['percentage']) / 100
                if total_data['amount']:
                    final_total_amount += total_data['amount']

        if 'upsell_by_percentage' in price_data:
            upsell_data = price_data['upsell_by_percentage']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                has_minimum = upsell_data.get('has_minimum', True)
                has_maximum = upsell_data.get('has_maximum', False)
                add_amount = final_total_amount * upsell_data['percentage'] / 100
                if has_minimum and add_amount < upsell_data['minimum']:
                    add_amount = upsell_data['minimum']
                if has_maximum and add_amount > upsell_data['maximum']:
                    add_amount = upsell_data['maximum']
                final_total_amount += add_amount

        if 'upsell_by_amount' in price_data:
            upsell_data = price_data['upsell_by_amount']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                multiply_amount = 1
                flag = False
                if 'is_route' in upsell_data and upsell_data['is_route']:
                    multiply_amount *= route_count
                    flag = True
                if 'is_segment' in upsell_data and upsell_data['is_segment']:
                    multiply_amount *= segment_count
                    flag = True
                if not flag and not upsell_by_amount_charge:
                    multiply_amount = 0

                add_amount = upsell_data['amount'] * multiply_amount
                final_total_amount += add_amount

        upsell_amount = final_total_amount - total_amount

        payload = {
            'upsell_amount': round(upsell_amount),
        }
        return payload

    def calculate_commission(self, price_data, commission_amount, agent_id, pax_count, infant_count=0, route_count=0, segment_count=0, **kwargs):
        original_commission = commission_amount
        total_charge = 0.0
        total_commission = 0.0
        total_discount = 0.0
        if 'charge_by_percentage' in price_data:
            charge_data = price_data['charge_by_percentage']
            if charge_data['percentage']:
                add_amount = commission_amount * charge_data['percentage'] / 100
                has_minimum = charge_data.get('has_minimum', True)
                has_maximum = charge_data.get('has_maximum', False)

                if has_minimum and add_amount < charge_data['minimum']:
                    add_amount = charge_data['minimum']
                if has_maximum and add_amount > charge_data['maximum']:
                    add_amount = charge_data['maximum']

                if add_amount <= original_commission:
                    total_charge += add_amount
                    original_commission -= add_amount
        if 'charge_by_amount' in price_data:
            charge_data = price_data['charge_by_amount']
            if charge_data['amount']:
                multiplier = 1
                if 'is_route' in charge_data and charge_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in charge_data and charge_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in charge_data and charge_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in charge_data and charge_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = charge_data['amount'] * multiplier
                if add_amount <= original_commission:
                    total_charge += add_amount
                    original_commission -= add_amount
        if 'commission_by_percentage' in price_data:
            com_data = price_data['commission_by_percentage']
            if com_data['percentage']:
                add_amount = commission_amount * com_data['percentage'] / 100

                has_minimum = com_data.get('has_minimum', True)
                has_maximum = com_data.get('has_maximum', False)

                if has_minimum and add_amount < com_data['minimum']:
                    add_amount = com_data['minimum']
                if has_maximum and add_amount > com_data['maximum']:
                    add_amount = com_data['maximum']

                if add_amount <= original_commission:
                    total_commission += add_amount
                    original_commission -= add_amount
        if 'commission_by_amount' in price_data:
            com_data = price_data['commission_by_amount']
            if com_data['amount']:
                multiplier = 1
                if 'is_route' in com_data and com_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in com_data and com_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in com_data and com_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in com_data and com_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = com_data['amount'] * multiplier
                if add_amount <= original_commission:
                    total_commission += add_amount
                    original_commission -= add_amount
        if 'discount_by_percentage' in price_data:
            com_data = price_data['discount_by_percentage']
            if com_data['percentage']:
                add_amount = total_commission * com_data['percentage'] / 100
                has_minimum = com_data.get('has_minimum', True)
                has_maximum = com_data.get('has_maximum', False)
                if has_minimum and add_amount < com_data['minimum']:
                    add_amount = com_data['minimum']
                if has_maximum and add_amount > com_data['maximum']:
                    add_amount = com_data['maximum']

                if total_commission >= add_amount:
                    total_discount += add_amount
                    total_commission -= add_amount
        if 'discount_by_amount' in price_data:
            com_data = price_data['discount_by_amount']
            if com_data['amount']:
                multiplier = 1
                if 'is_route' in com_data and com_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in com_data and com_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in com_data and com_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in com_data and com_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = com_data['amount'] * multiplier
                if total_commission >= add_amount:
                    total_discount += add_amount
                    total_commission -= add_amount

        payload = {
            'agent_id': agent_id,
            'commission_amount': round(total_commission),
            'charge_amount': round(total_charge),
        }
        return payload

    def get_ticketing_calculation(self, rule_obj, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, tkt_res=None, roc_amount=0.0, rac_amount=0.0, **kwargs):
        if rule_obj.get('pricing_type'):
            if rule_obj['pricing_type'] == 'from_nta':
                if tkt_res:
                    fare_amount = tkt_res['nta_agent_amount']
                    tax_amount = 0.0
                    if rac_amount:
                        fare_amount -= rac_amount
            elif rule_obj['pricing_type'] == 'from_sales':
                if tkt_res:
                    fare_amount = tkt_res['sales_amount']
                    tax_amount = 0.0
                    if roc_amount:
                        fare_amount += roc_amount

        sales_data = rule_obj['ticketing']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_total_amount = fare_amount + tax_amount

        nta_agent_data = rule_obj['ticketing'].get('nta_agent', {})
        nta_agent_res = self.calculate_price(nta_agent_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        nta_agent_total_amount = fare_amount + tax_amount + nta_agent_res['upsell_amount']

        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount

        # August 16, 2023 - SAM
        # October 17, 2023 - SAM
        tax_ho_commission_amount = 0.0
        if rule_obj['ticketing'].get('ho_commission', {}):
            com_data = rule_obj['ticketing']['ho_commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0 and ho_commission_amount > 0 and com_tax_percentage > 0:
                com_tax_charge = (ho_commission_amount * com_tax_percentage) / 100
                tax_ho_commission_amount += com_tax_charge
            if com_tax_amount != 0 and com_tax_amount > 0:
                tax_ho_commission_amount += com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            if com_rounding < 0:
                temp = tax_ho_commission_amount / digit
                tax_ho_commission_amount = round(temp) * digit
            else:
                temp = tax_ho_commission_amount * digit
                tax_ho_commission_amount = round(temp) / digit

        tax_total_commission_amount = 0.0
        if rule_obj['ticketing'].get('commission', {}):
            com_data = rule_obj['ticketing']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            calc_commission_amount = total_commission_amount
            if tax_ho_commission_amount > 0:
                calc_commission_amount -= tax_ho_commission_amount
            if com_tax_percentage != 0 and calc_commission_amount > 0 and com_tax_percentage < 0:
                com_tax_charge = (calc_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
                # total_commission_amount = total_commission_amount + com_tax_charge
            if com_tax_amount != 0 and com_tax_amount < 0:
                tax_total_commission_amount += com_tax_amount
                # total_commission_amount = total_commission_amount + com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = total_commission_amount / digit
            # total_commission_amount = ceil(temp) * digit
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            # nta_agent_total_amount = sales_total_amount - total_commission_amount
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit

        # END
        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ticketing',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'pax_type': pax_type,
            'route_count': route_count,
            'segment_count': segment_count,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'nta_agent_amount': nta_agent_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
            'tax_ho_commission_amount': tax_ho_commission_amount,
        }
        return payload

    def get_ancillary_calculation(self, rule_obj, fare_amount, tax_amount, **kwargs):
        sales_data = rule_obj['ancillary']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_total_amount = fare_amount + tax_amount

        nta_agent_data = rule_obj['ancillary'].get('nta_agent', {})
        nta_agent_res = self.calculate_price(nta_agent_data, fare_amount, tax_amount)
        nta_agent_total_amount = fare_amount + tax_amount + nta_agent_res['upsell_amount']

        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount
        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ancillary',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'nta_agent_amount': nta_agent_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
        }
        return payload

    def get_reservation_calculation(self, rule_obj, total_amount, route_count=0, segment_count=0, upsell_by_amount_charge=True, tkt_rsv_res=None, roc_amount=0.0, rac_amount=0.0, **kwargs):
        if rule_obj.get('pricing_type'):
            if rule_obj['pricing_type'] == 'from_nta':
                if tkt_rsv_res:
                    total_amount = tkt_rsv_res['nta_agent_amount']
                    if rac_amount:
                        total_amount -= rac_amount
            elif rule_obj['pricing_type'] == 'from_sales':
                if tkt_rsv_res:
                    total_amount = tkt_rsv_res['sales_amount']
                    if roc_amount:
                        total_amount += roc_amount

        sales_data = rule_obj['reservation']['sales']
        sales_res = self.calculate_price(sales_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = total_amount + total_upsell_amount

        nta_total_amount = total_amount

        nta_agent_data = rule_obj['reservation'].get('nta_agent', {})
        nta_agent_res = self.calculate_price(nta_agent_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        nta_agent_total_amount = total_amount + nta_agent_res['upsell_amount']

        total_commission_amount = sales_total_amount - nta_agent_total_amount
        ho_commission_amount = nta_agent_total_amount - nta_total_amount

        # August 16, 2023 - SAM
        # if total_commission_amount > 0 and rule_obj['reservation'].get('commission', {}):
        #     com_data = rule_obj['reservation']['commission']
        #     com_tax_percentage = com_data.get('tax_percentage', 0)
        #     com_tax_amount = com_data.get('tax_amount', 0)
        #     com_rounding = com_data.get('rounding', 0)
        #     if com_tax_percentage != 0:
        #         com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
        #         total_commission_amount = total_commission_amount + com_tax_charge
        #     if com_tax_amount != 0:
        #         total_commission_amount = total_commission_amount + com_tax_amount
        #     if com_rounding > 0:
        #         digit = 1
        #         for i in range(com_rounding):
        #             digit *= 10
        #         temp = total_commission_amount / digit
        #         total_commission_amount = ceil(temp) * digit
        #     # nta_agent_total_amount = sales_total_amount - total_commission_amount
        # END

        # October 19, 2023 - SAM
        tax_ho_commission_amount = 0.0
        if rule_obj['reservation'].get('ho_commission', {}):
            com_data = rule_obj['reservation']['ho_commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0 and ho_commission_amount > 0 and com_tax_percentage > 0:
                com_tax_charge = (ho_commission_amount * com_tax_percentage) / 100
                tax_ho_commission_amount += com_tax_charge
            if com_tax_amount != 0 and com_tax_amount > 0:
                tax_ho_commission_amount += com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            if com_rounding < 0:
                temp = tax_ho_commission_amount / digit
                tax_ho_commission_amount = round(temp) * digit
            else:
                temp = tax_ho_commission_amount * digit
                tax_ho_commission_amount = round(temp) / digit


        tax_total_commission_amount = 0.0
        if rule_obj['reservation'].get('commission', {}):
            com_data = rule_obj['reservation']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            calc_commission_amount = total_commission_amount
            if tax_ho_commission_amount > 0:
                calc_commission_amount -= tax_ho_commission_amount
            if com_tax_percentage != 0 and calc_commission_amount > 0 and com_tax_percentage < 0:
                com_tax_charge = (calc_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
                # total_commission_amount = total_commission_amount + com_tax_charge
            if com_tax_amount != 0 and com_tax_amount < 0:
                tax_total_commission_amount += com_tax_amount
                # total_commission_amount = total_commission_amount + com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = total_commission_amount / digit
            # total_commission_amount = ceil(temp) * digit
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            # nta_agent_total_amount = sales_total_amount - total_commission_amount
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit

        # END

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'reservation',
            'route_count': route_count,
            'segment_count': segment_count,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'ho_commission_amount': ho_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
            'tax_ho_commission_amount': tax_ho_commission_amount,
        }
        return payload

    def get_commission_calculation(self, rule_obj, commission_amount, agent_id, upline_list, pax_count, infant_count=0, route_count=0, segment_count=0, **kwargs):
        com_data = rule_obj['commission']

        parent_charge_amount = 0.0
        parent_agent_id = ''
        # January 6, 2022 - SAM
        # Untuk melakukan pengecekkan apakah user memiliki parent agent (upline) atau tidak
        # Contoh ada parent agent, upline list [ A , B , C ]
        # upline_list[1:] => [ B, C ] => Parent Agentnya ada
        # Contoh tidak ada parent agent, upline list [ A ]
        # upline_list[1:] => [ ] => Parent Agentnya tidak ada
        if upline_list[1:]:
            parent_agent_id = upline_list[1]['id']
            parent_res = self.calculate_commission(com_data['parent'], upline_list[1]['id'], commission_amount, pax_count, infant_count, route_count, segment_count)
            parent_charge_amount = parent_res['charge_amount']
            if parent_charge_amount > commission_amount:
                parent_charge_amount = 0.0
            else:
                commission_amount -= parent_charge_amount

        ho_charge_amount = 0.0
        ho_agent_id = ''
        if upline_list:
            ho_agent_id = upline_list[-1]['id']
            ho_res = self.calculate_commission(com_data['ho'], commission_amount, upline_list[-1]['id'], pax_count, infant_count, route_count, segment_count)
            ho_charge_amount = ho_res['charge_amount']
            if ho_charge_amount > commission_amount:
                ho_charge_amount = 0.0
            else:
                commission_amount -= ho_charge_amount

        agent_res = self.calculate_commission(com_data['agent'], commission_amount, agent_id, pax_count, infant_count, route_count, segment_count)
        upline_res_list = []
        upline_head = 0
        for upline in upline_list[1:]:
            for idx, upline_obj in enumerate(com_data['upline_list']):
                if idx < upline_head:
                    continue

                if upline_obj['agent_type_code'] == upline['agent_type_id']['code']:
                    upline_head = idx + 1
                    upline_res = self.calculate_commission(upline_obj, commission_amount, upline['id'], pax_count, infant_count, route_count, segment_count)
                    upline_res_list.append(upline_res)
                    break

        agent_commission_amount = agent_res['commission_amount']
        if agent_commission_amount > commission_amount:
            agent_commission_amount = 0.0
        else:
            commission_amount -= agent_commission_amount

        for upline_res in upline_res_list:
            if upline_res['commission_amount'] > commission_amount:
                upline_res['commission_amount'] = 0.0
            else:
                commission_amount -= upline_res['commission_amount']

        residual_agent_id = ''
        if upline_list:
            residual_agent_id = upline_list[-1]['id']
            # January 6, 2022 - SAM
            # Untuk melakukan pengecekkan apakah user memiliki parent agent (upline) atau tidak
            # Contoh ada parent agent, upline list [ A , B , C ]
            # upline_list[1:] => [ B, C ] => Parent Agentnya ada
            # Contoh tidak ada parent agent, upline list [ A ]
            # upline_list[1:] => [ ] => Parent Agentnya tidak ada
            if upline_list[1:]:
                if com_data['residual_amount_to'] == 'parent':
                    residual_agent_id = upline_list[1]['id']

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'commission',
            'agent_id': agent_id,
            'upline_list': upline_list,
            'pax_count': pax_count,
            'infant_count': infant_count,
            'route_count': route_count,
            'segment_count': segment_count,
            'parent_charge_amount': parent_charge_amount,
            'parent_agent_id': parent_agent_id,
            'ho_charge_amount': ho_charge_amount,
            'ho_agent_id': ho_agent_id,
            'agent_commission_amount': agent_commission_amount,
            'upline_commission_list': upline_res_list,
            'residual_amount': commission_amount,
            'residual_agent_id': residual_agent_id
        }
        return payload


class CustomerPricing(object):
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.data = {}
        self.do_config()

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        # June 27, 2023 - SAM
        # Karena mostly data decimal 2 terbanyak, sementara hardcode untuk default 2 decimal di belakang koma
        data_with_two_dec = float(data) * 100
        data_round = round(data_with_two_dec)
        data = data_round / 100
        if not agent_data:
            # res = round(data)
            res = data
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def do_config(self):
        data = self.get_backend_data()
        if not data:
            return False

        for ho_id, pricing_data in data.get('customer_pricing_data', {}).items():
            for agent_id, rec in pricing_data.items():
                if self.agent_id == int(agent_id):
                    self.data = rec
        return True

    def get_backend_data(self):
        try:
            payload = request.env['tt.customer.pricing'].sudo().get_customer_pricing_api()
        except Exception as e:
            _logger.error('Error Get Customer Pricing Backend Data, %s' % str(e))
            payload = {}
        return payload

    def get_pricing_data(self, customer_parent_type_code, customer_parent_id, provider_type_code, provider_code, carrier_code, origin_code, origin_city, origin_country, destination_code, destination_city, destination_country, class_of_service_list, charge_code_list, tour_code_list, pricing_datetime, departure_date_list, currency_code_list, total_amount, **kwargs):
        # if self.is_data_expired():
        #     self.do_config()
        if not self.data:
            return {}

        for rec_idx, rec in enumerate(self.data['customer_pricing_list']):
            if rec['state'] == 'disable':
                continue

            is_customer_parent_type = False
            is_customer_parent = False
            is_provider_type = False
            is_provider = False
            is_carrier = False

            customer_parent_type_data = rec['customer_parent_type']
            if customer_parent_type_data['access_type'] == 'all':
                is_customer_parent_type = True
            elif not customer_parent_type_code:
                pass
            elif customer_parent_type_data['access_type'] == 'allow' and customer_parent_type_code in customer_parent_type_data['customer_parent_type_code_list']:
                is_customer_parent_type = True
            elif customer_parent_type_data['access_type'] == 'restrict' and customer_parent_type_code not in customer_parent_type_data['customer_parent_type_code_list']:
                is_customer_parent_type = True

            customer_parent_data = rec['customer_parent']
            if customer_parent_data['access_type'] == 'all':
                is_customer_parent = True
            elif not customer_parent_id:
                pass
            elif customer_parent_data['access_type'] == 'allow' and customer_parent_id in customer_parent_data['customer_parent_id_list']:
                is_customer_parent = True
            elif customer_parent_data['access_type'] == 'restrict' and customer_parent_id not in customer_parent_data['customer_parent_id_list']:
                is_customer_parent = True

            provider_type_data = rec['provider_type']
            if provider_type_data['access_type'] == 'all':
                is_provider_type = True
            elif not provider_type_code:
                pass
            elif provider_type_data['access_type'] == 'allow' and provider_type_code in provider_type_data['provider_type_code_list']:
                is_provider_type = True
            elif provider_type_data['access_type'] == 'restrict' and provider_type_code not in provider_type_data['provider_type_code_list']:
                is_provider_type = True

            provider_data = rec['provider']
            if provider_data['access_type'] == 'all':
                is_provider = True
            elif not provider_code:
                pass
            elif provider_data['access_type'] == 'allow' and provider_code in provider_data['provider_code_list']:
                is_provider = True
            elif provider_data['access_type'] == 'restrict' and provider_code not in provider_data['provider_code_list']:
                is_provider = True

            carrier_data = rec['carrier']
            if carrier_data['access_type'] == 'all':
                is_carrier = True
            elif not carrier_code:
                pass
            elif carrier_data['access_type'] == 'allow' and carrier_code in carrier_data['carrier_code_list']:
                is_carrier = True
            elif carrier_data['access_type'] == 'restrict' and carrier_code not in carrier_data['carrier_code_list']:
                is_carrier = True

            result_list = [is_customer_parent_type, is_customer_parent, is_provider_type, is_provider, is_carrier]
            if not all(res for res in result_list):
                continue

            for rule_idx, rule in enumerate(rec['rule_list']):
                if rule['state'] == 'disable':
                    continue

                if rule['set_expiration_date']:
                    if pricing_datetime < rule['date_from'] or pricing_datetime > rule['date_to']:
                        continue

                is_origin = False
                is_destination = False
                is_class_of_service = False
                is_charge_code = False
                is_tour_code = False
                is_dot = False
                is_currency = False
                is_total_amount = False
                if not rule.get('currency_code'):
                    is_currency = True
                elif rule['currency_code'] and rule['currency_code'] in currency_code_list:
                    is_currency = True
                if not is_currency:
                    continue

                route_data_origin = rule['route']['origin']
                if route_data_origin['access_type'] == 'all':
                    is_origin = True
                elif route_data_origin['access_type'] == 'allow':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True
                elif route_data_origin['access_type'] == 'restrict':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code not in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city not in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country not in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True

                route_data_destination = rule['route']['destination']
                if route_data_destination['access_type'] == 'all':
                    is_destination = True
                elif route_data_destination['access_type'] == 'allow':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True
                elif route_data_destination['access_type'] == 'restrict':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code not in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city not in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country not in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True

                cos_data = rule['route']['class_of_service']
                if cos_data['access_type'] == 'all':
                    is_class_of_service = True
                elif not class_of_service_list:
                    pass
                elif cos_data['access_type'] == 'allow' and any(class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True
                elif cos_data['access_type'] == 'restrict' and not any(class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True

                charge_code_data = rule['route']['charge_code']
                if charge_code_data['access_type'] == 'all':
                    is_charge_code = True
                elif not charge_code_list:
                    pass
                elif charge_code_data['access_type'] == 'allow' and any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True
                elif charge_code_data['access_type'] == 'restrict' and not any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True

                tour_code_data = rule['route']['tour_code']
                if tour_code_data['access_type'] == 'all':
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_any' and tour_code_list:
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_blank' and not tour_code_list:
                    is_tour_code = True
                elif not tour_code_list:
                    pass
                elif tour_code_data['access_type'] == 'allow' and any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'restrict' and not any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True

                dot_data = rule['route']['date_of_travel']
                if dot_data['access_type'] == 'all':
                    is_dot = True
                elif not departure_date_list:
                    pass
                elif dot_data['access_type'] == 'allow' and all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True
                elif dot_data['access_type'] == 'restrict' and not all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True

                total_data = util.get_tree_data(rule, ['route', 'total'])
                if not total_data or total_data['access_type'] == 'all':
                    is_total_amount = True
                elif total_data['access_type'] == 'less':
                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            is_total_amount = True
                    else:
                        if total_amount < less_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'greater':
                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            is_total_amount = True
                    else:
                        if total_amount > greater_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'between':
                    less_flag = greater_flag = False

                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            less_flag = True
                    else:
                        if total_amount < less_amount:
                            less_flag = True

                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            greater_flag = True
                    else:
                        if total_amount > greater_amount:
                            greater_flag = True

                    if less_flag and greater_flag:
                        is_total_amount = True

                result_2_list = [is_origin, is_destination, is_class_of_service, is_charge_code, is_tour_code, is_dot, is_total_amount]
                if not all(res for res in result_2_list):
                    continue

                pricing_data = copy.deepcopy(rec)
                if 'rule_list' in pricing_data:
                    pricing_data.pop('rule_list')

                rule.update({
                    'pricing_id': rec['id'],
                    'parent_data': pricing_data,
                    'rule_id': rule['id'],
                    'pricing_index': rec_idx,
                    'rule_index': rule_idx
                })
                return rule
        return {}

    def calculate_price(self, price_data, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        is_infant = True if pax_type == 'INF' else False
        total_amount = fare_amount + tax_amount
        final_total_amount = total_amount
        if 'upsell_by_percentage' in price_data:
            upsell_data = price_data['upsell_by_percentage']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                has_minimum = upsell_data.get('has_minimum', True)
                has_maximum = upsell_data.get('has_maximum', False)
                add_amount = final_total_amount * upsell_data['percentage'] / 100
                if has_minimum and add_amount < upsell_data['minimum']:
                    add_amount = upsell_data['minimum']
                if has_maximum and add_amount > upsell_data['maximum']:
                    add_amount = upsell_data['maximum']
                final_total_amount += add_amount

        if 'upsell_by_amount' in price_data:
            upsell_data = price_data['upsell_by_amount']
            if not is_infant or (is_infant and upsell_data.get('is_infant', False)):
                multiply_amount = 1
                flag = False
                if 'is_route' in upsell_data and upsell_data['is_route']:
                    multiply_amount *= route_count
                    flag = True
                if 'is_segment' in upsell_data and upsell_data['is_segment']:
                    multiply_amount *= segment_count
                    flag = True
                if not flag and not upsell_by_amount_charge:
                    multiply_amount = 0

                add_amount = upsell_data['amount'] * multiply_amount
                final_total_amount += add_amount

        upsell_amount = final_total_amount - total_amount

        payload = {
            'upsell_amount': round(upsell_amount),
        }
        return payload

    def get_ticketing_calculation(self, rule_obj, fare_amount, tax_amount, pax_type='', route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        sales_data = rule_obj['ticketing']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount, pax_type, route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_total_amount = fare_amount + tax_amount

        total_commission_amount = sales_total_amount - nta_total_amount
        # August 16, 2023 - SAM
        # October 18, 2023 - SAM
        # if total_commission_amount > 0 and rule_obj['ticketing'].get('commission', {}):
        #     com_data = rule_obj['ticketing']['commission']
        #     com_tax_percentage = com_data.get('tax_percentage', 0)
        #     com_tax_amount = com_data.get('tax_amount', 0)
        #     com_rounding = com_data.get('rounding', 0)
        #     if com_tax_percentage != 0:
        #         com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
        #         total_commission_amount = total_commission_amount + com_tax_charge
        #     if com_tax_amount != 0:
        #         total_commission_amount = total_commission_amount + com_tax_amount
        #     if com_rounding > 0:
        #         digit = 1
        #         for i in range(com_rounding):
        #             digit *= 10
        #         temp = total_commission_amount / digit
        #         total_commission_amount = ceil(temp) * digit
        #     # nta_total_amount = sales_total_amount - total_commission_amount

        tax_total_commission_amount = 0.0
        if rule_obj['ticketing'].get('commission', {}):
            com_data = rule_obj['ticketing']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0 and total_commission_amount > 0 and com_tax_percentage < 0:
                com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
            if com_tax_amount != 0 and com_tax_amount < 0:
                tax_total_commission_amount += com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit
        # END

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ticketing',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'pax_type': pax_type,
            'route_count': route_count,
            'segment_count': segment_count,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
        }
        return payload

    def get_ancillary_calculation(self, rule_obj, fare_amount, tax_amount, **kwargs):
        sales_data = rule_obj['ancillary']['sales']
        sales_res = self.calculate_price(sales_data, fare_amount, tax_amount)
        total_upsell_amount = sales_res['upsell_amount']
        sales_total_amount = fare_amount + tax_amount + total_upsell_amount

        nta_total_amount = fare_amount + tax_amount

        total_commission_amount = sales_total_amount - nta_total_amount
        payload = {
            'rule_id': rule_obj['id'],
            'section': 'ancillary',
            'fare_amount': fare_amount,
            'tax_amount': tax_amount,
            'sales_amount': sales_total_amount,
            'nta_amount': nta_total_amount,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount
        }
        return payload

    def get_reservation_calculation(self, rule_obj, total_amount, route_count=0, segment_count=0, upsell_by_amount_charge=True, **kwargs):
        sales_data = rule_obj['reservation']['sales']
        sales_res = self.calculate_price(sales_data, total_amount, 0.0, '', route_count, segment_count, upsell_by_amount_charge)
        total_upsell_amount = sales_res['upsell_amount']

        # August 16, 2023 - SAM
        total_commission_amount = total_upsell_amount
        # if total_commission_amount > 0 and rule_obj['reservation'].get('commission', {}):
        #     com_data = rule_obj['ticketing']['commission']
        #     com_tax_percentage = com_data.get('tax_percentage', 0)
        #     com_tax_amount = com_data.get('tax_amount', 0)
        #     com_rounding = com_data.get('rounding', 0)
        #     if com_tax_percentage != 0:
        #         com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
        #         total_commission_amount = total_commission_amount + com_tax_charge
        #     if com_tax_amount != 0:
        #         total_commission_amount = total_commission_amount + com_tax_amount
        #     if com_rounding > 0:
        #         digit = 1
        #         for i in range(com_rounding):
        #             digit *= 10
        #         temp = total_commission_amount / digit
        #         total_commission_amount = ceil(temp) * digit
        # END

        # October 19, 2023 - SAM
        tax_total_commission_amount = 0.0
        if rule_obj['reservation'].get('commission', {}):
            com_data = rule_obj['reservation']['commission']
            com_tax_percentage = com_data.get('tax_percentage', 0)
            com_tax_amount = com_data.get('tax_amount', 0)
            com_rounding = com_data.get('rounding', 0)
            if com_tax_percentage != 0:
                com_tax_charge = (total_commission_amount * com_tax_percentage) / 100
                tax_total_commission_amount += com_tax_charge
                # total_commission_amount = total_commission_amount + com_tax_charge
            if com_tax_amount != 0:
                tax_total_commission_amount += com_tax_amount
                # total_commission_amount = total_commission_amount + com_tax_amount
            # if com_rounding > 0:
            digit = 1
            for i in range(abs(com_rounding)):
                digit *= 10
            # temp = total_commission_amount / digit
            # total_commission_amount = ceil(temp) * digit
            # temp = tax_total_commission_amount / digit
            # tax_total_commission_amount = ceil(temp) * digit
            # nta_agent_total_amount = sales_total_amount - total_commission_amount
            abs_tax_total_commission_amount = abs(tax_total_commission_amount)
            if com_rounding < 0:
                temp = abs_tax_total_commission_amount / digit
                tax_total_commission_amount = -1.0 * round(temp) * digit
            else:
                temp = abs_tax_total_commission_amount * digit
                tax_total_commission_amount = -1.0 * round(temp) / digit
        # END

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'reservation',
            'route_count': route_count,
            'segment_count': segment_count,
            'upsell_amount': total_upsell_amount,
            'commission_amount': total_commission_amount,
            'tax_commission_amount': tax_total_commission_amount,
        }
        return payload


class AgentCommission(object):
    def __init__(self, agent_type):
        self.agent_type = agent_type
        self.data = {}
        self.do_config()

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        # June 27, 2023 - SAM
        # Karena mostly data decimal 2 terbanyak, sementara hardcode untuk default 2 decimal di belakang koma
        data_with_two_dec = float(data) * 100
        data_round = round(data_with_two_dec)
        data = data_round / 100
        if not agent_data:
            # res = round(data)
            res = data
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def do_config(self):
        data = self.get_backend_data()
        if not data:
            return False

        self.data = data.get('agent_commission_data', {})
        # for agent_type, rec in data.get('agent_commission_data', {}).items():
        #     if self.agent_type == agent_type:
        #         self.data = rec
        return True

    def get_backend_data(self):
        try:
            payload = request.env['tt.agent.commission'].sudo().get_agent_commission_api()
        except Exception as e:
            _logger.error('Error Get Agent Commission Backend Data, %s' % str(e))
            payload = {}
        return payload

    def get_pricing_data(self, provider_type_code, agent_id, provider_code, carrier_code, origin_code, origin_city,
                         origin_country, destination_code, destination_city, destination_country, class_of_service_list,
                         charge_code_list, tour_code_list, pricing_datetime, departure_date_list, currency_code_list, total_amount, **kwargs):
        # if self.is_data_expired():
        #     self.do_config()
        if not self.data:
            return {}

        agent_commission_data = []
        if kwargs['context'].get('co_ho_id'):
            if self.data.get(str(kwargs['context']['co_ho_id'])):
                agent_commission_data = self.data[str(kwargs['context']['co_ho_id'])]['agent_commission_list']
            else:
                agent_commission_data = []
        for rec_idx, rec in enumerate(agent_commission_data):
            if rec['state'] == 'disable':
                continue

            is_agent_type = False
            is_provider_type = False
            is_agent = False
            is_provider = False
            is_carrier = False
            agent_type_data = rec['agent_type']
            if agent_type_data['access_type'] == 'all':
                is_agent_type = True
            elif not self.agent_type:
                pass
            elif agent_type_data['access_type'] == 'allow' and self.agent_type in agent_type_data['agent_type_code_list']:
                is_agent_type = True
            elif agent_type_data['access_type'] == 'restrict' and self.agent_type not in agent_type_data['agent_type_code_list']:
                is_agent_type = True

            provider_type_data = rec['provider_type']
            if provider_type_data['access_type'] == 'all':
                is_provider_type = True
            elif not provider_type_code:
                pass
            elif provider_type_data['access_type'] == 'allow' and provider_type_code in provider_type_data['provider_type_code_list']:
                is_provider_type = True
            elif provider_type_data['access_type'] == 'restrict' and provider_type_code not in provider_type_data['provider_type_code_list']:
                is_provider_type = True

            agent_data = rec['agent']
            if agent_data['access_type'] == 'all':
                is_agent = True
            elif not agent_id:
                pass
            elif agent_data['access_type'] == 'allow' and agent_id in agent_data['agent_id_list']:
                is_agent = True
            elif agent_data['access_type'] == 'restrict' and agent_id not in agent_data['agent_id_list']:
                is_agent = True

            provider_data = rec['provider']
            if provider_data['access_type'] == 'all':
                is_provider = True
            elif not provider_code:
                pass
            elif provider_data['access_type'] == 'allow' and provider_code in provider_data['provider_code_list']:
                is_provider = True
            elif provider_data['access_type'] == 'restrict' and provider_code not in provider_data['provider_code_list']:
                is_provider = True

            carrier_data = rec['carrier']
            if carrier_data['access_type'] == 'all':
                is_carrier = True
            elif not carrier_code:
                pass
            elif carrier_data['access_type'] == 'allow' and carrier_code in carrier_data['carrier_code_list']:
                is_carrier = True
            elif carrier_data['access_type'] == 'restrict' and carrier_code not in carrier_data['carrier_code_list']:
                is_carrier = True

            result_list = [is_agent_type, is_provider_type, is_agent, is_provider, is_carrier]
            if not all(res for res in result_list):
                continue

            for rule_idx, rule in enumerate(rec['rule_list']):
                if rule['state'] == 'disable':
                    continue

                if rule['set_expiration_date']:
                    if pricing_datetime < rule['date_from'] or pricing_datetime > rule['date_to']:
                        continue

                is_origin = False
                is_destination = False
                is_class_of_service = False
                is_charge_code = False
                is_tour_code = False
                is_dot = False
                is_currency = False
                is_total_amount = False
                if not rule.get('currency_code'):
                    is_currency = True
                elif rule['currency_code'] and rule['currency_code'] in currency_code_list:
                    is_currency = True
                if not is_currency:
                    continue

                route_data_origin = rule['route']['origin']
                if route_data_origin['access_type'] == 'all':
                    is_origin = True
                elif route_data_origin['access_type'] == 'allow':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True
                elif route_data_origin['access_type'] == 'restrict':
                    origin_temp_list = []
                    if origin_code and route_data_origin['destination_code_list']:
                        if origin_code not in route_data_origin['destination_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_city and route_data_origin['city_code_list']:
                        if origin_city not in route_data_origin['city_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if origin_country and route_data_origin['country_code_list']:
                        if origin_country not in route_data_origin['country_code_list']:
                            origin_temp_list.append(True)
                        else:
                            origin_temp_list.append(False)
                    if all(state == True for state in origin_temp_list):
                        is_origin = True

                route_data_destination = rule['route']['destination']
                if route_data_destination['access_type'] == 'all':
                    is_destination = True
                elif route_data_destination['access_type'] == 'allow':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True
                elif route_data_destination['access_type'] == 'restrict':
                    destination_temp_list = []
                    if destination_code and route_data_destination['destination_code_list']:
                        if destination_code not in route_data_destination['destination_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_city and route_data_destination['city_code_list']:
                        if destination_city not in route_data_destination['city_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if destination_country and route_data_destination['country_code_list']:
                        if destination_country not in route_data_destination['country_code_list']:
                            destination_temp_list.append(True)
                        else:
                            destination_temp_list.append(False)
                    if all(state == True for state in destination_temp_list):
                        is_destination = True

                cos_data = rule['route']['class_of_service']
                if cos_data['access_type'] == 'all':
                    is_class_of_service = True
                elif not class_of_service_list:
                    pass
                elif cos_data['access_type'] == 'allow' and any(
                        class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True
                elif cos_data['access_type'] == 'restrict' and not any(
                        class_of_service in cos_data['class_of_service_list'] for class_of_service in class_of_service_list):
                    is_class_of_service = True

                charge_code_data = rule['route']['charge_code']
                if charge_code_data['access_type'] == 'all':
                    is_charge_code = True
                elif not charge_code_list:
                    pass
                elif charge_code_data['access_type'] == 'allow' and any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True
                elif charge_code_data['access_type'] == 'restrict' and not any(charge_code in charge_code_data['charge_code_list'] for charge_code in charge_code_list):
                    is_charge_code = True

                tour_code_data = rule['route']['tour_code']
                if tour_code_data['access_type'] == 'all':
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_any' and tour_code_list:
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'if_blank' and not tour_code_list:
                    is_tour_code = True
                elif not tour_code_list:
                    pass
                elif tour_code_data['access_type'] == 'allow' and any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True
                elif tour_code_data['access_type'] == 'restrict' and not any(tour_code in tour_code_data['tour_code_list'] for tour_code in tour_code_list):
                    is_tour_code = True

                dot_data = rule['route']['date_of_travel']
                if dot_data['access_type'] == 'all':
                    is_dot = True
                elif not departure_date_list:
                    pass
                elif dot_data['access_type'] == 'allow' and all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True
                elif dot_data['access_type'] == 'restrict' and not all(
                        dot_data['start_date'] <= departure_date <= dot_data['end_date'] for departure_date in
                        departure_date_list):
                    is_dot = True

                total_data = util.get_tree_data(rule, ['route', 'total'])
                if not total_data or total_data['access_type'] == 'all':
                    is_total_amount = True
                elif total_data['access_type'] == 'less':
                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            is_total_amount = True
                    else:
                        if total_amount < less_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'greater':
                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            is_total_amount = True
                    else:
                        if total_amount > greater_amount:
                            is_total_amount = True
                elif total_data['access_type'] == 'between':
                    less_flag = greater_flag = False

                    is_less_equal = total_data['is_less_equal']
                    less_amount = total_data['less_amount']
                    if is_less_equal:
                        if total_amount <= less_amount:
                            less_flag = True
                    else:
                        if total_amount < less_amount:
                            less_flag = True

                    is_greater_equal = total_data['is_greater_equal']
                    greater_amount = total_data['greater_amount']
                    if is_greater_equal:
                        if total_amount >= greater_amount:
                            greater_flag = True
                    else:
                        if total_amount > greater_amount:
                            greater_flag = True

                    if less_flag and greater_flag:
                        is_total_amount = True

                result_2_list = [is_origin, is_destination, is_class_of_service, is_charge_code, is_tour_code, is_dot, is_total_amount]
                if not all(res for res in result_2_list):
                    continue

                pricing_data = copy.deepcopy(rec)
                if 'rule_list' in pricing_data:
                    pricing_data.pop('rule_list')

                rule.update({
                    'pricing_id': rec['id'],
                    'parent_data': pricing_data,
                    'rule_id': rule['id'],
                    'pricing_index': rec_idx,
                    'rule_index': rule_idx
                })
                return rule
        return {}

    def calculate_commission(self, price_data, commission_amount, agent_id, pax_count, infant_count=0, route_count=0, segment_count=0, **kwargs):
        original_commission = commission_amount
        total_charge = 0.0
        total_commission = 0.0
        total_discount = 0.0
        if 'charge_by_percentage' in price_data:
            charge_data = price_data['charge_by_percentage']
            if charge_data['percentage']:
                add_amount = commission_amount * charge_data['percentage'] / 100
                has_minimum = charge_data.get('has_minimum', True)
                has_maximum = charge_data.get('has_maximum', False)

                if has_minimum and add_amount < charge_data['minimum']:
                    add_amount = charge_data['minimum']
                if has_maximum and add_amount > charge_data['maximum']:
                    add_amount = charge_data['maximum']

                if add_amount <= original_commission:
                    total_charge += add_amount
                    original_commission -= add_amount
        if 'charge_by_amount' in price_data:
            charge_data = price_data['charge_by_amount']
            if charge_data['amount']:
                multiplier = 1
                if 'is_route' in charge_data and charge_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in charge_data and charge_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in charge_data and charge_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in charge_data and charge_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = charge_data['amount'] * multiplier
                if add_amount <= original_commission:
                    total_charge += add_amount
                    original_commission -= add_amount
        if 'commission_by_percentage' in price_data:
            com_data = price_data['commission_by_percentage']
            if com_data['percentage']:
                add_amount = commission_amount * com_data['percentage'] / 100

                has_minimum = com_data.get('has_minimum', True)
                has_maximum = com_data.get('has_maximum', False)

                if has_minimum and add_amount < com_data['minimum']:
                    add_amount = com_data['minimum']
                if has_maximum and add_amount > com_data['maximum']:
                    add_amount = com_data['maximum']

                if add_amount <= original_commission:
                    total_commission += add_amount
                    original_commission -= add_amount
        if 'commission_by_amount' in price_data:
            com_data = price_data['commission_by_amount']
            if com_data['amount']:
                multiplier = 1
                if 'is_route' in com_data and com_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in com_data and com_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in com_data and com_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in com_data and com_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = com_data['amount'] * multiplier
                if add_amount <= original_commission:
                    total_commission += add_amount
                    original_commission -= add_amount
        if 'discount_by_percentage' in price_data:
            com_data = price_data['discount_by_percentage']
            if com_data['percentage']:
                add_amount = total_commission * com_data['percentage'] / 100
                has_minimum = com_data.get('has_minimum', True)
                has_maximum = com_data.get('has_maximum', False)
                if has_minimum and add_amount < com_data['minimum']:
                    add_amount = com_data['minimum']
                if has_maximum and add_amount > com_data['maximum']:
                    add_amount = com_data['maximum']

                if total_commission >= add_amount:
                    total_discount += add_amount
                    total_commission -= add_amount
        if 'discount_by_amount' in price_data:
            com_data = price_data['discount_by_amount']
            if com_data['amount']:
                multiplier = 1
                if 'is_route' in com_data and com_data['is_route']:
                    multiplier *= route_count
                if 'is_segment' in com_data and com_data['is_segment']:
                    multiplier *= segment_count

                total_pax = 0
                if 'is_pax' in com_data and com_data['is_pax']:
                    total_pax += pax_count
                if 'is_infant' in com_data and com_data['is_infant']:
                    total_pax += infant_count

                if total_pax:
                    multiplier *= total_pax

                add_amount = com_data['amount'] * multiplier
                if total_commission >= add_amount:
                    total_discount += add_amount
                    total_commission -= add_amount

        payload = {
            'agent_id': agent_id,
            'commission_amount': round(total_commission),
            'charge_amount': round(total_charge),
            'discount_amount': round(total_discount),
        }
        return payload

    def get_commission_calculation(self, rule_obj, commission_amount, agent_id, upline_list, pax_count, infant_count=0, route_count=0, segment_count=0, **kwargs):
        com_data = rule_obj['commission']

        parent_charge_amount = 0.0
        parent_agent_id = ''
        # January 6, 2022 - SAM
        # Untuk melakukan pengecekkan apakah user memiliki parent agent (upline) atau tidak
        # Contoh ada parent agent, upline list [ A , B , C ]
        # upline_list[1:] => [ B, C ] => Parent Agentnya ada
        # Contoh tidak ada parent agent, upline list [ A ]
        # upline_list[1:] => [ ] => Parent Agentnya tidak ada
        if upline_list[1:]:
            parent_agent_id = upline_list[1]['id']
            parent_res = self.calculate_commission(com_data['parent'], commission_amount, upline_list[1]['id'], pax_count, infant_count, route_count, segment_count)
            parent_charge_amount = parent_res['charge_amount']
            if parent_charge_amount > commission_amount:
                parent_charge_amount = 0.0
            else:
                commission_amount -= parent_charge_amount

        ho_charge_amount = 0.0
        ho_agent_id = ''
        if upline_list:
            ho_agent_id = upline_list[-1]['id']
            ho_res = self.calculate_commission(com_data['ho'], commission_amount, upline_list[-1]['id'], pax_count, infant_count, route_count, segment_count)
            ho_charge_amount = ho_res['charge_amount']
            if ho_charge_amount > commission_amount:
                ho_charge_amount = 0.0
            else:
                commission_amount -= ho_charge_amount

        agent_res = self.calculate_commission(com_data['agent'], commission_amount, agent_id, pax_count, infant_count, route_count, segment_count)
        upline_res_list = []
        upline_head = 0
        for upline in upline_list[1:]:
            for idx, upline_obj in enumerate(com_data['upline_list']):
                if idx < upline_head:
                    continue

                if upline_obj['agent_type_code'] == upline['agent_type_id']['code']:
                    upline_head = idx + 1
                    upline_res = self.calculate_commission(upline_obj, commission_amount, upline['id'], pax_count, infant_count, route_count, segment_count)
                    upline_res_list.append(upline_res)
                    break

        agent_discount_amount = agent_res['discount_amount']
        if agent_discount_amount > commission_amount:
            agent_discount_amount = 0
        else:
            commission_amount -= agent_discount_amount

        agent_commission_amount = agent_res['commission_amount']
        if agent_commission_amount > commission_amount:
            # November 15, 2023 - SAM
            # Sementara pakai pendekatan kalau selisih nya kurang dari 1.0 masih valid
            # Case nya agent_commission_amount = 9102, commission_amount = 9101.93
            if (agent_commission_amount - commission_amount) < 1.0:
                commission_amount = 0.0
            else:
                agent_commission_amount = 0.0
        else:
            commission_amount -= agent_commission_amount

        for upline_res in upline_res_list:
            if upline_res['commission_amount'] > commission_amount:
                upline_res['commission_amount'] = 0.0
            else:
                commission_amount -= upline_res['commission_amount']

        residual_agent_id = ''
        if upline_list:
            residual_agent_id = upline_list[-1]['id']
            # January 6, 2022 - SAM
            # Untuk melakukan pengecekkan apakah user memiliki parent agent (upline) atau tidak
            # Contoh ada parent agent, upline list [ A , B , C ]
            # upline_list[1:] => [ B, C ] => Parent Agentnya ada
            # Contoh tidak ada parent agent, upline list [ A ]
            # upline_list[1:] => [ ] => Parent Agentnya tidak ada
            if upline_list[1:]:
                if com_data['residual_amount_to'] == 'parent':
                    residual_agent_id = upline_list[1]['id']

        payload = {
            'rule_id': rule_obj['id'],
            'section': 'commission',
            'agent_id': agent_id,
            'upline_list': upline_list,
            'pax_count': pax_count,
            'infant_count': infant_count,
            'route_count': route_count,
            'segment_count': segment_count,
            'parent_charge_amount': parent_charge_amount,
            'parent_agent_id': parent_agent_id,
            'ho_charge_amount': ho_charge_amount,
            'ho_agent_id': ho_agent_id,
            'agent_commission_amount': agent_commission_amount,
            'agent_discount_amount': agent_discount_amount,
            'upline_commission_list': upline_res_list,
            'residual_amount': commission_amount,
            'residual_agent_id': residual_agent_id
        }
        return payload


# November 12, 2021 - SAM
class RepricingToolsV2(object):
    def __init__(self, provider_type, context):
        self.provider_type = provider_type
        self.context = context
        self.agent_type = ''
        self.agent_id = ''
        self.agent_type_data = {}
        self.customer_parent_type = ''
        self.customer_parent_id = ''
        self.upline_list = []
        self.ho_agent_id = ''
        self.ticket_fare_list = []
        self.ancillary_fare_list = []
        self.provider_data_dict = {}
        self.agent_data_dict = {}
        self.customer_data_dict = {}
        self.agent_commission_data_dict = {}

        if self.context:
            upline_list = self.context.get('co_user_info', [])
            customer_parent_type = self.context.get('co_customer_parent_type_code', '')
            if not customer_parent_type:
                customer_parent_type = 'fpo'

            self.__dict__.update({
                'agent_type': self.context.get('co_agent_type_code', ''),
                'agent_id': self.context.get('co_agent_id', ''),
                'upline_list': upline_list,
                'customer_parent_type': customer_parent_type,
                'customer_parent_id': self.context.get('co_customer_parent_id', ''),
                'agent_type_data': upline_list[0]['agent_type_id'] if upline_list else {},
                'ho_agent_id': upline_list[-1]['id'] if upline_list else '',
            })

        self.provider_pricing = ProviderPricing(provider_type)
        self.agent_pricing = AgentPricing(self.agent_type)
        self.customer_pricing = CustomerPricing(self.agent_id)
        self.agent_commission = AgentCommission(self.agent_type)

    def _default_sc_summary_values(self):
        res = {
            'total_fare_amount': 0.0,
            'total_tax_amount': 0.0,
            'total_upsell_amount': 0.0,
            'total_commission_amount': 0.0
        }
        return res

    def ceil(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = ceil(temp) * digit
        return res

    def floor(self, data, number):
        digit = 1
        for i in range(number):
            digit *= 10
        temp = data / digit
        res = floor(temp) * digit
        return res

    def round(self, data, agent_data={}):
        # June 27, 2023 - SAM
        # Karena mostly data decimal 2 terbanyak, sementara hardcode untuk default 2 decimal di belakang koma
        data_with_two_dec = float(data) * 100
        data_round = round(data_with_two_dec)
        data = data_round / 100
        if not agent_data:
            # res = round(data)
            res = data
            return res

        if agent_data['rounding_amount_type'] == 'round':
            digit = 1
            for i in range(agent_data['rounding_places']):
                digit *= 10
            temp = data / digit
            res = round(temp) * digit
        elif agent_data['rounding_amount_type'] == 'ceil':
            res = self.ceil(data, agent_data['rounding_places'])
        elif agent_data['rounding_amount_type'] == 'floor':
            res = self.floor(data, agent_data['rounding_places'])
        else:
            res = data
        return res

    def clear_fare_list(self):
        self.ticket_fare_list = []
        self.ancillary_fare_list = []

    def add_ticket_fare(self, fare_data):
        self.ticket_fare_list.append(fare_data)

    def add_ancillary_fare(self, fare_data):
        self.ancillary_fare_list.append(fare_data)

    def get_provider_less(self, agent_id='', agent_type_code='', provider='', carrier_code='', origin='', origin_city='', origin_country='', destination='', destination_city='', destination_country='', departure_date_list=[], context={}, **kwargs):
        if not self.ticket_fare_list:
            raise Exception('Ticket Fare List is empty')

        class_of_service_list = []
        charge_code_list = []
        tour_code_list = []
        currency_code_list = []
        pax_count_dict = {
            'ADT': 0
        }
        total_amount = Decimal("0.0")
        for fare in self.ticket_fare_list:
            if fare.get('class_of_service') and fare['class_of_service'] not in class_of_service_list:
                class_of_service_list.append(fare['class_of_service'])

            if fare.get('tour_code') and fare['tour_code'] not in tour_code_list:
                tour_code_list.append(fare['tour_code'])

            if 'service_charges' not in fare:
                continue
                # raise Exception('Service Charges is not found')

            for idx, sc in enumerate(fare['service_charges']):
                charge_code = sc['charge_code']
                if charge_code not in charge_code_list:
                    charge_code_list.append(charge_code)
                currency_code = sc['currency']
                if currency_code not in currency_code_list:
                    currency_code_list.append(currency_code)

                pax_type = sc['pax_type']
                pax_count = sc['pax_count']
                if pax_type not in pax_count_dict or pax_count_dict[pax_type] < pax_count:
                    pax_count_dict[pax_type] = pax_count

                charge_type = sc.get('charge_type', '')
                amount = sc.get('amount', 0.0)
                if pax_count and amount and charge_type not in ['ROC', 'RAC']:
                    total = Decimal(str(pax_count)) * Decimal(str(amount))
                    total_amount += total
        total_amount = float(total_amount)

        rule_param = {
            'agent_id': agent_id,
            'agent_type_code': agent_type_code,
            'provider_code': provider,
            'carrier_code': carrier_code,
            'origin_code': origin,
            'origin_city': origin_city,
            'origin_country': origin_country,
            'destination_code': destination,
            'destination_city': destination_city,
            'destination_country': destination_country,
            'class_of_service_list': class_of_service_list,
            'tour_code_list': tour_code_list,
            'charge_code_list': charge_code_list,
            'pricing_datetime': datetime.now().strftime(FORMAT_DATETIME),
            'departure_date_list': departure_date_list,
            'currency_code_list': currency_code_list,
            'context': context,
            'total_amount': total_amount,
        }
        rule_obj = self.provider_pricing.get_pricing_data(**rule_param)

        pricing_less_list = []
        for pax_type, pax_count in pax_count_dict.items():
            if not pax_count:
                continue

            res = self.provider_pricing.get_less_calculation(rule_obj, pax_type)
            pricing_less_list.append(res)

        payload = {
            'pricing_less_list': pricing_less_list,
            'rule_data': rule_param,
            'provider_pricing_data': rule_obj,
        }
        return payload

    def calculate_pricing(self, provider='', carrier_code='', origin='', origin_city='', origin_country='', destination='', destination_city='', destination_country='', class_of_service_list=[], charge_code_list=[], tour_code_list=[], route_count=0, segment_count=0, show_commission=True, show_upline_commission=True, pricing_datetime=None, departure_date_list=[], upsell_by_amount_charge=True, context={}, **kwargs):
        '''
            pricing_datetime = %Y-%m-%d %H:%M:%S
        '''
        '''
            Note June 16, 2022
            ROC : 10
            RAC : 19
            DISC : 1
        '''
        if not self.ticket_fare_list:
            _logger.error('Ticket Fare List is empty')
            return False
            # raise Exception('Ticket Fare List is empty')

        if not pricing_datetime:
            pricing_datetime = datetime.now().strftime(FORMAT_DATETIME)

        # sc_temp = copy.deepcopy(self.ticket_fare_list[0]['service_charges'][0])

        # Ada nama field total yang berbeda di webservice lain jadi dibuat dinamis
        # total_field_name = 'total'
        # for key in sc_temp.keys():
        #     if 'total' in key:
        #         total_field_name = key
        #         break

        ## 2-1

        # April 13, 2022 - SAM
        # Menambahkan mekanisme untuk auto mendapatkan class of service list dan charge code list
        temp_cos_list = []
        temp_tc_list = []
        temp_sc_list = []
        class_of_service_list = []
        charge_code_list = []
        currency_code_list = []
        tour_code_list = []
        total_amount = Decimal("0.0")
        for fare in self.ticket_fare_list:
            cos = fare.get('class_of_service', '')
            if cos and cos not in class_of_service_list:
                class_of_service_list.append(cos)
            tc = fare.get('tour_code', '')
            if tc and tc not in tour_code_list:
                tour_code_list.append(tc)
            for sc in fare.get('service_charges', []):
                c_code = sc.get('charge_code', '')
                if c_code and c_code not in charge_code_list:
                    charge_code_list.append(c_code)
                cur_code = sc.get('currency', '')
                if cur_code and cur_code not in currency_code_list:
                    currency_code_list.append(cur_code)

                charge_type = sc.get('charge_type', '')
                pax_count = sc.get('pax_count', 0)
                amount = sc.get('amount', 0.0)
                if pax_count and amount and charge_type not in ['ROC', 'RAC']:
                    total = Decimal(str(pax_count)) * Decimal(str(amount))
                    total_amount += total
        total_amount = float(total_amount)

        # if not class_of_service_list:
        #     class_of_service_list = temp_cos_list
        # if not tour_code_list:
        #     tour_code_list = temp_tc_list
        # if not charge_code_list:
        #     charge_code_list = temp_sc_list
        # END

        rule_param = {
            'provider_code': provider,
            'carrier_code': carrier_code,
            'origin_code': origin,
            'origin_city': origin_city,
            'origin_country': origin_country,
            'destination_code': destination,
            'destination_city': destination_city,
            'destination_country': destination_country,
            'class_of_service_list': class_of_service_list,
            'charge_code_list': charge_code_list,
            'tour_code_list': tour_code_list,
            'pricing_datetime': pricing_datetime,
            'departure_date_list': departure_date_list,
            'currency_code_list': currency_code_list,
            'upsell_by_amount_charge': upsell_by_amount_charge,
            'context': context,
            'total_amount': total_amount
        }
        co_ho_id = context['co_ho_id'] if context and context.get('co_ho_id') else ''
        rule_key_list = [provider, carrier_code, origin, origin_city, origin_country, destination, destination_city, destination_country, pricing_datetime, self.provider_type, str(self.agent_type), str(self.agent_id), str(self.customer_parent_type), str(self.customer_parent_id), '-', str(co_ho_id), '-', str(total_amount)] + class_of_service_list + charge_code_list + tour_code_list + currency_code_list
        rule_key = ''.join(rule_key_list)
        if rule_key in self.provider_data_dict:
            rule_obj = self.provider_data_dict[rule_key]
        else:
            rule_obj = self.provider_pricing.get_pricing_data(self.agent_id, self.agent_type, **rule_param)
            self.provider_data_dict[rule_key] = rule_obj

        if rule_key in self.agent_data_dict:
            agent_obj = self.agent_data_dict[rule_key]
        else:
            agent_obj = self.agent_pricing.get_pricing_data(self.provider_type, self.agent_id, **rule_param)
            self.agent_data_dict[rule_key] = agent_obj

        if rule_key in self.customer_data_dict:
            cust_obj = self.customer_data_dict[rule_key]
        else:
            cust_obj = self.customer_pricing.get_pricing_data(self.customer_parent_type, self.customer_parent_id, self.provider_type, **rule_param)
            self.customer_data_dict[rule_key] = cust_obj

        if rule_key in self.agent_commission_data_dict:
            agent_com_obj = self.agent_commission_data_dict[rule_key]
        else:
            agent_com_obj = self.agent_commission.get_pricing_data(self.provider_type, self.agent_id, **rule_param)
            self.agent_commission_data_dict[rule_key] = agent_com_obj

        pricing_type = rule_obj.get('pricing_type', 'standard')
        # September 5, 2022 - SAM
        # if pricing_type == 'from_nta':
        #     show_commission = True
        #     show_upline_commission = True
        # END
        ## 1-2
        pax_count_dict = {
            # 'ADT': 0
        }
        sc_summary_dict = {
            # 'ADT': self._default_sc_summary_values()
        }
        # class_of_service_list = class_of_service_list if class_of_service_list else []
        # charge_code_list = charge_code_list if charge_code_list else []
        total_commission_amount = 0.0
        total_reservation_amount = 0.0
        sc_temp = None
        pax_type_list = []

        # September 15, 2023 - SAM
        sc_temp_repo = {}
        # END

        has_roc_rac = False
        for fare in self.ticket_fare_list:
            # if fare.get('class_of_service') and fare['class_of_service'] not in class_of_service_list:
            #     class_of_service_list.append(fare['class_of_service'])

            if 'service_charges' not in fare:
                continue
                # raise Exception('Service Charges is not found')

            del_sc_id_list = []
            rac_nta_list = []
            for idx, sc in enumerate(fare['service_charges']):
                if not sc_temp:
                    sc_temp = copy.deepcopy(sc)

                charge_code = sc['charge_code']
                # if charge_code not in charge_code_list:
                #     charge_code_list.append(charge_code)

                pax_type = sc['pax_type']

                if pax_type not in sc_temp_repo:
                    sc_temp_repo[pax_type] = copy.deepcopy(sc)

                if pax_type not in sc_summary_dict:
                    sc_summary_dict[pax_type] = self._default_sc_summary_values()
                    pax_type_list.append(pax_type)
                sc_data = sc_summary_dict[pax_type]

                pax_count = sc['pax_count']
                if pax_type not in pax_count_dict or pax_count_dict[pax_type] < pax_count:
                    pax_count_dict[pax_type] = pax_count

                amount = self.round(sc['amount'])
                sc_total = amount * pax_count
                sc.update({
                    'amount': amount,
                    # 'foreign_amount': amount,
                    'total': sc_total
                })
                if sc['charge_type'] == 'FARE':
                    sc_data['total_fare_amount'] += sc_total
                    total_reservation_amount += sc_total
                elif sc['charge_type'] == 'ROC':
                    has_roc_rac = True
                    sc_data['total_upsell_amount'] += sc_total
                elif sc['charge_type'] == 'RAC':
                    has_roc_rac = True
                    if pricing_type == 'from_nta':
                        rac_nta_list.append(sc)
                    elif pricing_type == 'from_sales':
                        del_sc_id_list.append(idx)
                    else:
                        # standard
                        sc_total = -sc_total
                        sc_data['total_commission_amount'] += sc_total
                        total_commission_amount += sc_total
                        del_sc_id_list.append(idx)
                else:
                    sc_data['total_tax_amount'] += sc_total
                    total_reservation_amount += sc_total
                    sc.update({
                        'charge_type': 'TAX',
                    })

            for sc in rac_nta_list:
                pax_type = sc['pax_type']
                if pax_type not in sc_summary_dict:
                    sc_summary_dict[pax_type] = self._default_sc_summary_values()
                sc_data = sc_summary_dict[pax_type]

                total = sc['total']
                if sc_data['total_tax_amount'] >= total:
                    sc_data['total_tax_amount'] += total
                    sc.update({
                        'charge_type': 'TAX',
                    })
                else:
                    sc_data['total_fare_amount'] += total,
                    sc.update({
                        'charge_type': 'FARE',
                    })

            for idx in del_sc_id_list[::-1]:
                fare['service_charges'].pop(idx)

        if not sc_temp:
            _logger.error('Service Charge detail is not found')
            return False
            # raise Exception('Service Charge detail is not found')

        if not pax_type_list:
            _logger.error('Pax Type is empty')
            return False

        pax_type_list.sort()
        default_pax_type = pax_type_list[0]

        for fare in self.ancillary_fare_list:
            if 'service_charges' not in fare:
                continue
                # raise Exception('Service Charges is not found')
            elif not fare['service_charges']:
                continue

            del_sc_id_list = []
            for idx, sc in enumerate(fare['service_charges']):
                if sc['charge_type'] == 'FARE':
                    total_reservation_amount += sc['amount']
                # elif sc['charge_type'] == 'ROC':
                #     continue
                elif sc['charge_type'] == 'RAC':
                    if pricing_type == 'from_nta':
                        total_reservation_amount += sc['amount']
                        sc.update({
                            'charge_type': 'TAX',
                        })
                    elif pricing_type == 'from_sales':
                        del_sc_id_list.append(idx)
                    else:
                        total_commission_amount += -sc['amount']
                        del_sc_id_list.append(idx)
                else:
                    total_reservation_amount += sc['amount']

            for idx in del_sc_id_list[::-1]:
                fare['service_charge'].pop(idx)

        fare_data = self.ticket_fare_list[-1]

        # June 16, 2022 - SAM
        # Buat mekanisme untuk memisahkan upsell
        total_all_pax_count = 0
        for pax_count in pax_count_dict.values():
            total_all_pax_count += pax_count
        # END

        # December 17, 2021 - SAM
        # Flow 2
        is_agent_commission_applied = False
        tkt_res_lib = {}
        tkt_rsv_res_lib = {}
        for pricing_idx in range(3):
            for pax_type, sc_sum in sc_summary_dict.items():
                pax_count = pax_count_dict[pax_type]
                if pax_count == 0:
                    _logger.error('Pax Count 0, Pax Type %s' % pax_type)
                    continue

                fare_amount = sc_sum['total_fare_amount'] / pax_count
                tax_amount = sc_sum['total_tax_amount'] / pax_count
                roc_amount = sc_sum['total_upsell_amount'] / pax_count
                rac_amount = sc_sum['total_commission_amount'] / pax_count

                # TEST ONLY
                # fare_amount = 612000
                # tax_amount = 410759

                sub_total = fare_amount + tax_amount

                calc_param = {
                    'fare_amount': fare_amount,
                    'roc_amount': roc_amount,
                    'rac_amount': rac_amount,
                    'pax_type': pax_type,
                    'route_count': route_count,
                    'segment_count': segment_count,
                    'upsell_by_amount_charge': upsell_by_amount_charge,
                }
                if pricing_idx == 0:
                    if rule_obj:
                        tkt_res = self.provider_pricing.get_ticketing_calculation(rule_obj=rule_obj, tax_amount=tax_amount, **calc_param)
                        tkt_res_lib[pax_type] = tkt_res

                        if tkt_res['upsell_amount']:
                            if pax_type in sc_temp_repo:
                                sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                            else:
                                sc_values = copy.deepcopy(sc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'roc',
                                'pax_type': pax_type,
                                'pax_count': pax_count,
                                'amount': tkt_res['upsell_amount'],
                                'foreign_amount': tkt_res['upsell_amount'],
                                'total': tkt_res['upsell_amount'] * pax_count,
                            })
                            fare_data['service_charges'].append(sc_values)
                            sc_total = tkt_res['upsell_amount'] * pax_count
                            total_reservation_amount += sc_total

                        tax_amount += tkt_res['upsell_amount']
                        sub_total += tkt_res['upsell_amount']

                        # if tkt_res['ho_commission_amount']:
                        #     if tkt_res['ho_commission_amount'] > 0:
                        #         if show_commission and show_upline_commission and self.ho_agent_id:
                        #             if pax_type in sc_temp_repo:
                        #                 sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                        #             else:
                        #                 sc_values = copy.deepcopy(sc_temp)
                        #             sc_values.update({
                        #                 'charge_type': 'RAC',
                        #                 'charge_code': 'racho',
                        #                 'pax_type': pax_type,
                        #                 'pax_count': pax_count,
                        #                 'amount': -tkt_res['ho_commission_amount'],
                        #                 'foreign_amount': -tkt_res['ho_commission_amount'],
                        #                 'total': -tkt_res['ho_commission_amount'] * pax_count,
                        #                 'commission_agent_id': self.ho_agent_id,
                        #             })
                        #             fare_data['service_charges'].append(sc_values)
                        #     else:
                        #         # # April 14, 2022 - SAM
                        #         # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                        #         # temp_ho_com_total = -tkt_res['ho_commission_amount'] * pax_count
                        #         # total_commission_amount += temp_ho_com_total
                        #         # # END
                        #         pass

                        # tkt_commission_total = tkt_res['commission_amount'] * pax_count
                        # total_commission_amount += tkt_commission_total
                        #
                        # tax_amount += tkt_res['upsell_amount']
                        # sub_total += tkt_res['upsell_amount']

                        # October 18, 2023 - SAM
                        ho_commission_amount = tkt_res.get('ho_commission_amount', 0.0)
                        tax_ho_commission_amount = tkt_res.get('tax_ho_commission_amount', 0.0)
                        commission_amount = tkt_res.get('commission_amount', 0.0)
                        tax_commission_amount = tkt_res.get('tax_commission_amount', 0.0)
                        total_ho_commission_amount = ho_commission_amount * pax_count
                        total_tax_ho_commission_amount = tax_ho_commission_amount * pax_count
                        total_tax_commission_amount = tax_commission_amount * pax_count
                        pricing_breakdown = rule_obj.get('pricing_breakdown', False)

                        if ho_commission_amount:
                            if ho_commission_amount > 0:
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'racho',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -ho_commission_amount,
                                            'foreign_amount': -ho_commission_amount,
                                            'total': -total_ho_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACHSP',
                                            'charge_code': 'rachosvc',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -ho_commission_amount,
                                            'foreign_amount': -ho_commission_amount,
                                            'total': -total_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCHSP',
                                            'charge_code': 'rochosvc',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': ho_commission_amount,
                                            'foreign_amount': ho_commission_amount,
                                            'total': total_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        if tax_ho_commission_amount:
                            if tax_ho_commission_amount > 0:
                                commission_amount -= tax_ho_commission_amount
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rachotax',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_ho_commission_amount,
                                            'foreign_amount': -tax_ho_commission_amount,
                                            'total': -total_tax_ho_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACHVP',
                                            'charge_code': 'rachovat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_ho_commission_amount,
                                            'foreign_amount': -tax_ho_commission_amount,
                                            'total': -total_tax_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCHVP',
                                            'charge_code': 'rochovat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_ho_commission_amount,
                                            'foreign_amount': tax_ho_commission_amount,
                                            'total': total_tax_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    # else:
                                    #     if pax_type in sc_temp_repo:
                                    #         sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    #     else:
                                    #         sc_values = copy.deepcopy(sc_temp)
                                    #     sc_values.update({
                                    #         'charge_type': 'ROC',
                                    #         'charge_code': 'rochovat',
                                    #         'pax_type': pax_type,
                                    #         'pax_count': pax_count,
                                    #         'amount': tax_ho_commission_amount,
                                    #         'foreign_amount': tax_ho_commission_amount,
                                    #         'total': total_tax_ho_commission_amount,
                                    #     })
                                    #     fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        if tax_commission_amount:
                            if tax_commission_amount < 0:
                                commission_amount += tax_commission_amount
                                if show_commission:
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACAVP',
                                            'charge_code': 'racvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_commission_amount,
                                            'foreign_amount': tax_commission_amount,
                                            'total': total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCAVP',
                                            'charge_code': 'rocvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_commission_amount,
                                            'foreign_amount': -tax_commission_amount,
                                            'total': -total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        sub_total_commission_amount = commission_amount * pax_count
                        if commission_amount:
                            if commission_amount > 0:
                                total_commission_amount += sub_total_commission_amount
                            else:
                                if total_commission_amount >= abs(sub_total_commission_amount):
                                    total_commission_amount -= abs(sub_total_commission_amount)
                                    if pricing_breakdown:
                                        diff_commission_amount = abs(sub_total_commission_amount)
                                        base_diff_commission_amount = abs(commission_amount)
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACCHG',
                                            'charge_code': 'racchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -base_diff_commission_amount,
                                            'foreign_amount': -base_diff_commission_amount,
                                            'total': -diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCCHG',
                                            'charge_code': 'rocchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': base_diff_commission_amount,
                                            'foreign_amount': base_diff_commission_amount,
                                            'total': diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                else:
                                    if pricing_breakdown and total_commission_amount > 0:
                                        diff_commission_amount = total_commission_amount
                                        base_diff_commission_amount = diff_commission_amount / pax_count
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACCHG',
                                            'charge_code': 'racchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -base_diff_commission_amount,
                                            'foreign_amount': -base_diff_commission_amount,
                                            'total': -diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCCHG',
                                            'charge_code': 'rocchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': base_diff_commission_amount,
                                            'foreign_amount': base_diff_commission_amount,
                                            'total': diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                    diff_commission_amount = abs(sub_total_commission_amount) - total_commission_amount
                                    base_diff_commission_amount = diff_commission_amount / pax_count
                                    total_commission_amount = 0.0
                                    # diff_commission_amount = abs(sub_total_commission_amount)
                                    # base_diff_commission_amount = abs(commission_amount)
                                    if pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'ROC',
                                        'charge_code': 'rocadj',
                                        'pax_type': pax_type,
                                        'pax_count': pax_count,
                                        'amount': base_diff_commission_amount,
                                        'foreign_amount': base_diff_commission_amount,
                                        'total': diff_commission_amount,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                                    tax_amount += tkt_res['upsell_amount']
                                    sub_total += tkt_res['upsell_amount']
                                    sc_total = diff_commission_amount
                                    tax_amount += base_diff_commission_amount
                                    sub_total += base_diff_commission_amount
                                    total_reservation_amount += sc_total
                        # END

                    # Pembulatan
                    round_total = self.round(sub_total, self.agent_type_data)
                    diff_total = round_total - sub_total
                    if diff_total:
                        sc_total = diff_total * pax_count
                        if pax_type in sc_temp_repo:
                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                        else:
                            sc_values = copy.deepcopy(sc_temp)
                        sc_values.update({
                            'charge_type': 'ROC',
                            'charge_code': 'rocround',
                            'pax_type': pax_type,
                            'pax_count': pax_count,
                            'amount': diff_total,
                            'foreign_amount': diff_total,
                            'total': sc_total,
                        })
                        fare_data['service_charges'].append(sc_values)
                        total_reservation_amount += sc_total
                        # December 21, 2021 - SAM
                        # Sementara pembulatan masuk ke komisi ho agar tidak bingung saat penghitungan komisi agent
                        # total_commission_amount += sc_total
                        if self.ho_agent_id and diff_total > 0:
                            if pax_type in sc_temp_repo:
                                sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                            else:
                                sc_values = copy.deepcopy(sc_temp)
                            sc_values.update({
                                'charge_type': 'RAC',
                                'charge_code': 'racroundho',
                                'pax_type': pax_type,
                                'pax_count': pax_count,
                                'amount': -diff_total,
                                'foreign_amount': -diff_total,
                                'total': -diff_total * pax_count,
                                'commission_agent_id': self.ho_agent_id,
                            })
                            fare_data['service_charges'].append(sc_values)
                        # END
                    # Pembulatan END

                if pricing_idx == 1:
                    if agent_obj:
                        agent_tkt = self.agent_pricing.get_ticketing_calculation(rule_obj=agent_obj, tax_amount=tax_amount, tkt_res=tkt_res_lib.get(pax_type, None), **calc_param)

                        if agent_tkt['upsell_amount']:
                            if pax_type in sc_temp_repo:
                                sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                            else:
                                sc_values = copy.deepcopy(sc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'rocagt',
                                'pax_type': pax_type,
                                'pax_count': pax_count,
                                'amount': agent_tkt['upsell_amount'],
                                'foreign_amount': agent_tkt['upsell_amount'],
                                'total': agent_tkt['upsell_amount'] * pax_count,
                            })
                            fare_data['service_charges'].append(sc_values)
                            sc_total = agent_tkt['upsell_amount'] * pax_count
                            total_reservation_amount += sc_total

                        # if agent_tkt['commission_amount']:
                        #     if agent_tkt['commission_amount'] > 0:
                        #         if show_commission:
                        #             if pax_type in sc_temp_repo:
                        #                 sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                        #             else:
                        #                 sc_values = copy.deepcopy(sc_temp)
                        #             sc_values.update({
                        #                 'charge_type': 'RAC',
                        #                 'charge_code': 'rac',
                        #                 'pax_type': pax_type,
                        #                 'pax_count': pax_count,
                        #                 'amount': -agent_tkt['commission_amount'],
                        #                 'foreign_amount': -agent_tkt['commission_amount'],
                        #                 'total': -agent_tkt['commission_amount'] * pax_count,
                        #             })
                        #             fare_data['service_charges'].append(sc_values)
                        #     else:
                        #         # April 14 2022 - SAM
                        #         # Mengurangi komisi apabila minus
                        #         temp_total_com_amount = -agent_tkt['commission_amount'] * pax_count
                        #         total_commission_amount -= temp_total_com_amount
                        #         # END
                        #
                        # if agent_tkt['ho_commission_amount']:
                        #     if agent_tkt['ho_commission_amount'] > 0:
                        #         if show_commission and show_upline_commission and self.ho_agent_id:
                        #             if pax_type in sc_temp_repo:
                        #                 sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                        #             else:
                        #                 sc_values = copy.deepcopy(sc_temp)
                        #             sc_values.update({
                        #                 'charge_type': 'RAC',
                        #                 'charge_code': 'racagtho',
                        #                 'pax_type': pax_type,
                        #                 'pax_count': pax_count,
                        #                 'amount': -agent_tkt['ho_commission_amount'],
                        #                 'foreign_amount': -agent_tkt['ho_commission_amount'],
                        #                 'total': -agent_tkt['ho_commission_amount'] * pax_count,
                        #                 'commission_agent_id': self.ho_agent_id,
                        #             })
                        #             fare_data['service_charges'].append(sc_values)
                        #     else:
                        #         # # April 14, 2022 - SAM
                        #         # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                        #         # temp_total_com_amount = -agent_tkt['ho_commission_amount'] * pax_count
                        #         # total_commission_amount += temp_total_com_amount
                        #         # # END
                        #         pass

                        tax_amount += agent_tkt['upsell_amount']

                        # October 17, 2023 - SAM
                        ho_commission_amount = agent_tkt.get('ho_commission_amount', 0.0)
                        tax_ho_commission_amount = agent_tkt.get('tax_ho_commission_amount', 0.0)
                        commission_amount = agent_tkt.get('commission_amount', 0.0)
                        tax_commission_amount = agent_tkt.get('tax_commission_amount', 0.0)
                        total_ho_commission_amount = ho_commission_amount * pax_count
                        total_tax_ho_commission_amount = tax_ho_commission_amount * pax_count
                        total_tax_commission_amount = tax_commission_amount * pax_count
                        pricing_breakdown = agent_obj.get('pricing_breakdown', False)

                        if ho_commission_amount:
                            if ho_commission_amount > 0:
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'racagtho',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -ho_commission_amount,
                                            'foreign_amount': -ho_commission_amount,
                                            'total': -total_ho_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACHSA',
                                            'charge_code': 'racagthosvc',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -ho_commission_amount,
                                            'foreign_amount': -ho_commission_amount,
                                            'total': -total_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCHSA',
                                            'charge_code': 'rocagthosvc',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': ho_commission_amount,
                                            'foreign_amount': ho_commission_amount,
                                            'total': total_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        if tax_ho_commission_amount:
                            if tax_ho_commission_amount > 0:
                                commission_amount -= tax_ho_commission_amount
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'racagthotax',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_ho_commission_amount,
                                            'foreign_amount': -tax_ho_commission_amount,
                                            'total': -total_tax_ho_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACHVA',
                                            'charge_code': 'racagthovat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_ho_commission_amount,
                                            'foreign_amount': -tax_ho_commission_amount,
                                            'total': -total_tax_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCHVA',
                                            'charge_code': 'rocagthovat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_ho_commission_amount,
                                            'foreign_amount': tax_ho_commission_amount,
                                            'total': total_tax_ho_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    # else:
                                    #     if pax_type in sc_temp_repo:
                                    #         sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    #     else:
                                    #         sc_values = copy.deepcopy(sc_temp)
                                    #     sc_values.update({
                                    #         'charge_type': 'ROC',
                                    #         'charge_code': 'rocagthovat',
                                    #         'pax_type': pax_type,
                                    #         'pax_count': pax_count,
                                    #         'amount': tax_ho_commission_amount,
                                    #         'foreign_amount': tax_ho_commission_amount,
                                    #         'total': total_tax_ho_commission_amount,
                                    #     })
                                    #     fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        if tax_commission_amount:
                            if tax_commission_amount < 0:
                                commission_amount += tax_commission_amount
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'racagttax',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_commission_amount,
                                            'foreign_amount': tax_commission_amount,
                                            'total': total_tax_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACAVA',
                                            'charge_code': 'racagtvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_commission_amount,
                                            'foreign_amount': tax_commission_amount,
                                            'total': total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCAVA',
                                            'charge_code': 'rocagtvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_commission_amount,
                                            'foreign_amount': -tax_commission_amount,
                                            'total': -total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        sub_total_commission_amount = commission_amount * pax_count
                        if commission_amount:
                            if commission_amount > 0:
                                if show_commission:
                                    if pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'rac',
                                        'pax_type': pax_type,
                                        'pax_count': pax_count,
                                        'amount': -commission_amount,
                                        'foreign_amount': -commission_amount,
                                        'total': -sub_total_commission_amount,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                            else:
                                if total_commission_amount >= abs(sub_total_commission_amount):
                                    total_commission_amount -= abs(sub_total_commission_amount)
                                    if pricing_breakdown:
                                        diff_commission_amount = abs(sub_total_commission_amount)
                                        base_diff_commission_amount = abs(commission_amount)
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACCHG',
                                            'charge_code': 'racagtchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -base_diff_commission_amount,
                                            'foreign_amount': -base_diff_commission_amount,
                                            'total': -diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCCHG',
                                            'charge_code': 'rocagtchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': base_diff_commission_amount,
                                            'foreign_amount': base_diff_commission_amount,
                                            'total': diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                else:
                                    if pricing_breakdown and total_commission_amount > 0:
                                        diff_commission_amount = total_commission_amount
                                        base_diff_commission_amount = diff_commission_amount / pax_count
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACCHG',
                                            'charge_code': 'racchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -base_diff_commission_amount,
                                            'foreign_amount': -base_diff_commission_amount,
                                            'total': -diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCCHG',
                                            'charge_code': 'rocchg',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': base_diff_commission_amount,
                                            'foreign_amount': base_diff_commission_amount,
                                            'total': diff_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                    diff_commission_amount = abs(sub_total_commission_amount) - total_commission_amount
                                    base_diff_commission_amount = diff_commission_amount / pax_count
                                    total_commission_amount = 0.0
                                    # diff_commission_amount = abs(sub_total_commission_amount)
                                    # base_diff_commission_amount = abs(commission_amount)
                                    if pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'ROC',
                                        'charge_code': 'rocagtadj',
                                        'pax_type': pax_type,
                                        'pax_count': pax_count,
                                        'amount': base_diff_commission_amount,
                                        'foreign_amount': base_diff_commission_amount,
                                        'total': diff_commission_amount,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                                    sc_total = diff_commission_amount
                                    total_reservation_amount += sc_total
                                    tax_amount += base_diff_commission_amount
                        # END
                if pricing_idx == 2:
                    if cust_obj:
                        cust_tkt = self.customer_pricing.get_ticketing_calculation(cust_obj, tax_amount=tax_amount, **calc_param)

                        if cust_tkt['upsell_amount']:
                            if pax_type in sc_temp_repo:
                                sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                            else:
                                sc_values = copy.deepcopy(sc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'roccust',
                                'pax_type': pax_type,
                                'pax_count': pax_count,
                                'amount': cust_tkt['upsell_amount'],
                                'foreign_amount': cust_tkt['upsell_amount'],
                                'total': cust_tkt['upsell_amount'] * pax_count,
                            })
                            fare_data['service_charges'].append(sc_values)
                            sc_total = cust_tkt['upsell_amount'] * pax_count
                            total_reservation_amount += sc_total

                        tax_amount += cust_tkt['upsell_amount']

                        commission_amount = cust_tkt.get('commission_amount', 0.0)
                        tax_commission_amount = cust_tkt.get('tax_commission_amount', 0.0)
                        total_tax_commission_amount = tax_commission_amount * pax_count
                        pricing_breakdown = cust_obj.get('pricing_breakdown', False)

                        if tax_commission_amount:
                            if tax_commission_amount < 0:
                                commission_amount += tax_commission_amount
                                if show_commission:
                                    if show_upline_commission and self.ho_agent_id:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'raccusttax',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_commission_amount,
                                            'foreign_amount': tax_commission_amount,
                                            'total': total_tax_commission_amount,
                                            'commission_agent_id': self.ho_agent_id,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACAVC',
                                            'charge_code': 'raccustvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': tax_commission_amount,
                                            'foreign_amount': tax_commission_amount,
                                            'total': total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCAVC',
                                            'charge_code': 'roccustvat',
                                            'pax_type': pax_type,
                                            'pax_count': pax_count,
                                            'amount': -tax_commission_amount,
                                            'foreign_amount': -tax_commission_amount,
                                            'total': -total_tax_commission_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            else:
                                pass

                        if commission_amount:
                            if commission_amount > 0:
                                if show_commission:
                                    if pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'rac',
                                        'pax_type': pax_type,
                                        'pax_count': pax_count,
                                        'amount': -commission_amount,
                                        'foreign_amount': -commission_amount,
                                        'total': -commission_amount * pax_count,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                            else:
                                # April 14, 2022 - SAM
                                # Mengurangi komisi agent
                                # temp_total_com_amount = -cust_tkt['commission_amount'] * pax_count
                                # total_commission_amount -= temp_total_com_amount
                                # END
                                # October 18, 2023 - SAM
                                # Update mekanisme
                                sub_total_commission_amount = commission_amount * pax_count
                                # if total_commission_amount >= abs(sub_total_commission_amount):
                                #     total_commission_amount -= abs(sub_total_commission_amount)
                                # else:
                                # diff_commission_amount = abs(sub_total_commission_amount) - total_commission_amount
                                # base_diff_commission_amount = diff_commission_amount / pax_count
                                # total_commission_amount = 0.0
                                diff_commission_amount = abs(sub_total_commission_amount)
                                base_diff_commission_amount = abs(commission_amount)
                                if pax_type in sc_temp_repo:
                                    sc_values = copy.deepcopy(sc_temp_repo[pax_type])
                                else:
                                    sc_values = copy.deepcopy(sc_temp)
                                sc_values.update({
                                    'charge_type': 'ROC',
                                    'charge_code': 'roccustadj',
                                    'pax_type': pax_type,
                                    'pax_count': pax_count,
                                    'amount': base_diff_commission_amount,
                                    'foreign_amount': base_diff_commission_amount,
                                    'total': diff_commission_amount,
                                })
                                fare_data['service_charges'].append(sc_values)
                                sc_total = diff_commission_amount
                                total_reservation_amount += sc_total
                                tax_amount += base_diff_commission_amount
                                # END

            ## 3
            for fare in self.ancillary_fare_list:
                if 'service_charges' not in fare:
                    continue
                    # raise Exception('Service Charges is not found')
                elif not fare['service_charges']:
                    continue

                fare_amount = 0.0
                tax_amount = 0.0
                del_sc_id_list = []
                for idx, sc in enumerate(fare['service_charges']):
                    if sc['charge_type'] == 'FARE':
                        fare_amount += sc['amount']
                    # elif sc['charge_type'] == 'ROC':
                    #     continue
                    elif sc['charge_type'] == 'RAC':
                        del_sc_id_list.append(idx)
                    else:
                        tax_amount += sc['amount']

                for idx in del_sc_id_list[::-1]:
                    fare['service_charge'].pop(idx)

                sc_anc_temp = copy.deepcopy(fare['service_charges'][0])
                if pricing_idx == 0:
                    if rule_obj:
                        tkt_anc_res = self.provider_pricing.get_ancillary_calculation(rule_obj, fare_amount, tax_amount)

                        if tkt_anc_res['upsell_amount']:
                            sc_values = copy.deepcopy(sc_anc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'roc',
                                'amount': tkt_anc_res['upsell_amount'],
                                'foreign_amount': tkt_anc_res['upsell_amount'],
                                'total': tkt_anc_res['upsell_amount'],
                            })
                            fare['service_charges'].append(sc_values)
                            total_reservation_amount += tkt_anc_res['upsell_amount']

                        if tkt_anc_res['ho_commission_amount']:
                            if tkt_anc_res['ho_commission_amount'] > 0:
                                if show_commission and show_upline_commission and self.ho_agent_id:
                                    sc_values = copy.deepcopy(sc_anc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'racho',
                                        'amount': -tkt_anc_res['ho_commission_amount'],
                                        'foreign_amount': -tkt_anc_res['ho_commission_amount'],
                                        'total': -tkt_anc_res['ho_commission_amount'],
                                        'commission_agent_id': self.ho_agent_id,
                                    })
                                    fare['service_charges'].append(sc_values)
                            else:
                                # # April 14, 2022 - SAM
                                # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                                # temp_ho_com_total = -tkt_anc_res['ho_commission_amount']
                                # total_commission_amount += temp_ho_com_total
                                # # END
                                pass

                        total_commission_amount += tkt_anc_res['commission_amount']
                        tax_amount += tkt_anc_res['upsell_amount']

                if pricing_idx == 1:
                    if agent_obj:
                        agent_anc_tkt = self.agent_pricing.get_ancillary_calculation(agent_obj, fare_amount, tax_amount)

                        if agent_anc_tkt['upsell_amount']:
                            sc_values = copy.deepcopy(sc_anc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'rocagt',
                                'amount': agent_anc_tkt['upsell_amount'],
                                'foreign_amount': agent_anc_tkt['upsell_amount'],
                                'total': agent_anc_tkt['upsell_amount'],
                            })
                            fare['service_charges'].append(sc_values)
                            total_reservation_amount += agent_anc_tkt['upsell_amount']

                        if agent_anc_tkt['commission_amount']:
                            if agent_anc_tkt['commission_amount'] > 0:
                                if show_commission:
                                    if sc_anc_temp['pax_type'] in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[sc_anc_temp['pax_type']])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'rac',
                                        'pax_type': sc_anc_temp['pax_type'],
                                        'pax_count': 1,
                                        'amount': -agent_anc_tkt['commission_amount'],
                                        'foreign_amount': -agent_anc_tkt['commission_amount'],
                                        'total': -agent_anc_tkt['commission_amount'],
                                    })
                                    fare_data['service_charges'].append(sc_values)
                            else:
                                # # April 14, 2022 - SAM
                                # # Mengurangi komisi agent
                                temp_com_total = -agent_anc_tkt['commission_amount']
                                total_commission_amount -= temp_com_total
                                # # END

                        if agent_anc_tkt['ho_commission_amount']:
                            if agent_anc_tkt['ho_commission_amount'] > 0:
                                if show_commission and show_upline_commission and self.ho_agent_id:
                                    sc_values = copy.deepcopy(sc_anc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'racagtho',
                                        'amount': -agent_anc_tkt['ho_commission_amount'],
                                        'foreign_amount': -agent_anc_tkt['ho_commission_amount'],
                                        'total': -agent_anc_tkt['ho_commission_amount'],
                                        'commission_agent_id': self.ho_agent_id,
                                    })
                                    fare['service_charges'].append(sc_values)
                            else:
                                # # April 14, 2022 - SAM
                                # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                                # temp_ho_com_total = -agent_anc_tkt['ho_commission_amount']
                                # total_commission_amount += temp_ho_com_total
                                # # END
                                pass


                if pricing_idx == 2:
                    if cust_obj:
                        cust_anc_tkt = self.customer_pricing.get_ancillary_calculation(cust_obj, fare_amount, tax_amount)

                        if cust_anc_tkt['upsell_amount']:
                            sc_values = copy.deepcopy(sc_anc_temp)
                            sc_values.update({
                                'charge_type': 'ROC',
                                'charge_code': 'roccust',
                                'amount': cust_anc_tkt['upsell_amount'],
                                'foreign_amount': cust_anc_tkt['upsell_amount'],
                                'total': cust_anc_tkt['upsell_amount'],
                            })
                            fare['service_charges'].append(sc_values)
                            total_reservation_amount += cust_anc_tkt['upsell_amount']

                        if cust_anc_tkt['commission_amount']:
                            if cust_anc_tkt['commission_amount'] > 0:
                                if show_commission:
                                    if sc_anc_temp['pax_type'] in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[sc_anc_temp['pax_type']])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'RAC',
                                        'charge_code': 'rac',
                                        'pax_type': sc_anc_temp['pax_type'],
                                        'pax_count': 1,
                                        'amount': -cust_anc_tkt['commission_amount'],
                                        'foreign_amount': -cust_anc_tkt['commission_amount'],
                                        'total': -cust_anc_tkt['commission_amount'],
                                    })
                                    fare_data['service_charges'].append(sc_values)
                            else:
                                # # April 14, 2022 - SAM
                                # # Mengurangi komisi agent jika minus
                                temp_ho_com_total = -cust_anc_tkt['commission_amount']
                                total_commission_amount -= temp_ho_com_total
                                # # END

            ## 4
            if pricing_idx == 0:
                if rule_obj:
                    tkt_rsv_res = self.provider_pricing.get_reservation_calculation(rule_obj, total_reservation_amount, route_count, segment_count)
                    tkt_rsv_res_lib = tkt_rsv_res
                    if tkt_rsv_res['upsell_amount']:
                        # # June 16, 2022 - SAM
                        # total_reservation_amount += tkt_rsv_res['upsell_amount']
                        # sc_values = copy.deepcopy(sc_temp)
                        # sc_values.update({
                        #     'charge_type': 'ROC',
                        #     'charge_code': 'rocrsv',
                        #     'pax_type': 'ADT',
                        #     'pax_count': 1,
                        #     'amount': tkt_rsv_res['upsell_amount'],
                        #     'foreign_amount': tkt_rsv_res['upsell_amount'],
                        #     'total': tkt_rsv_res['upsell_amount'],
                        # })
                        # fare_data['service_charges'].append(sc_values)

                        calc_amount = tkt_rsv_res['upsell_amount'] / total_all_pax_count
                        calc_amount = self.ceil(calc_amount, 0)
                        for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                            if pcd_pax_count > 0:
                                total_calc_amount = calc_amount * pcd_pax_count
                                total_reservation_amount += total_calc_amount
                                if pcd_pax_type in sc_temp_repo:
                                    sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                else:
                                    sc_values = copy.deepcopy(sc_temp)
                                sc_values.update({
                                    'charge_type': 'ROC',
                                    'charge_code': 'rocrsv',
                                    'pax_type': pcd_pax_type,
                                    'pax_count': pcd_pax_count,
                                    'amount': calc_amount,
                                    'foreign_amount': calc_amount,
                                    'total': total_calc_amount,
                                })
                                fare_data['service_charges'].append(sc_values)

                    # if tkt_rsv_res['ho_commission_amount']:
                    #     if tkt_rsv_res['ho_commission_amount'] > 0:
                    #         if show_commission and show_upline_commission and self.ho_agent_id:
                    #             # # June 16, 2022 - SAM
                    #             # sc_values = copy.deepcopy(sc_temp)
                    #             # sc_values.update({
                    #             #     'charge_type': 'RAC',
                    #             #     'charge_code': 'rachorsv',
                    #             #     'pax_type': 'ADT',
                    #             #     'pax_count': 1,
                    #             #     'amount': -tkt_rsv_res['ho_commission_amount'],
                    #             #     'foreign_amount': -tkt_rsv_res['ho_commission_amount'],
                    #             #     'total': -tkt_rsv_res['ho_commission_amount'],
                    #             #     'commission_agent_id': self.ho_agent_id
                    #             # })
                    #             # fare_data['service_charges'].append(sc_values)
                    #
                    #             calc_amount = tkt_rsv_res['ho_commission_amount'] / total_all_pax_count
                    #             calc_amount = self.ceil(calc_amount, 0)
                    #             for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                    #                 if pcd_pax_count > 0:
                    #                     total_calc_amount = calc_amount * pcd_pax_count
                    #                     if pcd_pax_type in sc_temp_repo:
                    #                         sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                    #                     else:
                    #                         sc_values = copy.deepcopy(sc_temp)
                    #                     sc_values.update({
                    #                         'charge_type': 'RAC',
                    #                         'charge_code': 'rachorsv',
                    #                         'pax_type': pcd_pax_type,
                    #                         'pax_count': pcd_pax_count,
                    #                         'amount': -calc_amount,
                    #                         'foreign_amount': -calc_amount,
                    #                         'total': -total_calc_amount,
                    #                         'commission_agent_id': self.ho_agent_id
                    #                     })
                    #                     fare_data['service_charges'].append(sc_values)
                    #     else:
                    #         # # April 14, 2022 - SAM
                    #         # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                    #         # temp_ho_com_total = -tkt_rsv_res['ho_commission_amount']
                    #         # total_commission_amount += temp_ho_com_total
                    #         # # END
                    #         pass
                    #
                    # total_commission_amount += tkt_rsv_res['commission_amount']

                    # October 18, 2023 - SAM
                    ho_commission_amount = tkt_rsv_res.get('ho_commission_amount', 0.0)
                    tax_ho_commission_amount = tkt_rsv_res.get('tax_ho_commission_amount', 0.0)
                    commission_amount = tkt_rsv_res.get('commission_amount', 0.0)
                    tax_commission_amount = tkt_rsv_res.get('tax_commission_amount', 0.0)
                    pricing_breakdown = rule_obj.get('pricing_breakdown', False)

                    if ho_commission_amount:
                        if ho_commission_amount > 0:
                            if show_commission:
                                calc_amount = ho_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'rachorsv',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACHSP',
                                                'charge_code': 'rachorsvsvc',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCHSP',
                                                'charge_code': 'rochorsvsvc',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if tax_ho_commission_amount:
                        if tax_ho_commission_amount > 0:
                            commission_amount -= tax_ho_commission_amount
                            if show_commission:
                                calc_amount = tax_ho_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'rachorsvtax',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACHVP',
                                                'charge_code': 'rachorsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCHVP',
                                                'charge_code': 'rochorsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                # else:
                                #     for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                #         if pcd_pax_count > 0:
                                #             total_calc_amount = calc_amount * pcd_pax_count
                                #             if pcd_pax_type in sc_temp_repo:
                                #                 sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                #             else:
                                #                 sc_values = copy.deepcopy(sc_temp)
                                #             sc_values.update({
                                #                 'charge_type': 'ROC',
                                #                 'charge_code': 'rochorsvvat',
                                #                 'pax_type': pcd_pax_type,
                                #                 'pax_count': pcd_pax_count,
                                #                 'amount': calc_amount,
                                #                 'foreign_amount': calc_amount,
                                #                 'total': total_calc_amount,
                                #             })
                                #             fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if tax_commission_amount:
                        if tax_commission_amount < 0:
                            commission_amount += tax_commission_amount
                            calc_amount = tax_commission_amount / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            if show_commission:
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACAVP',
                                                'charge_code': 'racrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCAVP',
                                                'charge_code': 'rocrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if commission_amount:
                        if commission_amount > 0:
                            total_commission_amount += commission_amount
                        else:
                            if total_commission_amount >= abs(commission_amount):
                                total_commission_amount -= abs(commission_amount)
                                if pricing_breakdown:
                                    diff_commission_amount = abs(commission_amount)
                                    calc_amount = diff_commission_amount / total_all_pax_count
                                    calc_amount = self.ceil(calc_amount, 0)
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            total_reservation_amount += total_calc_amount
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACCHG',
                                                'charge_code': 'racrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCCHG',
                                                'charge_code': 'rocrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                            else:
                                if pricing_breakdown and total_commission_amount > 0:
                                    diff_commission_amount = total_commission_amount
                                    calc_amount = diff_commission_amount / total_all_pax_count
                                    calc_amount = self.ceil(calc_amount, 0)
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            total_reservation_amount += total_calc_amount
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACCHG',
                                                'charge_code': 'racrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCCHG',
                                                'charge_code': 'rocrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                diff_commission_amount = abs(commission_amount) - total_commission_amount
                                total_commission_amount = 0.0
                                # diff_commission_amount = abs(commission_amount)
                                calc_amount = diff_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                    if pcd_pax_count > 0:
                                        total_calc_amount = calc_amount * pcd_pax_count
                                        total_reservation_amount += total_calc_amount
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROC',
                                            'charge_code': 'rocrsvadj',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': calc_amount,
                                            'foreign_amount': calc_amount,
                                            'total': total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                    # END

            if pricing_idx == 1:
                if agent_obj:
                    agent_rsv_res = self.agent_pricing.get_reservation_calculation(agent_obj, total_reservation_amount, route_count, segment_count, tkt_rsv_res=tkt_rsv_res_lib)
                    if agent_rsv_res['upsell_amount']:
                        # # June 16, 2022 - SAN
                        # total_reservation_amount += agent_rsv_res['upsell_amount']
                        # sc_values = copy.deepcopy(sc_temp)
                        # sc_values.update({
                        #     'charge_type': 'ROC',
                        #     'charge_code': 'rocrsvagt',
                        #     'pax_type': 'ADT',
                        #     'pax_count': 1,
                        #     'amount': agent_rsv_res['upsell_amount'],
                        #     'foreign_amount': agent_rsv_res['upsell_amount'],
                        #     'total': agent_rsv_res['upsell_amount'],
                        # })
                        # fare_data['service_charges'].append(sc_values)
                        calc_amount = agent_rsv_res['upsell_amount'] / total_all_pax_count
                        calc_amount = self.ceil(calc_amount, 0)
                        for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                            if pcd_pax_count > 0:
                                total_calc_amount = calc_amount * pcd_pax_count
                                total_reservation_amount += total_calc_amount
                                if pcd_pax_type in sc_temp_repo:
                                    sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                else:
                                    sc_values = copy.deepcopy(sc_temp)
                                sc_values.update({
                                    'charge_type': 'ROC',
                                    'charge_code': 'rocrsvagt',
                                    'pax_type': pcd_pax_type,
                                    'pax_count': pcd_pax_count,
                                    'amount': calc_amount,
                                    'foreign_amount': calc_amount,
                                    'total': total_calc_amount,
                                })
                                fare_data['service_charges'].append(sc_values)

                    # if agent_rsv_res['commission_amount']:
                    #     if agent_rsv_res['commission_amount'] > 0:
                    #         if show_commission:
                    #             # # June 16, 2022 - SAM
                    #             # sc_values = copy.deepcopy(sc_temp)
                    #             # sc_values.update({
                    #             #     'charge_type': 'RAC',
                    #             #     'charge_code': 'rac',
                    #             #     'pax_type': 'ADT',
                    #             #     'pax_count': 1,
                    #             #     'amount': -agent_rsv_res['commission_amount'],
                    #             #     'foreign_amount': -agent_rsv_res['commission_amount'],
                    #             #     'total': -agent_rsv_res['commission_amount'],
                    #             # })
                    #             # fare_data['service_charges'].append(sc_values)
                    #
                    #             if default_pax_type in sc_temp_repo:
                    #                 sc_values = copy.deepcopy(sc_temp_repo[default_pax_type])
                    #             else:
                    #                 sc_values = copy.deepcopy(sc_temp)
                    #             sc_values.update({
                    #                 'charge_type': 'RAC',
                    #                 'charge_code': 'rac',
                    #                 # 'pax_type': 'ADT',
                    #                 'pax_type': default_pax_type,
                    #                 'pax_count': 1,
                    #                 'amount': -agent_rsv_res['commission_amount'],
                    #                 'foreign_amount': -agent_rsv_res['commission_amount'],
                    #                 'total': -agent_rsv_res['commission_amount'],
                    #             })
                    #             fare_data['service_charges'].append(sc_values)
                    #     else:
                    #         # April 14 2022 - SAM
                    #         # Mengurangi komisi apabila minus
                    #         temp_total_com_amount = -agent_rsv_res['commission_amount']
                    #         total_commission_amount -= temp_total_com_amount
                    #         # END
                    #
                    # if agent_rsv_res['ho_commission_amount']:
                    #     if agent_rsv_res['ho_commission_amount'] > 0:
                    #         if show_commission and show_upline_commission and self.ho_agent_id:
                    #             # # June 16, 2022 - SAM
                    #             # sc_values = copy.deepcopy(sc_temp)
                    #             # sc_values.update({
                    #             #     'charge_type': 'RAC',
                    #             #     'charge_code': 'racagthorsv',
                    #             #     'pax_type': 'ADT',
                    #             #     'pax_count': 1,
                    #             #     'amount': -agent_rsv_res['ho_commission_amount'],
                    #             #     'foreign_amount': -agent_rsv_res['ho_commission_amount'],
                    #             #     'total': -agent_rsv_res['ho_commission_amount'],
                    #             #     'commission_agent_id': self.ho_agent_id
                    #             # })
                    #             # fare_data['service_charges'].append(sc_values)
                    #
                    #             calc_amount = agent_rsv_res['ho_commission_amount'] / total_all_pax_count
                    #             calc_amount = self.ceil(calc_amount, 0)
                    #             for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                    #                 if pcd_pax_count > 0:
                    #                     total_calc_amount = calc_amount * pcd_pax_count
                    #                     if pcd_pax_type in sc_temp_repo:
                    #                         sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                    #                     else:
                    #                         sc_values = copy.deepcopy(sc_temp)
                    #                     sc_values.update({
                    #                         'charge_type': 'RAC',
                    #                         'charge_code': 'racagthorsv',
                    #                         'pax_type': pcd_pax_type,
                    #                         'pax_count': pcd_pax_count,
                    #                         'amount': -calc_amount,
                    #                         'foreign_amount': -calc_amount,
                    #                         'total': -total_calc_amount,
                    #                         'commission_agent_id': self.ho_agent_id
                    #                     })
                    #                     fare_data['service_charges'].append(sc_values)
                    #     else:
                    #         # # April 14, 2022 - SAM
                    #         # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                    #         # temp_ho_com_total = -agent_rsv_res['ho_commission_amount']
                    #         # total_commission_amount += temp_ho_com_total
                    #         # # END
                    #         pass

                    # October 19, 2023 - SAM
                    ho_commission_amount = agent_rsv_res.get('ho_commission_amount', 0.0)
                    tax_ho_commission_amount = agent_rsv_res.get('tax_ho_commission_amount', 0.0)
                    commission_amount = agent_rsv_res.get('commission_amount', 0.0)
                    tax_commission_amount = agent_rsv_res.get('tax_commission_amount', 0.0)
                    pricing_breakdown = agent_obj.get('pricing_breakdown', False)

                    if ho_commission_amount:
                        if ho_commission_amount > 0:
                            if show_commission:
                                calc_amount = ho_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'racagthorsv',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACHSA',
                                                'charge_code': 'racagthorsvsvc',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCHSA',
                                                'charge_code': 'rocagthorsvsvc',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if tax_ho_commission_amount:
                        if tax_ho_commission_amount > 0:
                            commission_amount -= tax_ho_commission_amount
                            calc_amount = tax_ho_commission_amount / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            if show_commission:
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'racagthorsvtax',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACHVA',
                                                'charge_code': 'racagthorsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCHVA',
                                                'charge_code': 'rocagthorsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                # else:
                                #     for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                #         if pcd_pax_count > 0:
                                #             total_calc_amount = calc_amount * pcd_pax_count
                                #             if pcd_pax_type in sc_temp_repo:
                                #                 sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                #             else:
                                #                 sc_values = copy.deepcopy(sc_temp)
                                #             sc_values.update({
                                #                 'charge_type': 'ROC',
                                #                 'charge_code': 'rocagthorsvvat',
                                #                 'pax_type': pcd_pax_type,
                                #                 'pax_count': pcd_pax_count,
                                #                 'amount': calc_amount,
                                #                 'foreign_amount': calc_amount,
                                #                 'total': total_calc_amount,
                                #             })
                                #             fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if tax_commission_amount:
                        if tax_commission_amount < 0:
                            commission_amount += tax_commission_amount
                            calc_amount = tax_commission_amount / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            if show_commission:
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'racagtrsvtax',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACAVA',
                                                'charge_code': 'racagtrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCAVA',
                                                'charge_code': 'rocagtrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if commission_amount:
                        if commission_amount > 0:
                            if show_commission:
                                calc_amount = commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                    if pcd_pax_count > 0:
                                        total_calc_amount = calc_amount * pcd_pax_count
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rac',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                        else:
                            if total_commission_amount >= abs(commission_amount):
                                total_commission_amount -= abs(commission_amount)
                                if pricing_breakdown:
                                    diff_commission_amount = abs(commission_amount)
                                    calc_amount = diff_commission_amount / total_all_pax_count
                                    calc_amount = self.ceil(calc_amount, 0)
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            total_reservation_amount += total_calc_amount
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACCHG',
                                                'charge_code': 'racagtrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCCHG',
                                                'charge_code': 'rocagtrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                            else:
                                if pricing_breakdown and total_commission_amount > 0:
                                    diff_commission_amount = total_commission_amount
                                    calc_amount = diff_commission_amount / total_all_pax_count
                                    calc_amount = self.ceil(calc_amount, 0)
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            total_reservation_amount += total_calc_amount
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACCHG',
                                                'charge_code': 'racagtrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCCHG',
                                                'charge_code': 'rocagtrsvchg',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                diff_commission_amount = abs(commission_amount) - total_commission_amount
                                total_commission_amount = 0.0
                                # diff_commission_amount = abs(commission_amount)
                                calc_amount = diff_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                    if pcd_pax_count > 0:
                                        total_calc_amount = calc_amount * pcd_pax_count
                                        total_reservation_amount += total_calc_amount
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROC',
                                            'charge_code': 'rocagtrsvadj',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': calc_amount,
                                            'foreign_amount': calc_amount,
                                            'total': total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                    # END

                if agent_com_obj:
                    is_agent_commission_applied = True
                    total_pax_count = 0
                    infant_count = 0
                    for pax_type, pax_count in pax_count_dict.items():
                        if pax_type == 'INF':
                            infant_count += pax_count
                        else:
                            total_pax_count += pax_count

                    total_commission_amount = self.round(total_commission_amount)

                    com_param = {
                        # 'rule_obj': agent_obj,
                        'rule_obj': agent_com_obj,
                        'commission_amount': total_commission_amount,
                        'agent_id': self.agent_id,
                        'upline_list': self.upline_list,
                        'pax_count': total_pax_count,
                        'infant_count': infant_count,
                        'route_count': route_count,
                        'segment_count': segment_count,
                    }
                    pricing_breakdown = agent_com_obj.get('pricing_breakdown', False)
                    # agent_com_res = self.agent_pricing.get_commission_calculation(**com_param)
                    agent_com_res = self.agent_commission.get_commission_calculation(**com_param)
                    if agent_com_res['agent_discount_amount']:
                        if agent_com_res['agent_discount_amount'] > 0:
                            # # June 20, 2022 - SAM
                            # sc_values = copy.deepcopy(sc_temp)
                            # sc_values.update({
                            #     'charge_type': 'DISC',
                            #     'charge_code': 'disc',
                            #     'pax_type': 'ADT',
                            #     'pax_count': 1,
                            #     'amount': -agent_com_res['agent_discount_amount'],
                            #     'foreign_amount': -agent_com_res['agent_discount_amount'],
                            #     'total': -agent_com_res['agent_discount_amount'],
                            # })
                            # fare_data['service_charges'].append(sc_values)
                            # total_commission_amount -= agent_com_res['agent_discount_amount']

                            real_discount_amount = 0.0
                            calc_amount = agent_com_res['agent_discount_amount'] / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    real_discount_amount += total_calc_amount
                                    if pcd_pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'DISC',
                                        'charge_code': 'disc',
                                        'pax_type': pcd_pax_type,
                                        'pax_count': pcd_pax_count,
                                        'amount': -calc_amount,
                                        'foreign_amount': -calc_amount,
                                        'total': -total_calc_amount,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                            total_commission_amount -= real_discount_amount
                        else:
                            # April 14 2022 - SAM
                            # Mengurangi komisi apabila minus
                            temp_total_com_amount = -agent_com_res['agent_discount_amount']
                            total_commission_amount -= temp_total_com_amount
                            # END

                    if agent_com_res['agent_commission_amount']:
                        if agent_com_res['agent_commission_amount'] > 0:
                            # # June 16, 2022 - SAM
                            # if show_commission:
                            #     sc_values = copy.deepcopy(sc_temp)
                            #     sc_values.update({
                            #         'charge_type': 'RAC',
                            #         'charge_code': 'rac',
                            #         'pax_type': 'ADT',
                            #         'pax_count': 1,
                            #         'amount': -agent_com_res['agent_commission_amount'],
                            #         'foreign_amount': -agent_com_res['agent_commission_amount'],
                            #         'total': -agent_com_res['agent_commission_amount'],
                            #     })
                            #     fare_data['service_charges'].append(sc_values)
                            # total_commission_amount -= agent_com_res['agent_commission_amount']

                            real_commission_amount = 0.0
                            calc_amount = agent_com_res['agent_commission_amount'] / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    real_commission_amount += total_calc_amount
                                    if show_commission:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rac',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            total_commission_amount -= real_commission_amount
                        else:
                            # April 14 2022 - SAM
                            # Mengurangi komisi apabila minus
                            temp_total_com_amount = -agent_com_res['agent_commission_amount']
                            total_commission_amount -= temp_total_com_amount
                            # END

                    if agent_com_res['parent_agent_id'] and agent_com_res['parent_charge_amount']:
                        if agent_com_res['parent_charge_amount'] > 0:
                            # # June 16, 2022 - SAM
                            # if show_commission and show_upline_commission:
                            #     sc_values = copy.deepcopy(sc_temp)
                            #     sc_values.update({
                            #         'charge_type': 'RAC',
                            #         'charge_code': 'rac0',
                            #         'pax_type': 'ADT',
                            #         'pax_count': 1,
                            #         'amount': -agent_com_res['parent_charge_amount'],
                            #         'foreign_amount': -agent_com_res['parent_charge_amount'],
                            #         'total': -agent_com_res['parent_charge_amount'],
                            #         'commission_agent_id': agent_com_res['parent_agent_id']
                            #     })
                            #     fare_data['service_charges'].append(sc_values)
                            # total_commission_amount -= agent_com_res['parent_charge_amount']

                            real_commission_amount = 0.0
                            calc_amount = agent_com_res['parent_charge_amount'] / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    real_commission_amount += total_calc_amount
                                    if show_commission and show_upline_commission:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rac0',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                            'commission_agent_id': agent_com_res['parent_agent_id']
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACUA',
                                            'charge_code': 'raccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)

                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCUA',
                                            'charge_code': 'roccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': calc_amount,
                                            'foreign_amount': calc_amount,
                                            'total': total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            total_commission_amount -= real_commission_amount
                        else:
                            # # April 14, 2022 - SAM
                            # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                            # temp_ho_com_total = -agent_com_res['parent_charge_amount']
                            # total_commission_amount += temp_ho_com_total
                            # # END
                            pass

                    if agent_com_res['ho_agent_id'] and agent_com_res['ho_charge_amount']:
                        if agent_com_res['ho_charge_amount'] > 0:
                            # # June 16, 2022 - SAM
                            # if show_commission and show_upline_commission:
                            #     sc_values = copy.deepcopy(sc_temp)
                            #     sc_values.update({
                            #         'charge_type': 'RAC',
                            #         'charge_code': 'rac0',
                            #         'pax_type': 'ADT',
                            #         'pax_count': 1,
                            #         'amount': -agent_com_res['ho_charge_amount'],
                            #         'foreign_amount': -agent_com_res['ho_charge_amount'],
                            #         'total': -agent_com_res['ho_charge_amount'],
                            #         'commission_agent_id': agent_com_res['ho_agent_id']
                            #     })
                            #     fare_data['service_charges'].append(sc_values)
                            # total_commission_amount -= agent_com_res['ho_charge_amount']
                            real_commission_amount = 0.0
                            calc_amount = agent_com_res['ho_charge_amount'] / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    real_commission_amount += total_calc_amount
                                    if show_commission and show_upline_commission:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rac0',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                            'commission_agent_id': agent_com_res['ho_agent_id']
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACUA',
                                            'charge_code': 'raccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCUA',
                                            'charge_code': 'roccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': calc_amount,
                                            'foreign_amount': calc_amount,
                                            'total': total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            total_commission_amount -= real_commission_amount
                        else:
                            # # April 14, 2022 - SAM
                            # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                            # temp_ho_com_total = -agent_com_res['ho_charge_amount']
                            # total_commission_amount += temp_ho_com_total
                            # # END
                            pass

                    for idx, upline in enumerate(agent_com_res['upline_commission_list'], 1):
                        if upline['commission_amount']:
                            if upline['commission_amount'] > 0:
                                # # June 16, 2022 - SAM
                                # if show_commission and show_upline_commission:
                                #     sc_values = copy.deepcopy(sc_temp)
                                #     sc_values.update({
                                #         'charge_type': 'RAC',
                                #         'charge_code': 'rac%s' % idx,
                                #         'pax_type': 'ADT',
                                #         'pax_count': 1,
                                #         'amount': -upline['commission_amount'],
                                #         'foreign_amount': -upline['commission_amount'],
                                #         'total': -upline['commission_amount'],
                                #         'commission_agent_id': upline['agent_id']
                                #     })
                                #     fare_data['service_charges'].append(sc_values)
                                # total_commission_amount -= upline['commission_amount']

                                real_commission_amount = 0.0
                                calc_amount = upline['commission_amount'] / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                    if pcd_pax_count > 0:
                                        total_calc_amount = calc_amount * pcd_pax_count
                                        real_commission_amount += total_calc_amount
                                        if show_commission and show_upline_commission:
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'rac%s' % idx,
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                                'commission_agent_id': upline['agent_id']
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                        if pricing_breakdown:
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACUA',
                                                'charge_code': 'raccom',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCUA',
                                                'charge_code': 'roccom',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                total_commission_amount -= real_commission_amount
                            else:
                                # # April 14, 2022 - SAM
                                # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                                # temp_ho_com_total = -upline['commission_amount']
                                # total_commission_amount += temp_ho_com_total
                                # # END
                                pass

                    if agent_com_res['residual_agent_id'] and agent_com_res['residual_amount']:
                        if agent_com_res['residual_amount'] > 0:
                            # # June 16, 2022 - SAM
                            # if show_commission and show_upline_commission:
                            #     sc_values = copy.deepcopy(sc_temp)
                            #     sc_values.update({
                            #         'charge_type': 'RAC',
                            #         'charge_code': 'racsd',
                            #         'pax_type': 'ADT',
                            #         'pax_count': 1,
                            #         'amount': -agent_com_res['residual_amount'],
                            #         'foreign_amount': -agent_com_res['residual_amount'],
                            #         'total': -agent_com_res['residual_amount'],
                            #         'commission_agent_id': agent_com_res['residual_agent_id']
                            #     })
                            #     fare_data['service_charges'].append(sc_values)
                            # total_commission_amount -= agent_com_res['residual_amount']

                            real_commission_amount = 0.0
                            calc_amount = agent_com_res['residual_amount'] / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    real_commission_amount += total_calc_amount
                                    if show_commission and show_upline_commission:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'racsd',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                            'commission_agent_id': agent_com_res['residual_agent_id']
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                    if pricing_breakdown:
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RACUA',
                                            'charge_code': 'raccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'ROCUA',
                                            'charge_code': 'roccom',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': calc_amount,
                                            'foreign_amount': calc_amount,
                                            'total': total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                            total_commission_amount -= real_commission_amount
                        else:
                            # # April 14, 2022 - SAM
                            # # Kalau expected apabila komisi HO minus dan ingin ditambahkan ke komisi agent
                            # temp_ho_com_total = -agent_com_res['residual_amount']
                            # total_commission_amount += temp_ho_com_total
                            # # END
                            pass

                # Pembulatan
                # grand_total = 0.0
                # for fare in self.ticket_fare_list:
                #     for sc in fare['service_charges']:
                #         if sc['charge_type'] != 'RAC':
                #             grand_total += sc['total']
                # for fare in self.ancillary_fare_list:
                #     for sc in fare['service_charges']:
                #         if sc['charge_type'] != 'RAC':
                #             grand_total += sc['total']
                # round_gt = self.round(grand_total, self.agent_type_data)
                # diff_gt = round_gt - grand_total
                # if diff_gt:
                #     sc_values = copy.deepcopy(sc_temp)
                #     sc_values.update({
                #         'charge_type': 'ROC',
                #         'charge_code': 'roc',
                #         'pax_type': 'ADT',
                #         'pax_count': 1,
                #         'amount': diff_gt,
                #         'foreign_amount': diff_gt,
                #         'total': diff_gt,
                #     })
                #     fare_data['service_charges'].append(sc_values)

            if pricing_idx == 2:
                if cust_obj:
                    cust_rsv_res = self.customer_pricing.get_reservation_calculation(cust_obj, total_reservation_amount, route_count, segment_count)
                    if cust_rsv_res['upsell_amount']:
                        # # June 16, 2022 - SAM
                        # total_reservation_amount += cust_rsv_res['upsell_amount']
                        # sc_values = copy.deepcopy(sc_temp)
                        # sc_values.update({
                        #     'charge_type': 'ROC',
                        #     'charge_code': 'rocrsvcust',
                        #     'pax_type': 'ADT',
                        #     'pax_count': 1,
                        #     'amount': cust_rsv_res['upsell_amount'],
                        #     'foreign_amount': cust_rsv_res['upsell_amount'],
                        #     'total': cust_rsv_res['upsell_amount'],
                        # })
                        # fare_data['service_charges'].append(sc_values)

                        calc_amount = cust_rsv_res['upsell_amount'] / total_all_pax_count
                        calc_amount = self.ceil(calc_amount, 0)
                        for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                            if pcd_pax_count > 0:
                                total_calc_amount = calc_amount * pcd_pax_count
                                total_reservation_amount += total_calc_amount
                                if pcd_pax_type in sc_temp_repo:
                                    sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                else:
                                    sc_values = copy.deepcopy(sc_temp)
                                sc_values.update({
                                    'charge_type': 'ROC',
                                    'charge_code': 'rocrsvcust',
                                    'pax_type': pcd_pax_type,
                                    'pax_count': pcd_pax_count,
                                    'amount': calc_amount,
                                    'foreign_amount': calc_amount,
                                    'total': total_calc_amount,
                                })
                                fare_data['service_charges'].append(sc_values)

                    # if cust_rsv_res['commission_amount']:
                    #     if cust_rsv_res['commission_amount'] > 0:
                    #         if show_commission:
                    #             # # June 16, 2022 - SAM
                    #             # sc_values = copy.deepcopy(sc_temp)
                    #             # sc_values.update({
                    #             #     'charge_type': 'RAC',
                    #             #     'charge_code': 'rac',
                    #             #     'pax_type': 'ADT',
                    #             #     'pax_count': 1,
                    #             #     'amount': -cust_rsv_res['commission_amount'],
                    #             #     'foreign_amount': -cust_rsv_res['commission_amount'],
                    #             #     'total': -cust_rsv_res['commission_amount'],
                    #             # })
                    #             # fare_data['service_charges'].append(sc_values)
                    #
                    #             calc_amount = cust_rsv_res['commission_amount'] / total_all_pax_count
                    #             calc_amount = self.ceil(calc_amount, 0)
                    #             for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                    #                 if pcd_pax_count > 0:
                    #                     total_calc_amount = calc_amount * pcd_pax_count
                    #                     if pcd_pax_type in sc_temp_repo:
                    #                         sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                    #                     else:
                    #                         sc_values = copy.deepcopy(sc_temp)
                    #                     sc_values.update({
                    #                         'charge_type': 'RAC',
                    #                         'charge_code': 'rac',
                    #                         'pax_type': pcd_pax_type,
                    #                         'pax_count': pcd_pax_count,
                    #                         'amount': -calc_amount,
                    #                         'foreign_amount': -calc_amount,
                    #                         'total': -total_calc_amount,
                    #                     })
                    #                     fare_data['service_charges'].append(sc_values)
                    #     else:
                    #         # April 14 2022 - SAM
                    #         # Mengurangi komisi apabila minus
                    #         temp_total_com_amount = -cust_rsv_res['commission_amount']
                    #         total_commission_amount -= temp_total_com_amount
                    #         # END

                    # October 19, 2023 - SAM
                    commission_amount = cust_rsv_res.get('commission_amount', 0.0)
                    tax_commission_amount = cust_rsv_res.get('tax_commission_amount', 0.0)
                    pricing_breakdown = cust_obj.get('pricing_breakdown', False)

                    if tax_commission_amount:
                        if tax_commission_amount < 0:
                            commission_amount += tax_commission_amount
                            if show_commission:
                                calc_amount = tax_commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                if show_upline_commission and self.ho_agent_id:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RAC',
                                                'charge_code': 'raccustrsvtax',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                                'commission_agent_id': self.ho_agent_id
                                            })
                                            fare_data['service_charges'].append(sc_values)
                                if pricing_breakdown:
                                    for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                        if pcd_pax_count > 0:
                                            total_calc_amount = calc_amount * pcd_pax_count
                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'RACAVC',
                                                'charge_code': 'raccustrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': calc_amount,
                                                'foreign_amount': calc_amount,
                                                'total': total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)

                                            if pcd_pax_type in sc_temp_repo:
                                                sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                            else:
                                                sc_values = copy.deepcopy(sc_temp)
                                            sc_values.update({
                                                'charge_type': 'ROCAVC',
                                                'charge_code': 'roccustrsvvat',
                                                'pax_type': pcd_pax_type,
                                                'pax_count': pcd_pax_count,
                                                'amount': -calc_amount,
                                                'foreign_amount': -calc_amount,
                                                'total': -total_calc_amount,
                                            })
                                            fare_data['service_charges'].append(sc_values)
                        else:
                            pass

                    if commission_amount:
                        if commission_amount > 0:
                            if show_commission:
                                calc_amount = commission_amount / total_all_pax_count
                                calc_amount = self.ceil(calc_amount, 0)
                                for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                    if pcd_pax_count > 0:
                                        total_calc_amount = calc_amount * pcd_pax_count
                                        if pcd_pax_type in sc_temp_repo:
                                            sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                        else:
                                            sc_values = copy.deepcopy(sc_temp)
                                        sc_values.update({
                                            'charge_type': 'RAC',
                                            'charge_code': 'rac',
                                            'pax_type': pcd_pax_type,
                                            'pax_count': pcd_pax_count,
                                            'amount': -calc_amount,
                                            'foreign_amount': -calc_amount,
                                            'total': -total_calc_amount,
                                        })
                                        fare_data['service_charges'].append(sc_values)
                        else:
                            # if total_commission_amount >= abs(commission_amount):
                            #     total_commission_amount -= abs(commission_amount)
                            # else:
                            # diff_commission_amount = abs(commission_amount) - total_commission_amount
                            # total_commission_amount = 0.0
                            diff_commission_amount = abs(commission_amount)
                            calc_amount = diff_commission_amount / total_all_pax_count
                            calc_amount = self.ceil(calc_amount, 0)
                            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                                if pcd_pax_count > 0:
                                    total_calc_amount = calc_amount * pcd_pax_count
                                    total_reservation_amount += total_calc_amount
                                    if pcd_pax_type in sc_temp_repo:
                                        sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                                    else:
                                        sc_values = copy.deepcopy(sc_temp)
                                    sc_values.update({
                                        'charge_type': 'ROC',
                                        'charge_code': 'roccustrsvadj',
                                        'pax_type': pcd_pax_type,
                                        'pax_count': pcd_pax_count,
                                        'amount': calc_amount,
                                        'foreign_amount': calc_amount,
                                        'total': total_calc_amount,
                                    })
                                    fare_data['service_charges'].append(sc_values)
                    # END

        # May 30, 2022 - SAM
        if not is_agent_commission_applied and total_commission_amount > 0:
            com_agent_id = self.agent_id
            if self.upline_list:
                com_agent_id = self.upline_list[-1]['id']

            # _logger.info('Agent Commission is not applied, commission given to Agent ID %s' % com_agent_id)
            # # June 16, 2022 - SAM
            # sc_values = copy.deepcopy(sc_temp)
            # sc_values.update({
            #     'charge_type': 'RAC',
            #     'charge_code': 'racsdo',
            #     'pax_type': 'ADT',
            #     'pax_count': 1,
            #     'amount': -total_commission_amount,
            #     'foreign_amount': -total_commission_amount,
            #     'total': -total_commission_amount,
            #     'commission_agent_id': com_agent_id
            # })
            # fare_data['service_charges'].append(sc_values)
            # total_commission_amount -= total_commission_amount

            calc_amount = total_commission_amount / total_all_pax_count
            calc_amount = self.ceil(calc_amount, 0)
            for pcd_pax_type, pcd_pax_count in pax_count_dict.items():
                if pcd_pax_count > 0:
                    total_calc_amount = calc_amount * pcd_pax_count
                    if pcd_pax_type in sc_temp_repo:
                        sc_values = copy.deepcopy(sc_temp_repo[pcd_pax_type])
                    else:
                        sc_values = copy.deepcopy(sc_temp)
                    sc_values.update({
                        'charge_type': 'RAC',
                        'charge_code': 'racsdo',
                        'pax_type': pcd_pax_type,
                        'pax_count': pcd_pax_count,
                        'amount': -calc_amount,
                        'foreign_amount': -calc_amount,
                        'total': -total_calc_amount,
                        'commission_agent_id': com_agent_id
                    })
                    fare_data['service_charges'].append(sc_values)
            total_commission_amount -= total_commission_amount
        # END

        # April 13, 2022 - SAM
        # Menambahkan pengecekkan untuk repricing
        is_has_commission = False
        for sc in fare_data.get('service_charges', []):
            charge_type = sc.get('charge_type', '')
            if not charge_type or charge_type not in ['RAC']:
                continue

            charge_code = sc['charge_code']
            if charge_code != 'rac':
                continue
            amount = sc['amount']
            if amount == 0:
                continue
            is_has_commission = True
            break
        # END

        # January 6, 2022 - SAM
        # Menambahkan informasi tentang rule yang didapatkan
        rule_data = {
            'agent_id': self.agent_id,
            'agent_type_code': self.agent_type,
            'provider_type_code': self.provider_type,
            'customer_parent_type_code': self.customer_parent_type,
            'customer_parent_id': self.customer_parent_id,
        }
        rule_data.update(rule_param)
        payload = {
            'rule_data': rule_data,
            'provider_pricing_data': rule_obj,
            'agent_pricing_data': agent_obj,
            'customer_pricing_data': cust_obj,
            'agent_commission_data': agent_com_obj,
        }
        # END

        # April 13, 2022 - SAM
        # Kalau komisi tidak ditemukan dan pricing provider nya tidak ter-set maka error
        # if not is_has_commission and not rule_obj:
        #     try:
        #         msg_str = 'Error pricing, has no commission and provider pricing is not set, %s' % json.dumps(rule_data)
        #         values = {
        #             'code': 9903,
        #             'provider': 'Repricing Tools Error',
        #             'message': msg_str,
        #         }
        #         telegram_tools.telegram_notif_api(values, self.context)
        #     except:
        #         _logger.error('Error notif error telegram, %s' % traceback.format_exc())
        #     raise Exception('Pricing is not set')
        return payload
