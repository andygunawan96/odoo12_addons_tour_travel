from odoo import models, fields, api, _
from ...tools import variables,util,ERR
import logging, traceback,pytz
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)

class TtReportDashboard(models.Model):
    _name = 'tt.report.dashboard'

    def returning_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination']:
                return i
        return -1

    def returning_index_sector(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination'] and dic['sector'] == params['sector']:
                return i

        return -1

    def check_index(self, arr, key, param):
        for i, dic in enumerate(arr):
            if dic[key] == param:
                return i
        return -1

    def check_date_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['year'] == params['year'] and dic['month'] == params['month']:
                return i
        return -1

    def check_tour_route_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['category'] == params['category'] and dic['route'] == params['route']:
                return i
        return -1

    def check_offline_provider(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['provider_type'] == params['provider_type'] and dic['offline_provider_type'] == params['offline_provider_type']:
                return i
        return -1

    def convert_to_datetime(self, data):
        to_return = datetime.strptime(data, '%Y-%m-%d')
        return to_return

    def daterange(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + timedelta(n)

    def get_report_json_api(self, data, context):
        type = data['report_type']
        if type == 'overall':
            res = self.get_report_overall(data)
        elif type == 'overall_airline':
            res = self.get_report_overall_airline(data)
        elif type == 'overall_train':
            res = self.get_report_overall_train(data)
        elif type == 'overall_event':
            res = self.get_report_overall_event(data)
        elif type == 'overall_tour':
            res = self.get_report_overall_tour(data)
        elif type == 'overall_activity':
            res = self.get_report_overall_activity(data)
        elif type == 'overall_hotel':
            res = self.get_report_overall_hotel(data)
        elif type == 'overall_visa':
            res = self.get_report_overall_visa(data)
        elif type == 'overall_offline':
            res = self.get_report_overall_offline(data)
        elif type == 'airline':
            res = self.get_report_airline(data)
        elif type == 'event':
            res = self.get_report_event(data)
        elif type == 'train':
            res = self.get_report_train(data)
        elif type == 'activity':
            res = self.get_report_activity(data)
        elif type == 'hotel':
            res = self.get_report_hotel(data)
        elif type == 'tour':
            res = self.get_report_tour(data)
        elif type == 'issued_hour':
            res = self.get_issued_hour(data)
        elif type == 'payment_method':
            res = self.get_payment_report(data)
        elif type == 'get_total_rupiah':
            res = self.get_total_rupiah(data)
        elif type == 'get_top_up_rupiah':
            res = self.get_top_up_rupiah(data)
        elif type == 'get_average_rupiah':
            res = self.get_average_rupiah(data)
        else:
            return ERR.get_error(1001, "Cannot find action")
        return ERR.get_no_error(res)

    def get_report_xls_api(self, data,  context):
        return ERR.get_no_error()

    def get_report_overall(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}
            result_list = []

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = [0,0,0]

            total = 0
            num_data = 0
            for i in values['lines']:

                # create main graph
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])][0] += 1
                    result[str(i['reservation_issued_date'])][1] += i['amount']
                    total += i['amount']
                    num_data += 1

                    # create overview
                    provider_index = self.check_index(result_list, "provider", i['provider_type_name'])
                    if provider_index == -1:
                        temp_dict = {
                            'provider': i['provider_type_name'],
                            'counter': 1,
                            i['reservation_state']: 1
                        }
                        result_list.append(temp_dict)
                    else:
                        result_list[provider_index]['counter'] += 1
                        try:
                            result_list[provider_index][i['reservation_state']] += 1
                        except:
                            result_list[provider_index][i['reservation_state']] = 1

            for i in result:
                result[i][2] = result[i][1] / result[i][0] if result[i][0] > 0 else 0

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0,
                'overview': result_list
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e


    def get_report_overall_airline(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # result for graph
            result = {}

            # overview base on the same timeframe
            destination_sector_summary = []
            destination_direction_summary = []

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

                    # ============= Search best for every sector ==================
                    returning_index = self.returning_index_sector(destination_sector_summary,
                                                                  {'departure': i['departure'],
                                                                   'destination': i['destination'],
                                                                   'sector': i['reservation_sector']})
                    if returning_index == -1:
                        new_dict = {
                            'sector': i['reservation_sector'],
                            'departure': i['departure'],
                            'destination': i['destination'],
                            'counter': 1,
                            'elder_count': i['reservation_elder'],
                            'adult_count': i['reservation_adult'],
                            'child_count': i['reservation_child'],
                            'infant_count': i['reservation_infant'],
                            'passenger_count': i['reservation_passenger']
                        }
                        destination_sector_summary.append(new_dict)
                    else:
                        destination_sector_summary[returning_index]['counter'] += 1
                        destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                        destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
                        destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
                        destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
                        destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']

                    # ============= Search for best 50 routes ====================
                    returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'],
                                                                                           'destination': i[
                                                                                               'destination']})
                    if returning_index == -1:
                        new_dict = {
                            'direction': i['reservation_direction'],
                            'departure': i['departure'],
                            'destination': i['destination'],
                            'sector': i['reservation_sector'],
                            'counter': 1,
                            'elder_count': i['reservation_elder'],
                            'adult_count': i['reservation_adult'],
                            'child_count': i['reservation_child'],
                            'infant_count': i['reservation_infant'],
                            'passenger_count': i['reservation_passenger']
                        }
                        destination_direction_summary.append(new_dict)
                    else:
                        destination_direction_summary[returning_index]['counter'] += 1
                        destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                        destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
                        destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
                        destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
                        destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']

            # grouping data
            international_filter = list(filter(lambda x: x['sector'] == 'International', destination_sector_summary))
            domestic_filter = list(filter(lambda x: x['sector'] == 'Domestic', destination_sector_summary))
            one_way_filter = list(filter(lambda x: x['direction'] == 'OW', destination_direction_summary))
            return_filter = list(filter(lambda x: x['direction'] == 'RT', destination_direction_summary))
            multi_city_filter = list(filter(lambda x: x['direction'] == 'MC', destination_direction_summary))

            # ==== LETS get sorting ==================
            destination_sector_summary.sort(key=lambda x: x['counter'], reverse=True)
            destination_direction_summary.sort(key=lambda x: x['counter'], reverse=True)
            international_filter.sort(key=lambda x: x['counter'], reverse=True)
            domestic_filter.sort(key=lambda x: x['counter'], reverse=True)
            one_way_filter.sort(key=lambda x: x['counter'], reverse=True)
            return_filter.sort(key=lambda x: x['counter'], reverse=True)
            multi_city_filter.sort(key=lambda x: x['counter'], reverse=True)

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0,
                'overview': {
                    'sector_summary': destination_sector_summary,
                    'direction_summary': destination_direction_summary,
                    'international': international_filter,
                    'domestic': domestic_filter,
                    'one_way': one_way_filter,
                    'return': return_filter,
                    'multi_city': multi_city_filter
                }
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_train(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # overview base on the same timeframe
            destination_sector_summary = []
            destination_direction_summary = []

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

                    # ============= Search best for every sector ==================
                    returning_index = self.returning_index_sector(destination_sector_summary,
                                                                  {'departure': i['departure'],
                                                                   'destination': i['destination'],
                                                                   'sector': i['reservation_sector']})
                    if returning_index == -1:
                        new_dict = {
                            'sector': i['reservation_sector'],
                            'departure': i['departure'],
                            'destination': i['destination'],
                            'counter': 1,
                            'elder_count': i['reservation_elder'],
                            'adult_count': i['reservation_adult'],
                            'child_count': i['reservation_child'],
                            'infant_count': i['reservation_infant'],
                            'passenger_count': i['reservation_passenger']
                        }
                        destination_sector_summary.append(new_dict)
                    else:
                        destination_sector_summary[returning_index]['counter'] += 1
                        destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                        destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
                        destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
                        destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
                        destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']

                    # ============= Search for best 50 routes ====================
                    returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'],
                                                                                           'destination': i[
                                                                                               'destination']})
                    if returning_index == -1:
                        new_dict = {
                            'direction': i['reservation_direction'],
                            'departure': i['departure'],
                            'destination': i['destination'],
                            'sector': i['reservation_sector'],
                            'counter': 1,
                            'elder_count': i['reservation_elder'],
                            'adult_count': i['reservation_adult'],
                            'child_count': i['reservation_child'],
                            'infant_count': i['reservation_infant'],
                            'passenger_count': i['reservation_passenger']
                        }
                        destination_direction_summary.append(new_dict)
                    else:
                        destination_direction_summary[returning_index]['counter'] += 1
                        destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                        destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
                        destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
                        destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
                        destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']

                    # grouping data
                international_filter = list(
                    filter(lambda x: x['sector'] == 'International', destination_sector_summary))
                domestic_filter = list(filter(lambda x: x['sector'] == 'Domestic', destination_sector_summary))
                one_way_filter = list(filter(lambda x: x['direction'] == 'OW', destination_direction_summary))
                return_filter = list(filter(lambda x: x['direction'] == 'RT', destination_direction_summary))
                multi_city_filter = list(filter(lambda x: x['direction'] == 'MC', destination_direction_summary))

                # ==== LETS get sorting ==================
                destination_sector_summary.sort(key=lambda x: x['counter'], reverse=True)
                destination_direction_summary.sort(key=lambda x: x['counter'], reverse=True)
                international_filter.sort(key=lambda x: x['counter'], reverse=True)
                domestic_filter.sort(key=lambda x: x['counter'], reverse=True)
                one_way_filter.sort(key=lambda x: x['counter'], reverse=True)
                return_filter.sort(key=lambda x: x['counter'], reverse=True)
                multi_city_filter.sort(key=lambda x: x['counter'], reverse=True)

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0,
                'overview': {
                    'sector_summary': destination_sector_summary,
                    'direction_summary': destination_direction_summary,
                    'international': international_filter,
                    'domestic': domestic_filter,
                    'one_way': one_way_filter,
                    'return': return_filter,
                    'multi_city': multi_city_filter
                }
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_hotel(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_tour(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_activity(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_event(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_visa(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_offline(self, data):
        try:
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type']
            }
            values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            result = {}

            # lets populate result with empty date dictionary
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            delta = end_date - start_date

            for i in range(delta.days + 1):
                tanggal = start_date + timedelta(days=i)
                result[tanggal.strftime('%Y-%m-%d')] = 0

            total = 0
            num_data = 0
            for i in values['lines']:
                if i['reservation_state'] == 'issued':
                    result[str(i['reservation_issued_date'])] += 1
                    total += i['amount']
                    num_data += 1

            to_return = {
                'graph': {
                    'label': list(result.keys()),
                    'data': list(result.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(num_data) if num_data > 0 else 0
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_airline(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        sector_dictionary = [{
            'sector': 'International',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'sector': 'Domestic',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'sector': 'Other',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }]
        direction_dictionary = [{
            'direction': 'One Way',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'direction': 'Return',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'direction': 'Multi-City',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }]
        provider_type_summary = []
        destination_sector_summary = []
        destination_direction_summary = []
        carrier_name_summary = []
        issued_depart_international_summary = []
        issued_depart_domestic_summary = []
        no_departure = ""
        no_destination = ""
        # ================ proceed the data =====================
        current_order_number = ''
        for i in values['lines']:

            if current_order_number != i['reservation_order_number']:
                if not i['destination']:
                    no_destination += " {}".format(i['reservation_order_number'])
                if not i['departure']:
                    no_departure += " {}".format(i['reservation_order_number'])

                # ============= Issued compareed to depart date ==============
                filter_data = list(
                    filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], values['lines']))

                depart_index = 0
                if len(filter_data) > 1:
                    earliest_depart = filter_data[0]['journey_departure_date']
                    for j, dic in enumerate(filter_data):
                        if earliest_depart > dic['journey_departure_date']:
                            depart_index = j
                # lets count
                if filter_data[0]['reservation_issued_date_og']:
                    date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'],
                                                          '%Y-%m-%d %H:%M:%S')
                    if filter_data[0]['reservation_issued_date_og']:
                        date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                        if date_count.days < 0:
                            _logger.error("please check {}".format(i['reservation_order_number']))
                    else:
                        date_count = 0

                    if filter_data[0]['reservation_sector'] == 'International':
                        issued_depart_index = self.check_index(issued_depart_international_summary, "day",
                                                               date_count.days)
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_international_summary.append(temp_dict)
                        else:
                            issued_depart_international_summary[issued_depart_index]['counter'] += 1
                            issued_depart_international_summary[issued_depart_index]['passenger'] += filter_data[0][
                                'reservation_passenger']
                    else:
                        issued_depart_index = self.check_index(issued_depart_domestic_summary, "day", date_count.days)
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_domestic_summary.append(temp_dict)
                        else:
                            issued_depart_domestic_summary[issued_depart_index]['counter'] += 1
                            issued_depart_domestic_summary[issued_depart_index]['passenger'] += filter_data[0][
                                'reservation_passenger']
                # except:
                #     _logger.error("{}".format(i['reservation_order_number']))
                #     pass
                # ============= Issued Booked ratio by date ==================
                try:
                    month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                          'month': month[int(i['booked_month']) - 1]})
                    if month_index == -1:
                        temp_dict = {
                            'year': i['booked_year'],
                            'month': month[int(i['booked_month']) - 1],
                            'detail': self.add_month_detail()
                        }
                        if i['reservation_booked_date']:
                            splits = i['reservation_booked_date'].split("-")
                            day_index = int(splits[2]) - 1
                            temp_dict['detail'][day_index]['booked_counter'] += 1
                        if i['reservation_issued_date']:
                            splits = i['reservation_issued_date'].split("-")
                            day_index = int(splits[2]) - 1
                            temp_dict['detail'][day_index]['issued_counter'] += 1
                        summary_by_date.append(temp_dict)
                    else:
                        if i['reservation_booked_date']:
                            splits = i['reservation_booked_date'].split("-")
                            day_index = int(splits[2]) - 1
                            summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                        if i['reservation_issued_date']:
                            splits = i['reservation_issued_date'].split("-")
                            day_index = int(splits[2]) - 1
                            summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                except:
                    pass

                # ============= Summary by Carrier ===========================
                if not i['reservation_provider_name']:
                    i['reservation_provider_name'] = "Undefined"
                carrier_index = self.check_index(carrier_name_summary, 'carrier_name', i['reservation_provider_name'])
                if carrier_index == -1:
                    temp_dict = {
                        'carrier_name': i['reservation_provider_name'],
                        'international_counter': 0,
                        'international_valuation': 0,
                        'domestic_counter': 0,
                        'domestic_valuation': 0,
                        'elder_count': i['reservation_elder'],
                        'adult_count': i['reservation_adult'],
                        'child_count': i['reservation_child'],
                        'infant_count': i['reservation_infant'],
                        'passenger_count': i['reservation_passenger'],
                        'total_transaction': 0,
                        'issued': 0,
                        'fail_issued': 0,
                        'fail_booked': 0,
                        'expired': 0,
                        'other': 0,
                        'flight': []
                    }

                    # add counter for every provider
                    if i['reservation_sector'] == 'International':
                        temp_dict['international_counter'] += 1
                        temp_dict['international_valuation'] += i['amount']
                        temp_dict['total_transaction'] += 1
                    else:
                        temp_dict['domestic_counter'] += 1
                        temp_dict['domestic_valuation'] += i['amount']
                        temp_dict['total_transaction'] += 1

                    # to check issued fail ratio
                    if i['reservation_state'] == 'issued':
                        temp_dict['issued'] += 1
                    elif i['reservation_state'] == 'cancel2':
                        temp_dict['expired'] += 1
                    elif i['reservation_state'] == 'fail_issued':
                        temp_dict['fail_issued'] += 1
                    elif i['reservation_state'] == 'fail_booked':
                        temp_dict['fail_booked'] += 1
                    else:
                        temp_dict['other'] += 1
                    destination_dict = {
                        'departure': i['departure'],
                        'destination': i['destination'],
                        'counter': 1,
                        'elder_count': i['reservation_elder'],
                        'adult_count': i['reservation_adult'],
                        'child_count': i['reservation_child'],
                        'infant_count': i['reservation_infant'],
                        'passenger_count': i['reservation_passenger'],
                        'total_amount': i['amount']
                    }
                    temp_dict['flight'].append(destination_dict)
                    carrier_name_summary.append(temp_dict)
                else:
                    if i['reservation_sector'] == 'International':
                        carrier_name_summary[carrier_index]['international_counter'] += 1
                        carrier_name_summary[carrier_index]['international_valuation'] += i['amount']
                        carrier_name_summary[carrier_index]['total_transaction'] += 1
                        carrier_name_summary[carrier_index]['passenger_count'] += i['reservation_passenger']
                        carrier_name_summary[carrier_index]['elder_count'] += i['reservation_elder']
                        carrier_name_summary[carrier_index]['adult_count'] += i['reservation_adult']
                        carrier_name_summary[carrier_index]['child_count'] += i['reservation_child']
                        carrier_name_summary[carrier_index]['infant_count'] += i['reservation_infant']
                    elif i['reservation_sector'] == 'Domestic':
                        carrier_name_summary[carrier_index]['domestic_counter'] += 1
                        carrier_name_summary[carrier_index]['domestic_valuation'] += i['amount']
                        carrier_name_summary[carrier_index]['total_transaction'] += 1
                        carrier_name_summary[carrier_index]['passenger_count'] += i['reservation_passenger']
                        carrier_name_summary[carrier_index]['elder_count'] += i['reservation_elder']
                        carrier_name_summary[carrier_index]['adult_count'] += i['reservation_adult']
                        carrier_name_summary[carrier_index]['child_count'] += i['reservation_child']
                        carrier_name_summary[carrier_index]['infant_count'] += i['reservation_infant']
                    else:
                        carrier_name_summary[carrier_index]['total_transaction'] += 1

                    # to check issued fail ratio
                    if i['reservation_state'] == 'issued':
                        carrier_name_summary[carrier_index]['issued'] += 1
                    elif i['reservation_state'] == 'cancel2':
                        carrier_name_summary[carrier_index]['expired'] += 1
                    elif i['reservation_state'] == 'fail_issued':
                        carrier_name_summary[carrier_index]['fail_issued'] += 1
                    elif i['reservation_state'] == 'fail_booked':
                        carrier_name_summary[carrier_index]['fail_booked'] += 1
                    else:
                        carrier_name_summary[carrier_index]['other'] += 1

                    destination_index = self.returning_index(carrier_name_summary[carrier_index]['flight'],
                                                             {'departure': i['departure'],
                                                              'destination': i['destination']})
                    if destination_index == -1:
                        destination_dict = {
                            'departure': i['departure'],
                            'destination': i['destination'],
                            'counter': 1,
                            'elder_count': i['reservation_elder'],
                            'adult_count': i['reservation_adult'],
                            'child_count': i['reservation_child'],
                            'infant_count': i['reservation_infant'],
                            'passenger_count': i['reservation_passenger'],
                            'total_amount': i['amount']
                        }
                        carrier_name_summary[carrier_index]['flight'].append(destination_dict)
                    else:
                        carrier_name_summary[carrier_index]['flight'][destination_index]['counter'] += 1
                        carrier_name_summary[carrier_index]['flight'][destination_index]['total_amount'] += i['amount']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['passenger_count'] += i[
                            'reservation_passenger']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['elder_count'] += i[
                            'reservation_elder']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['adult_count'] += i[
                            'reservation_adult']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['child_count'] += i[
                            'reservation_child']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['infant_count'] += i[
                            'reservation_infant']

                # ============= Summary by Domestic/International ============
                if i['reservation_sector'] == 'International':
                    sector_dictionary[0]['valuation'] += int(i['amount'])
                    sector_dictionary[0]['counter'] += 1
                    sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                elif i['reservation_sector'] == 'Domestic':
                    sector_dictionary[1]['valuation'] += int(i['amount'])
                    sector_dictionary[1]['counter'] += 1
                    sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                else:
                    sector_dictionary[2]['valuation'] += int(i['amount'])
                    sector_dictionary[2]['counter'] += 1
                    sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                # ============= Summary by flight Type (OW, R, MC) ===========
                if i['reservation_direction'] == 'OW':
                    direction_dictionary[0]['valuation'] += int(i['amount'])
                    direction_dictionary[0]['counter'] += 1
                    direction_dictionary[0]['passenger_count'] = int(i['reservation_passenger'])
                elif i['reservation_direction'] == 'RT':
                    direction_dictionary[1]['valuation'] += int(i['amount'])
                    direction_dictionary[1]['counter'] += 1
                    direction_dictionary[1]['passenger_count'] = int(i['reservation_passenger'])
                else:
                    direction_dictionary[2]['valuation'] += int(i['amount'])
                    direction_dictionary[2]['counter'] += 1
                    direction_dictionary[2]['passenger_count'] = int(i['reservation_passenger'])

                # ============= Search best for every sector ==================
                returning_index = self.returning_index_sector(destination_sector_summary, {'departure': i['departure'],
                                                                                           'destination': i[
                                                                                               'destination'],
                                                                                           'sector': i[
                                                                                               'reservation_sector']})
                if returning_index == -1:
                    new_dict = {
                        'sector': i['reservation_sector'],
                        'departure': i['departure'],
                        'destination': i['destination'],
                        'counter': 1,
                        'elder_count': i['reservation_elder'],
                        'adult_count': i['reservation_adult'],
                        'child_count': i['reservation_child'],
                        'infant_count': i['reservation_infant'],
                        'passenger_count': i['reservation_passenger']
                    }
                    destination_sector_summary.append(new_dict)
                else:
                    destination_sector_summary[returning_index]['counter'] += 1
                    destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                    destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
                    destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
                    destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
                    destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']

                # ============= Search for best 50 routes ====================
                returning_index = self.returning_index(destination_direction_summary,
                                                       {'departure': i['departure'], 'destination': i['destination']})
                if returning_index == -1:
                    new_dict = {
                        'direction': i['reservation_direction'],
                        'departure': i['departure'],
                        'destination': i['destination'],
                        'sector': i['reservation_sector'],
                        'counter': 1,
                        'elder_count': i['reservation_elder'],
                        'adult_count': i['reservation_adult'],
                        'child_count': i['reservation_child'],
                        'infant_count': i['reservation_infant'],
                        'passenger_count': i['reservation_passenger']
                    }
                    destination_direction_summary.append(new_dict)
                else:
                    destination_direction_summary[returning_index]['counter'] += 1
                    destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                    destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
                    destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
                    destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
                    destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']

        # ======== LETS filter some stuffs ===================
        # filtered_by_provider = list(filter(lambda x: x['provider_type_name'] == provider_type_summary[0]['provider_type'], values['lines']))
        international_filter = list(filter(lambda x: x['sector'] == 'International', destination_sector_summary))
        domestic_filter = list(filter(lambda x: x['sector'] == 'Domestic', destination_sector_summary))
        one_way_filter = list(filter(lambda x: x['direction'] == 'OW', destination_direction_summary))
        return_filter = list(filter(lambda x: x['direction'] == 'RT', destination_direction_summary))
        multi_city_filter = list(filter(lambda x: x['direction'] == 'MC', destination_direction_summary))

        # ==== LETS get sorting ==================
        destination_sector_summary.sort(key=lambda x: x['counter'], reverse=True)
        destination_direction_summary.sort(key=lambda x: x['counter'], reverse=True)
        provider_type_summary.sort(key=lambda x: x['counter'], reverse=True)
        international_filter.sort(key=lambda x: x['counter'], reverse=True)
        domestic_filter.sort(key=lambda x: x['counter'], reverse=True)
        one_way_filter.sort(key=lambda x: x['counter'], reverse=True)
        return_filter.sort(key=lambda x: x['counter'], reverse=True)
        multi_city_filter.sort(key=lambda x: x['counter'], reverse=True)
        issued_depart_international_summary.sort(key=lambda x: x['counter'], reverse=True)
        issued_depart_domestic_summary.sort(key=lambda x: x['counter'], reverse=True)

        ## declaration of result
        international_top_route_result = []
        domestic_top_route_result = []

        ## top route international
        for i in range(0, 10):
            temp_dict = {
                'origin': international_filter[i]['departure'],
                'destination': international_filter[i]['destination'],
                'transaction': international_filter[i]['counter'],
                'passenger': international_filter[i]['passenger_count']
            }
            international_top_route_result.append(temp_dict)

        ## top route domestic
        for i in range(0, 10):
            temp_dict = {
                'origin': domestic_filter[i]['departure'],
                'destination': domestic_filter[i]['destination'],
                'transaction': domestic_filter[i]['counter'],
                'passenger': domestic_filter[i]['passenger_count']
            }
            domestic_top_route_result.append(temp_dict)

        ## create overall chart
        label_data = []
        data_data = []
        for i in sector_dictionary:
            label_data.append(i['sector'] if i['sector'] else '')
            data_data.append([i['counter'] if i['counter'] else 0, i['passenger_count'] if i['passenger_count'] else 0])

        to_return = {
            'overall_graph': {
                'label': label_data,
                'data': data_data
            },
            'international_domestic': direction_dictionary,
            'international_top_route': international_top_route_result,
            'domestic_top_route': domestic_top_route_result
        }

        return to_return

    def get_report_activity(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        # global summary
        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        product_summary = []
        for i in values['lines']:
            # ============= Issued Booked ratio by date ==================
            try:
                month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                      'month': month[int(i['booked_month']) - 1]})
                if month_index == -1:
                    temp_dict = {
                        'year': i['booked_year'],
                        'month': month[int(i['booked_month']) - 1],
                        'detail': self.add_month_detail()
                    }
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
                    summary_by_date.append(temp_dict)
                else:
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
            except:
                pass

            product_index = self.check_index(product_summary, 'product', i['reservation_activity_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['reservation_activity_name'],
                    'counter': 1,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger': i['reservation_passenger'],
                    'amount': i['amount']
                }
                product_summary.append(temp_dict)
            else:
                product_summary[product_index]['counter'] += 1
                product_summary[product_index]['passenger'] += i['reservation_passenger']
                product_summary[product_index]['amount'] += i['amount']
                product_summary[product_index]['elder_count'] += i['reservation_elder']
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        product_summary.sort(key=lambda x: x['counter'])

        ## creating chart data
        label_data = []
        data_data = []
        for i in product_summary:
            label_data.append(i['reservation_activity_name'])
            data_data.append([i['counter'], i['reservation_passenger']])

        ## create dictionary to return
        to_return = {
            'overall_graph': {
                'label': label_data,
                'data': data_data
            }
        }

        ## return the dictionary
        return to_return

    def get_report_event(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        product_summary = []
        for i in values['lines']:
            # ============= Issued Booked ratio by date ==================
            try:
                month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                      'month': month[int(i['booked_month']) - 1]})
                if month_index == -1:
                    temp_dict = {
                        'year': i['booked_year'],
                        'month': month[int(i['booked_month']) - 1],
                        'detail': self.add_month_detail()
                    }
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
                    summary_by_date.append(temp_dict)
                else:
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
            except:
                pass

            product_index = self.check_index(product_summary, 'product', i['reservation_activity_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['reservation_activity_name'],
                    'counter': 1,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger': i['reservation_passenger'],
                    'amount': i['amount']
                }
                product_summary.append(temp_dict)
            else:
                product_summary[product_index]['counter'] += 1
                product_summary[product_index]['passenger'] += i['reservation_passenger']
                product_summary[product_index]['amount'] += i['amount']
                product_summary[product_index]['elder_count'] += i['reservation_elder']
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        ## temporary list
        label_data = []
        data_data = []

        ##assign value to list
        for i in product_summary:
            label_data.append(i['reservation_activity_name'])
            data_data.append([i['counter'], i['reservation_passenger']])

        ## create dictionary to return
        to_return = {
            'overall_graph': {
                'label': label_data,
                'data': data_data
            }
        }

        ## return the dictionary
        return to_return

    # def get_report_passport(self, data):
    #     temp_dict = {
    #         'start_date': data['start_date'],
    #         'end_date': data['end_date'],
    #         'type': data['report_type']
    #     }
    #     values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
    #     return ERR.get_no_error(values)
    #
    # def get_report_ppob(self, data):
    #     temp_dict = {
    #         'start_date': data['start_date'],
    #         'end_date': data['end_date'],
    #         'type': data['report_type']
    #     }
    #     values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)
    #     return ERR.get_no_error(values)

    def get_report_train(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        # ============== INITIATE RESULT DICT ==================
        sector_dictionary = [{
            'sector': 'International',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'sector': 'Domestic',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'sector': 'Other',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }]
        direction_dictionary = [{
            'direction': 'One Way',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'direction': 'Return',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }, {
            'direction': 'Multi-City',
            'valuation': 0,
            'passenger_count': 0,
            'counter': 0
        }]
        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        provider_type_summary = []
        destination_sector_summary = []
        destination_direction_summary = []
        carrier_name_summary = []
        issued_depart_summary = []
        to_check = []
        # ================ proceed the data =====================
        for i in values['lines']:

            # ============= Issued Booked ratio by date ==================
            try:
                month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                      'month': month[int(i['booked_month']) - 1]})
                if month_index == -1:
                    temp_dict = {
                        'year': i['booked_year'],
                        'month': month[int(i['booked_month']) - 1],
                        'detail': self.add_month_detail()
                    }
                    if i['reservation_booked_date']:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['booked_counter'] += 1
                    if i['reservation_issued_date']:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['issued_counter'] += 1
                    summary_by_date.append(temp_dict)
                else:
                    if i['reservation_booked_']:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                    if i['reservation_issued_date']:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
            except:
                pass

            # ============= Issued compareed to depart date ==============
            filter_data = list(
                filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], values['lines']))

            depart_index = 0
            if len(filter_data) > 1:
                earliest_depart = filter_data[0]['journey_departure_date']
                for j, dic in enumerate(filter_data):
                    if earliest_depart > dic['journey_departure_date']:
                        depart_index = j
            # lets count
            try:
                date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'],
                                                      '%Y-%m-%d %H:%M')
                if filter_data[0]['reservation_issued_date_og']:
                    date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                else:
                    date_count = 0

                issued_depart_index = self.check_index(issued_depart_summary, "day", date_count.days)
                if issued_depart_index == -1:
                    temp_dict = {
                        "day": date_count.days,
                        "counter": 1
                    }
                    issued_depart_summary.append(temp_dict)
                else:
                    issued_depart_summary[issued_depart_index]['counter'] += 1
            except:
                _logger.error("{}".format(i['reservation_order_number']))
                pass

            # ============= Carrier summary check ========================
            carrier_index = self.check_index(carrier_name_summary, 'carrier_name', i['reservation_provider_name'])
            if carrier_index == -1:
                temp_dict = {
                    'carrier_name': i['reservation_provider_name'],
                    'international_counter': 0,
                    'domestic_counter': 0,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger_count': i['reservation_passenger'],
                    'total_transaction': 0,
                    'issued': 0,
                    'fail_issued': 0,
                    'fail_booked': 0,
                    'expired': 0,
                    'other': 0,
                    'flight': []
                }

                # add counter for every provider
                if i['reservation_sector'] == 'International':
                    temp_dict['international_counter'] += 1
                    temp_dict['total_transaction'] += 1
                else:
                    temp_dict['domestic_counter'] += 1
                    temp_dict['total_transaction'] += 1

                # to check issued fail ratio
                if i['reservation_state'] == 'issued':
                    temp_dict['issued'] += 1
                elif i['reservation_state'] == 'cancel2':
                    temp_dict['expired'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    temp_dict['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    temp_dict['fail_booked'] += 1
                else:
                    temp_dict['other'] += 1
                destination_dict = {
                    'departure': i['departure'],
                    'destination': i['destination'],
                    'counter': 1,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger_count': i['reservation_passenger']
                }
                temp_dict['flight'].append(destination_dict)
                carrier_name_summary.append(temp_dict)
            else:
                if i['reservation_sector'] == 'International':
                    carrier_name_summary[carrier_index]['international_counter'] += 1
                    carrier_name_summary[carrier_index]['total_transaction'] += 1
                    carrier_name_summary[carrier_index]['passenger_count'] += i['reservation_passenger']
                    carrier_name_summary[carrier_index]['elder_count'] += i['reservation_elder']
                    carrier_name_summary[carrier_index]['adult_count'] += i['reservation_adult']
                    carrier_name_summary[carrier_index]['child_count'] += i['reservation_child']
                    carrier_name_summary[carrier_index]['infant_count'] += i['reservation_infant']
                elif i['reservation_sector'] == 'Domestic':
                    carrier_name_summary[carrier_index]['domestic_counter'] += 1
                    carrier_name_summary[carrier_index]['total_transaction'] += 1
                    carrier_name_summary[carrier_index]['passenger_count'] += i['reservation_passenger']
                    carrier_name_summary[carrier_index]['elder_count'] += i['reservation_elder']
                    carrier_name_summary[carrier_index]['adult_count'] += i['reservation_adult']
                    carrier_name_summary[carrier_index]['child_count'] += i['reservation_child']
                    carrier_name_summary[carrier_index]['infant_count'] += i['reservation_infant']
                else:
                    carrier_name_summary[carrier_index]['total_transaction'] += 1

                # to check issued fail ratio
                if i['reservation_state'] == 'issued':
                    carrier_name_summary[carrier_index]['issued'] += 1
                elif i['reservation_state'] == 'cancel2':
                    carrier_name_summary[carrier_index]['expired'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    carrier_name_summary[carrier_index]['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    carrier_name_summary[carrier_index]['fail_booked'] += 1
                else:
                    carrier_name_summary[carrier_index]['other'] += 1

                destination_index = self.returning_index(carrier_name_summary[carrier_index]['flight'],
                                                         {'departure': i['departure'], 'destination': i['destination']})
                if destination_index == -1:
                    destination_dict = {
                        'departure': i['departure'],
                        'destination': i['destination'],
                        'counter': 1,
                        'elder_count': i['reservation_elder'],
                        'adult_count': i['reservation_adult'],
                        'child_count': i['reservation_child'],
                        'infant_count': i['reservation_infant'],
                        'passenger_count': i['reservation_passenger']
                    }
                    carrier_name_summary[carrier_index]['flight'].append(destination_dict)
                else:
                    carrier_name_summary[carrier_index]['flight'][destination_index]['counter'] += 1
                    carrier_name_summary[carrier_index]['flight'][destination_index]['passenger_count'] += i[
                        'reservation_passenger']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['elder_count'] += i[
                        'reservation_elder']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['adult_count'] += i[
                        'reservation_adult']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['child_count'] += i[
                        'reservation_child']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['infant_count'] += i[
                        'reservation_infant']

            # ============= International or Domestic route ==============
            if i['reservation_sector'] == 'International':
                sector_dictionary[0]['valuation'] += int(i['amount'])
                sector_dictionary[0]['counter'] += 1
                sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            elif i['reservation_sector'] == 'Domestic':
                sector_dictionary[1]['valuation'] += int(i['amount'])
                sector_dictionary[1]['counter'] += 1
                sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            else:
                sector_dictionary[2]['valuation'] += int(i['amount'])
                sector_dictionary[2]['counter'] += 1
                sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

            # ============= Type of direction ============================
            if i['reservation_direction'] == 'OW':
                direction_dictionary[0]['valuation'] += int(i['amount'])
                direction_dictionary[0]['counter'] += 1
                direction_dictionary[0]['passenger_count'] = int(i['reservation_passenger'])
            elif i['reservation_direction'] == 'RT':
                direction_dictionary[1]['valuation'] += int(i['amount'])
                direction_dictionary[1]['counter'] += 1
                direction_dictionary[1]['passenger_count'] = int(i['reservation_passenger'])
            else:
                direction_dictionary[2]['valuation'] += int(i['amount'])
                direction_dictionary[2]['counter'] += 1
                direction_dictionary[2]['passenger_count'] = int(i['reservation_passenger'])

            # ============= Seek top 50 products by sector ===============
            returning_index = self.returning_index(destination_sector_summary,
                                                   {'departure': i['departure'], 'destination': i['destination']})
            if returning_index == -1:
                new_dict = {
                    'sector': i['reservation_sector'],
                    'departure': i['departure'],
                    'destination': i['destination'],
                    'counter': 1,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger_count': i['reservation_passenger']
                }
                destination_sector_summary.append(new_dict)
            else:
                destination_sector_summary[returning_index]['counter'] += 1
                destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
                destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
                destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
                destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']

            # ============= Seek top 50 products =========================
            returning_index = self.returning_index(destination_direction_summary,
                                                   {'departure': i['departure'], 'destination': i['destination']})
            if returning_index == -1:
                new_dict = {
                    'direction': i['reservation_direction'],
                    'departure': i['departure'],
                    'destination': i['destination'],
                    'counter': 1,
                    'elder_count': i['reservation_elder'],
                    'adult_count': i['reservation_adult'],
                    'child_count': i['reservation_child'],
                    'infant_count': i['reservation_infant'],
                    'passenger_count': i['reservation_passenger']
                }
                destination_direction_summary.append(new_dict)
            else:
                destination_direction_summary[returning_index]['counter'] += 1
                destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
                destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
                destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
                destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
                destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']

        # ======== LETS filter some stuffs ===================
        # filtered_by_provider = list(filter(lambda x: x['provider_type_name'] == provider_type_summary[0]['provider_type'], values['lines']))
        international_filter = list(filter(lambda x: x['sector'] == 'International', destination_sector_summary))
        domestic_filter = list(filter(lambda x: x['sector'] == 'Domestic', destination_sector_summary))
        one_way_filter = list(filter(lambda x: x['direction'] == 'OW', destination_direction_summary))
        return_filter = list(filter(lambda x: x['direction'] == 'RT', destination_direction_summary))
        multi_city_filter = list(filter(lambda x: x['direction'] == 'MC', destination_direction_summary))

        # ==== LETS get sorting ==================
        destination_sector_summary.sort(key=lambda x: x['counter'], reverse=True)
        destination_direction_summary.sort(key=lambda x: x['counter'], reverse=True)
        provider_type_summary.sort(key=lambda x: x['counter'], reverse=True)
        international_filter.sort(key=lambda x: x['counter'], reverse=True)
        domestic_filter.sort(key=lambda x: x['counter'], reverse=True)
        one_way_filter.sort(key=lambda x: x['counter'], reverse=True)
        return_filter.sort(key=lambda x: x['counter'], reverse=True)
        multi_city_filter.sort(key=lambda x: x['counter'], reverse=True)
        issued_depart_summary.sort(key=lambda x: x['counter'], reverse=True)

        top_route_result = []
        for i in range(0, 10):
            temp_dict = {
                'origin': domestic_filter[i]['departure'],
                'destination': domestic_filter[i]['destination'],
                'transaction': domestic_filter[i]['count'],
                'passenger': domestic_filter[i]['passenger_count']
            }
            top_route_result.append(temp_dict)

        ## create overall chart
        label_data = []
        data_data = []
        for i in sector_dictionary:
            label_data.append(i['sector'] if i['sector'] else '')
            data_data.append([i['counter'] if i['counter'] else 0, i['passenger_count'] if i['passenger_count'] else 0])

        to_return = {
            'graph': {
                'label': label_data,
                'data': data_data
            },
            'international_domestic': direction_dictionary,
            'top_route': top_route_result
        }

        return to_return

    def get_report_hotel(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        provider_summary = []
        hotel_summary = []
        night_summary = []
        for i in values['lines']:

            # ============= Issued Booked ratio by date ==================
            try:
                month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                      'month': month[int(i['booked_month']) - 1]})
                if month_index == -1:
                    temp_dict = {
                        'year': i['booked_year'],
                        'month': month[int(i['booked_month']) - 1],
                        'detail': self.add_month_detail()
                    }
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
                    summary_by_date.append(temp_dict)
                else:
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
            except:
                pass

            # #count the nights
            night_index = self.check_index(night_summary, 'night', i['reservation_night'])
            if night_index == -1:
                temp_dict = {
                    'night': i['reservation_night'],
                    'counter': 1,
                    'issued': 0,
                    'fail_issued': 0,
                    'fail_booked': 0,
                    'expire': 0,
                    'other': 0,
                    # 'passenger': 0
                }
                if i['reservation_state'] == 'issued':
                    temp_dict['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    temp_dict['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    temp_dict['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    temp_dict['expire'] += 1
                else:
                    temp_dict['other'] += 1
                night_summary.append(temp_dict)
            else:
                night_summary[night_index]['counter'] += 1
                if i['reservation_state'] == 'issued':
                    night_summary[night_index]['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    night_summary[night_index]['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    night_summary[night_index]['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    night_summary[night_index]['expire'] += 1
                else:
                    night_summary[night_index]['other'] += 1

            # hotel count
            hotel_index = self.check_index(hotel_summary, 'hotel_name', i['reservation_hotel_name'])
            if hotel_index == -1:
                temp_dict = {
                    'hotel_name': i['reservation_hotel_name'],
                    'counter': 1,
                    'issued': 0,
                    'fail_issued': 0,
                    'fail_booked': 0,
                    'expire': 0,
                    'other': 0,
                    # 'passenger': 0
                }
                if i['reservation_state'] == 'issued':
                    temp_dict['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    temp_dict['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    temp_dict['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    temp_dict['expire'] += 1
                else:
                    temp_dict['other'] += 1
                hotel_summary.append(temp_dict)
            else:
                hotel_summary[hotel_index]['counter'] += 1
                if i['reservation_state'] == 'issued':
                    hotel_summary[hotel_index]['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    hotel_summary[hotel_index]['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    hotel_summary[hotel_index]['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    hotel_summary[hotel_index]['expire'] += 1
                else:
                    hotel_summary[hotel_index]['other'] += 1

            # provider summary
            provider_index = self.check_index(provider_summary, 'provider', i['reservation_provider_name'])
            if provider_index == -1:
                temp_dict = {
                    'provider': i['reservation_provider_name'],
                    'counter': 1,
                    'issued': 0,
                    'fail_issued': 0,
                    'fail_booked': 0,
                    'expire': 0,
                    'other': 0,
                    # 'passenger': 0
                }
                if i['reservation_state'] == 'issued':
                    temp_dict['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    temp_dict['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    temp_dict['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    temp_dict['expire'] += 1
                else:
                    temp_dict['other'] += 1
                provider_summary.append(temp_dict)
            else:
                provider_summary[provider_index]['counter'] += 1
                if i['reservation_state'] == 'issued':
                    provider_summary[provider_index]['issued'] += 1
                elif i['reservation_state'] == 'fail_issued':
                    provider_summary[provider_index]['fail_issued'] += 1
                elif i['reservation_state'] == 'fail_booked':
                    provider_summary[provider_index]['fail_booked'] += 1
                elif i['reservation_state'] == 'cancel2':
                    provider_summary[provider_index]['expire'] += 1
                else:
                    provider_summary[provider_index]['other'] += 1

        #create graph
        label_data = []
        data_data = []
        for i in provider_summary:
            label_data.append(i['hotel_name'] if i['hotel_name'] else '')
            data_data.append(i['counter'] if i['counter'] else 0)
        to_return = {
            'graph': {
                'label': label_data,
                'data': data_data
            }
        }

        return to_return

    def get_report_tour(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': data['report_type']
        }
        values = self.env['report.tt_report_selling.report_selling'].get_reports(temp_dict)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        country_summary = []
        tour_route_summary = []
        provider_summary = []
        temp_order_number = ''

        for i in values['lines']:

            # ============= Issued Booked ratio by date ==================
            try:
                month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                      'month': month[int(i['booked_month']) - 1]})
                if month_index == -1:
                    temp_dict = {
                        'year': i['booked_year'],
                        'month': month[int(i['booked_month']) - 1],
                        'detail': self.add_month_detail()
                    }
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        temp_dict['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
                    summary_by_date.append(temp_dict)
                else:
                    try:
                        splits = i['reservation_booked_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['booked_counter'] += 1
                    except:
                        pass
                    try:
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                    except:
                        pass
            except:
                pass

            if temp_order_number != i['reservation_order_number']:
                temp_order_number = i['reservation_order_number']
                # count every country in tour
                # filter the respected order number, then count the country
                country_filtered = list(
                    filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], values['lines']))
                country_list = []

                for j in country_filtered:
                    if j['tour_location_country'] not in country_list:
                        country_list.append(j['tour_location_country'])
                try:
                    country_merge = ", ".join(country_list)
                except:
                    _logger.error("Do check {} ".format(i['reservation_order_number']))
                    pass
                    # raise Exception("Do check {} ".format(i['reservation_order_number']))

                country_index = self.check_index(country_summary, 'country', country_merge)
                if country_index == -1:
                    temp_dict = {
                        'country': country_merge,
                        'counter': 1
                    }
                    country_summary.append(temp_dict)
                else:
                    country_summary[country_index]['counter'] += 1

                tour_route_index = self.check_tour_route_index(tour_route_summary, {'category': i['tour_category'],
                                                                                    'route': i['tour_route']})
                if tour_route_index == -1:
                    temp_dict = {
                        'category': i['tour_category'],
                        'route': i['tour_route'],
                        'counter': 1
                    }
                    tour_route_summary.append(temp_dict)
                else:
                    tour_route_summary[tour_route_index]['counter'] += 1

                provider_index = self.check_index(provider_summary, 'provider', i['reservation_provider_name'])
                if provider_index == -1:
                    temp_dict = {
                        'provider': i['reservation_provider_name'],
                        'total_amount': i['amount'],
                        'counter': 1,
                        'issued': 0,
                        'expire': 0,
                        'fail_booked': 0,
                        'fail_issued': 0,
                        'other': 0
                    }

                    if i['reservation_state'] == 'issued':
                        temp_dict['issued'] += 1
                    elif i['reservation_state'] == 'cancel2':
                        temp_dict['expire'] += 1
                    elif i['reservation_state'] == 'fail_booked':
                        temp_dict['fail_booked'] += 1
                    elif i['reservation_state'] == 'fail_issued':
                        temp_dict['fail_issued'] += 1
                    else:
                        temp_dict['other'] += 1
                    provider_summary.append(temp_dict)
                else:
                    provider_summary[provider_index]['counter'] += 1
                    if i['reservation_state'] == 'issued':
                        provider_summary[provider_index]['issued'] += 1
                    elif i['reservation_state'] == 'cancel2':
                        provider_summary[provider_index]['expire'] += 1
                    elif i['reservation_state'] == 'fail_booked':
                        provider_summary[provider_index]['fail_booked'] += 1
                    elif i['reservation_state'] == 'fail_issued':
                        provider_summary[provider_index]['fail_issued'] += 1
                    else:
                        provider_summary[provider_index]['other'] += 1
            else:
                continue

        # create graph
        label_data = []
        data_data = []
        for i in country_summary:
            label_data.append(i['country'] if i['country'] else '')
            data_data.append(i['counter'] if i['counter'] else 0)

        to_return = {
            'graph': {
                'label': label_data,
                'data': data_data
            }
        }

        return to_return

    def get_total_rupiah(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': "overall"
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        total = 0
        for i in values['lines']:
            # check for every book state, and count if issued
            if i['reservation_state'] == 'issued':
                total += i['amount']

        to_return = {
            'data': total,
            'total': total,
            'type': 'total_rupiah'
        }

        return to_return

    def get_top_up_rupiah(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': "top_up"
        }
        values = self.env['report.tt_report_dashboard.overall']._get_reports(temp_dict)

        total = 0
        for i in values['lines']:
            total += i['validate_amount']

        to_return = {
            'total': total
        }

        return to_return

    def get_average_rupiah(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': "overall"
        }
        values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

        total = 0
        num_data = 0
        for i in values['lines']:
            # check for every book state, and count if issued
            if i['reservation_state'] == 'issued':
                total += i['amount']
                num_data += 1

        if num_data > 0:
            average = float(total)/float(num_data)
        else:
            average = float(total) / 1

        to_return = {
            'data': average,
            'total': total,
            'num_data': num_data,
            'type': 'average_rupiah'
        }
        return to_return

    def get_payment_report(self, data):
        temp_dict = {
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'type': 'payment_method'
        }

        values = self.env['report.tt_report_dashboard.overall']._get_reports(temp_dict)

        to_return = {

        }
        return to_return