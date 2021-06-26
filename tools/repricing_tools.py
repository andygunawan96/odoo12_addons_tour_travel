import logging, traceback
import json, copy
from datetime import datetime, timedelta
from math import ceil, floor
from odoo.http import request
from .destination_tools import DestinationToolsV2 as DestinationTools


_logger = logging.getLogger(__name__)


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
