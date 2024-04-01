from odoo import models, fields, api, _
from ...tools import variables,util,ERR
import logging, traceback,pytz
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
from calendar import monthrange
import os,json

_logger = logging.getLogger(__name__)

class TtReportDashboard(models.Model):
    _name = 'tt.report.dashboard'

    #####################################################
    #    This section consists of function(s) for returning index of certain array
    #####################################################
    # input
    #   arr -> array [{'departure': [something](str), 'destination': [something](str), ...}]
    #   params -> dictionary {'departure': [something](str), 'destination': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def returning_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination']:
                return i
        return -1

    # input
    #   arr -> array [{'departure': [something](str), 'destination': [something](str), 'sector': [something](str), ...}]
    #   params -> dictionary {'departure': [something](str), 'destination': [something](str), 'sector': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def returning_index_sector(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination'] and dic['sector'] == params['sector']:
                return i

        return -1

    # input
    #   arr -> array [{'agent_id': [something](int), 'agent_type_id': [something](int), ...}]
    #   params -> dictionary {'agent_id': [something](int), 'agent_type_id': [something](int)}
    # return
    #   integer, -1 if no index found in arr
    #
    def person_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['agent_id'] == params['agent_id'] and dic['agent_type_id'] == params['agent_type_id']:
                return i

        return -1

    # input
    #   arr -> array [{'customer_id': [something](int), 'customer_name': [something](string), ..}]
    #   params -> dictionary {'customer_id': [something](int), 'customer_name': [something](string)}
    # return
    #   integer, -1 id no index found in arr
    #
    def customer_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['customer_id'] == params['customer_id'] and dic['customer_name'] == params['customer_name']:
                return i

        return -1

    # input
    #   arr -> array [{'customer_parent_id': [something](int), 'customer_parent_name': [something](string), ..}]
    #   params -> dictionary {'customer_parent_id': [something](int), 'customer_parent_name': [something](string)}
    # return
    #   integer, -1 id no index found in arr
    #
    def customer_parent_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['customer_parent_id'] == params['customer_parent_id'] and dic['customer_parent_name'] == params['customer_parent_name']:
                return i

        return -1

    # input
    #   arr -> array [{'agent_name': [something](str), 'agent_type_name': [something](str), ...}]
    #   params -> dictionary {'agent_name': [something](str), 'agent_type_name': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def person_index_by_name(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['agent_name'] == params['agent_name'] and dic['agent_type_name'] == params['agent_type_name']:
                return i

        return -1

    # input
    #   arr -> array [{'carrier_name': [something](str), ...}]
    #   params -> dictionary {'carrier_name': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_carrier(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['carrier_name'] == params['carrier_name']:
                return i
        return -1

    # input
    #   arr -> array [{'departure': [something](str), 'destination': [something](str), ...}]
    #   params -> dictionary {'departure': [something](str), 'destination': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_carrier_route(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['departure'] == params['departure'] and dic['destination'] == params['destination']:
                return i
        return -1

    # input
    #   arr -> array [{'city': [something](str), ...}]
    #   params -> dictionary {'city': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_location(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['city'] == params['city']:
                return i
        return -1

    # input
    #   arr -> array [{'name': [something](str), ...}]
    #   params -> dictionary {'name': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_hotel_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['name'] == params['name']:
                return i
        return -1

    # input
    #   arr -> array [{'name': [something](str), ...}]
    #   key -> name of the dictionary key (str)
    #   params -> [something](str)
    # return
    #   integer, -1 if no index found in arr
    #
    def check_index(self, arr, key, param):
        for i, dic in enumerate(arr):
            if dic[key] == param:
                return i
        return -1

    # input
    #   arr -> array [{'name': [something](str), ...}]
    #   params -> dictionary {'name': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_date_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['year'] == params['year'] and dic['month'] == params['month']:
                return i
        return -1

    # input
    #   arr -> array [{'category': [something](str), 'route': [something](str), ...}]
    #   params -> dictionary {'category': [something](str), 'route': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_tour_route_index(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['category'] == params['category'] and dic['route'] == params['route']:
                return i
        return -1

    # input
    #   arr -> array [{'provider_type': [something](str), 'offline_provider_type': [something](str), ...}]
    #   params -> dictionary {'provider_type': [something](str), 'offline_provider_type': [something](str)}
    # return
    #   integer, -1 if no index found in arr
    #
    def check_offline_provider(self, arr, params):
        for i, dic in enumerate(arr):
            if dic['provider_type'] == params['provider_type'] and dic['offline_provider_type'] == params['offline_provider_type']:
                return i
        return -1

    #####################################################
    #    This section consists of function(s) for adding month (days) detail
    #####################################################

    # input
    #   year (int) and month (int)
    # return
    #   [
    #       {day: 1, 'issued_counter': 0, 'booker_counter': 0},
    #       {day: 2, 'issued_counter': 0, 'booker_counter': 0},
    #       {day: 3, 'issued_counter': 0, 'booker_counter': 0},
    #   ]
    #
    def add_month_detail(self, year=0, month=0):
        temp_list = []
        if month == 0 and year == 0:
            for i in range(1, 32):
                temp_dict = {
                    'day': i,
                    'issued_counter': 0,
                    'booked_counter': 0
                }
                temp_list.append(temp_dict)
        else:
            day = monthrange(year, month)
            for i in range(1, day[1] + 1):
                temp_dict = {
                    'day': i,
                    'issued_counter': 0,
                    'booked_counter': 0
                }
                temp_list.append(temp_dict)

        return temp_list

    # input
    #   year (int) and month (int)
    # return
    #   [
    #       {'day': 1, 'reservation': 0, 'invoice': 0, 'revenue': 0, 'profit': 0, 'average': 0},
    #       {'day': 2, 'reservation': 0, 'invoice': 0, 'revenue': 0, 'profit': 0, 'average': 0},
    #       {'day': 3, 'reservation': 0, 'invoice': 0, 'revenue': 0, 'profit': 0, 'average': 0},
    #   ]
    #
    def add_issued_month_detail(self, year=0, month=0):
        temp_list = []
        if month == 0 and year == 0:
            for i in range(1, 32):
                temp_dict = {
                    'day': i,
                    'reservation': 0,
                    'invoice': 0,
                    'revenue': 0,
                    'profit': 0,
                    'average': 0
                }
                temp_list.append(temp_dict)
        else:
            day = monthrange(year, month)
            for i in range(1, day[1] + 1):
                temp_dict = {
                    'day': i,
                    'reservation': 0,
                    'invoice': 0,
                    'revenue': 0,
                    'profit': 0,
                    'average': 0
                }
                temp_list.append(temp_dict)

        return temp_list

    # input
    #   data -> datetime
    # return
    #   "YYYY-MM-DD" (str)
    def convert_to_datetime(self, data):
        to_return = datetime.strptime(data, '%Y-%m-%d')
        return to_return

    def daterange(self, start_date, end_date):
        for n in range(int((end_date - start_date).days)):
            yield start_date + timedelta(n)

    #####################################################
    #    MAIN FUNCTION
    #####################################################
    # this is the function that's being called by the gateway
    # in short this is the main function
    def get_report_json_api(self, data, context = {}):
        logged_user = self.env['res.users'].browse(int(context['co_uid']))
        is_admin = logged_user.has_group('base.group_erp_manager')
        if is_admin and data['ho_seq_id'] == "":
            data['ho_seq_id'] = False
        elif is_admin and data['ho_seq_id'] != "":
            pass
        else:
            data['ho_seq_id'] = self.env['tt.agent'].browse(context['co_ho_id']).seq_id

        # is_ho = 1
        # check if agent is ho
        is_ho = (logged_user.has_group('tt_base.group_tt_tour_travel') and context['co_agent_id'] == context['co_ho_id']) or is_admin
        if is_ho and data['agent_seq_id'] == "":
            data['agent_seq_id'] = False
        elif is_ho and data['agent_seq_id'] != "":
            pass
        else:
            # get the id of the agent
            data['agent_seq_id'] = self.env['tt.agent'].browse(context['co_agent_id']).seq_id

        is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
        if is_not_corpor and data['customer_parent_seq_id'] == "":
            data['customer_parent_seq_id'] = False
        elif is_not_corpor and data['customer_parent_seq_id'] != "":
            pass
        else:
            # get the id of the customer parent
            data['customer_parent_seq_id'] = self.env['tt.customer.parent'].browse(context['co_customer_parent_id']).seq_id

        if data['provider'] != 'all' and data['provider'] != '':
            # check if provider is exist
            provider_type = self.env['tt.provider'].search([('code', '=', data['provider'])])

            # if provider is not exist
            if not provider_type:
                raise UserError(_('Provider is not exist'))

            # get correspond provider type
            provider_type_by_provider = provider_type['provider_type_id'].code

            # if provider is not in provider type
            if data['report_type'] != "overall":
                splits = data['report_type'].split("_")
                if str(provider_type_by_provider) != splits[1]:
                    raise UserError(_("Provider %s is not in %s"))
            else:
                data['report_type'] = "overall_" + str(provider_type_by_provider)

        type = data['report_type']
        if type == 'overall':
            res = self.get_report_overall(data, is_ho, context)
        elif type == 'overall_airline':
            res = self.get_report_overall_airline(data, is_ho, context)
        elif type == 'overall_train':
            res = self.get_report_overall_train(data, is_ho, context)
        elif type == 'overall_event':
            res = self.get_report_overall_event(data, is_ho, context)
        elif type == 'overall_tour':
            res = self.get_report_overall_tour(data, is_ho, context)
        elif type == 'overall_activity':
            res = self.get_report_overall_activity(data, is_ho, context)
        elif type == 'overall_hotel':
            res = self.get_report_overall_hotel(data, is_ho, context)
        elif type == 'overall_visa':
            res = self.get_report_overall_visa(data, is_ho, context)
        elif type == 'overall_offline':
            res = self.get_report_overall_offline(data, is_ho, context)
        elif type == 'overall_ppob':
            res = self.get_report_overall_ppob(data, is_ho, context)
        elif type == 'overall_passport':
            res = self.get_report_overall_passport(data, is_ho, context)
        elif type == 'overall_phc':
            res = self.get_report_overall_phc(data, is_ho, context)
        elif type == 'overall_periksain':
            res = self.get_report_overall_periksain(data, is_ho, context)
        elif type == 'overall_medical':
            res = self.get_report_overall_medical(data, is_ho, context)
        elif type == 'overall_bus':
            res = self.get_report_overall_bus(data, is_ho, context)
        elif type == 'overall_insurance':
            res = self.get_report_overall_insurance(data, is_ho, context)
        elif type == 'overall_swabexpress':
            res = self.get_report_overall_swabexpress(data, is_ho, context)
        elif type == 'overall_labpintar':
            res = self.get_report_overall_labpintar(data, is_ho, context)
        elif type == 'overall_mitrakeluarga':
            res = self.get_report_overall_mitrakeluarga(data, is_ho, context)
        elif type == 'overall_sentramedika':
            res = self.get_report_overall_sentramedika(data, is_ho, context)
        elif type == 'overall_groupbooking':
            res = self.get_report_overall_groupbooking(data, is_ho, context)

        # under this section is old or test function, left it there for future reference
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
        elif type == 'get_book_issued_ratio':
            res = self.get_book_issued_ratio(data)
        else:
            return ERR.get_error(1001, "Cannot find action")
        if is_admin:
            res['dependencies'] = {
                'is_admin': 1,
                'is_ho': 1,
                'is_not_corpor': 1,
                'current_ho': self.env['tt.agent'].search([('seq_id', '=', data['ho_seq_id'])], limit=1).name,
                'current_agent': self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name,
                'current_customer_parent': self.env['tt.customer.parent'].search([('seq_id', '=', data['customer_parent_seq_id'])], limit=1).name,
                'ho_list': self.env['report.tt_report_dashboard.overall'].get_ho_all(),
                'agent_type': self.env['report.tt_report_dashboard.overall'].get_agent_type_all(),
                'agent_list': self.env['report.tt_report_dashboard.overall'].get_agent_all(),
                'customer_parent_list': self.env['report.tt_report_dashboard.overall'].get_customer_parent_all(),
                'provider_type': variables.PROVIDER_TYPE,
                'provider': self.env['report.tt_report_dashboard.overall'].get_provider_all(),
                'form_data': data
            }
        elif is_ho:
            res['dependencies'] = {
                'is_admin': 0,
                'is_ho': 1,
                'is_not_corpor': 1,
                'current_ho': self.env['tt.agent'].browse(context['co_ho_id']).name,
                'current_agent': self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name,
                'current_customer_parent': self.env['tt.customer.parent'].search([('seq_id', '=', data['customer_parent_seq_id'])], limit=1).name,
                'ho_list': [],
                'agent_type': self.env['report.tt_report_dashboard.overall'].get_agent_type_by_ho(self.env['tt.agent'].browse(context['co_ho_id']).id),
                'agent_list': self.env['report.tt_report_dashboard.overall'].get_agent_by_ho(self.env['tt.agent'].browse(context['co_ho_id']).id),
                'customer_parent_list': self.env['report.tt_report_dashboard.overall'].get_customer_parent_by_ho(self.env['tt.agent'].browse(context['co_ho_id']).id),
                'provider_type': variables.PROVIDER_TYPE,
                'provider': self.env['report.tt_report_dashboard.overall'].get_provider_all(),
                'form_data': data
            }
        elif is_not_corpor:
            res['profit_ho'] = 0
            res['profit_agent'] = 0
            res['dependencies'] = {
                'is_admin': 0,
                'is_ho': 0,
                'is_not_corpor': 1,
                'current_ho': self.env['tt.agent'].browse(context['co_ho_id']).name,
                'current_agent': self.env['tt.agent'].browse(context['co_agent_id']).name,
                'current_customer_parent': self.env['tt.customer.parent'].search([('seq_id', '=', data['customer_parent_seq_id'])], limit=1).name,
                'ho_list': [],
                'agent_type': [],
                'agent_list': [],
                'customer_parent_list': self.env['report.tt_report_dashboard.overall'].get_customer_parent_by_agent(self.env['tt.agent'].browse(context['co_ho_id']).id, self.env['tt.agent'].browse(context['co_agent_id']).id),
                'provider_type': variables.PROVIDER_TYPE,
                'provider': self.env['report.tt_report_dashboard.overall'].get_provider_all(),
                'form_data': data
            }
        else:
            res['profit_ho'] = 0
            res['profit_agent'] = 0
            res['dependencies'] = {
                'is_admin': 0,
                'is_ho': 0,
                'is_not_corpor': 0,
                'current_ho': self.env['tt.agent'].browse(context['co_ho_id']).name,
                'current_agent': self.env['tt.agent'].browse(context['co_agent_id']).name,
                'current_customer_parent': self.env['tt.customer.parent'].browse(context['co_customer_parent_id']).name,
                'ho_list': [],
                'agent_type': [],
                'agent_list': [],
                'customer_parent_list': [],
                'provider_type': variables.PROVIDER_TYPE,
                'provider': self.env['report.tt_report_dashboard.overall'].get_provider_all(),
                'form_data': data
            }
        _logger.info('#########HASIL REPORT###############\n%s\n#############################' % json.dumps(res))
        ## save file for log purpose
        folder_path = '/var/log/tour_travel/report_dashboard'
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        file = open('%s/report_response_%s.txt' % (folder_path,datetime.now().strftime('%Y-%m-%d_%H:%M:%S')),'w')
        file.write(json.dumps(res))
        file.close()
        _logger.info('Success: Get report dashboard. Request: %s' % str(json.dumps(data)))
        return ERR.get_no_error(res)

    def get_report_xls_api(self, data,  context):
        return ERR.get_no_error()

    #####################################################
    #    DEPENDENCIES FUNCTION
    #####################################################
    # this is the function that's being called by the sub main function (see below)
    # within this section one function in charge of handling data to product report of certain scope i.e book issued ratio
    # most of the input is form data that the sub main function get.

    # old function of get profit
    # currently not being use, since this function is merge is get reservation function
    def get_profit(self, data):
        try:
            # prepare value
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'provider': data['provider'],
                'provider_type': data['report_type'],
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'agent_type_seq_id': data['agent_type_seq_id']
            }

            # execute the query
            profit_lines = self.env['report.tt_report_dashboard.overall'].get_profit(temp_dict)

            # return to sub main function
            return profit_lines
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle processing data to produce booked-issued ratio
    # data contains all of the parameter from the frontend
    def get_book_issued_ratio(self, data):
        try:
            # get all data
            # prepare data
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'book_issued'
            }
            # execute the query
            all_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # constant dependencies
            mode = data['mode']
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            current_id = ''

            # create book vs issue "result list"
            summary_by_date = []
            summary_provider = []

            # iterate every data
            # i = reservation dictionary inside all_values['lines']
            for i in all_values['lines']:
                try:
                    # check if current id = iteration # ID
                    # because returned line from SQL could produce more than one line for every resrvation
                    if current_id != i['reservation_id']:
                        current_id = i['reservation_id']
                        # convert month number (1) to text and index (January) in constant
                        month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'],
                                                                              'month': month[int(i['booked_month']) - 1]})
                        if month_index == -1:
                            # create dictionary separate by month
                            temp_dict = {
                                'year': i['booked_year'],
                                'month_index': int(i['booked_month']),
                                'month': month[int(i['booked_month']) - 1],
                                'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
                            }
                            # separate book date
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

                            # append to list of dictionaries
                            summary_by_date.append(temp_dict)
                        else:
                            # if data already exist, then we do not need to create another temp dictionary
                            # we just need to update the value within the correct slot
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

                        # this section handle overview for booked issued ratio
                        # the overview will return something like (airline 100 reservation, and so on, in the shape of list of dictionary)
                        provider_index = self.check_index(summary_provider, "provider", i['provider_type_name'])
                        if provider_index == -1:
                            # this is also the same logic, if provider type cannot be found inside summary provider, then index will return -1
                            # meaning the data isn't yet exist in summary provider
                            # declare dependencies
                            temp_dict = {
                                'provider': i['provider_type_name'],
                                'counter': 1,
                                'booked': 0,
                                'issued': 0,
                                'cancel2': 0,
                                'fail_booked': 0,
                                'fail_issued': 0,
                            }

                            # add the first data
                            temp_dict[i['reservation_state']] += 1

                            # add to big list
                            summary_provider.append(temp_dict)
                        else:
                            # data is exist in summary_provider
                            # only need to update the number
                            summary_provider[provider_index]['counter'] += 1
                            try:
                                summary_provider[provider_index][i['reservation_state']] += 1
                            except:
                                pass

                except:
                    pass

            # sort the data by year and month
            # the result will be (Year 2019, month January), (Year 2020, month January) and so on
            summary_by_date.sort(key=lambda x: (x['year'], x['month_index']))
            summary_provider.sort(key=lambda x: x['counter'], reverse=True)

            # shape the data for return
            # by shape means trim unecessary data, and group data
            book_data = {}
            issued_data = {}
            if mode == 'month':
                # if mode = month means the data will be sum to month instead of date
                try:
                    counter = summary_by_date[0]['month_index'] - 1
                except:
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    counter = int(month) - 1
                for i in summary_by_date:
                    # fill skipped months
                    if i['month_index'] - 1 < counter:
                        while counter < 12:
                            book_data[month[counter]] = 0
                            issued_data[month[counter]] = 0
                            counter += 1
                        # resert counter after 12
                        if counter == 12:
                            counter = 0
                    if i['month_index'] - 1 > counter:
                        while counter < i['month_index'] - 1:
                            book_data[month[counter]] = 0
                            issued_data[month[counter]] = 0
                            counter += 1

                    # for every month in summary by date
                    book_data[i['month']] = 0
                    issued_data[i['month']] = 0
                    for j in i['detail']:
                        # for every date in a month (i)
                        book_data[i['month']] += j['booked_counter']
                        issued_data[i['month']] += j['issued_counter']
                    counter += 1
            else:
                for i in summary_by_date:
                    # for every month in summary by date
                    for j in i['detail']:
                        # for every date in a month (i)
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])
                        if today >= data['start_date'] and today <= data['end_date']:
                            book_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['booked_counter']
                            issued_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['issued_counter']
                        # else:
                        #     book_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0
                        #     issued_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # check if date is only 1 data, we'll "try" to cheat graph
            # instead of handle point, we'll make it handle "constant"
            # o the idea is if there's only 1 data
            # duplicate the data, so minimum data within graph is 2
            # in preparation we'll make list of end result
            book_label_list = list(book_data.keys())
            book_content_list = list(book_data.values())
            issued_content_list = list(issued_data.values())
            # check if list length is exactly one,
            # if so we're gonna dup the data
            if len(book_label_list) == 1:
                book_label_list.append(book_label_list[0])
                book_content_list.append(book_content_list[0])
                issued_content_list.append(issued_content_list[0])

            # build to return data
            to_return = {
                # it will be very absurd to stand alone, however this particular graph will corenspond to second graph in front end, so theres that
                'second_graph': {
                    # label for graph in frontend
                    # if mode month then label will be ['January', 'February', ...]
                    # if mode is not month then label will be ['1-11-2020', '2-11-2020', ...]
                    'label': book_label_list,
                    # data = list of booked reservation
                    'data': book_content_list,
                    # data2 = list of issued reservation
                    'data2': issued_content_list
                },
                'second_overview': summary_provider
            }
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle and process data for customer ranking by revenue
    # data = form data from frontend
    # profit = reservation data from function who calls this function (reservation data contains profit data)
    def get_report_group_by_customer(self, data, profit, is_ho, context):
        try:
            agent_name_context = None
            is_not_corpor = True
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
                # prepare data to get channel base on reservation performance in database
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                # 'agent_seq_id': 8,
                'addons': 'chanel'
            }

            # i use chanel as the variable name, because it has the same logic with chanel, also explains the addons parameter
            # execute the query
            chanel_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # declare mode of group by (timewise either days or month)
            mode = data['mode']
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # declare variable to temp handle processed data
            summary_customer = []
            summary_customer_parent = []
            current_id = ''

            # iterate every value in chanel_values['lines']
            passed_resv_id_list = []  # reservation ID list in which CSC amount will be added to the first customer encountered, because there is no way to include CSC per customer without LEFT JOIN
            for i in chanel_values['lines']:
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if i['reservation_id'] == current_id:
                    continue
                else:
                    current_id = i['reservation_id']

                # looking for index of particular person
                # within the summary_customer list
                # will return -1 if no match found
                customer_index = self.customer_index(summary_customer, {'customer_id': i['customer_id'], 'customer_name': i['customer_name']})

                if customer_index == -1:
                    # no customer with particular data exist
                    temp_dict = {
                        'customer_id': i['customer_id'],
                        'customer_name': i['customer_name'],
                        'revenue': i['amount'],
                        'profit': 0,
                        'reservation': 1
                    }
                    if current_id not in passed_resv_id_list:
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['profit'] += i['channel_profit']
                            temp_dict['revenue'] += i['channel_profit']
                        passed_resv_id_list.append(current_id)

                    # add to summary_customer
                    summary_customer.append(temp_dict)
                else:
                    # data is exist, so we only need to update existing data yey
                    summary_customer[customer_index]['revenue'] += i['amount']
                    summary_customer[customer_index]['reservation'] += 1
                    if current_id not in passed_resv_id_list:
                        if not i['is_upsell_in_service_charge']:
                            summary_customer[customer_index]['profit'] += i['channel_profit']
                            summary_customer[customer_index]['revenue'] += i['channel_profit']
                        passed_resv_id_list.append(current_id)

                # looking for index of particular customer group (FPO and such)
                # within the summary_customer_parent list
                # will return -1 if no match found
                customer_parent_index = self.customer_parent_index(summary_customer_parent, {'customer_parent_id': i['customer_parent_id'], 'customer_parent_name': i['customer_parent_name']})

                if customer_parent_index == -1:
                    # create temp dict because no data found
                    if not i['is_upsell_in_service_charge']:
                        revenue_amount = i['amount'] + i['channel_profit']
                        profit_amount = i['channel_profit']
                    else:
                        revenue_amount = i['amount']
                        profit_amount = 0
                    temp_dict = {
                        'customer_parent_id': i['customer_parent_id'],
                        'customer_parent_name': i['customer_parent_name'],
                        'revenue': revenue_amount,
                        'profit': profit_amount,
                        'reservation': 1
                    }

                    # add to summary_customer_parent
                    summary_customer_parent.append(temp_dict)
                else:
                    if not i['is_upsell_in_service_charge']:
                        summary_customer_parent[customer_parent_index]['revenue'] += i['amount'] + i['channel_profit']
                        summary_customer_parent[customer_parent_index]['profit'] += i['channel_profit']
                    else:
                        summary_customer_parent[customer_parent_index]['revenue'] += i['amount']
                        summary_customer_parent[customer_parent_index]['profit'] += 0
                    summary_customer_parent[customer_parent_index]['reservation'] += 1

            list_person = []
            list_customer = []
            # proceed profit
            for i in profit:
                # by customer
                person_index = self.customer_index(summary_customer, {'customer_id': i['customer_id'], 'customer_name': i['customer_name']})
                try:
                    if i['ledger_transaction_type'] == 3:
                        if i['ledger_id'] not in list_person:
                            if is_ho or agent_name_context == i['ledger_agent_name']:
                                summary_customer[person_index]['profit'] += i['debit'] - i['credit']
                                list_person.append(i['ledger_id'])
                except:
                    pass

                # by customer type
                person_type_index = self.customer_parent_index(summary_customer_parent, {'customer_parent_id': i['customer_parent_id'], 'customer_parent_name': i['customer_parent_name']})
                try:
                    if i['ledger_transaction_type'] == 3:
                        if i['ledger_id'] not in list_customer:
                            if is_ho or agent_name_context == i['ledger_agent_name']:
                                summary_customer_parent[person_type_index]['profit'] += i['debit'] - i['credit']
                                list_customer.append(i['ledger_id'])
                except:
                    pass

            # sort data
            summary_customer.sort(key=lambda x: (x['revenue'], x['reservation']), reverse=True)
            summary_customer_parent.sort(key=lambda x: (x['revenue'], x['reservation']), reverse=True)

            # create return dict for customer
            label_data = []
            revenue_data = []
            reservation_data = []
            average_data = []
            profit_data = []

            # for customer_type
            label_data2 = []
            revenue_data2 = []
            reservation_data2 = []
            average_data2 = []
            profit_data2 = []

            # lets populate list to return
            if len(summary_customer) < 20:
                for i in summary_customer:
                    label_data.append(i['customer_name'])
                    revenue_data.append(i['revenue'])
                    reservation_data.append(i['reservation'])
                    average_data.append(i['revenue'] / i['reservation'])
                    if not is_not_corpor:
                        i.update({
                            'profit': 0
                        })
                    profit_data.append(i['profit'])
            else:
                for i in range(20):
                    label_data.append(summary_customer[i]['customer_name'])
                    revenue_data.append(summary_customer[i]['revenue'])
                    reservation_data.append(summary_customer[i]['reservation'])
                    average_data.append(summary_customer[i]['revenue'] / summary_customer[i]['reservation'])
                    if not is_not_corpor:
                        summary_customer[i].update({
                            'profit': 0
                        })
                    profit_data.append(summary_customer[i]['profit'])

            # lets populate list to return
            if len(summary_customer_parent) < 20:
                for i in summary_customer_parent:
                    label_data2.append(i['customer_parent_name'])
                    revenue_data2.append(i['revenue'])
                    reservation_data2.append(i['reservation'])
                    average_data2.append(i['revenue'] / i['reservation'])
                    if not is_not_corpor:
                        i.update({
                            'profit': 0
                        })
                    profit_data2.append(i['profit'])
            else:
                for i in range(20):
                    label_data2.append(summary_customer_parent[i]['customer_parent_name'])
                    revenue_data2.append(summary_customer_parent[i]['revenue'])
                    reservation_data2.append(summary_customer_parent[i]['reservation'])
                    average_data2.append(summary_customer_parent[i]['revenue'] / summary_customer_parent[i]['reservation'])
                    if not is_not_corpor:
                        summary_customer_parent[i].update({
                            'profit': 0
                        })
                    profit_data2.append(summary_customer_parent[i]['profit'])

            # lets built to return
            to_return = {
                # it will be very absurd if stand alone,
                # however this particular graph will co-respond to fourth and fifth graph in front end, so theres that
                # in front end you will also find as fourth and fifth graph and all
                'fifth_graph': {
                    'label': label_data,
                    'data': revenue_data,
                    'data2': reservation_data,
                    'data3': average_data,
                    'data4': profit_data
                },
                'fifth_overview': summary_customer,
                'fourth_graph': {
                    'label': label_data2,
                    'data': revenue_data2,
                    'data2': reservation_data2,
                    'data3': average_data2,
                    'data4': profit_data2
                },
                'fourth_overview': summary_customer_parent
            }

            # return data
            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle and process data for channel ranking by revenue
    # data = form data from frontend
    # profit = reservation data from function who calls this function (reservation data contains profit data)
    def get_report_group_by_chanel(self, data, profit, is_ho, context={}):
        try:
            agent_name_context = None
            agent_id_context = None
            is_not_corpor = True
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # prepare data to get channel base on reservation performance in database
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                # 'agent_seq_id': 8,
                'addons': 'chanel'
            }

            # execute the query
            chanel_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # declare mode of group by (timewise either days or month)
            mode = data['mode']
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # declare variable to temp handle processed data
            summary_chanel = []
            current_id = ''

            # iterate every value in chanel_values['lines']
            for i in chanel_values['lines']:
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if i['reservation_id'] == current_id:
                    continue
                else:
                    current_id = i['reservation_id']

                person_index = self.person_index(summary_chanel, {'agent_id': i['agent_id'], 'agent_type_id': i['agent_type_id']})

                if person_index == -1:
                    # data is not exist
                    # create data
                    if not i['is_upsell_in_service_charge']:
                        revenue_amount = i['amount'] + i['channel_profit']
                        profit_amount = i['channel_profit']
                    else:
                        revenue_amount = i['amount']
                        profit_amount = 0
                    temp_dict = {
                        'agent_id': i['agent_id'],
                        'agent_type_id': i['agent_type_id'],
                        'agent_name': i['agent_name'],
                        'agent_type_name': i['agent_type_name'],
                        'revenue': revenue_amount,
                        'profit': profit_amount,
                        'reservation': 1
                    }
                    # add to final list
                    summary_chanel.append(temp_dict)
                else:
                    # data exist
                    if not i['is_upsell_in_service_charge']:
                        summary_chanel[person_index]['revenue'] += i['amount'] + i['channel_profit']
                        summary_chanel[person_index]['profit'] += i['channel_profit']
                    else:
                        summary_chanel[person_index]['revenue'] += i['amount']
                        summary_chanel[person_index]['profit'] += 0
                    summary_chanel[person_index]['reservation'] += 1

            # summary_ho = False
            # for i in summary_chanel:
            #     if i['agent_type_name'] == self.env.ref('tt_base.agent_type_ho').name:
            #         summary_ho = True
            #         break
            list_id = []
            # proceed profit
            for i in profit:
                person_index = self.person_index_by_name(summary_chanel, {'agent_name': i['ledger_agent_name'], 'agent_type_name': i['ledger_agent_type_name']})
                try:
                    if i['ledger_id'] not in list_id:
                        if i['ledger_transaction_type'] == 3:
                            if is_ho or agent_name_context == i['ledger_agent_name']:
                                summary_chanel[person_index]['profit'] += i['debit'] - i['credit']
                            list_id.append(i['ledger_id'])

                except:
                    pass

            # sort data
            summary_chanel.sort(key=lambda x: (x['revenue'], x['reservation']), reverse=True)

            # create return dict
            label_data = []
            revenue_data = []
            reservation_data = []
            average_data = []
            profit_data = []

            # lets populate list to return
            if len(summary_chanel) < 20:
                for i in summary_chanel:
                    label_data.append(i['agent_name'])
                    revenue_data.append(i['revenue'])
                    reservation_data.append(i['reservation'])
                    average_data.append(i['revenue']/i['reservation'])
                    if not is_not_corpor:
                        i.update({
                            'profit': 0
                        })
                    profit_data.append(i['profit'])
            else:
                for i in range(20):
                    label_data.append(summary_chanel[i]['agent_name'])
                    revenue_data.append(summary_chanel[i]['revenue'])
                    reservation_data.append(summary_chanel[i]['reservation'])
                    average_data.append(summary_chanel[i]['revenue'] / summary_chanel[i]['reservation'])
                    if not is_not_corpor:
                        summary_chanel[i].update({
                            'profit': 0
                        })
                    profit_data.append(summary_chanel[i]['profit'])

            # lets built to return
            to_return = {
                'third_graph': {
                    'label': label_data,
                    'data': revenue_data,
                    'data2': reservation_data,
                    'data3': average_data,
                    'data4': profit_data
                },
                'third_overview': summary_chanel
            }

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    ######################################################################
    # this section contains of sub main function (function that is called by the main function)
    ######################################################################

    # this function handle data handler and processing for all of provider Type
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall(self, data, is_ho, context={}):
        try:
            # check if user ask for a specific provider
            # this function is to tell the sql handler that the data we want is base on issued date
            # the default of sql query is to search by created date
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id','=', data['agent_seq_id'])], limit=1).name
            if data['provider']:
                provider_type = self.env['tt.provider'].search([('code', '=', data['provider'])])
                data['report_type'] = 'overall_' + provider_type['provider_type_id'].code

            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            # change date to UTC0 from UTC+7
            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            # get all data by issued date (between start and end)
            currency_obj = None
            currency_obj = self.env['res.currency'].search([('name','=', data['currency'])], limit=1)
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                # 'agent_seq_id': False,
                'addons': 'none',
                'currency_id': currency_obj.id if currency_obj else None
            }

            # execute the query
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # count different of days between dates
            delta = end_date - start_date

            # if day counts > 35 then graph result will be group monthly, else graph data will be group by date
            if delta.days > 35:
                # group by month
                mode = 'month'

            # global result variable
            total = 0
            profit_total = 0 # GANTI PROFIT = DEBIT - CREDIT AGAR REVERSE LEDGER KE DETECT
            profit_ho = 0
            profit_agent_parent = 0
            profit_agent = 0
            num_data = 0
            invoice_total = 0

            # second we gonna get invoice data based on the reservation that we know (incase there are 2 invoice within 1 reservation)
            # create list of reservation id for invoice query
            reservation_ids = []
            for i in issued_values['lines']:
                # for every line from first step, we will extract the reservatoin_id, will be use to search invoice data
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            # get invoice data
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                # 'agent_seq_id': False,
                'reservation': reservation_ids,
                'addons': 'none',
                'currency_id': currency_obj.id if currency_obj else None
            }

            #executing invoice search
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            summary_provider = []

            # declare current id
            reservation_id_list = {} #dict of list provider agar id kembar tidak tertumpuk
            ledger_id_list = {} #dict of list provider agar id kembar tidak tertumpuk
            current_journey = ''
            current_segment = ''
            current_pnr = {}
            pnr_within = []
            currency = ''

            for line in issued_values['lines']:
                if currency:
                    break
                currency = line.get('currency', '')

            # third we process the data to produce a trim proceed data, that is only need to be show

            # for every data in issued_values['lines']
            # iterate every value in chanel_values['lines']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])

            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk
            reservation_id_list_issued = {}  # dict of list provider agar id kembar tidak tertumpuk
            ledger_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            for i in issued_values['lines']:
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []
                if not reservation_id_list_issued.get(i['provider_type_name']):
                    reservation_id_list_issued[i['provider_type_name']] = []
                if i['provider_type_name'] == 'Offline':
                    to_check = i['provider_type_name'] + "_" + i['reservation_offline_provider_type']
                    provider_index = self.check_index(summary_provider, "provider", to_check)
                else:
                    provider_index = self.check_index(summary_provider, "provider", i['provider_type_name'])

                if provider_index == -1:
                    if i['provider_type_name'] == 'Offline':
                        if not i['is_upsell_in_service_charge']:
                            profit_amount = i['channel_profit']
                        else:
                            profit_amount = 0
                        temp_dict = {
                            'provider': i['provider_type_name'] + "_" + i['reservation_offline_provider_type'],
                            'counter': 1,
                            i['reservation_state']: 1,
                            'total_price': profit_amount,
                            'total_commission': profit_amount
                        }
                    else:
                        if not i['is_upsell_in_service_charge']:
                            profit_amount = i['channel_profit']
                        else:
                            profit_amount = 0
                        temp_dict = {
                            'provider': i['provider_type_name'],
                            'counter': 1,
                            i['reservation_state']: 1,
                            'total_price': profit_amount,
                            'total_commission': profit_amount
                        }
                    summary_provider.append(temp_dict)
                else:
                    if i['reservation_id'] not in reservation_id_list_issued[i['provider_type_name']]:
                        summary_provider[provider_index]['counter'] += 1
                        try:
                            summary_provider[provider_index][i['reservation_state']] += 1
                        except:
                            summary_provider[provider_index][i['reservation_state']] = 1
                        if not i['is_upsell_in_service_charge']:
                            summary_provider[provider_index]['total_price'] += i['channel_profit']
                            summary_provider[provider_index]['total_commission'] += i['channel_profit']

                reservation_id_list_issued[i['provider_type_name']].append(i['reservation_id'])

                #profit
                if i['ledger_transaction_type'] == 3:
                    if is_ho or agent_name_context == i['ledger_agent_name']:
                        if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                            summary_provider[provider_index]['total_commission'] += i['debit'] - i['credit']
                            ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
                if not is_not_corpor:
                    summary_provider[provider_index].update({
                        'total_commission': 0
                    })
                #revenue
                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    summary_provider[provider_index]['total_price'] += i['amount']
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

            ##

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     try:
            #         # check if reservation id is not equal to current reservation id
            #         # by default current id is empty string ('')
            #         if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #             #reset pnr list
            #             pnr_within = []
            #             # if reservation id is not equal to current id it means, it's a different reservation than previous line
            #
            #             # triple try except is to keep track with current pnr, journey, and segment, making sure that the program dosen't count twite for the same data
            #             try:
            #                 current_journey = i['journey_id']
            #             except:
            #                 current_journey = ''
            #
            #             try:
            #                 current_segment = i['segment_id']
            #             except:
            #                 current_segment = ''
            #
            #             try:
            #                 current_pnr = i['ledger_pnr']
            #                 pnr_within.append(i['ledger_pnr'])
            #             except:
            #                 current_pnr = ''
            #
            #             # get index of month
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 # seperate string date to extract day date
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #
            #                 # assign the first value to temp dict
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount']
            #
            #                 # add to global variable
            #                 total += i['amount']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
            #                 total += i['amount']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # after adding summary issued we group the data by provider
            #             if i['provider_type_name'] == 'Offline':
            #                 to_check = i['provider_type_name'] + "_" + i['reservation_offline_provider_type']
            #                 provider_index = self.check_index(summary_provider, "provider", to_check)
            #             else:
            #                 provider_index = self.check_index(summary_provider, "provider", i['provider_type_name'])
            #             if provider_index == -1:
            #                 if i['ledger_agent_type_name'] == 'HO' and is_ho == True or i['ledger_agent_type_name'] != 'HO': #BUAT USER HO YANG LEDGER AGENT TYPE HO ATAU AGENT
            #                     if i['provider_type_name'] == 'Offline':
            #                         temp_dict = {
            #                             'provider': i['provider_type_name'] + "_" + i['reservation_offline_provider_type'],
            #                             'counter': 1,
            #                             i['reservation_state']: 1,
            #                             'total_price': i['amount'],
            #                             'total_commission': i['commission'] if is_ho == False else i['commission_amount']
            #                         }
            #                     else:
            #                         temp_dict = {
            #                             'provider': i['provider_type_name'],
            #                             'counter': 1,
            #                             i['reservation_state']: 1,
            #                             'total_price': i['amount'],
            #                             'total_commission': i['commission'] if is_ho == False else i['commission_amount']
            #                         }
            #                 else: # KALAU AGENT TETAPI DAPAT KOMISI HO BIKIN DULU TAPI DI ISIKAN VALUE DI NEXT LOOP (KALAU KETEMU)
            #                     if i['provider_type_name'] == 'Offline':
            #                         temp_dict = {
            #                             'provider': i['provider_type_name'] + "_" + i['reservation_offline_provider_type'],
            #                             'counter': 0,
            #                             i['reservation_state']: 0,
            #                             'total_price': 0,
            #                             'total_commission': 0
            #                         }
            #                     else:
            #                         temp_dict = {
            #                             'provider': i['provider_type_name'],
            #                             'counter': 0,
            #                             i['reservation_state']: 0,
            #                             'total_price': 0,
            #                             'total_commission': 0
            #                         }
            #                 summary_provider.append(temp_dict)
            #             else:
            #                 summary_provider[provider_index]['counter'] += 1
            #                 try:
            #                     summary_provider[provider_index][i['reservation_state']] += 1
            #                     summary_provider[provider_index]['total_price'] += i['amount']
            #                     if is_ho == True:
            #                         summary_provider[provider_index]['total_commission'] += i['commission_amount']
            #                     else:
            #                         summary_provider[provider_index]['total_commission'] += i['commission']
            #                 except:
            #                     summary_provider[provider_index][i['reservation_state']] = 1
            #                     summary_provider[provider_index]['total_price'] = i['amount']
            #                     if is_ho == True:
            #                         summary_provider[provider_index]['total_commission'] = i['commission_amount']
            #                     else:
            #                         summary_provider[provider_index]['total_commission'] = i['commission']
            #             current_id[i['provider_type_name']].append(i['reservation_id'])
            #         else:
            #             # if current id equal to i['reservation_id']
            #             # get current journey
            #             # this try except to prevent error for data without journey information
            #             try:
            #                 temp_journey = i['journey_id']
            #             except:
            #                 temp_journey = ''
            #
            #             try:
            #                 temp_segment = i['segment_id']
            #             except:
            #                 temp_segment = ''
            #
            #             try:
            #                 temp_pnr = i['ledger_pnr']
            #             except:
            #                 temp_pnr = ''
            #
            #             if i['reservation_id'] in current_id[i['provider_type_name']] and summary_provider[-1]['total_price'] == 0: #KALAU PROVIDER BELUM TERTAMBAH ASUMSI SUMMARY PROVIDER SUDAH ADA
            #                 if i['provider_type_name'] == 'Offline':
            #                     to_check = i['provider_type_name'] + "_" + i['reservation_offline_provider_type']
            #                     provider_index = self.check_index(summary_provider, "provider", to_check)
            #                 else:
            #                     provider_index = self.check_index(summary_provider, "provider", i['provider_type_name'])
            #                 summary_provider[provider_index]['counter'] += 1
            #                 try:
            #                     summary_provider[provider_index][i['reservation_state']] += 1
            #                     summary_provider[provider_index]['total_price'] += i['amount']
            #                     if is_ho == True:
            #                         summary_provider[provider_index]['total_commission'] += i['commission_amount']
            #                     else:
            #                         summary_provider[provider_index]['total_commission'] += i['commission']
            #                 except:
            #                     summary_provider[provider_index][i['reservation_state']] = 1
            #                     summary_provider[provider_index]['total_price'] = i['amount']
            #                     if is_ho == True:
            #                         summary_provider[provider_index]['total_commission'] = i['commission_amount']
            #                     else:
            #                         summary_provider[provider_index]['total_commission'] = i['commission']
            #             # check if provider is airline
            #             if i['provider_type_name'] == 'Airline':
            #                 if current_segment != i['segment_id'] and current_pnr != i['ledger_pnr']:
            #                     # if both segment and pnr is diff, then we want to count the ledger
            #                     # hence update to current pnr and segment
            #                     current_segment = i['segment_id']
            #                     current_pnr = i['ledger_pnr']
            #
            #                     if current_pnr in pnr_within:
            #                         continue
            #                     else:
            #                         pnr_within.append(current_pnr)
            #
            #                     # count like always
            #                     if i['ledger_transaction_type'] == 3:
            #                         month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                         splits = i['reservation_issued_date'].split("-")
            #                         day_index = int(splits[2]) - 1
            #                         if is_ho or agent_name_context == i['ledger_agent_name']:
            #                             summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                             profit_total += i['debit'] - i['credit']
            #                             profit_ho += i['debit'] - i['credit']
            #                         # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                         #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         #     profit_total += i['debit'] - i['credit']
            #                         #     profit_ho += i['debit'] - i['credit']
            #                         # elif i['ledger_agent_type_name'] != 'HO':
            #                         #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         #     profit_total += i['debit'] - i['credit']
            #                         #     profit_agent += i['debit'] - i['credit']
            #                 elif current_segment == i['segment_id'] and current_pnr == i['ledger_pnr']:
            #                     # count like always
            #                     if i['ledger_transaction_type'] == 3:
            #                         month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                         splits = i['reservation_issued_date'].split("-")
            #                         day_index = int(splits[2]) - 1
            #                         if is_ho or agent_name_context == i['ledger_agent_name']:
            #                             summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                             profit_total += i['debit'] - i['credit']
            #                             profit_ho += i['debit'] - i['credit']
            #                         # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                         #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         #     profit_total += i['debit'] - i['credit']
            #                         #     profit_ho += i['debit'] - i['credit']
            #                         # elif i['ledger_agent_type_name'] != 'HO':
            #                         #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         #     profit_total += i['debit'] - i['credit']
            #                         #     profit_agent += i['debit'] - i['credit']
            #             else:
            #                 # else
            #                 if i['ledger_transaction_type'] == 3:
            #                     month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                     splits = i['reservation_issued_date'].split("-")
            #                     day_index = int(splits[2]) - 1
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #     except Exception as e:
            #         _logger.error("ERROR REPORT DASHBOARD %s" % traceback.format_exc())

            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    #filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            summary_provider.sort(key=lambda x: x['counter'], reverse=True)

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1
            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent_parent': profit_agent_parent,
                'profit_agent': profit_agent,
                'first_overview': summary_provider,
                'currency': currency
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for airline
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_airline(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            # convert time to GMT 0
            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }

            # execute the query
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # overview base on the same timeframe
            sector_dictionary = [{
                'sector': 'International',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Domestic',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Other',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }]
            destination_sector_summary = []
            destination_direction_summary = []
            start_point_summary = {}
            end_point_summary = {}
            top_carrier = []
            issued_depart_international_summary = []
            issued_depart_domestic_summary = []

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            # create list of reservation id for invoice query
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            # get invoice data
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # get service charge
            # get invoice data
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'reservation': '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            service_charge = self.env['report.tt_report_dashboard.overall'].get_service_charge(temp_dict)

            # declare list to return
            summary_issued = []

            # declare current id
            current_id = {}
            current_segment = ''
            current_pnr = ''
            pnr_within = []

            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # proceed invoice with the assumption of create date = issued date
            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             # reset pnr
            #             pnr_within = []
            #
            #             # set journey to current journey
            #             current_segment = i['segment_id']
            #             current_pnr = i['ledger_pnr']
            #
            #             # add new pnr
            #             pnr_within.append(i['ledger_pnr'])
            #
            #             # get index of month
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 # add the first profit if ledger type is 3 a.k.a commission
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         if is_ho and agent_name_context == i['ledger_agent_name']:
            #                             profit_ho += i['debit'] - i['credit']
            #                         else:
            #                             profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         if is_ho and agent_name_context == i['ledger_agent_name']:
            #                             profit_ho += i['debit'] - i['credit']
            #                         else:
            #                             profit_agent += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         # Departure
            #         try:
            #             # seperate city of departure
            #             depart = i['departure'].split(" - ")
            #             start_point_summary[depart[0]] += 1
            #         except:
            #             # seperate city of departure
            #             depart = i['departure'].split(" - ")
            #             start_point_summary[depart[0]] = 1
            #
            #         # Destination
            #         try:
            #             # seperate city of destination
            #             desti = i['destination'].split(" - ")
            #             end_point_summary[desti[0]] += 1
            #         except:
            #             # seperate city of destination
            #             desti = i['destination'].split(" - ")
            #             end_point_summary[desti[0]] = 1
            #
            #         # Top Carrier
            #         try:
            #             carrier_index = self.check_carrier(top_carrier, {'carrier_name': i['airline']})
            #
            #             if carrier_index == -1:
            #                 # filter service charge
            #                 # product total corresponding to particular pnr
            #                 # filter from service charge data
            #                 temp_charge = list(
            #                     filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i['reservation_order_number'], service_charge))
            #
            #                 nta_total = 0
            #                 commission = 0
            #                 for k in temp_charge:
            #                     if k['booking_charge_type'] == 'RAC':
            #                         commission -= k['booking_charge_total']
            #                         nta_total += k['booking_charge_total']
            #                     else:
            #                         if k['booking_charge_type'] != '' and k['booking_charge_total']:
            #                             nta_total += k['booking_charge_total']
            #                 grand_total = nta_total + commission
            #
            #                 # carrier is not exist yet
            #                 # declare a temporary dictionary
            #                 temp_dict = {
            #                     'carrier_name': i['airline'],
            #                     'counter': 1,
            #                     'revenue': grand_total,
            #                     'passenger': i['reservation_passenger'],
            #                     'route': [{
            #                         'departure': i['departure'],
            #                         'destination': i['destination'],
            #                         'counter': 1,
            #                         'passenger': i['reservation_passenger']
            #                     }]
            #                 }
            #                 # add to main list
            #                 top_carrier.append(temp_dict)
            #             else:
            #                 # check index of route within top_carrier dictionary
            #                 carrier_route_index = self.check_carrier_route(top_carrier[carrier_index]['route'], {'departure': i['departure'], 'destination': i['destination']})
            #
            #                 # filter service charge
            #                 # product total corresponding to particular pnr
            #                 # filter from service charge data
            #                 temp_charge = list(
            #                     filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i[
            #                         'reservation_order_number'], service_charge))
            #
            #                 # this section below is to count total revenue group by carrier/airline
            #                 # so no more provider like amadeus, or altea
            #                 # and no more multi carrier i.e Garuda,Lion
            #                 nta_total = 0
            #                 commission = 0
            #                 for k in temp_charge:
            #                     if k['booking_charge_type'] == 'RAC':
            #                         commission -= k['booking_charge_total']
            #                         nta_total += k['booking_charge_total']
            #                     else:
            #                         if k['booking_charge_type'] != '' and k['booking_charge_total']:
            #                             nta_total += k['booking_charge_total']
            #                 grand_total = nta_total + commission
            #
            #                 # each carrier will also have top 10 route by that particular Airline
            #                 # this code below responsible for that
            #                 if carrier_route_index == -1:
            #                     # route is not exist yet
            #                     # create temporary dict
            #                     temp_dict = {
            #                         'departure': i['departure'],
            #                         'destination': i['destination'],
            #                         'counter': 1,
            #                         'passenger': int(i['reservation_passenger'])
            #                     }
            #                     # add to list
            #                     top_carrier[carrier_index]['route'].append(temp_dict)
            #                 else:
            #                     # if exist then only add counter
            #                     top_carrier[carrier_index]['route'][carrier_route_index]['counter'] += 1
            #                     top_carrier[carrier_index]['route'][carrier_route_index]['passenger'] += int(i['reservation_passenger'])
            #                 # add carrier counter
            #                 top_carrier[carrier_index]['counter'] += 1
            #                 top_carrier[carrier_index]['revenue'] += grand_total
            #                 top_carrier[carrier_index]['passenger'] += i['reservation_passenger']
            #         except:
            #             pass
            #
            #         # ============= Summary by Domestic/International ============
            #         # this summary basically make table to create international and domestic by direction
            #         # like one way, return or even multi city
            #         if i['reservation_sector'] == 'International':
            #             # for every reservation with international destination
            #             # valuation = revenue
            #             sector_dictionary[0]['valuation'] += float(i['amount'])
            #             # counter = # of reservation
            #             sector_dictionary[0]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 # OW = one way
            #                 sector_dictionary[0]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 # rt = return
            #                 sector_dictionary[0]['return'] += 1
            #             else:
            #                 # else considered as multicity as of today 2020-12-08
            #                 sector_dictionary[0]['multi_city'] += 1
            #             # adding total passenger in international section
            #             sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            #         elif i['reservation_sector'] == 'Domestic':
            #             # for every reservation with domestic destination
            #             sector_dictionary[1]['valuation'] += float(i['amount'])
            #             sector_dictionary[1]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[1]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[1]['return'] += 1
            #             else:
            #                 sector_dictionary[1]['multi_city'] += 1
            #             sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            #         else:
            #             # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
            #             sector_dictionary[2]['valuation'] += float(i['amount'])
            #             sector_dictionary[2]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[2]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[2]['return'] += 1
            #             else:
            #                 sector_dictionary[2]['multi_city'] += 1
            #             sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])
            #
            #         # ============= end of Summary by Domestic/International ============
            #
            #         # issued depart days difference
            #         # ============= Issued compareed to depart date ==============
            #         # filter the data, resulting all of the data with respected order number
            #         filter_data = list(
            #             filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], issued_values['lines']))
            #
            #         # look for the nearest departure date from issued date
            #         depart_index = 0
            #         if len(filter_data) > 1:
            #             earliest_depart = filter_data[0]['journey_departure_date']
            #             for j, dic in enumerate(filter_data):
            #                 if earliest_depart > dic['journey_departure_date']:
            #                     depart_index = j
            #         # lets count
            #         if filter_data[0]['reservation_issued_date_og']:
            #             # conver journey date (string) to datetime
            #             date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'],'%Y-%m-%d %H:%M:%S')
            #             # check if reservation has issued dates
            #             # this should be quite obselete since this function only calls for issued reservation
            #             # but this function also written in more general function so.. there's that
            #             if filter_data[0]['reservation_issued_date_og']:
            #                 # actually counting the day difference between each date
            #                 date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
            #                 if date_count.days < 0:
            #                     # if for some whatever reason the date result in negative
            #                     # just print to logger, maybe if someday needed to be check there's the data in logger
            #                     _logger.error("please check {}".format(i['reservation_order_number']))
            #             else:
            #                 date_count = 0
            #
            #             # for airline only i dicided to seperate the data between international departure
            #             # and domestic departure, it makes more sense and insightful
            #             # so in here we check if the reservation has international or domestic destination (well from sector actually)
            #             if filter_data[0]['reservation_sector'] == 'International':
            #                 # if the data is international then we'll add it in international list
            #                 issued_depart_index = self.check_index(issued_depart_international_summary, "day", date_count.days)
            #                 # as always check the index
            #                 # if no index found a.k.a -1 then we'll create and add the data
            #                 if issued_depart_index == -1:
            #                     temp_dict = {
            #                         "day": date_count.days,
            #                         "counter": 1,
            #                         'passenger': filter_data[0]['reservation_passenger']
            #                     }
            #                     issued_depart_international_summary.append(temp_dict)
            #                 else:
            #                     # if data exist then we only need to update existing data
            #                     issued_depart_international_summary[issued_depart_index]['counter'] += 1
            #                     issued_depart_international_summary[issued_depart_index]['passenger'] += filter_data[0][
            #                         'reservation_passenger']
            #             else:
            #                 # as of today 2020-12-08 else considered as domestic
            #                 # so we'll add it in domestic section
            #                 issued_depart_index = self.check_index(issued_depart_domestic_summary, "day",
            #                                                        date_count.days)
            #                 if issued_depart_index == -1:
            #                     temp_dict = {
            #                         "day": date_count.days,
            #                         "counter": 1,
            #                         'passenger': filter_data[0]['reservation_passenger']
            #                     }
            #                     issued_depart_domestic_summary.append(temp_dict)
            #                 else:
            #                     issued_depart_domestic_summary[issued_depart_index]['counter'] += 1
            #                     issued_depart_domestic_summary[issued_depart_index]['passenger'] += filter_data[0][
            #                         'reservation_passenger']
            #
            #         # ============= end of Issued compareed to depart date ==============
            #
            #         if i['reservation_state'] == 'issued':
            #             # total += i['amount']
            #             # num_data += 1
            #
            #             # ============= Search best for every sector ==================
            #             # in this section we only compare how many reservation is actually for international destination
            #             # and how many domestic reservation
            #             # just to make is useful this report also sumarize passenger count, and reservation count
            #             returning_index = self.returning_index_sector(destination_sector_summary,{'departure': i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
            #             # once again as always we check for index then create and add if not exist, update if data already exist
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'sector': i['reservation_sector'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_sector_summary.append(new_dict)
            #             else:
            #                 destination_sector_summary[returning_index]['counter'] += 1
            #                 destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']
            #
            #             # ============= Search for best 50 routes ====================
            #             # in this section we want to extract top i dunno like 15 route of each sector
            #             # this code can produce more than 15, but will be trim later down the line
            #             # to make it insightful i add revenue data, and passenger count
            #             returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})
            #
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'direction': i['reservation_direction'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'sector': i['reservation_sector'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_direction_summary.append(new_dict)
            #             else:
            #                 destination_direction_summary[returning_index]['counter'] += 1
            #                 destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         # els in here means iterate data has the same order number as previous lines
            #         # with that we only need to update ledger count
            #         # no more filtering for smaller overview
            #
            #         # this if logic is needed because in a reservation can contain multi journey and multi segment and multi ledger
            #         # it will double with each join (in SQL)
            #         # in order not to double count, this if condition is needed
            #         if current_segment != i['segment_id'] and current_pnr != i['ledger_pnr']:
            #             # if both segment and pnr is diff, then we want to count the ledger
            #             # hence update to current pnr and segment
            #             current_segment = i['segment_id']
            #             current_pnr = i['ledger_pnr']
            #
            #             # this if condition is needed because even after i add ORDER BY in SQL for some reason ledger PNR could still be in mumbo jumbo
            #             # so we need to keep track what pnr is already count
            #             if current_pnr in pnr_within:
            #                 continue
            #             else:
            #                 pnr_within.append(current_pnr)
            #
            #             # Let's count
            #             if i['ledger_transaction_type'] == 3:   # type 3 = commission
            #                 # as always we look for what index particular data is
            #                 month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                 # get the date (also known as index in summary issued)
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                 # if HQ guy asking then we'll count everything
            #                 # if not HQ guy then we'll only count respected agent
            #                 if is_ho or agent_name_context == i['ledger_agent_name']:
            #                     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     profit_total += i['debit'] - i['credit']
            #                     profit_ho += i['debit'] - i['credit']
            #                 # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_ho += i['debit'] - i['credit']
            #                 # elif i['ledger_agent_type_name'] != 'HO':
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_agent += i['debit'] - i['credit']
            #
            #             # update top carrier base on same reservation but diff segment and diff pnr
            #             try:
            #                 # so because pnr and segment difference, we could safely assume that this is a new airline, could be the same
            #                 # but eitherway we'll gonna count it anyway so this section is for that
            #                 carrier_index = self.check_carrier(top_carrier, {'carrier_name': i['airline']})
            #
            #                 # at this point this seems really redundant so you know the drill.
            #                 if carrier_index == -1:
            #                     # filter service charge
            #                     # product total corresponding to particular pnr
            #                     # filter from service charge data
            #                     temp_charge = list(filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] ==i['reservation_order_number'], service_charge))
            #
            #                     # this section count revenue for each airline by looking thru the service charge
            #                     # so it's like super accurate
            #                     nta_total = 0
            #                     commission = 0
            #                     for k in temp_charge:
            #                         if k['booking_charge_type'] == 'RAC':
            #                             commission -= k['booking_charge_total']
            #                             nta_total += k['booking_charge_total']
            #                         else:
            #                             if k['booking_charge_type'] != '' and k['booking_charge_total']:
            #                                 nta_total += k['booking_charge_total']
            #                     grand_total = nta_total + commission
            #
            #                     # maybe not section above but below this you know the drill
            #                     # carrier is not exist yet
            #                     # declare a temporary dictionary
            #                     temp_dict = {
            #                         'carrier_name': i['airline'],
            #                         'counter': 1,
            #                         'revenue': grand_total,
            #                         'passenger': i['reservation_passenger'],
            #                         'route': [{
            #                             'departure': i['departure'],
            #                             'destination': i['destination'],
            #                             'counter': 1,
            #                             'passenger': i['reservation_passenger']
            #                         }]
            #                     }
            #                     # add to main list
            #                     top_carrier.append(temp_dict)
            #                 else:
            #                     # check index of route within top_carrier dictionary
            #                     carrier_route_index = self.check_carrier_route(top_carrier[carrier_index]['route'], {'departure': i['departure'], 'destination': i['destination']})
            #
            #                     # filter service charge
            #                     # product total corresponding to particular pnr
            #                     # filter from service charge data
            #                     temp_charge = list(filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i['reservation_order_number'], service_charge))
            #
            #                     # this section count revenue for each airline by looking thru the service charge
            #                     # so it's like super accurate
            #                     nta_total = 0
            #                     commission = 0
            #                     for k in temp_charge:
            #                         if k['booking_charge_type'] == 'RAC':
            #                             commission -= k['booking_charge_total']
            #                             nta_total += k['booking_charge_total']
            #                         else:
            #                             if k['booking_charge_type'] != '' and k['booking_charge_total']:
            #                                 nta_total += k['booking_charge_total']
            #                     grand_total = nta_total + commission
            #
            #                     # same drill
            #                     if carrier_route_index == -1:
            #                         # route is not exist yet
            #                         # create temporary dict
            #                         temp_dict = {
            #                             'departure': i['departure'],
            #                             'destination': i['destination'],
            #                             'counter': 1,
            #                             'passenger': int(i['reservation_passenger'])
            #                         }
            #                         # add to list
            #                         top_carrier[carrier_index]['route'].append(temp_dict)
            #                     else:
            #                         # if exist then only add counter
            #                         top_carrier[carrier_index]['route'][carrier_route_index]['counter'] += 1
            #                         top_carrier[carrier_index]['route'][carrier_route_index][
            #                             'passenger'] += int(i['reservation_passenger'])
            #                     # add carrier counter
            #                     top_carrier[carrier_index]['counter'] += 1
            #                     top_carrier[carrier_index]['revenue'] += grand_total
            #                     top_carrier[carrier_index]['passenger'] += i['reservation_passenger']
            #             except:
            #                 pass
            #
            #         elif current_segment == i['segment_id'] and current_pnr == i['ledger_pnr']:
            #             # if we have same segment and same pnr then we want to count for profit and all
            #             # count like always
            #             if i['ledger_transaction_type'] == 3:
            #                 month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                 # if HQ guy asking then we'll count everything
            #                 # if not HQ guy then we'll only count respected agent
            #                 if is_ho or agent_name_context == i['ledger_agent_name']:
            #                     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     profit_total += i['debit'] - i['credit']
            #                     profit_ho += i['debit'] - i['credit']
            #                 # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_ho += i['debit'] - i['credit']
            #                 # elif i['ledger_agent_type_name'] != 'HO':
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_agent += i['debit'] - i['credit']

            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # Departure
                    try:
                        # seperate city of departure
                        depart = i['departure'].split(" - ")
                        start_point_summary[depart[0]] += 1
                    except:
                        # seperate city of departure
                        depart = i['departure'].split(" - ")
                        start_point_summary[depart[0]] = 1

                    # Destination
                    try:
                        # seperate city of destination
                        desti = i['destination'].split(" - ")
                        end_point_summary[desti[0]] += 1
                    except:
                        # seperate city of destination
                        desti = i['destination'].split(" - ")
                        end_point_summary[desti[0]] = 1

                    # Top Carrier
                    try:
                        carrier_index = self.check_carrier(top_carrier, {'carrier_name': i['airline']})

                        if carrier_index == -1:
                            # filter service charge
                            # product total corresponding to particular pnr
                            # filter from service charge data
                            temp_charge = list(
                                filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i['reservation_order_number'], service_charge))

                            nta_total = 0
                            commission = 0
                            for k in temp_charge:
                                if k['booking_charge_type'] == 'RAC':
                                    commission -= k['booking_charge_total']
                                    nta_total += k['booking_charge_total']
                                else:
                                    if k['booking_charge_type'] != '' and k['booking_charge_total']:
                                        nta_total += k['booking_charge_total']
                            grand_total = nta_total + commission

                            # carrier is not exist yet
                            # declare a temporary dictionary
                            temp_dict = {
                                'carrier_name': i['airline'],
                                'counter': 1,
                                'revenue': grand_total,
                                'passenger': i['reservation_passenger'],
                                'route': [{
                                    'departure': i['departure'],
                                    'destination': i['destination'],
                                    'counter': 1,
                                    'passenger': i['reservation_passenger']
                                }]
                            }
                            # add to main list
                            top_carrier.append(temp_dict)
                        else:
                            # check index of route within top_carrier dictionary
                            carrier_route_index = self.check_carrier_route(top_carrier[carrier_index]['route'], {'departure': i['departure'], 'destination': i['destination']})

                            # filter service charge
                            # product total corresponding to particular pnr
                            # filter from service charge data
                            temp_charge = list(
                                filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i[
                                    'reservation_order_number'], service_charge))

                            # this section below is to count total revenue group by carrier/airline
                            # so no more provider like amadeus, or altea
                            # and no more multi carrier i.e Garuda,Lion
                            nta_total = 0
                            commission = 0
                            for k in temp_charge:
                                if k['booking_charge_type'] == 'RAC':
                                    commission -= k['booking_charge_total']
                                    nta_total += k['booking_charge_total']
                                else:
                                    if k['booking_charge_type'] != '' and k['booking_charge_total']:
                                        nta_total += k['booking_charge_total']
                            grand_total = nta_total + commission

                            # each carrier will also have top 10 route by that particular Airline
                            # this code below responsible for that
                            if carrier_route_index == -1:
                                # route is not exist yet
                                # create temporary dict
                                temp_dict = {
                                    'departure': i['departure'],
                                    'destination': i['destination'],
                                    'counter': 1,
                                    'passenger': int(i['reservation_passenger'])
                                }
                                # add to list
                                top_carrier[carrier_index]['route'].append(temp_dict)
                            else:
                                # if exist then only add counter
                                top_carrier[carrier_index]['route'][carrier_route_index]['counter'] += 1
                                top_carrier[carrier_index]['route'][carrier_route_index]['passenger'] += int(i['reservation_passenger'])
                            # add carrier counter
                            top_carrier[carrier_index]['counter'] += 1
                            top_carrier[carrier_index]['revenue'] += grand_total
                            top_carrier[carrier_index]['passenger'] += i['reservation_passenger']
                    except:
                        pass

                    # ============= Summary by Domestic/International ============
                    # this summary basically make table to create international and domestic by direction
                    # like one way, return or even multi city
                    if i['reservation_sector'] == 'International':
                        # for every reservation with international destination
                        # valuation = revenue
                        sector_dictionary[0]['valuation'] += float(i['amount'])
                        # counter = # of reservation
                        sector_dictionary[0]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            # OW = one way
                            sector_dictionary[0]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            # rt = return
                            sector_dictionary[0]['return'] += 1
                        else:
                            # else considered as multicity as of today 2020-12-08
                            sector_dictionary[0]['multi_city'] += 1
                        # adding total passenger in international section
                        sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                    elif i['reservation_sector'] == 'Domestic':
                        # for every reservation with domestic destination
                        sector_dictionary[1]['valuation'] += float(i['amount'])
                        sector_dictionary[1]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[1]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[1]['return'] += 1
                        else:
                            sector_dictionary[1]['multi_city'] += 1
                        sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                    else:
                        # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
                        sector_dictionary[2]['valuation'] += float(i['amount'])
                        sector_dictionary[2]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[2]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[2]['return'] += 1
                        else:
                            sector_dictionary[2]['multi_city'] += 1
                        sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                    # ============= end of Summary by Domestic/International ============

                    # issued depart days difference
                    # ============= Issued compareed to depart date ==============
                    # filter the data, resulting all of the data with respected order number
                    filter_data = list(
                        filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], issued_values['lines']))

                    # look for the nearest departure date from issued date
                    depart_index = 0
                    if len(filter_data) > 1:
                        earliest_depart = filter_data[0]['journey_departure_date']
                        for j, dic in enumerate(filter_data):
                            if earliest_depart > dic['journey_departure_date']:
                                depart_index = j
                    # lets count
                    if filter_data[0]['reservation_issued_date_og']:
                        # conver journey date (string) to datetime
                        date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'],'%Y-%m-%d %H:%M:%S')
                        # check if reservation has issued dates
                        # this should be quite obselete since this function only calls for issued reservation
                        # but this function also written in more general function so.. there's that
                        if filter_data[0]['reservation_issued_date_og']:
                            # actually counting the day difference between each date
                            date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                            if date_count.days < 0:
                                # if for some whatever reason the date result in negative
                                # just print to logger, maybe if someday needed to be check there's the data in logger
                                _logger.error("please check {}".format(i['reservation_order_number']))
                        else:
                            date_count = 0

                        # for airline only i dicided to seperate the data between international departure
                        # and domestic departure, it makes more sense and insightful
                        # so in here we check if the reservation has international or domestic destination (well from sector actually)
                        if filter_data[0]['reservation_sector'] == 'International':
                            # if the data is international then we'll add it in international list
                            issued_depart_index = self.check_index(issued_depart_international_summary, "day", date_count.days)
                            # as always check the index
                            # if no index found a.k.a -1 then we'll create and add the data
                            if issued_depart_index == -1:
                                temp_dict = {
                                    "day": date_count.days,
                                    "counter": 1,
                                    'passenger': filter_data[0]['reservation_passenger']
                                }
                                issued_depart_international_summary.append(temp_dict)
                            else:
                                # if data exist then we only need to update existing data
                                issued_depart_international_summary[issued_depart_index]['counter'] += 1
                                issued_depart_international_summary[issued_depart_index]['passenger'] += filter_data[0][
                                    'reservation_passenger']
                        else:
                            # as of today 2020-12-08 else considered as domestic
                            # so we'll add it in domestic section
                            issued_depart_index = self.check_index(issued_depart_domestic_summary, "day",
                                                                   date_count.days)
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

                    # ============= end of Issued compareed to depart date ==============

                    if i['reservation_state'] == 'issued':
                        # total += i['amount']
                        # num_data += 1

                        # ============= Search best for every sector ==================
                        # in this section we only compare how many reservation is actually for international destination
                        # and how many domestic reservation
                        # just to make is useful this report also sumarize passenger count, and reservation count
                        returning_index = self.returning_index_sector(destination_sector_summary,{'departure': i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
                        # once again as always we check for index then create and add if not exist, update if data already exist
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
                        # in this section we want to extract top i dunno like 15 route of each sector
                        # this code can produce more than 15, but will be trim later down the line
                        # to make it insightful i add revenue data, and passenger count
                        returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})

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

                    # current_id[i['provider_type_name']].append(i['reservation_id'])
                else:
                    # els in here means iterate data has the same order number as previous lines
                    # with that we only need to update ledger count
                    # no more filtering for smaller overview

                    # this if logic is needed because in a reservation can contain multi journey and multi segment and multi ledger
                    # it will double with each join (in SQL)
                    # in order not to double count, this if condition is needed
                    if current_segment != i['segment_id'] and current_pnr != i['ledger_pnr']:
                        # if both segment and pnr is diff, then we want to count the ledger
                        # hence update to current pnr and segment
                        current_segment = i['segment_id']
                        current_pnr = i['ledger_pnr']

                        # this if condition is needed because even after i add ORDER BY in SQL for some reason ledger PNR could still be in mumbo jumbo
                        # so we need to keep track what pnr is already count
                        if current_pnr in pnr_within:
                            continue
                        else:
                            pnr_within.append(current_pnr)

                        # Let's count
                        if i['ledger_transaction_type'] == 3:   # type 3 = commission
                            # as always we look for what index particular data is
                            month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
                            # get the date (also known as index in summary issued)
                            splits = i['reservation_issued_date'].split("-")
                            day_index = int(splits[2]) - 1
                            # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
                            # if HQ guy asking then we'll count everything
                            # if not HQ guy then we'll only count respected agent
                            # if is_ho or agent_name_context == i['ledger_agent_name']:
                            #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                            #     profit_total += i['debit'] - i['credit']
                            #     profit_ho += i['debit'] - i['credit']
                            # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
                            #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                            #     profit_total += i['debit'] - i['credit']
                            #     profit_ho += i['debit'] - i['credit']
                            # elif i['ledger_agent_type_name'] != 'HO':
                            #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                            #     profit_total += i['debit'] - i['credit']
                            #     profit_agent += i['debit'] - i['credit']

                        # update top carrier base on same reservation but diff segment and diff pnr
                        try:
                            # so because pnr and segment difference, we could safely assume that this is a new airline, could be the same
                            # but eitherway we'll gonna count it anyway so this section is for that
                            carrier_index = self.check_carrier(top_carrier, {'carrier_name': i['airline']})

                            # at this point this seems really redundant so you know the drill.
                            if carrier_index == -1:
                                # filter service charge
                                # product total corresponding to particular pnr
                                # filter from service charge data
                                temp_charge = list(filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] ==i['reservation_order_number'], service_charge))

                                # this section count revenue for each airline by looking thru the service charge
                                # so it's like super accurate
                                nta_total = 0
                                commission = 0
                                for k in temp_charge:
                                    if k['booking_charge_type'] == 'RAC':
                                        commission -= k['booking_charge_total']
                                        nta_total += k['booking_charge_total']
                                    else:
                                        if k['booking_charge_type'] != '' and k['booking_charge_total']:
                                            nta_total += k['booking_charge_total']
                                grand_total = nta_total + commission

                                # maybe not section above but below this you know the drill
                                # carrier is not exist yet
                                # declare a temporary dictionary
                                temp_dict = {
                                    'carrier_name': i['airline'],
                                    'counter': 1,
                                    'revenue': grand_total,
                                    'passenger': i['reservation_passenger'],
                                    'route': [{
                                        'departure': i['departure'],
                                        'destination': i['destination'],
                                        'counter': 1,
                                        'passenger': i['reservation_passenger']
                                    }]
                                }
                                # add to main list
                                top_carrier.append(temp_dict)
                            else:
                                # check index of route within top_carrier dictionary
                                carrier_route_index = self.check_carrier_route(top_carrier[carrier_index]['route'], {'departure': i['departure'], 'destination': i['destination']})

                                # filter service charge
                                # product total corresponding to particular pnr
                                # filter from service charge data
                                temp_charge = list(filter(lambda x: x['booking_pnr'] == i['ledger_pnr'] and x['order_number'] == i['reservation_order_number'], service_charge))

                                # this section count revenue for each airline by looking thru the service charge
                                # so it's like super accurate
                                nta_total = 0
                                commission = 0
                                for k in temp_charge:
                                    if k['booking_charge_type'] == 'RAC':
                                        commission -= k['booking_charge_total']
                                        nta_total += k['booking_charge_total']
                                    else:
                                        if k['booking_charge_type'] != '' and k['booking_charge_total']:
                                            nta_total += k['booking_charge_total']
                                grand_total = nta_total + commission

                                # same drill
                                if carrier_route_index == -1:
                                    # route is not exist yet
                                    # create temporary dict
                                    temp_dict = {
                                        'departure': i['departure'],
                                        'destination': i['destination'],
                                        'counter': 1,
                                        'passenger': int(i['reservation_passenger'])
                                    }
                                    # add to list
                                    top_carrier[carrier_index]['route'].append(temp_dict)
                                else:
                                    # if exist then only add counter
                                    top_carrier[carrier_index]['route'][carrier_route_index]['counter'] += 1
                                    top_carrier[carrier_index]['route'][carrier_route_index][
                                        'passenger'] += int(i['reservation_passenger'])
                                # add carrier counter
                                top_carrier[carrier_index]['counter'] += 1
                                top_carrier[carrier_index]['revenue'] += grand_total
                                top_carrier[carrier_index]['passenger'] += i['reservation_passenger']
                        except:
                            pass

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])

            # grouping data
            # it's like spliting the data into smaller container
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
            issued_depart_international_summary.sort(key=lambda x: x['counter'], reverse=True)
            issued_depart_domestic_summary.sort(key=lambda x: x['counter'], reverse=True)
            departure_summary = sorted(start_point_summary.items(), key=lambda item: item[1], reverse=True)
            destination_summary = sorted(end_point_summary.items(), key=lambda item: item[1], reverse=True)
            top_carrier.sort(key=lambda x: x['counter'], reverse=True)
            # sort route within top carrier
            for i in top_carrier:
                i['route'].sort(key=lambda x: x['counter'], reverse=True)

            # trim top carrier data
            carrier_summary = []
            counter = 0
            for i in top_carrier:
                # get the top 10 data
                if counter < 10:
                    # get top 10 route too
                    i['route'] = i['route'][:10]
                    carrier_summary.append(i)
                    # add counter
                    counter += 1
                else:
                    # cram other than top 10
                    try:
                        for j in i['route']:
                            route_index = self.check_carrier_route(carrier_summary[10]['route'], {'departure': j['departure'], 'destination': j['destination']})
                            if route_index == -1:
                                temp_dict = {
                                    'departure': j['departure'],
                                    'destination': j['destination'],
                                    'counter': j['counter'],
                                    'passenger': j['passenger']
                                }
                                # add to list
                                carrier_summary[10]['route'].append(temp_dict)
                            else:
                                carrier_summary[10]['route'][route_index]['counter'] += j['counter']
                                carrier_summary[10]['route'][route_index]['passenger'] += j['passenger']
                    except:
                        carrier_summary.append({
                            'carrier_name': 'Other',
                            'counter': 1,
                            'route': i['route']
                        })

            # sort and trim "other" carrier
            try:
                carrier_summary[10]['route'].sort(key=lambda x: x['counter'], reverse=True)
                carrier_summary[10]['route'] = carrier_summary[10]['route'][:10]
            except:
                pass

            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice total
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically
                #
                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                # build and trim data to exact date asked, just because
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # adding overview in graph
            departure_graph = {}
            destination_graph = {}

            # create counter variabel
            counter = 1
            other_counter = 0
            for i in departure_summary:
                if counter < 10:
                    departure_graph[i[0]] = i[1]
                    counter += 1
                else:
                    other_counter += i[1]

            departure_graph['Other'] = other_counter

            # reset the counter
            counter = 1
            other_counter = 0
            for i in destination_summary:
                if counter < 10:
                    destination_graph[i[0]] = i[1]
                    counter += 1
                else:
                    other_counter += i[1]

            destination_graph['Other'] = other_counter

            # prepare data to return
            # this data actually printed in frontend console.log so for debugging if it's easier then there's that
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': {
                    'sector_summary': sector_dictionary,
                    'international': international_filter[:20],
                    'domestic': domestic_filter[:20],
                    'one_way': one_way_filter[:20],
                    'return': return_filter[:20],
                    'multi_city': multi_city_filter[:20],
                    'departure_graph': {
                        'label': list(departure_graph.keys()),
                        'data': list(departure_graph.values())
                    },
                    'destination_graph': {
                        'label': list(destination_graph.keys()),
                        'data': list(destination_graph.values())
                    },
                    'international_issued_depart': issued_depart_international_summary[:15],
                    'domestic_issued_depart': issued_depart_domestic_summary[:15],
                    'carrier': carrier_summary
                }
            }
            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for train
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_train(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            # to get report by issued
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            #constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # ============== INITIATE RESULT DICT ==================
            sector_dictionary = [{
                'sector': 'International',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Domestic',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Other',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }]

            # overview base on the same timeframe
            destination_sector_summary = []
            destination_direction_summary = []
            issued_depart_summary = []

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # declare list to return
            summary_issued = []

            # declare current id
            current_id = {}
            current_journey = ''

            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # proceed invoice with the assumption of create date = issued date
            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             # set journey to current journey (id)
            #             current_journey = i['journey_id']
            #
            #             # search for month index within summary issued
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 # add the first profit if ledger type is 3 a.k.a commission
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         # ============= Summary by Domestic/International ============
            #         # this summary basically make table to create international and domestic by direction
            #         # like one way, return or even multi city
            #         if i['reservation_sector'] == 'International':
            #             # for every reservation with international destination
            #             # valuation = revenue
            #             sector_dictionary[0]['valuation'] += float(i['amount'])
            #             # counter = # of reservation
            #             sector_dictionary[0]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 # OW = one way
            #                 sector_dictionary[0]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 # rt = return
            #                 sector_dictionary[0]['return'] += 1
            #             else:
            #                 # else considered as multicity as of today 2020-12-08
            #                 sector_dictionary[0]['multi_city'] += 1
            #                 # adding total passenger in international section
            #             sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            #         elif i['reservation_sector'] == 'Domestic':
            #             # for every reservation with domestic destination
            #             sector_dictionary[1]['valuation'] += float(i['amount'])
            #             sector_dictionary[1]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[1]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[1]['return'] += 1
            #             else:
            #                 sector_dictionary[1]['multi_city'] += 1
            #             sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            #         else:
            #             # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
            #             sector_dictionary[2]['valuation'] += float(i['amount'])
            #             sector_dictionary[2]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[2]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[2]['return'] += 1
            #             else:
            #                 sector_dictionary[2]['multi_city'] += 1
            #             sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])
            #
            #         # issued depart days difference
            #         # ============= Issued compareed to depart date ==============
            #         # filter the data, resulting all of the data with respected order number
            #         filter_data = list(
            #             filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
            #                    issued_values['lines']))
            #
            #         # look for the nearest departure date from issued date
            #         depart_index = 0
            #         if len(filter_data) > 1:
            #             earliest_depart = filter_data[0]['journey_departure_date']
            #             for j, dic in enumerate(filter_data):
            #                 if earliest_depart > dic['journey_departure_date']:
            #                     depart_index = j
            #         # lets count
            #         if filter_data[0]['reservation_issued_date_og']:
            #             # conver journey date (string) to datetime
            #             date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'], '%Y-%m-%d %H:%M')
            #             # check if reservation has issued dates
            #             # this should be quite obselete since this function only calls for issued reservation
            #             # but this function also written in more general function so.. there's that
            #             if filter_data[0]['reservation_issued_date_og']:
            #                 # actually counting the day difference between each date
            #                 date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
            #                 if date_count.days < 0:
            #                     # if for some whatever reason the date result in negative
            #                     # just print to logger, maybe if someday needed to be check there's the data in logger
            #                     _logger.error("please check {}".format(i['reservation_order_number']))
            #             else:
            #                 date_count = 0
            #
            #             # check for index in issued depart summary
            #             issued_depart_index = self.check_index(issued_depart_summary, "day", date_count.days)
            #             # if no index found a.k.a -1 then we'll create and add the data
            #             if issued_depart_index == -1:
            #                 temp_dict = {
            #                     "day": date_count.days,
            #                     "counter": 1,
            #                     'passenger': filter_data[0]['reservation_passenger']
            #                 }
            #                 issued_depart_summary.append(temp_dict)
            #             else:
            #                 # if data exist then we only need to update existing data
            #                 issued_depart_summary[issued_depart_index]['counter'] += 1
            #                 issued_depart_summary[issued_depart_index]['passenger'] += \
            #                 filter_data[0][
            #                     'reservation_passenger']
            #
            #         # ============= end of Issued compareed to depart date ==============
            #
            #
            #         if i['reservation_state'] == 'issued':
            #             # total += i['amount']
            #             # num_data += 1
            #
            #             # ============= Search best for every sector ==================
            #             # in this section we only compare how many reservation is actually for international destination
            #             # and how many domestic reservation
            #             # just to make is useful this report also sumarize passenger count, and reservation count
            #             returning_index = self.returning_index_sector(destination_sector_summary, {'departure':
            #             # once again as always we check for index then create and add if not exist, update if data already exist
            #              i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'sector': i['reservation_sector'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_sector_summary.append(new_dict)
            #             else:
            #                 destination_sector_summary[returning_index]['counter'] += 1
            #                 destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']
            #
            #             # ============= Search for best 50 routes ====================
            #             # in this section we want to extract top i dunno like 15 route of each sector
            #             # this code can produce more than 15, but will be trim later down the line
            #             # to make it insightful i add revenue data, and passenger count
            #             returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})
            #
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'direction': i['reservation_direction'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'sector': i['reservation_sector'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_direction_summary.append(new_dict)
            #             else:
            #                 destination_direction_summary[returning_index]['counter'] += 1
            #                 destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']
            #
            #         # update current id
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         # els in here means iterate data has the same order number as previous lines
            #         # with that we only need to update ledger count
            #         # no more filtering for smaller overview
            #
            #         # in order not to double count, this if condition is needed
            #         if current_journey == i['journey_id']:
            #             if i['ledger_transaction_type'] == 3:
            #                 # get index of particular year and month
            #                 month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                 # split date to extract day
            #                 splits = i['reservation_issued_date'].split("-")
            #                 # get day
            #                 day_index = int(splits[2]) - 1
            #                 # add profit to respected array
            #                 # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                 # if HQ guy asking then we'll count everything
            #                 # if not HQ guy then we'll only count respected agent
            #                 if is_ho or agent_name_context == i['ledger_agent_name']:
            #                     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     profit_total += i['debit'] - i['credit']
            #                     profit_ho += i['debit'] - i['credit']
            #                 # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_ho += i['debit'] - i['credit']
            #                 # elif i['ledger_agent_type_name'] != 'HO':
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_agent += i['debit'] - i['credit']

            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= Summary by Domestic/International ============
                    # this summary basically make table to create international and domestic by direction
                    # like one way, return or even multi city
                    if i['reservation_sector'] == 'International':
                        # for every reservation with international destination
                        # valuation = revenue
                        sector_dictionary[0]['valuation'] += float(i['amount'])
                        # counter = # of reservation
                        sector_dictionary[0]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            # OW = one way
                            sector_dictionary[0]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            # rt = return
                            sector_dictionary[0]['return'] += 1
                        else:
                            # else considered as multicity as of today 2020-12-08
                            sector_dictionary[0]['multi_city'] += 1
                            # adding total passenger in international section
                        sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                    elif i['reservation_sector'] == 'Domestic':
                        # for every reservation with domestic destination
                        sector_dictionary[1]['valuation'] += float(i['amount'])
                        sector_dictionary[1]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[1]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[1]['return'] += 1
                        else:
                            sector_dictionary[1]['multi_city'] += 1
                        sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                    else:
                        # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
                        sector_dictionary[2]['valuation'] += float(i['amount'])
                        sector_dictionary[2]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[2]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[2]['return'] += 1
                        else:
                            sector_dictionary[2]['multi_city'] += 1
                        sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                    # issued depart days difference
                    # ============= Issued compareed to depart date ==============
                    # filter the data, resulting all of the data with respected order number
                    filter_data = list(
                        filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
                               issued_values['lines']))

                    # look for the nearest departure date from issued date
                    depart_index = 0
                    if len(filter_data) > 1:
                        earliest_depart = filter_data[0]['journey_departure_date']
                        for j, dic in enumerate(filter_data):
                            if earliest_depart > dic['journey_departure_date']:
                                depart_index = j
                    # lets count
                    if filter_data[0]['reservation_issued_date_og']:
                        # conver journey date (string) to datetime
                        date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'], '%Y-%m-%d %H:%M')
                        # check if reservation has issued dates
                        # this should be quite obselete since this function only calls for issued reservation
                        # but this function also written in more general function so.. there's that
                        if filter_data[0]['reservation_issued_date_og']:
                            # actually counting the day difference between each date
                            date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                            if date_count.days < 0:
                                # if for some whatever reason the date result in negative
                                # just print to logger, maybe if someday needed to be check there's the data in logger
                                _logger.error("please check {}".format(i['reservation_order_number']))
                        else:
                            date_count = 0

                        # check for index in issued depart summary
                        issued_depart_index = self.check_index(issued_depart_summary, "day", date_count.days)
                        # if no index found a.k.a -1 then we'll create and add the data
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_summary.append(temp_dict)
                        else:
                            # if data exist then we only need to update existing data
                            issued_depart_summary[issued_depart_index]['counter'] += 1
                            issued_depart_summary[issued_depart_index]['passenger'] += \
                            filter_data[0][
                                'reservation_passenger']

                    # ============= end of Issued compareed to depart date ==============


                    if i['reservation_state'] == 'issued':
                        # total += i['amount']
                        # num_data += 1

                        # ============= Search best for every sector ==================
                        # in this section we only compare how many reservation is actually for international destination
                        # and how many domestic reservation
                        # just to make is useful this report also sumarize passenger count, and reservation count
                        returning_index = self.returning_index_sector(destination_sector_summary, {'departure':
                        # once again as always we check for index then create and add if not exist, update if data already exist
                         i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
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
                        # in this section we want to extract top i dunno like 15 route of each sector
                        # this code can produce more than 15, but will be trim later down the line
                        # to make it insightful i add revenue data, and passenger count
                        returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})

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

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])

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
            issued_depart_summary.sort(key=lambda x: x['counter'], reverse=True)

            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically
                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': {
                    'sector_summary': sector_dictionary,
                    'international': international_filter[:20],
                    'domestic': domestic_filter[:20],
                    'one_way': one_way_filter[:20],
                    'return': return_filter[:20],
                    'multi_city': multi_city_filter[:20],
                    'issued_depart': issued_depart_summary[:15]
                }
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for hotel
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_hotel(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            # get report by issued
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            # execute query
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            location_overview = []
            issued_depart_summary = []

            # declare current id
            current_id = {}

            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         try:
            #             # this section responsible to build overview in hotel
            #             # the overview group the data by city, and adding like top 10 hotel within the city
            #             # code below is searching for index of city within location_overview
            #             location_index = self.check_location(location_overview, {'city': i['hotel_city']})
            #
            #             # if city cannot be found in location_overview, index will return as -1
            #             # hence we need to create and append the data
            #             if location_index == -1:
            #                 # build a temporary dictionary
            #                 temp_dict = {
            #                     'country': i['country_name'] if i['country_name'] else '',
            #                     'city': i['hotel_city'],
            #                     'counter': 1,
            #                     'revenue': i['amount'],
            #                     'passenger': i['reservation_passenger'],
            #                     'hotel': [{
            #                         'name': i['reservation_hotel_name'],
            #                         'counter': 1,
            #                         'passenger': i['reservation_passenger'],
            #                         'revenue': i['amount']
            #                     }]
            #                 }
            #                 # append to location_overview
            #                 location_overview.append(temp_dict)
            #             else:
            #                 # if city is exist, then we only need to look out for specific hotel
            #                 # if hotel not found same drill as city, and if exist then we only need to update the data
            #                 hotel_index = self.check_hotel_index(location_overview[location_index]['hotel'], {'name': i['reservation_hotel_name']})
            #
            #                 if hotel_index == -1:
            #                     temp_dict = {
            #                         'name': i['reservation_hotel_name'],
            #                         'counter': 1,
            #                         'passenger': i['reservation_passenger'],
            #                         'revenue': i['amount']
            #                     }
            #                     location_overview[location_index]['hotel'].append(temp_dict)
            #                 else:
            #                     # this only update the data
            #                     location_overview[location_index]['hotel'][hotel_index]['counter'] += 1
            #                     location_overview[location_index]['hotel'][hotel_index]['passenger'] += i['reservation_passenger']
            #                 # this update the data for the city
            #                 location_overview[location_index]['counter'] += 1
            #                 location_overview[location_index]['revenue'] += i['amount']
            #                 location_overview[location_index]['passenger'] += i['reservation_passenger']
            #         except:
            #             pass
            #
            #         # issued to check in days difference
            #         # have the same logic as issued to depart in airline and train
            #         # ============= Issued compareed to depart date ==============
            #         # filter the data, resulting all of the data with respected order number
            #         filter_data = list(
            #             filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
            #                    issued_values['lines']))
            #
            #         # look for the nearest departure date from issued date
            #         depart_index = 0
            #         if len(filter_data) > 1:
            #             earliest_depart = filter_data[0]['reservation_check_in_date']
            #             for j, dic in enumerate(filter_data):
            #                 if earliest_depart > dic['reservation_check_in_date']:
            #                     depart_index = j
            #         # lets count
            #         if filter_data[0]['reservation_issued_date_og']:
            #             date_time_convert = datetime(filter_data[depart_index]['reservation_check_in_date'].year, filter_data[depart_index]['reservation_check_in_date'].month, filter_data[depart_index]['reservation_check_in_date'].day)
            #             if filter_data[0]['reservation_issued_date_og']:
            #                 date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
            #                 if date_count.days < 0:
            #                     _logger.error("please check {}".format(i['reservation_order_number']))
            #             else:
            #                 date_count = 0
            #
            #             issued_depart_index = self.check_index(issued_depart_summary, "day",
            #                                                    date_count.days)
            #             if issued_depart_index == -1:
            #                 temp_dict = {
            #                     "day": date_count.days,
            #                     "counter": 1,
            #                     'passenger': filter_data[0]['reservation_passenger']
            #                 }
            #                 issued_depart_summary.append(temp_dict)
            #             else:
            #                 issued_depart_summary[issued_depart_index]['counter'] += 1
            #                 issued_depart_summary[issued_depart_index]['passenger'] += \
            #                     filter_data[0][
            #                         'reservation_passenger']
            #
            #         # ============= end of Issued compareed to depart date ==============
            #
            #         # update current id to reservation id of current iteration
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agennt
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']

            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    try:
                        # this section responsible to build overview in hotel
                        # the overview group the data by city, and adding like top 10 hotel within the city
                        # code below is searching for index of city within location_overview
                        location_index = self.check_location(location_overview, {'city': i['hotel_city']})

                        # if city cannot be found in location_overview, index will return as -1
                        # hence we need to create and append the data
                        if location_index == -1:
                            # build a temporary dictionary
                            temp_dict = {
                                'country': i['country_name'] if i['country_name'] else '',
                                'city': i['hotel_city'],
                                'counter': 1,
                                'revenue': i['amount'],
                                'passenger': i['reservation_passenger'],
                                'hotel': [{
                                    'name': i['reservation_hotel_name'],
                                    'counter': 1,
                                    'passenger': i['reservation_passenger'],
                                    'revenue': i['amount']
                                }]
                            }
                            # append to location_overview
                            location_overview.append(temp_dict)
                        else:
                            # if city is exist, then we only need to look out for specific hotel
                            # if hotel not found same drill as city, and if exist then we only need to update the data
                            hotel_index = self.check_hotel_index(location_overview[location_index]['hotel'], {'name': i['reservation_hotel_name']})

                            if hotel_index == -1:
                                temp_dict = {
                                    'name': i['reservation_hotel_name'],
                                    'counter': 1,
                                    'passenger': i['reservation_passenger'],
                                    'revenue': i['amount']
                                }
                                location_overview[location_index]['hotel'].append(temp_dict)
                            else:
                                # this only update the data
                                location_overview[location_index]['hotel'][hotel_index]['counter'] += 1
                                location_overview[location_index]['hotel'][hotel_index]['passenger'] += i['reservation_passenger']
                            # this update the data for the city
                            location_overview[location_index]['counter'] += 1
                            location_overview[location_index]['revenue'] += i['amount']
                            location_overview[location_index]['passenger'] += i['reservation_passenger']
                    except:
                        pass

                    # issued to check in days difference
                    # have the same logic as issued to depart in airline and train
                    # ============= Issued compareed to depart date ==============
                    # filter the data, resulting all of the data with respected order number
                    filter_data = list(
                        filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
                               issued_values['lines']))

                    # look for the nearest departure date from issued date
                    depart_index = 0
                    if len(filter_data) > 1:
                        earliest_depart = filter_data[0]['reservation_check_in_date']
                        for j, dic in enumerate(filter_data):
                            if earliest_depart > dic['reservation_check_in_date']:
                                depart_index = j
                    # lets count
                    if filter_data[0]['reservation_issued_date_og']:
                        date_time_convert = datetime(filter_data[depart_index]['reservation_check_in_date'].year, filter_data[depart_index]['reservation_check_in_date'].month, filter_data[depart_index]['reservation_check_in_date'].day)
                        if filter_data[0]['reservation_issued_date_og']:
                            date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                            if date_count.days < 0:
                                _logger.error("please check {}".format(i['reservation_order_number']))
                        else:
                            date_count = 0

                        issued_depart_index = self.check_index(issued_depart_summary, "day",
                                                               date_count.days)
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_summary.append(temp_dict)
                        else:
                            issued_depart_summary[issued_depart_index]['counter'] += 1
                            issued_depart_summary[issued_depart_index]['passenger'] += \
                                filter_data[0][
                                    'reservation_passenger']

                    # ============= end of Issued compareed to depart date ==============

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])

            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            location_overview.sort(key=lambda x: x['counter'], reverse=True)
            issued_depart_summary.sort(key=lambda x: x['counter'], reverse=True)

            # sort hotel inside locaion overview
            for i in location_overview:
                i['hotel'].sort(key=lambda x: x['counter'], reverse=True)

            #trim to top 10
            # there will be 11 data, as i compress 11 to n as other
            #declare final list
            location_summary = []
            counter = 0
            for i in location_overview:
                if counter < 10:
                    # trim to top 10
                    i['hotel'] = i['hotel'][:10]

                    # add to overall list
                    location_summary.append(i)

                    # add counter
                    counter += 1
                else:
                # put everything else at other
                    try:
                        for j in i['hotel']:
                            # try to merge hotel from a lot of line (means look for index of hotel #again)
                            hotel_index = self.check_hotel_index(location_summary[10]['hotel'], {'name': j['name']})

                            if hotel_index == -1:
                                # no data yet (either not overlapping, or just hasn't been inputed)
                                location_summary[10]['hotel'].append({
                                    'name': j['name'],
                                    'counter': j['counter'],
                                    'passenger': j['passenger']
                                })
                            else:
                                # everything is there
                                location_summary[10]['hotel'][hotel_index]['counter'] += j['counter']
                                location_summary[10]['hotel'][hotel_index]['passenger'] += j['passenger']
                        location_summary[10]['counter'] += i['counter']
                    except:
                        # index 10 do not exist
                        location_summary.append({
                            'country': 'Other',
                            'city': 'Other',
                            'counter': i['counter'],
                            'hotel': i['hotel']})

            # sort end result of location summary
            # and despite it's other we would only return top 10 data
            try:
                location_summary[10]['hotel'].sort(key=lambda x: x['counter'], reverse=True)
                location_summary[10]['hotel'] = location_summary[10]['hotel'][:10]
            except:
                pass

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            # this data actually printed in frontend console.log so for debugging if it's easier then there's that
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'first_overview': {
                    'location': location_summary,
                    'issued_depart': issued_depart_summary[:15]
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for tour
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_tour(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            product_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[
            #                                                                      int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         # ============= product summary =====================================
            #         product_index = self.check_index(product_summary, 'product', i['tour_name'])
            #         if product_index == -1:
            #             temp_dict = {
            #                 'product': i['tour_name'],
            #                 'product_type': i['tour_type'],
            #                 'counter': 1,
            #                 'elder_count': i['reservation_elder'],
            #                 'adult_count': i['reservation_adult'],
            #                 'child_count': i['reservation_child'],
            #                 'infant_count': i['reservation_infant'],
            #                 'passenger': i['reservation_passenger'],
            #                 'amount': i['amount']
            #             }
            #             product_summary.append(temp_dict)
            #         else:
            #             product_summary[product_index]['counter'] += 1
            #             product_summary[product_index]['passenger'] += i['reservation_passenger']
            #             product_summary[product_index]['amount'] += i['amount']
            #             product_summary[product_index]['elder_count'] += i['reservation_elder']
            #             product_summary[product_index]['adult_count'] += i['reservation_adult']
            #             product_summary[product_index]['child_count'] += i['reservation_child']
            #             product_summary[product_index]['infant_count'] += i['reservation_infant']
            #         # ============= end of product summary ==============================
            #
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[
            #                                                                      int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= product summary =====================================
                    product_index = self.check_index(product_summary, 'product', i['tour_name'])
                    if product_index == -1:
                        temp_dict = {
                            'product': i['tour_name'],
                            'product_type': i['tour_type'],
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
                    # ============= end of product summary ==============================

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            product_summary.sort(key=lambda x: x['counter'], reverse=True)

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': product_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for activity
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_activity(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            product_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         # ============= product summary =====================================
            #         product_index = self.check_index(product_summary, 'product', i['reservation_activity_name'])
            #         if product_index == -1:
            #             temp_dict = {
            #                 'product': i['reservation_activity_name'],
            #                 'counter': 1,
            #                 'elder_count': i['reservation_elder'],
            #                 'adult_count': i['reservation_adult'],
            #                 'child_count': i['reservation_child'],
            #                 'infant_count': i['reservation_infant'],
            #                 'passenger': i['reservation_passenger'],
            #                 'amount': i['amount']
            #             }
            #             product_summary.append(temp_dict)
            #         else:
            #             product_summary[product_index]['counter'] += 1
            #             product_summary[product_index]['passenger'] += i['reservation_passenger']
            #             product_summary[product_index]['amount'] += i['amount']
            #             product_summary[product_index]['elder_count'] += i['reservation_elder']
            #             product_summary[product_index]['adult_count'] += i['reservation_adult']
            #             product_summary[product_index]['child_count'] += i['reservation_child']
            #             product_summary[product_index]['infant_count'] += i['reservation_infant']
            #         # ============= end of product summary ==============================
            #
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= product summary =====================================
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
                    # ============= end of product summary ==============================

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            product_summary.sort(key=lambda x: x['counter'], reverse=True)

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': product_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for event
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_event(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            product_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             product_index = self.check_index(product_summary, 'product', i['reservation_event_name'])
            #             if product_index == -1:
            #                 temp_dict = {
            #                     'product': i['reservation_event_name'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 product_summary.append(temp_dict)
            #             else:
            #                 product_summary[product_index]['counter'] += 1
            #                 product_summary[product_index]['passenger'] += i['reservation_passenger']
            #                 product_summary[product_index]['amount'] += i['amount']
            #                 product_summary[product_index]['elder_count'] += i['reservation_elder']
            #                 product_summary[product_index]['adult_count'] += i['reservation_adult']
            #                 product_summary[product_index]['child_count'] += i['reservation_child']
            #                 product_summary[product_index]['infant_count'] += i['reservation_infant']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= product summary =====================================
                    product_index = self.check_index(product_summary, 'product', i['reservation_event_name'])
                    if product_index == -1:
                        temp_dict = {
                            'product': i['reservation_event_name'],
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
                    # ============= end of product summary =====================================

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            product_summary.sort(key=lambda x: x['counter'], reverse=True)

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'first_overview': product_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for visa
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_visa(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            country_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # ============= Country summary Report =======================
            #             country_index = self.check_index(country_summary, 'country', i['country_name'])
            #             if country_index == -1:
            #                 temp_dict = {
            #                     'country': i['country_name'],
            #                     'counter': 1,
            #                     'passenger': i['reservation_passenger']
            #                 }
            #                 country_summary.append(temp_dict)
            #             else:
            #                 country_summary[country_index]['counter'] += 1
            #                 country_summary[country_index]['passenger'] += i['reservation_passenger']
            #         except:
            #             pass
            #
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= product summary =====================================
                    # ============= Country summary Report =======================
                    country_index = self.check_index(country_summary, 'country', i['country_name'])
                    if country_index == -1:
                        temp_dict = {
                            'country': i['country_name'],
                            'counter': 1,
                            'passenger': i['reservation_passenger']
                        }
                        country_summary.append(temp_dict)
                    else:
                        country_summary[country_index]['counter'] += 1
                        country_summary[country_index]['passenger'] += i['reservation_passenger']
                    # ============= end of product summary =====================================

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            country_summary.sort(key=lambda x: x['counter'], reverse=True)

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': country_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for offline
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_offline(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            offline_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # group data by offline provider type (airline, train, etc)
            #             offline_index = self.check_index(offline_summary, 'provider_type', i['reservation_offline_provider_type'])
            #             if offline_index == -1:
            #                 temp_dict = {
            #                     'category': 'Offline',
            #                     'provider_type': i['reservation_offline_provider_type'],
            #                     'counter': 1,
            #                     'amount': i['amount']
            #                 }
            #                 offline_summary.append(temp_dict)
            #             else:
            #                 offline_summary[offline_index]['counter'] += 1
            #                 offline_summary[offline_index]['amount'] += i['amount']
            #         except:
            #             pass
            #
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # group data by offline provider type (airline, train, etc)
                    offline_index = self.check_index(offline_summary, 'provider_type', i['reservation_offline_provider_type'])
                    if offline_index == -1:
                        temp_dict = {
                            'category': 'Offline',
                            'provider_type': i['reservation_offline_provider_type'],
                            'counter': 1,
                            'amount': i['amount']
                        }
                        offline_summary.append(temp_dict)
                    else:
                        offline_summary[offline_index]['counter'] += 1
                        offline_summary[offline_index]['amount'] += i['amount']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            offline_summary.sort(key=lambda x: (x['amount'], x['counter']))

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': offline_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for ppob
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_ppob(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            ppob_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate ppob_summary
            #             ppob_index = self.check_index(ppob_summary, 'product', i['carrier_name'])
            #             if ppob_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 ppob_summary.append(temp_dict)
            #             else:
            #                 ppob_summary[ppob_index]['counter'] += 1
            #                 ppob_summary[ppob_index]['amount'] += i['amount']
            #                 ppob_summary[ppob_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate ppob_summary
                    ppob_index = self.check_index(ppob_summary, 'product', i['carrier_name'])
                    if ppob_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        ppob_summary.append(temp_dict)
                    else:
                        ppob_summary[ppob_index]['counter'] += 1
                        ppob_summary[ppob_index]['amount'] += i['amount']
                        ppob_summary[ppob_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            ppob_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': ppob_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    # this function handle data handler and processing for passport
    # data = form data from frontend
    # is_ho = ho checker from main function
    def get_report_overall_passport(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            # convert time to UTC0 from UTC7
            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            # prepare data to search reservation list
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }

            # search reservation list
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # declare some constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            # count the date difference
            delta = end_date - start_date

            # check if difference in date more than 35 days, change "return" result to month (group by month, instead of daily (date) report)
            if delta.days > 35:
                # group by month
                mode = 'month'

            # preparing to look correspond invoice with list of reservation
            # making a list of reservation id(s)
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            # prepare data
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }

            # look for invoice
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            passport_summary = []
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk
            # declare current id

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate passport_summary
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             if i['ledger_transaction_type'] == 3:
            #                 # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                 # if HQ guy asking then we'll count everything
            #                 # if not HQ guy then we'll only count respected agent
            #                 if is_ho or agent_name_context == i['ledger_agent_name']:
            #                     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     profit_total += i['debit'] - i['credit']
            #                     profit_ho += i['debit'] - i['credit']
            #                 # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_ho += i['debit'] - i['credit']
            #                 # elif i['ledger_agent_type_name'] != 'HO':
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / len(filtered_data) if len(filtered_data) > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            # passport_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                'invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': passport_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_phc(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            phc_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agennt
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i[
            #                             'credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate phc_summary
            #             phc_index = self.check_index(phc_summary, 'product', i['carrier_name'])
            #             if phc_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 phc_summary.append(temp_dict)
            #             else:
            #                 phc_summary[phc_index]['counter'] += 1
            #                 phc_summary[phc_index]['amount'] += i['amount']
            #                 phc_summary[phc_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']
                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate phc_summary
                    phc_index = self.check_index(phc_summary, 'product', i['carrier_name'])
                    if phc_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        phc_summary.append(temp_dict)
                    else:
                        phc_summary[phc_index]['counter'] += 1
                        phc_summary[phc_index]['amount'] += i['amount']
                        phc_summary[phc_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            phc_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': phc_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_periksain(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            periksain_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate periksain_summary
            #             periksain_index = self.check_index(periksain_summary, 'product', i['carrier_name'])
            #             if periksain_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 periksain_summary.append(temp_dict)
            #             else:
            #                 periksain_summary[periksain_index]['counter'] += 1
            #                 periksain_summary[periksain_index]['amount'] += i['amount']
            #                 periksain_summary[periksain_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate periksain_summary
                    periksain_index = self.check_index(periksain_summary, 'product', i['carrier_name'])
                    if periksain_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        periksain_summary.append(temp_dict)
                    else:
                        periksain_summary[periksain_index]['counter'] += 1
                        periksain_summary[periksain_index]['amount'] += i['amount']
                        periksain_summary[periksain_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            periksain_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': periksain_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_medical(self, data, is_ho, context = {}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            medical_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate medical_summary
            #             medical_index = self.check_index(medical_summary, 'product', i['carrier_name'])
            #             if medical_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 medical_summary.append(temp_dict)
            #             else:
            #                 medical_summary[medical_index]['counter'] += 1
            #                 medical_summary[medical_index]['amount'] += i['amount']
            #                 medical_summary[medical_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate medical_summary
                    medical_index = self.check_index(medical_summary, 'product', i['carrier_name'])
                    if medical_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        medical_summary.append(temp_dict)
                    else:
                        medical_summary[medical_index]['counter'] += 1
                        medical_summary[medical_index]['amount'] += i['amount']
                        medical_summary[medical_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            medical_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': medical_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_bus(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT 0
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            # to get report by issued
            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            #constant dependencies
            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            # ============== INITIATE RESULT DICT ==================
            sector_dictionary = [{
                'sector': 'International',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Domestic',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }, {
                'sector': 'Other',
                'valuation': 0,
                'passenger_count': 0,
                'counter': 0,
                'one_way': 0,
                'return': 0,
                'multi_city': 0
            }]

            # overview base on the same timeframe
            destination_sector_summary = []
            destination_direction_summary = []
            issued_depart_summary = []

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0

            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # declare list to return
            summary_issued = []

            # declare current id
            current_id = {}
            current_journey = ''
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # proceed invoice with the assumption of create date = issued date
            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             # set journey to current journey (id)
            #             current_journey = i['journey_id']
            #
            #             # search for month index within summary issued
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 # add the first profit if ledger type is 3 a.k.a commission
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #         except:
            #             pass
            #
            #         # ============= Summary by Domestic/International ============
            #         # this summary basically make table to create international and domestic by direction
            #         # like one way, return or even multi city
            #         if i['reservation_sector'] == 'International':
            #             # for every reservation with international destination
            #             # valuation = revenue
            #             sector_dictionary[0]['valuation'] += float(i['amount'])
            #             # counter = # of reservation
            #             sector_dictionary[0]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 # OW = one way
            #                 sector_dictionary[0]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 # rt = return
            #                 sector_dictionary[0]['return'] += 1
            #             else:
            #                 # else considered as multicity as of today 2020-12-08
            #                 sector_dictionary[0]['multi_city'] += 1
            #                 # adding total passenger in international section
            #             sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            #         elif i['reservation_sector'] == 'Domestic':
            #             # for every reservation with domestic destination
            #             sector_dictionary[1]['valuation'] += float(i['amount'])
            #             sector_dictionary[1]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[1]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[1]['return'] += 1
            #             else:
            #                 sector_dictionary[1]['multi_city'] += 1
            #             sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            #         else:
            #             # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
            #             sector_dictionary[2]['valuation'] += float(i['amount'])
            #             sector_dictionary[2]['counter'] += 1
            #             if i['reservation_direction'] == 'OW':
            #                 sector_dictionary[2]['one_way'] += 1
            #             elif i['reservation_direction'] == 'RT':
            #                 sector_dictionary[2]['return'] += 1
            #             else:
            #                 sector_dictionary[2]['multi_city'] += 1
            #             sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])
            #
            #         # issued depart days difference
            #         # ============= Issued compareed to depart date ==============
            #         # filter the data, resulting all of the data with respected order number
            #         filter_data = list(
            #             filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
            #                    issued_values['lines']))
            #
            #         # look for the nearest departure date from issued date
            #         depart_index = 0
            #         if len(filter_data) > 1:
            #             earliest_depart = filter_data[0]['journey_departure_date']
            #             for j, dic in enumerate(filter_data):
            #                 if earliest_depart > dic['journey_departure_date']:
            #                     depart_index = j
            #         # lets count
            #         if filter_data[0]['reservation_issued_date_og']:
            #             # conver journey date (string) to datetime
            #             date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'], '%Y-%m-%d %H:%M:%S')
            #             # check if reservation has issued dates
            #             # this should be quite obselete since this function only calls for issued reservation
            #             # but this function also written in more general function so.. there's that
            #             if filter_data[0]['reservation_issued_date_og']:
            #                 # actually counting the day difference between each date
            #                 date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
            #                 if date_count.days < 0:
            #                     # if for some whatever reason the date result in negative
            #                     # just print to logger, maybe if someday needed to be check there's the data in logger
            #                     _logger.error("please check {}".format(i['reservation_order_number']))
            #             else:
            #                 date_count = 0
            #
            #             # check for index in issued depart summary
            #             issued_depart_index = self.check_index(issued_depart_summary, "day", date_count.days)
            #             # if no index found a.k.a -1 then we'll create and add the data
            #             if issued_depart_index == -1:
            #                 temp_dict = {
            #                     "day": date_count.days,
            #                     "counter": 1,
            #                     'passenger': filter_data[0]['reservation_passenger']
            #                 }
            #                 issued_depart_summary.append(temp_dict)
            #             else:
            #                 # if data exist then we only need to update existing data
            #                 issued_depart_summary[issued_depart_index]['counter'] += 1
            #                 issued_depart_summary[issued_depart_index]['passenger'] += \
            #                 filter_data[0][
            #                     'reservation_passenger']
            #
            #         # ============= end of Issued compareed to depart date ==============
            #
            #
            #         if i['reservation_state'] == 'issued':
            #             # total += i['amount']
            #             # num_data += 1
            #
            #             # ============= Search best for every sector ==================
            #             # in this section we only compare how many reservation is actually for international destination
            #             # and how many domestic reservation
            #             # just to make is useful this report also sumarize passenger count, and reservation count
            #             returning_index = self.returning_index_sector(destination_sector_summary, {'departure':
            #             # once again as always we check for index then create and add if not exist, update if data already exist
            #             i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'sector': i['reservation_sector'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_sector_summary.append(new_dict)
            #             else:
            #                 destination_sector_summary[returning_index]['counter'] += 1
            #                 destination_sector_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_sector_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_sector_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_sector_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_sector_summary[returning_index]['infant_count'] += i['reservation_infant']
            #
            #             # ============= Search for best 50 routes ====================
            #             # in this section we want to extract top i dunno like 15 route of each sector
            #             # this code can produce more than 15, but will be trim later down the line
            #             # to make it insightful i add revenue data, and passenger count
            #             returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})
            #
            #             if returning_index == -1:
            #                 new_dict = {
            #                     'direction': i['reservation_direction'],
            #                     'departure': i['departure'],
            #                     'destination': i['destination'],
            #                     'sector': i['reservation_sector'],
            #                     'counter': 1,
            #                     'elder_count': i['reservation_elder'],
            #                     'adult_count': i['reservation_adult'],
            #                     'child_count': i['reservation_child'],
            #                     'infant_count': i['reservation_infant'],
            #                     'passenger_count': i['reservation_passenger']
            #                 }
            #                 destination_direction_summary.append(new_dict)
            #             else:
            #                 destination_direction_summary[returning_index]['counter'] += 1
            #                 destination_direction_summary[returning_index]['passenger_count'] += i['reservation_passenger']
            #                 destination_direction_summary[returning_index]['elder_count'] += i['reservation_elder']
            #                 destination_direction_summary[returning_index]['adult_count'] += i['reservation_adult']
            #                 destination_direction_summary[returning_index]['child_count'] += i['reservation_child']
            #                 destination_direction_summary[returning_index]['infant_count'] += i['reservation_infant']
            #
            #         # update current id
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         # els in here means iterate data has the same order number as previous lines
            #         # with that we only need to update ledger count
            #         # no more filtering for smaller overview
            #
            #         # in order not to double count, this if condition is needed
            #         if current_journey == i['journey_id']:
            #             if i['ledger_transaction_type'] == 3:
            #                 # get index of particular year and month
            #                 month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})
            #                 # split date to extract day
            #                 splits = i['reservation_issued_date'].split("-")
            #                 # get day
            #                 day_index = int(splits[2]) - 1
            #                 # add profit to respected array
            #                 # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                 # if HQ guy asking then we'll count everything
            #                 # if not HQ guy then we'll only count respected agent
            #                 if is_ho or agent_name_context == i['ledger_agent_name']:
            #                     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     profit_total += i['debit'] - i['credit']
            #                     profit_ho += i['debit'] - i['credit']
            #                 # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_ho += i['debit'] - i['credit']
            #                 # elif i['ledger_agent_type_name'] != 'HO':
            #                 #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 #     profit_total += i['debit'] - i['credit']
            #                 #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # ============= Summary by Domestic/International ============
                    # this summary basically make table to create international and domestic by direction
                    # like one way, return or even multi city
                    if i['reservation_sector'] == 'International':
                        # for every reservation with international destination
                        # valuation = revenue
                        sector_dictionary[0]['valuation'] += float(i['amount'])
                        # counter = # of reservation
                        sector_dictionary[0]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            # OW = one way
                            sector_dictionary[0]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            # rt = return
                            sector_dictionary[0]['return'] += 1
                        else:
                            # else considered as multicity as of today 2020-12-08
                            sector_dictionary[0]['multi_city'] += 1
                            # adding total passenger in international section
                        sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                    elif i['reservation_sector'] == 'Domestic':
                        # for every reservation with domestic destination
                        sector_dictionary[1]['valuation'] += float(i['amount'])
                        sector_dictionary[1]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[1]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[1]['return'] += 1
                        else:
                            sector_dictionary[1]['multi_city'] += 1
                        sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                    else:
                        # for any other (maybe an update on the system or something, take makes the reservation neither international or domestic)
                        sector_dictionary[2]['valuation'] += float(i['amount'])
                        sector_dictionary[2]['counter'] += 1
                        if i['reservation_direction'] == 'OW':
                            sector_dictionary[2]['one_way'] += 1
                        elif i['reservation_direction'] == 'RT':
                            sector_dictionary[2]['return'] += 1
                        else:
                            sector_dictionary[2]['multi_city'] += 1
                        sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                    # issued depart days difference
                    # ============= Issued compareed to depart date ==============
                    # filter the data, resulting all of the data with respected order number
                    filter_data = list(
                        filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'],
                               issued_values['lines']))

                    # look for the nearest departure date from issued date
                    depart_index = 0
                    if len(filter_data) > 1:
                        earliest_depart = filter_data[0]['journey_departure_date']
                        for j, dic in enumerate(filter_data):
                            if earliest_depart > dic['journey_departure_date']:
                                depart_index = j
                    # lets count
                    if filter_data[0]['reservation_issued_date_og']:
                        # conver journey date (string) to datetime
                        date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'], '%Y-%m-%d %H:%M:%S')
                        # check if reservation has issued dates
                        # this should be quite obselete since this function only calls for issued reservation
                        # but this function also written in more general function so.. there's that
                        if filter_data[0]['reservation_issued_date_og']:
                            # actually counting the day difference between each date
                            date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                            if date_count.days < 0:
                                # if for some whatever reason the date result in negative
                                # just print to logger, maybe if someday needed to be check there's the data in logger
                                _logger.error("please check {}".format(i['reservation_order_number']))
                        else:
                            date_count = 0

                        # check for index in issued depart summary
                        issued_depart_index = self.check_index(issued_depart_summary, "day", date_count.days)
                        # if no index found a.k.a -1 then we'll create and add the data
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_summary.append(temp_dict)
                        else:
                            # if data exist then we only need to update existing data
                            issued_depart_summary[issued_depart_index]['counter'] += 1
                            issued_depart_summary[issued_depart_index]['passenger'] += \
                            filter_data[0][
                                'reservation_passenger']

                    # ============= end of Issued compareed to depart date ==============


                    if i['reservation_state'] == 'issued':
                        # total += i['amount']
                        # num_data += 1

                        # ============= Search best for every sector ==================
                        # in this section we only compare how many reservation is actually for international destination
                        # and how many domestic reservation
                        # just to make is useful this report also sumarize passenger count, and reservation count
                        returning_index = self.returning_index_sector(destination_sector_summary, {'departure':
                        # once again as always we check for index then create and add if not exist, update if data already exist
                        i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
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
                        # in this section we want to extract top i dunno like 15 route of each sector
                        # this code can produce more than 15, but will be trim later down the line
                        # to make it insightful i add revenue data, and passenger count
                        returning_index = self.returning_index(destination_direction_summary, {'departure': i['departure'], 'destination': i['destination']})

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

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
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
            issued_depart_summary.sort(key=lambda x: x['counter'], reverse=True)

            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically
                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0

                    # sum data from detail
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    # shift to next month yey
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:
                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': {
                    'sector_summary': sector_dictionary,
                    'international': international_filter[:20],
                    'domestic': domestic_filter[:20],
                    'one_way': one_way_filter[:20],
                    'return': return_filter[:20],
                    'multi_city': multi_city_filter[:20],
                    'issued_depart': issued_depart_summary[:15]
                }
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_insurance(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            insurance_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate insurance_summary
            #             insurance_index = self.check_index(insurance_summary, 'product', i['carrier_name'])
            #             if insurance_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 insurance_summary.append(temp_dict)
            #             else:
            #                 insurance_summary[insurance_index]['counter'] += 1
            #                 insurance_summary[insurance_index]['amount'] += i['amount']
            #                 insurance_summary[insurance_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate insurance_summary
                    insurance_index = self.check_index(insurance_summary, 'product', i['provider_name'])
                    if insurance_index == -1:
                        temp_dict = {
                            'product': i['provider_name'], ## SEMENTARA KARENA TIDAK ADA CARRIER NAME
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        insurance_summary.append(temp_dict)
                    else:
                        insurance_summary[insurance_index]['counter'] += 1
                        insurance_summary[insurance_index]['amount'] += i['amount']
                        insurance_summary[insurance_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            insurance_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': insurance_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_swabexpress(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            swabexpress_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agennt
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate swabexpress_summary
            #             swabexpress_index = self.check_index(swabexpress_summary, 'product', i['carrier_name'])
            #             if swabexpress_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 swabexpress_summary.append(temp_dict)
            #             else:
            #                 swabexpress_summary[swabexpress_index]['counter'] += 1
            #                 swabexpress_summary[swabexpress_index]['amount'] += i['amount']
            #                 swabexpress_summary[swabexpress_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate swabexpress_summary
                    swabexpress_index = self.check_index(swabexpress_summary, 'product', i['carrier_name'])
                    if swabexpress_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        swabexpress_summary.append(temp_dict)
                    else:
                        swabexpress_summary[swabexpress_index]['counter'] += 1
                        swabexpress_summary[swabexpress_index]['amount'] += i['amount']
                        swabexpress_summary[swabexpress_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            swabexpress_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': swabexpress_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_labpintar(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            labpintar_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate labpintar_summary
            #             labpintar_index = self.check_index(labpintar_summary, 'product', i['carrier_name'])
            #             if labpintar_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 labpintar_summary.append(temp_dict)
            #             else:
            #                 labpintar_summary[labpintar_index]['counter'] += 1
            #                 labpintar_summary[labpintar_index]['amount'] += i['amount']
            #                 labpintar_summary[labpintar_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate labpintar_summary
                    labpintar_index = self.check_index(labpintar_summary, 'product', i['carrier_name'])
                    if labpintar_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        labpintar_summary.append(temp_dict)
                    else:
                        labpintar_summary[labpintar_index]['counter'] += 1
                        labpintar_summary[labpintar_index]['amount'] += i['amount']
                        labpintar_summary[labpintar_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            labpintar_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': labpintar_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_mitrakeluarga(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            mitrakeluarga_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate mitrakeluarga_summary
            #             mitrakeluarga_index = self.check_index(mitrakeluarga_summary, 'product', i['carrier_name'])
            #             if mitrakeluarga_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 mitrakeluarga_summary.append(temp_dict)
            #             else:
            #                 mitrakeluarga_summary[mitrakeluarga_index]['counter'] += 1
            #                 mitrakeluarga_summary[mitrakeluarga_index]['amount'] += i['amount']
            #                 mitrakeluarga_summary[mitrakeluarga_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate mitrakeluarga_summary
                    mitrakeluarga_index = self.check_index(mitrakeluarga_summary, 'product', i['carrier_name'])
                    if mitrakeluarga_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        mitrakeluarga_summary.append(temp_dict)
                    else:
                        mitrakeluarga_summary[mitrakeluarga_index]['counter'] += 1
                        mitrakeluarga_summary[mitrakeluarga_index]['amount'] += i['amount']
                        mitrakeluarga_summary[mitrakeluarga_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            mitrakeluarga_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': mitrakeluarga_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    def get_report_overall_sentramedika(self, data, is_ho, context={}):
        try:
            agent_name_context = None
            agent_seq_id_name = None
            is_not_corpor = True
            if data.get('agent_seq_id'):
                agent_seq_id_name = self.env['tt.agent'].search([('seq_id', '=', data['agent_seq_id'])], limit=1).name
            if context:
                agent_name_context = context['co_agent_name']
                logged_user = self.env['res.users'].browse(int(context['co_uid']))
                is_admin = logged_user.has_group('base.group_erp_manager')
                is_not_corpor = not logged_user.has_group('tt_base.group_tt_corpor_user') or is_admin
            # process datetime to GMT
            # convert string to datetime
            start_date = self.convert_to_datetime(data['start_date'])
            end_date = self.convert_to_datetime(data['end_date'])

            temp_start_date = start_date - timedelta(days=1)
            data['start_date'] = temp_start_date.strftime('%Y-%m-%d') + " 17:00:00"
            data['end_date'] += " 16:59:59"

            # first step of this function is to get reservation date, base on issued date

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': data['report_type'],
                'provider': data['provider'],
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            issued_values = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            mode = 'days'
            month = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]

            delta = end_date - start_date

            if delta.days > 35:
                # group by month
                mode = 'month'

            total = 0
            num_data = 0
            profit_total = 0
            profit_ho = 0
            profit_agent = 0
            invoice_total = 0
            profit_agent_parent = 0
            reservation_ids = []
            for i in issued_values['lines']:
                reservation_ids.append((i['reservation_id'], i['provider_type_name']))

            temp_dict = {
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'type': 'invoice',
                'provider': data['provider'],
                'reservation': reservation_ids,
                'ho_seq_id': data.get('ho_seq_id') and data['ho_seq_id'] or '',
                'agent_seq_id': data.get('agent_seq_id') and data['agent_seq_id'] or '',
                'customer_parent_seq_id': data.get('customer_parent_seq_id') and data['customer_parent_seq_id'] or '',
                'agent_type': data['agent_type_seq_id'],
                'addons': 'none'
            }
            invoice = self.env['report.tt_report_selling.report_selling']._get_reports(temp_dict)

            # proceed invoice with the assumption of create date = issued date
            summary_issued = []
            sentramedika_summary = []

            # declare current id
            current_id = {}
            ledger_id_list = {}
            reservation_id_list = {}  # dict of list provider agar id kembar tidak tertumpuk

            # for i in issued_values['lines']:
            #     if not current_id.get(i['provider_type_name']):
            #         current_id[i['provider_type_name']] = []
            #     if i['reservation_id'] not in current_id[i['provider_type_name']]:
            #         try:
            #             profit_total += i['channel_profit']
            #             profit_agent += i['channel_profit']
            #
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #
            #             if month_index == -1:
            #                 # if year and month with details doens't exist yet
            #                 # create a temp dict
            #                 temp_dict = {
            #                     'year': i['issued_year'],
            #                     'month_index': int(i['issued_month']),
            #                     'month': month[int(i['issued_month']) - 1],
            #                     'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month'])),
            #                     'reservation': 0,
            #                     'revenue': 0,
            #                     'profit': 0
            #                 }
            #
            #                 # add the first data
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 temp_dict['detail'][day_index]['reservation'] += 1
            #                 temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     temp_dict['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #                 # add to the big list
            #                 summary_issued.append(temp_dict)
            #             else:
            #                 # if "summary" already exist
            #                 # update existing summary
            #                 splits = i['reservation_issued_date'].split("-")
            #                 day_index = int(splits[2]) - 1
            #                 summary_issued[month_index]['detail'][day_index]['reservation'] += 1
            #                 summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
            #                 total += i['amount'] + i['channel_profit']
            #                 num_data += 1
            #                 if i['ledger_transaction_type'] == 3:
            #                     # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #                     # if HQ guy asking then we'll count everything
            #                     # if not HQ guy then we'll only count respected agent
            #                     if is_ho or agent_name_context == i['ledger_agent_name']:
            #                         summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                         profit_total += i['debit'] - i['credit']
            #                         profit_ho += i['debit'] - i['credit']
            #                     # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_ho += i['debit'] - i['credit']
            #                     # elif i['ledger_agent_type_name'] != 'HO':
            #                     #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                     #     profit_total += i['debit'] - i['credit']
            #                     #     profit_agent += i['debit'] - i['credit']
            #
            #             # populate sentramedika_summary
            #             sentramedika_index = self.check_index(sentramedika_summary, 'product', i['carrier_name'])
            #             if sentramedika_index == -1:
            #                 temp_dict = {
            #                     'product': i['carrier_name'],
            #                     'counter': 1,
            #                     'passenger_count': i['reservation_passenger'],
            #                     'amount': i['amount']
            #                 }
            #                 sentramedika_summary.append(temp_dict)
            #             else:
            #                 sentramedika_summary[sentramedika_index]['counter'] += 1
            #                 sentramedika_summary[sentramedika_index]['amount'] += i['amount']
            #                 sentramedika_summary[sentramedika_index]['passenger_count'] += i['reservation_passenger']
            #         except:
            #             pass
            #         current_id[i['provider_type_name']].append(i['reservation_id'])
            #     else:
            #         if i['ledger_transaction_type'] == 3:
            #             month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],
            #                                                                  'month': month[int(i['issued_month']) - 1]})
            #             splits = i['reservation_issued_date'].split("-")
            #             day_index = int(splits[2]) - 1
            #             # check if commission (also known as profit) is belong to HQ or not, and if the user requesting is part of HQ or not
            #             # if HQ guy asking then we'll count everything
            #             # if not HQ guy then we'll only count respected agent
            #             if is_ho or agent_name_context == i['ledger_agent_name']:
            #                 summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #                 profit_total += i['debit'] - i['credit']
            #                 profit_ho += i['debit'] - i['credit']
            #             # if i['ledger_agent_type_name'] == 'HO' and is_ho == True:
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_ho += i['debit'] - i['credit']
            #             # elif i['ledger_agent_type_name'] != 'HO':
            #             #     summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
            #             #     profit_total += i['debit'] - i['credit']
            #             #     profit_agent += i['debit'] - i['credit']
            for idx,i in enumerate(issued_values['lines']):
                # if for some reason current reservation_id is the same as current_id (previous iteration id)
                # then continue
                if not reservation_id_list.get(i['provider_type_name']):
                    reservation_id_list[i['provider_type_name']] = []
                if not ledger_id_list.get(i['provider_type_name']):
                    ledger_id_list[i['provider_type_name']] = []

                if i['reservation_id'] not in reservation_id_list[i['provider_type_name']]:
                    if not i['is_upsell_in_service_charge'] and is_not_corpor:
                        profit_total += i['channel_profit']
                        profit_agent += i['channel_profit']
                    month_index = self.check_date_index(summary_issued, {'year': i['issued_year'], 'month': month[int(i['issued_month']) - 1]})

                    if month_index == -1:
                        # data is not exist
                        # create data
                        temp_dict = {
                            'year': i['issued_year'],
                            'month_index': int(i['issued_month']),
                            'month': month[int(i['issued_month']) - 1],
                            'detail': self.add_issued_month_detail(int(i['issued_year']), int(i['issued_month']))
                        }
                        # add the first data
                        # seperate string date to extract day date
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1

                        # assign the first value to temp dict
                        temp_dict['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            temp_dict['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                        else:
                            temp_dict['detail'][day_index]['revenue'] += i['amount']

                        # add to global variable
                        if not i['is_upsell_in_service_charge']:
                            total += i['amount'] + i['channel_profit']
                        else:
                            total += i['amount']
                        num_data += 1
                        # add to final list
                        summary_issued.append(temp_dict)
                    else:
                        # data exist

                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        summary_issued[month_index]['detail'][day_index]['reservation'] += 1
                        if not i['is_upsell_in_service_charge']:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount'] + i['channel_profit']
                            total += i['amount'] + i['channel_profit']
                        else:
                            summary_issued[month_index]['detail'][day_index]['revenue'] += i['amount']
                            total += i['amount']
                        num_data += 1
                    reservation_id_list[i['provider_type_name']].append(i['reservation_id'])

                    # populate sentramedika_summary
                    sentramedika_index = self.check_index(sentramedika_summary, 'product', i['carrier_name'])
                    if sentramedika_index == -1:
                        temp_dict = {
                            'product': i['carrier_name'],
                            'counter': 1,
                            'passenger_count': i['reservation_passenger'],
                            'amount': i['amount']
                        }
                        sentramedika_summary.append(temp_dict)
                    else:
                        sentramedika_summary[sentramedika_index]['counter'] += 1
                        sentramedika_summary[sentramedika_index]['amount'] += i['amount']
                        sentramedika_summary[sentramedika_index]['passenger_count'] += i['reservation_passenger']

                if i['ledger_id'] not in ledger_id_list[i['provider_type_name']]:
                    # proceed profit first graph
                    if i['ledger_transaction_type'] == 3:
                        month_index = self.check_date_index(summary_issued, {'year': i['issued_year'],'month': month[int(i['issued_month']) - 1]})
                        splits = i['reservation_issued_date'].split("-")
                        day_index = int(splits[2]) - 1
                        if is_not_corpor:
                            if is_ho and i['ledger_agent_type_name'] == 'HO':
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_ho += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO' and i['agent_name'] == i['ledger_agent_name']:  # punya agent
                                summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                profit_total += i['debit'] - i['credit']
                                profit_agent += i['debit'] - i['credit']
                            elif i['ledger_agent_type_name'] != 'HO':  # BUAT PARENT AGENT
                                if is_ho:
                                    summary_issued[month_index]['detail'][day_index]['profit'] += i['debit'] - i['credit']
                                    profit_total += i['debit'] - i['credit']
                                profit_agent_parent += i['debit'] - i['credit']
                    ledger_id_list[i['provider_type_name']].append(i['ledger_id'])
            # for every section in summary
            for i in summary_issued:
                # for every detail in section
                for j in i['detail']:
                    # built appropriate date
                    if i['month_index'] < 10 and j['day'] < 10:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                    elif i['month_index'] < 10 and j['day'] > 9:
                        today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                    elif i['month_index'] > 9 and j['day'] < 10:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                    else:
                        today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                    # filter invoice data
                    filtered_data = list(filter(lambda x: x['create_date'] == today, invoice['lines']))

                    # add to summary
                    j['invoice'] += len(filtered_data)

                    # count average
                    j['average'] = float(j['revenue']) / float(j['reservation']) if j['reservation'] > 0 else 0

                    # adding invoice
                    invoice_total += len(filtered_data)

            # sort summary_by_date month in the correct order
            summary_issued.sort(key=lambda x: (x['year'], x['month_index']))
            sentramedika_summary.sort(key=lambda x: x['amount'])

            # first graph data
            main_data = {}
            average_data = {}
            revenue_data = {}
            profit_data = {}

            # shape the data for return
            # a little reminder month and days mode determine by how many days in between requested report
            # more than 35 days, automatically group by month
            # less than 35 days, we'll return as is (divided by date)
            if mode == 'month':
                # if so happens to be in month mode, then we'll sum every data by month
                # because if you follow the program, you'll know that summary_issued divide the data into
                # year, month, with date details (date detail is list)
                # we have to sum the date detail basically

                # sum by month
                try:
                    # first counter is trying to find what month user requested date are
                    # why it has - 1 because if you look at constant dependencies
                    # index and month value will result in difference of 1 (since list index starts in 0 yada yada yada)
                    first_counter = summary_issued[0]['month_index'] - 1
                except:
                    # if for whatever reason, above method doesn't work
                    # then, we'll do the weird(?) way
                    # by extracting from date
                    splits = data['start_date'].split("-")
                    month = splits[1]
                    first_counter = int(month) - 1

                # with that done, we'll now process the data
                for i in summary_issued:
                    # fill skipped month(s)
                    # check if current month (year) with start
                    if i['month_index'] - 1 < first_counter:
                        # this is the condition for new year, where
                        # counter month > than the earlier month of the year
                        # we'll just gonna fill the gap
                        while first_counter < 12:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1
                        # resert counter after 12
                        if first_counter == 12:
                            first_counter = 0
                    if i['month_index'] - 1 > first_counter:
                        # this to catch up current month to present day ish
                        # or present month for that matter
                        while first_counter < i['month_index'] - 1:
                            main_data[month[first_counter]] = 0
                            average_data[month[first_counter]] = 0
                            revenue_data[month[first_counter]] = 0
                            profit_data[month[first_counter]] = 0
                            first_counter += 1

                    # so after first counter, which doen't make any sense since
                    # first counter was use to keep up...
                    # after first counter catch up present month/day
                    # we're gonna count the data
                    # declare variable with respected month
                    main_data[i['month']] = 0
                    average_data[i['month']] = 0
                    revenue_data[i['month']] = 0
                    profit_data[i['month']] = 0
                    for j in i['detail']:
                        # for detail in months
                        main_data[i['month']] += j['invoice']
                        average_data[i['month']] += j['average']
                        revenue_data[i['month']] += j['revenue']
                        if is_not_corpor:
                            profit_data[i['month']] += j['profit']
                    first_counter += 1

            else:
                # seperate by date
                for i in summary_issued:
                    for j in i['detail']:

                        # built appropriate date
                        if i['month_index'] < 10 and j['day'] < 10:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-0" + str(j['day'])
                        elif i['month_index'] < 10 and j['day'] > 9:
                            today = str(i['year']) + "-0" + str(i['month_index']) + "-" + str(j['day'])
                        elif i['month_index'] > 9 and j['day'] < 10:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-0" + str(j['day'])
                        else:
                            today = str(i['year']) + "-" + str(i['month_index']) + "-" + str(j['day'])

                        # lets cut the data that is not needed
                        if today >= data['start_date'] and today <= data['end_date']:
                            main_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j['invoice']
                            average_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['average']
                            revenue_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(
                                i['year'])] = j['revenue']
                            if is_not_corpor:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = j[
                                    'profit']
                            else:
                                profit_data[str(j['day']) + "-" + str(i['month_index']) + "-" + str(i['year'])] = 0

            # build to return data
            to_return = {
                'first_graph': {
                    'label': list(main_data.keys()),
                    'data': list(main_data.values()),
                    'data2': list(revenue_data.values()),
                    'data3': list(average_data.values()),
                    'data4': list(profit_data.values())
                },
                'total_rupiah': total,
                'average_rupiah': float(total) / float(invoice_total) if invoice_total > 0 else 0,
                'profit_total': profit_total,
                'profit_ho': profit_ho,
                'profit_agent': profit_agent,
                'profit_agent_parent': profit_agent_parent,
                'first_overview': sentramedika_summary
            }

            # update dependencies
            data['mode'] = mode

            # get book issued ratio
            book_issued = self.get_book_issued_ratio(data)

            # adding book_issued ratio graph
            to_return.update(book_issued)

            # We will populate third graph with agent
            # fourth and fifth with customer and customer parent respectively

            # get by chanel
            chanel_data = self.get_report_group_by_chanel(data, issued_values['lines'], is_ho, context)

            # adding chanel_data graph
            to_return.update(chanel_data)

            # if agent then we will populate with customer data (aka booker, and customer parent)
            customer_data = self.get_report_group_by_customer(data, issued_values['lines'], is_ho, context)

            # add customer to data
            to_return.update(customer_data)

            return to_return
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise e

    ######################################################################
    # this section contains of either old function or prototype
    ######################################################################
    # most of functions written under this line is not being use atm.
    # but can be use as reference if needed.

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
                            'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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
                if not i['provider_type_name']:
                    i['provider_type_name'] = "Undefined"
                carrier_index = self.check_index(carrier_name_summary, 'carrier_name', i['provider_type_name'])
                if carrier_index == -1:
                    temp_dict = {
                        'carrier_name': i['provider_type_name'],
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
                        'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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
                        'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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
                        'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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
            carrier_index = self.check_index(carrier_name_summary, 'carrier_name', i['provider_type_name'])
            if carrier_index == -1:
                temp_dict = {
                    'carrier_name': i['provider_type_name'],
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
                        'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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
            provider_index = self.check_index(provider_summary, 'provider', i['provider_type_name'])
            if provider_index == -1:
                temp_dict = {
                    'provider': i['provider_type_name'],
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
                        'detail': self.add_month_detail(int(i['booked_year']), int(i['booked_month']))
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

                provider_index = self.check_index(provider_summary, 'provider', i['provider_type_name'])
                if provider_index == -1:
                    temp_dict = {
                        'provider': i['provider_type_name'],
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
