from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class ReportSellingXls(models.TransientModel):
    _inherit = 'tt.report.selling.wizard'

    def add_month_detail(self):
        temp_list = []
        for i in range(1, 32):
            temp_dict = {
                'day': i,
                'issued_counter': 0,
                'booked_counter': 0
            }
            temp_list.append(temp_dict)

        return temp_list

    def _print_report_excel(self, data):
        res = ''
        if data['form']['provider_type'] == 'all':
            res = self._print_report_excel_all(data)
        if data['form']['provider_type'] == 'airline':
            res = self._print_report_excel_airline(data)
        if data['form']['provider_type'] == 'train':
            res = self._print_report_excel_train(data)
        if data['form']['provider_type'] == 'hotel':
            res = self._print_report_excel_hotel(data)
        if data['form']['provider_type'] == 'activity':
            res = self._print_report_excel_activity(data)
        if data['form']['provider_type'] == 'tour':
            res = self._print_report_excel_tour(data)
        if data['form']['provider_type'] == 'visa':
            res = self._print_report_excel_visa(data)
        if data['form']['provider_type'] == 'offline':
            res = self._print_report_excel_offline(data)
        if data['form']['provider_type'] == 'event':
            res = self._print_report_excel_event(data)
        if data['form']['provider_type'] == 'ppob':
            res = self._print_report_excel_ppob(data)
        if data['form']['provider_type'] == 'periksain':
            res = self._print_report_excel_periksain(data)
        if data['form']['provider_type'] == 'phc':
            res = self._print_report_excel_phc(data)
        if data['form']['provider_type'] == 'medical':
            res = self._print_report_excel_medical(data)
        if data['form']['provider_type'] == 'bus':
            res = self._print_report_excel_bus(data)
        if data['form']['provider_type'] == 'insurance':
            res = self._print_report_excel_insurance(data)
        if data['form']['provider_type'] == 'swabexpress':
            res = self._print_report_excel_swabexpress(data)
        if data['form']['provider_type'] == 'labpintar':
            res = self._print_report_excel_labpintar(data)
        if data['form']['provider_type'] == 'mitrakeluarga':
            res = self._print_report_excel_mitrakeluarga(data)
        return res

    def _print_report_excel_all(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        # ================ Initiate ======================
        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        result = []
        current_order_number = ''
        for i in values['lines']:
            if current_order_number != i['reservation_order_number']:
                current_order_number = i['reservation_order_number']
                #count for date
                try:
                    month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'], 'month': month[int(i['booked_month'])-1]})
                    if month_index == -1:
                        temp_dict = {
                            'year': i['booked_year'],
                            'month': month[int(i['booked_month'])-1],
                            'detail': self.add_month_detail()
                        }
                        #seperate book date
                        try:
                            splits = i['reservation_booked_date'].split("-")
                            day_index = int(splits[2]) - 1
                            temp_dict['detail'][day_index]['booked_counter'] += 1
                        except:
                            pass
                        if i['reservation_state'] == 'issued':
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
                        if i['reservation_state'] == 'issued':
                            try:
                                splits = i['reservation_issued_date'].split("-")
                                day_index = int(splits[2]) - 1
                                summary_by_date[month_index]['detail'][day_index]['issued_counter'] += 1
                            except:
                                pass
                except:
                    pass
                provider_index = self.check_index(result, "provider", i['provider_type_name'])
                if provider_index == -1:
                    temp_dict = {
                        'provider': i['provider_type_name'],
                        'counter': 1,
                        i['reservation_state']: 1
                    }
                    result.append(temp_dict)
                else:
                    result[provider_index]['counter'] += 1
                    try:
                        result[provider_index][i['reservation_state']] += 1
                    except:
                        result[provider_index][i['reservation_state']] = 1

        row_data = 8
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'provider_type', style.table_head_center)
        sheet.write(row_data, 2, 'number of transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Booked', style.table_head_center)
        sheet.write(row_data, 4, 'Issued', style.table_head_center)
        sheet.write(row_data, 5, 'Expired', style.table_head_center)
        sheet.write(row_data, 6, 'Failed Book', style.table_head_center)
        sheet.write(row_data, 7, 'Failed Issued', style.table_head_center)
        sheet.write(row_data, 8, 'Other (SUM)', style.table_head_center)
        counter = 0
        for i in result:
            temp_dict = i
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            sty_amount = style.table_data_amount
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even
                sty_amount = style.table_data_amount_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['provider'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            try:
                sheet.write(row_data, 3, i['booked'], sty_table_data)
            except:
                sheet.write(row_data, 3, '', sty_table_data)

            try:
                sheet.write(row_data, 4, i['issued'], sty_table_data)
            except:
                sheet.write(row_data, 4, '', sty_table_data)

            try:
                sheet.write(row_data, 5, i['cancel2'], sty_table_data)
            except:
                sheet.write(row_data, 5, '', sty_table_data)

            try:
                sheet.write(row_data, 6, i['fail_booked'], sty_table_data)
            except:
                sheet.write(row_data, 6, '', sty_table_data)

            try:
                sheet.write(row_data, 7, i['fail_issued'], sty_table_data)
            except:
                sheet.write(row_data, 7, '', sty_table_data)

            temp_dict.pop('provider')
            temp_dict.pop('counter')
            try:
                temp_dict.pop('booked')
            except:
                pass
            try:
                temp_dict.pop('issued')
            except:
                pass
            try:
                temp_dict.pop('cancel2')
            except:
                pass
            try:
                temp_dict.pop('fail_booked')
            except:
                pass
            try:
                temp_dict.pop('fail_issued')
            except:
                pass
            other_counter = 0
            for j in temp_dict:
                other_counter += int(i[j])

            sheet.write(row_data, 8, other_counter, sty_table_data)

        og_row_data = row_data
        side_counter = 0
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4
        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales All Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_airline(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        # ============== INITIATE RESULT DICT ==================
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
                current_order_number = i['reservation_order_number']
                if not i['destination']:
                    no_destination += " {}".format(i['reservation_order_number'])
                if not i['departure']:
                    no_departure += " {}".format(i['reservation_order_number'])

                # ============= Issued compareed to depart date ==============
                filter_data = list(filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], values['lines']))

                depart_index = 0
                if len(filter_data) > 1:
                    earliest_depart = filter_data[0]['journey_departure_date']
                    for j, dic in enumerate(filter_data):
                        if earliest_depart > dic['journey_departure_date']:
                            depart_index = j
                # lets count
                if filter_data[0]['reservation_issued_date_og']:
                    date_time_convert = datetime.strptime(filter_data[depart_index]['journey_departure_date'], '%Y-%m-%d %H:%M:%S')
                    if filter_data[0]['reservation_issued_date_og']:
                        date_count = date_time_convert - filter_data[0]['reservation_issued_date_og']
                        if date_count.days < 0:
                            _logger.error("please check {}".format(i['reservation_order_number']))
                    else:
                        date_count = 0

                    if filter_data[0]['reservation_sector'] == 'International':
                        issued_depart_index = self.check_index(issued_depart_international_summary, "day", date_count.days)
                        if issued_depart_index == -1:
                            temp_dict = {
                                "day": date_count.days,
                                "counter": 1,
                                'passenger': filter_data[0]['reservation_passenger']
                            }
                            issued_depart_international_summary.append(temp_dict)
                        else:
                            issued_depart_international_summary[issued_depart_index]['counter'] += 1
                            issued_depart_international_summary[issued_depart_index]['passenger'] += filter_data[0]['reservation_passenger']
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
                    month_index = self.check_date_index(summary_by_date, {'year': i['booked_year'], 'month': month[int(i['booked_month'])-1]})
                    if month_index == -1:
                        temp_dict = {
                            'year': i['booked_year'],
                            'month': month[int(i['booked_month'])-1],
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

                    #add counter for every provider
                    if i['reservation_sector'] == 'International':
                        temp_dict['international_counter'] += 1
                        temp_dict['international_valuation'] += i['amount']
                        temp_dict['total_transaction'] += 1
                    else:
                        temp_dict['domestic_counter'] += 1
                        temp_dict['domestic_valuation'] += i['amount']
                        temp_dict['total_transaction'] += 1

                    #to check issued fail ratio
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

                    destination_index = self.returning_index(carrier_name_summary[carrier_index]['flight'], {'departure': i['departure'], 'destination': i['destination']})
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
                        carrier_name_summary[carrier_index]['flight'][destination_index]['passenger_count'] += i['reservation_passenger']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['elder_count'] += i['reservation_elder']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['adult_count'] += i['reservation_adult']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['child_count'] += i['reservation_child']
                        carrier_name_summary[carrier_index]['flight'][destination_index]['infant_count'] += i['reservation_infant']

                # ============= Summary by Domestic/International ============
                if i['reservation_sector'] == 'International':
                    sector_dictionary[0]['valuation'] += float(i['amount'])
                    sector_dictionary[0]['counter'] += 1
                    sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                elif i['reservation_sector'] == 'Domestic':
                    sector_dictionary[1]['valuation'] += float(i['amount'])
                    sector_dictionary[1]['counter'] += 1
                    sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                else:
                    sector_dictionary[2]['valuation'] += float(i['amount'])
                    sector_dictionary[2]['counter'] += 1
                    sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                # ============= Summary by flight Type (OW, R, MC) ===========
                if i['reservation_direction'] == 'OW':
                    direction_dictionary[0]['valuation'] += float(i['amount'])
                    direction_dictionary[0]['counter'] += 1
                    direction_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
                elif i['reservation_direction'] == 'RT':
                    direction_dictionary[1]['valuation'] += float(i['amount'])
                    direction_dictionary[1]['counter'] += 1
                    direction_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
                else:
                    direction_dictionary[2]['valuation'] += float(i['amount'])
                    direction_dictionary[2]['counter'] += 1
                    direction_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

                # ============= Search best for every sector ==================
                returning_index = self.returning_index_sector(destination_sector_summary,{'departure': i['departure'], 'destination': i['destination'], 'sector': i['reservation_sector']})
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
                returning_index = self.returning_index(destination_direction_summary,{'departure': i['departure'], 'destination': i['destination']})
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

        sheet.write(5, 8, no_departure, style.table_data)
        sheet.write(6, 8, no_destination, style.table_data)
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

        # ============ FIRST TABLE ======================
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Sector', style.table_head_center)
        sheet.write('C9', '# of sales', style.table_head_center)
        sheet.write('D9', 'Passenger Count', style.table_head_center)

        sheet.write('A10', '1', style.table_data_even)
        sheet.write('B10', sector_dictionary[0]['sector'], style.table_data_even)
        sheet.write('C10', sector_dictionary[0]['counter'], style.table_data_even)
        sheet.write('D10', sector_dictionary[0]['passenger_count'], style.table_data_even)

        sheet.write('A11', '2', style.table_data)
        sheet.write('B11', sector_dictionary[1]['sector'], style.table_data)
        sheet.write('C11', sector_dictionary[1]['counter'], style.table_data)
        sheet.write('D11', sector_dictionary[1]['passenger_count'], style.table_data)

        sheet.write('A12', '3', style.table_data_even)
        sheet.write('B12', sector_dictionary[2]['sector'], style.table_data_even)
        sheet.write('C12', sector_dictionary[2]['counter'], style.table_data_even)
        sheet.write('D12', sector_dictionary[2]['passenger_count'], style.table_data_even)

        row_data = 15
        # ============ SECOND TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'International', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0,50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, international_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 1, international_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, international_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, international_filter[i]['counter'], sty_table_data)
                # sheet.write(row_data, 4, "{}, {}, {}, {}".format(
                #     international_filter[i]['elder_count'],
                #     international_filter[i]['adult_count'],
                #     international_filter[i]['child_count'],
                #     international_filter[i]['infant_count']
                # ), sty_table_data)
                sheet.write(row_data, 4, international_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ THIRD TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Domestic', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0,50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, domestic_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, domestic_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, domestic_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, domestic_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FORTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'One Way', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0,50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, one_way_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, one_way_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, one_way_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, one_way_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FUNF TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Return', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0,50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, return_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, return_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, return_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, return_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ SIXTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Multi City', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0,50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, multi_city_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, multi_city_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, multi_city_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, multi_city_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        # ============ MANY MANY TABLE ======================
        row_data = 8
        sheet.write(row_data, 6, 'Provider name', style.table_head_center)
        sheet.write(row_data, 7, 'International', style.table_head_center)
        sheet.write(row_data, 8, 'Domestic', style.table_head_center)
        sheet.write(row_data, 9, 'Issued', style.table_head_center)
        sheet.write(row_data, 10, 'Expire', style.table_head_center)
        sheet.write(row_data, 11, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 12, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 13, 'Other', style.table_head_center)
        sheet.write(row_data, 14, '# of Passengers', style.table_head_center)

        side_row_data = 6
        carrier_name_summary.sort(key=lambda x: x['total_transaction'], reverse=True)
        for i in carrier_name_summary:
            row_data += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, i['carrier_name'], sty_table_data)
            sheet.write(row_data, 7, i['international_counter'], sty_table_data)
            sheet.write(row_data, 8, i['domestic_counter'], sty_table_data)
            sheet.write(row_data, 9, i['issued'], sty_table_data)
            sheet.write(row_data, 10, i['expired'], sty_table_data)
            sheet.write(row_data, 11, i['fail_booked'], sty_table_data)
            sheet.write(row_data, 12, i['fail_issued'], sty_table_data)
            sheet.write(row_data, 13, i['other'], sty_table_data)
            sheet.write(row_data, 14, i['passenger_count'], sty_table_data)

            side_row_data += 2
            sheet.merge_range(side_row_data, 16, side_row_data, 19, i['carrier_name'], style.table_head_center)
            sheet.merge_range(side_row_data + 1, 16, side_row_data + 1, 18, 'International', style.table_data)
            sheet.write(side_row_data + 1, 19, i['international_counter'], style.table_data)
            sheet.merge_range(side_row_data + 2, 16, side_row_data + 2, 18, 'Domestic', style.table_data)
            sheet.write(side_row_data + 2, 19, i['domestic_counter'], style.table_data)
            side_row_data += 3
            sheet.write(side_row_data, 16, 'Origin', style.table_head_center)
            sheet.write(side_row_data, 17, 'Destination', style.table_head_center)
            sheet.write(side_row_data, 18, '# of Transaction', style.table_head_center)
            sheet.write(side_row_data, 19, '# of Passenger', style.table_head_center)

            i['flight'].sort(key=lambda x: x['counter'], reverse=True)

            for j in range(0,25):
                try:
                    side_row_data += 1
                    sty_table_data = style.table_data
                    if side_row_data % 2 == 0:
                        sty_table_data = style.table_data_even

                    sheet.write(side_row_data, 16, i['flight'][j]['departure'], sty_table_data)
                    sheet.write(side_row_data, 17, i['flight'][j]['destination'], sty_table_data)
                    sheet.write(side_row_data, 18, i['flight'][j]['counter'], sty_table_data)
                    sheet.write(side_row_data, 19, i['flight'][j]['passenger_count'], sty_table_data)
                except:
                    break;

        now_row_data = row_data
        row_data += 3
        sheet.merge_range(row_data -1, 6, row_data-1, 9, 'Inernational', style.table_head_center)
        sheet.write(row_data, 6, 'No', style.table_head_center)
        sheet.write(row_data, 7, '# of Days, issued - depart', style.table_head_center)
        sheet.write(row_data, 8, '# of transaction', style.table_head_center)
        sheet.write(row_data, 9, 'passenger', style.table_head_center)
        counter = 0
        for i in issued_depart_international_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, counter, sty_table_data)
            sheet.write(row_data, 7, i['day'], sty_table_data)
            sheet.write(row_data, 8, i['counter'], sty_table_data)
            sheet.write(row_data, 9, i['passenger'], sty_table_data)

        row_data = now_row_data + 3
        sheet.merge_range(row_data - 1, 11, row_data - 1, 14, 'Domestic', style.table_head_center)
        sheet.write(row_data, 11, 'No', style.table_head_center)
        sheet.write(row_data, 12, '# of Days, issued - depart', style.table_head_center)
        sheet.write(row_data, 13, '# of transaction', style.table_head_center)
        sheet.write(row_data, 14, 'passenger', style.table_head_center)
        counter = 0
        for i in issued_depart_domestic_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 11, counter, sty_table_data)
            sheet.write(row_data, 12, i['day'], sty_table_data)
            sheet.write(row_data, 13, i['counter'], sty_table_data)
            sheet.write(row_data, 14, i['passenger'], sty_table_data)

        og_row_data = 8
        side_counter = 21
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Airline Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_train(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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
                    carrier_name_summary[carrier_index]['flight'][destination_index]['elder_count'] += i['reservation_elder']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['adult_count'] += i['reservation_adult']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['child_count'] += i['reservation_child']
                    carrier_name_summary[carrier_index]['flight'][destination_index]['infant_count'] += i['reservation_infant']

            # ============= International or Domestic route ==============
            if i['reservation_sector'] == 'International':
                sector_dictionary[0]['valuation'] += float(i['amount'])
                sector_dictionary[0]['counter'] += 1
                sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            elif i['reservation_sector'] == 'Domestic':
                sector_dictionary[1]['valuation'] += float(i['amount'])
                sector_dictionary[1]['counter'] += 1
                sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            else:
                sector_dictionary[2]['valuation'] += float(i['amount'])
                sector_dictionary[2]['counter'] += 1
                sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

            # ============= Type of direction ============================
            if i['reservation_direction'] == 'OW':
                direction_dictionary[0]['valuation'] += float(i['amount'])
                direction_dictionary[0]['counter'] += 1
                direction_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            elif i['reservation_direction'] == 'RT':
                direction_dictionary[1]['valuation'] += float(i['amount'])
                direction_dictionary[1]['counter'] += 1
                direction_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            else:
                direction_dictionary[2]['valuation'] += float(i['amount'])
                direction_dictionary[2]['counter'] += 1
                direction_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

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

        # ============ FIRST TABLE ======================
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Sector', style.table_head_center)
        sheet.write('C9', '# of sales', style.table_head_center)
        sheet.write('D9', 'Passenger Count', style.table_head_center)

        sheet.write('A10', '1', style.table_data_even)
        sheet.write('B10', sector_dictionary[0]['sector'], style.table_data_even)
        sheet.write('C10', sector_dictionary[0]['counter'], style.table_data_even)
        sheet.write('D10', sector_dictionary[0]['passenger_count'], style.table_data_even)

        sheet.write('A11', '2', style.table_data)
        sheet.write('B11', sector_dictionary[1]['sector'], style.table_data)
        sheet.write('C11', sector_dictionary[1]['counter'], style.table_data)
        sheet.write('D11', sector_dictionary[1]['passenger_count'], style.table_data)

        sheet.write('A12', '3', style.table_data_even)
        sheet.write('B12', sector_dictionary[2]['sector'], style.table_data_even)
        sheet.write('C12', sector_dictionary[2]['counter'], style.table_data_even)
        sheet.write('D12', sector_dictionary[2]['passenger_count'], style.table_data_even)

        row_data = 15
        # ============ SECOND TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'International', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, international_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, international_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, international_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, international_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ THIRD TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Domestic', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, domestic_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, domestic_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, domestic_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, domestic_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FORTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'One Way', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, one_way_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, one_way_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, one_way_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, one_way_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FUNF TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Return', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, return_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, return_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, return_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, return_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ SIXTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Multi City', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, multi_city_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, multi_city_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, multi_city_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, multi_city_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        # ============ MANY MANY TABLE ======================
        row_data = 8
        sheet.write(row_data, 6, 'Provider name', style.table_head_center)
        sheet.write(row_data, 7, 'International', style.table_head_center)
        sheet.write(row_data, 8, 'Domestic', style.table_head_center)
        sheet.write(row_data, 9, 'Issued', style.table_head_center)
        sheet.write(row_data, 10, 'Expire', style.table_head_center)
        sheet.write(row_data, 11, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 12, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 13, 'Other', style.table_head_center)
        sheet.write(row_data, 14, '# of Passengers', style.table_head_center)

        side_row_data = 6
        carrier_name_summary.sort(key=lambda x: x['total_transaction'], reverse=True)
        for i in carrier_name_summary:
            row_data += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, i['carrier_name'], sty_table_data)
            sheet.write(row_data, 7, i['international_counter'], sty_table_data)
            sheet.write(row_data, 8, i['domestic_counter'], sty_table_data)
            sheet.write(row_data, 9, i['issued'], sty_table_data)
            sheet.write(row_data, 10, i['expired'], sty_table_data)
            sheet.write(row_data, 11, i['fail_booked'], sty_table_data)
            sheet.write(row_data, 12, i['fail_issued'], sty_table_data)
            sheet.write(row_data, 13, i['other'], sty_table_data)
            sheet.write(row_data, 14, i['passenger_count'], sty_table_data)

            side_row_data += 2
            sheet.merge_range(side_row_data, 16, side_row_data, 19, i['carrier_name'], style.table_head_center)
            sheet.merge_range(side_row_data + 1, 16, side_row_data + 1, 18, 'International', style.table_data)
            sheet.write(side_row_data + 1, 19, i['international_counter'], style.table_data)
            sheet.merge_range(side_row_data + 2, 16, side_row_data + 2, 18, 'Domestic', style.table_data)
            sheet.write(side_row_data + 2, 19, i['domestic_counter'], style.table_data)
            side_row_data += 3
            sheet.write(side_row_data, 16, 'Origin', style.table_head_center)
            sheet.write(side_row_data, 17, 'Destination', style.table_head_center)
            sheet.write(side_row_data, 18, '# of Transaction', style.table_head_center)
            sheet.write(side_row_data, 19, '# of Passenger', style.table_head_center)

            i['flight'].sort(key=lambda x: x['counter'], reverse=True)

            for j in range(0, 25):
                try:
                    side_row_data += 1
                    sty_table_data = style.table_data
                    if side_row_data % 2 == 0:
                        sty_table_data = style.table_data_even

                    sheet.write(side_row_data, 16, i['flight'][j]['departure'], sty_table_data)
                    sheet.write(side_row_data, 17, i['flight'][j]['destination'], sty_table_data)
                    sheet.write(side_row_data, 18, i['flight'][j]['counter'], sty_table_data)
                    sheet.write(side_row_data, 19, i['flight'][j]['passenger_count'], sty_table_data)
                except:
                    break;

        row_data += 2
        sheet.write(row_data, 6, 'No', style.table_head_center)
        sheet.write(row_data, 7, '# of Days, issued - depart', style.table_head_center)
        sheet.write(row_data, 8, 'count', style.table_head_center)
        counter = 0
        for i in issued_depart_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, counter, sty_table_data)
            sheet.write(row_data, 7, i['day'], sty_table_data)
            sheet.write(row_data, 8, i['counter'], sty_table_data)

        og_row_data = 8
        side_counter = 21
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Train Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_hotel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            #hotel count
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

            #provider summary
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

        #draw hotel summary
        row_data = 8
        counter = 0
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Hotel Name', style.table_head_center)
        sheet.write(row_data, 2, 'Total Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Issued', style.table_head_center)
        sheet.write(row_data, 4, 'Expire', style.table_head_center)
        sheet.write(row_data, 5, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 6, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 7, 'Other', style.table_head_center)
        # sheet.write(row_data, 8, '# of Passenger', style.table_head_center)
        for i in hotel_summary:
            row_data += 1
            counter += 1
            sty_data_table = style.table_data
            if row_data %2 == 0:
                sty_data_table = style.table_data_even

            sheet.write(row_data, 0, counter, sty_data_table)
            sheet.write(row_data, 1, i['hotel_name'], sty_data_table)
            sheet.write(row_data, 2, i['counter'], sty_data_table)
            sheet.write(row_data, 3, i['issued'], sty_data_table)
            sheet.write(row_data, 4, i['expire'], sty_data_table)
            sheet.write(row_data, 5, i['fail_issued'], sty_data_table)
            sheet.write(row_data, 6, i['fail_booked'], sty_data_table)
            sheet.write(row_data, 7, i['other'], sty_data_table)
            # sheet.write(row_data, 8, i['passenger'], sty_data_table)

        # draw provider summary
        row_data += 2
        counter = 0
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Provider', style.table_head_center)
        sheet.write(row_data, 2, 'Total Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Issued', style.table_head_center)
        sheet.write(row_data, 4, 'Expire', style.table_head_center)
        sheet.write(row_data, 5, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 6, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 7, 'Other', style.table_head_center)
        # sheet.write(row_data, 8, '# of Passenger', style.table_head_center)
        for i in provider_summary:
            row_data += 1
            counter += 1
            sty_data_table = style.table_data
            if row_data % 2 == 0:
                sty_data_table = style.table_data_even

            sheet.write(row_data, 0, counter, sty_data_table)
            sheet.write(row_data, 1, i['provider'], sty_data_table)
            sheet.write(row_data, 2, i['counter'], sty_data_table)
            sheet.write(row_data, 3, i['issued'], sty_data_table)
            sheet.write(row_data, 4, i['expire'], sty_data_table)
            sheet.write(row_data, 5, i['fail_issued'], sty_data_table)
            sheet.write(row_data, 6, i['fail_booked'], sty_data_table)
            sheet.write(row_data, 7, i['other'], sty_data_table)
            # sheet.write(row_data, 8, i['passenger'], sty_data_table)

        # draw hotel summary
        row_data += 2
        counter = 0
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, '# of night', style.table_head_center)
        sheet.write(row_data, 2, 'Total Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Issued', style.table_head_center)
        sheet.write(row_data, 4, 'Expire', style.table_head_center)
        sheet.write(row_data, 5, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 6, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 7, 'Other', style.table_head_center)
        # sheet.write(row_data, 8, '# of Passenger', style.table_head_center)
        for i in night_summary:
            row_data += 1
            counter += 1
            sty_data_table = style.table_data
            if row_data % 2 == 0:
                sty_data_table = style.table_data_even

            sheet.write(row_data, 0, counter, sty_data_table)
            sheet.write(row_data, 1, i['night'], sty_data_table)
            sheet.write(row_data, 2, i['counter'], sty_data_table)
            sheet.write(row_data, 3, i['issued'], sty_data_table)
            sheet.write(row_data, 4, i['expire'], sty_data_table)
            sheet.write(row_data, 5, i['fail_issued'], sty_data_table)
            sheet.write(row_data, 6, i['fail_booked'], sty_data_table)
            sheet.write(row_data, 7, i['other'], sty_data_table)
            # sheet.write(row_data, 8, i['passenger'], sty_data_table)

        og_row_data = 6
        side_counter = 9
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Hotel Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_activity(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        #global summary
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

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Activity Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_tour(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        country_summary = []
        tour_route_summary = []
        provider_summary = []
        current_order_number = ''
        # row_data = 8
        # for i in values['lines']:
        #     row_data += 1
        #     sty_table_data = style.table_data
        #     if row_data % 2 == 0:
        #         sty_table_data = style.table_data_even
        #
        #     sheet.write(row_data, 10, i['reservation_order_number'], sty_table_data)
        #     sheet.write(row_data, 11, i['tour_name'], sty_table_data)
        #     sheet.write(row_data, 12, i['tour_category'], sty_table_data)
        #     sheet.write(row_data, 13, i['tour_country_name'], sty_table_data)
        #     sheet.write(row_data, 14, i['tour_location_country'], sty_table_data)

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

            if current_order_number != i['reservation_order_number']:
                current_order_number = i['reservation_order_number']
                #count every country in tour
                #filter the respected order number, then count the country
                country_filtered = list(filter(lambda x: x['reservation_order_number'] == i['reservation_order_number'], values['lines']))
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

                tour_route_index = self.check_tour_route_index(tour_route_summary, {'category': i['tour_category'], 'route': i['tour_route']})
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

        #print country and will be updated
        row_data = 8
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, "country", style.table_head_center)
        sheet.write(row_data, 2, "# of transaction", style.table_head_center)
        counter = 0
        for i in country_summary:
            row_data += 1
            counter += 1
            sty_table_data = style._table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['country'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)

        #print provider
        row_data += 2
        sheet.write(row_data, 0, "No.", style.table_head_center)
        sheet.write(row_data, 1, "Provider", style.table_head_center)
        sheet.write(row_data, 2, "# of transaction", style.table_head_center)
        sheet.write(row_data, 3, "Issued", style.table_head_center)
        sheet.write(row_data, 4, "Expire", style.table_head_center)
        sheet.write(row_data, 5, "Fail Booked", style.table_head_center)
        sheet.write(row_data, 6, "Fail Issued", style.table_head_center)
        sheet.write(row_data, 7, "Other", style.table_head_center)
        sheet.write(row_data, 8, "Total Income", style.table_head_center)

        counter = 0
        for i in provider_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['provider'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['issued'], sty_table_data)
            sheet.write(row_data, 4, i['expire'], sty_table_data)
            sheet.write(row_data, 5, i['fail_booked'], sty_table_data)
            sheet.write(row_data, 6, i['fail_issued'], sty_table_data)
            sheet.write(row_data, 7, i['other'], sty_table_data)
            sheet.write(row_data, 8, i['total_amount'], sty_table_data)

        #print tour_route
        row_data += 2
        sheet.write(row_data, 0, "No", style.table_head_center)
        sheet.write(row_data, 1, "Category", style.table_head_center)
        sheet.write(row_data, 2, "Route", style.table_head_center)
        sheet.write(row_data, 3, "# of Transaction", style.table_head_center)

        counter = 0
        for i in tour_route_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['category'], sty_table_data)
            sheet.write(row_data, 2, i['route'], sty_table_data)
            sheet.write(row_data, 3, i['counter'], sty_table_data)

        row_data += 2

        for i in values['lines']:
            row_data += 1

            sheet.write(row_data, 0, row_data, sty_table_data)
            sheet.write(row_data, 1, i['reservation_order_number'], sty_table_data)
            sheet.write(row_data, 2, i['tour_location_country'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Tour Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_visa(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        country_summary = []
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

        # sort some stuff
        country_summary.sort(key=lambda x: x['counter'], reverse=True)

        row_data = 8
        counter = 0
        sheet.write(row_data, 0, "No.", style.table_head_center)
        sheet.write(row_data, 1, 'Country', style.table_head_center)
        sheet.write(row_data, 2, '# of transaction', style.table_head_center)
        sheet.write(row_data, 3, '# of passenger', style.table_head_center)
        for i in country_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['country'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['passenger'], sty_table_data)

        og_row_data = 6
        side_counter = 5
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Visa Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_offline(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

        month = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        summary_by_date = []
        provider_summary = []
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

            # ============= Summary by Provider ==========================
            provider_index = self.check_offline_provider(provider_summary, {"provider_type": i['provider_type_name'], 'offline_provider_type': i['reservation_offline_provider_type']})
            if provider_index == -1:
                temp_dict = {
                    'provider_type': i['provider_type_name'],
                    'provider_name': i['reservation_provider_name'],
                    'offline_provider_type': i['reservation_offline_provider_type'],
                    'total_amount': i['amount'],
                    'counter': 1
                }
                provider_summary.append(temp_dict)
            else:
                provider_summary[provider_index]['counter'] += 1
                provider_summary[provider_index]['total_amount'] += i['amount']

        row_data = 8
        counter = 0
        sheet.write(row_data, 0, "No", style.table_head_center)
        sheet.write(row_data, 1, "Provider Type", style.table_head_center)
        sheet.write(row_data, 2, "Provider Name", style.table_head_center)
        sheet.write(row_data, 3, "Offline Provider", style.table_head_center)
        sheet.write(row_data, 4, "Total Valuation", style.table_head_center)
        sheet.write(row_data, 5, "# of Transaction", style.table_head_center)

        for i in provider_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['provider_type'], sty_table_data)
            sheet.write(row_data, 2, i['provider_name'], sty_table_data)
            sheet.write(row_data, 3, i['offline_provider_type'], sty_table_data)
            sheet.write(row_data, 4, i['total_amount'], sty_table_data)
            sheet.write(row_data, 5, i['counter'], sty_table_data)

        og_row_data = 6
        side_counter = 7
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Offline Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_event(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Event Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_ppob(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales PPOB Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_periksain(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Periksain Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_phc(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales PHC Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_medical(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Medical Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_bus(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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
                sector_dictionary[0]['valuation'] += float(i['amount'])
                sector_dictionary[0]['counter'] += 1
                sector_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            elif i['reservation_sector'] == 'Domestic':
                sector_dictionary[1]['valuation'] += float(i['amount'])
                sector_dictionary[1]['counter'] += 1
                sector_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            else:
                sector_dictionary[2]['valuation'] += float(i['amount'])
                sector_dictionary[2]['counter'] += 1
                sector_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

            # ============= Type of direction ============================
            if i['reservation_direction'] == 'OW':
                direction_dictionary[0]['valuation'] += float(i['amount'])
                direction_dictionary[0]['counter'] += 1
                direction_dictionary[0]['passenger_count'] += int(i['reservation_passenger'])
            elif i['reservation_direction'] == 'RT':
                direction_dictionary[1]['valuation'] += float(i['amount'])
                direction_dictionary[1]['counter'] += 1
                direction_dictionary[1]['passenger_count'] += int(i['reservation_passenger'])
            else:
                direction_dictionary[2]['valuation'] += float(i['amount'])
                direction_dictionary[2]['counter'] += 1
                direction_dictionary[2]['passenger_count'] += int(i['reservation_passenger'])

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

        # ============ FIRST TABLE ======================
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Sector', style.table_head_center)
        sheet.write('C9', '# of sales', style.table_head_center)
        sheet.write('D9', 'Passenger Count', style.table_head_center)

        sheet.write('A10', '1', style.table_data_even)
        sheet.write('B10', sector_dictionary[0]['sector'], style.table_data_even)
        sheet.write('C10', sector_dictionary[0]['counter'], style.table_data_even)
        sheet.write('D10', sector_dictionary[0]['passenger_count'], style.table_data_even)

        sheet.write('A11', '2', style.table_data)
        sheet.write('B11', sector_dictionary[1]['sector'], style.table_data)
        sheet.write('C11', sector_dictionary[1]['counter'], style.table_data)
        sheet.write('D11', sector_dictionary[1]['passenger_count'], style.table_data)

        sheet.write('A12', '3', style.table_data_even)
        sheet.write('B12', sector_dictionary[2]['sector'], style.table_data_even)
        sheet.write('C12', sector_dictionary[2]['counter'], style.table_data_even)
        sheet.write('D12', sector_dictionary[2]['passenger_count'], style.table_data_even)

        row_data = 15
        # ============ SECOND TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'International', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, international_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, international_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, international_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, international_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ THIRD TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Domestic', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, domestic_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, domestic_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, domestic_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, domestic_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FORTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'One Way', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, one_way_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, one_way_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, one_way_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, one_way_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ FUNF TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Return', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, return_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, return_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, return_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, return_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        row_data += 3
        # ============ SIXTH TABLE ======================
        sheet.merge_range(row_data - 1, 0, row_data - 1, 4, 'Multi City', style.table_head_center)
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Origin', style.table_head_center)
        sheet.write(row_data, 2, 'Destination', style.table_head_center)
        sheet.write(row_data, 3, 'Count', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger Count', style.table_head_center)

        counter = 0
        for i in range(0, 50):
            try:
                counter += 1
                row_data += 1
                sty_table_data = style.table_data
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even

                sheet.write(row_data, 1, multi_city_filter[i]['departure'], sty_table_data)
                sheet.write(row_data, 2, multi_city_filter[i]['destination'], sty_table_data)
                sheet.write(row_data, 3, multi_city_filter[i]['counter'], sty_table_data)
                sheet.write(row_data, 4, multi_city_filter[i]['passenger_count'], sty_table_data)
                sheet.write(row_data, 0, counter, sty_table_data)
            except:
                break

        # ============ MANY MANY TABLE ======================
        row_data = 8
        sheet.write(row_data, 6, 'Provider name', style.table_head_center)
        sheet.write(row_data, 7, 'International', style.table_head_center)
        sheet.write(row_data, 8, 'Domestic', style.table_head_center)
        sheet.write(row_data, 9, 'Issued', style.table_head_center)
        sheet.write(row_data, 10, 'Expire', style.table_head_center)
        sheet.write(row_data, 11, 'Fail Booked', style.table_head_center)
        sheet.write(row_data, 12, 'Fail Issued', style.table_head_center)
        sheet.write(row_data, 13, 'Other', style.table_head_center)
        sheet.write(row_data, 14, '# of Passengers', style.table_head_center)

        side_row_data = 6
        carrier_name_summary.sort(key=lambda x: x['total_transaction'], reverse=True)
        for i in carrier_name_summary:
            row_data += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, i['carrier_name'], sty_table_data)
            sheet.write(row_data, 7, i['international_counter'], sty_table_data)
            sheet.write(row_data, 8, i['domestic_counter'], sty_table_data)
            sheet.write(row_data, 9, i['issued'], sty_table_data)
            sheet.write(row_data, 10, i['expired'], sty_table_data)
            sheet.write(row_data, 11, i['fail_booked'], sty_table_data)
            sheet.write(row_data, 12, i['fail_issued'], sty_table_data)
            sheet.write(row_data, 13, i['other'], sty_table_data)
            sheet.write(row_data, 14, i['passenger_count'], sty_table_data)

            side_row_data += 2
            sheet.merge_range(side_row_data, 16, side_row_data, 19, i['carrier_name'], style.table_head_center)
            sheet.merge_range(side_row_data + 1, 16, side_row_data + 1, 18, 'International', style.table_data)
            sheet.write(side_row_data + 1, 19, i['international_counter'], style.table_data)
            sheet.merge_range(side_row_data + 2, 16, side_row_data + 2, 18, 'Domestic', style.table_data)
            sheet.write(side_row_data + 2, 19, i['domestic_counter'], style.table_data)
            side_row_data += 3
            sheet.write(side_row_data, 16, 'Origin', style.table_head_center)
            sheet.write(side_row_data, 17, 'Destination', style.table_head_center)
            sheet.write(side_row_data, 18, '# of Transaction', style.table_head_center)
            sheet.write(side_row_data, 19, '# of Passenger', style.table_head_center)

            i['flight'].sort(key=lambda x: x['counter'], reverse=True)

            for j in range(0, 25):
                try:
                    side_row_data += 1
                    sty_table_data = style.table_data
                    if side_row_data % 2 == 0:
                        sty_table_data = style.table_data_even

                    sheet.write(side_row_data, 16, i['flight'][j]['departure'], sty_table_data)
                    sheet.write(side_row_data, 17, i['flight'][j]['destination'], sty_table_data)
                    sheet.write(side_row_data, 18, i['flight'][j]['counter'], sty_table_data)
                    sheet.write(side_row_data, 19, i['flight'][j]['passenger_count'], sty_table_data)
                except:
                    break;

        row_data += 2
        sheet.write(row_data, 6, 'No', style.table_head_center)
        sheet.write(row_data, 7, '# of Days, issued - depart', style.table_head_center)
        sheet.write(row_data, 8, 'count', style.table_head_center)
        counter = 0
        for i in issued_depart_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 6, counter, sty_table_data)
            sheet.write(row_data, 7, i['day'], sty_table_data)
            sheet.write(row_data, 8, i['counter'], sty_table_data)

        og_row_data = 8
        side_counter = 21
        for i in summary_by_date:
            row_data = og_row_data + 2
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['year'], style.table_head_center)
            row_data += 1
            sheet.merge_range(row_data, side_counter, row_data, side_counter + 2, i['month'], style.table_head_center)
            row_data += 1
            sheet.write(row_data, side_counter, 'Day', style.table_head_center)
            sheet.write(row_data, side_counter + 1, '# of Booked', style.table_head_center)
            sheet.write(row_data, side_counter + 2, '# of Issued', style.table_head_center)
            for j in i['detail']:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even
                sheet.write(row_data, side_counter, j['day'], sty_table_data)
                sheet.write(row_data, side_counter + 1, j['booked_counter'], sty_table_data)
                sheet.write(row_data, side_counter + 2, j['issued_counter'], sty_table_data)
            side_counter += 4

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Bus Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_insurance(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Insurance Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_swabexpress(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Swab Express Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_labpintar(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Lab Pintar Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _print_report_excel_mitrakeluarga(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_selling.report_selling']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ========== TITLE & SUBTITLE =================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date : ' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        # sheet.freeze_panes(9, 0)

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

            product_index = self.check_index(product_summary, 'product', i['carrier_name'])
            if product_index == -1:
                temp_dict = {
                    'product': i['carrier_name'],
                    'counter': 1,
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
                product_summary[product_index]['adult_count'] += i['reservation_adult']
                product_summary[product_index]['child_count'] += i['reservation_child']
                product_summary[product_index]['infant_count'] += i['reservation_infant']

        row_data = 9
        sheet.write(row_data, 0, 'No.', style.table_head_center)
        sheet.write(row_data, 1, 'Product Name', style.table_head_center)
        sheet.write(row_data, 2, '# of Transaction', style.table_head_center)
        sheet.write(row_data, 3, 'Amount', style.table_head_center)
        sheet.write(row_data, 4, 'Passenger', style.table_head_center)
        counter = 0
        for i in product_summary:
            row_data += 1
            counter += 1
            sty_table_data = style.table_data
            if row_data % 2 == 0:
                sty_table_data = style.table_data_even

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['product'], sty_table_data)
            sheet.write(row_data, 2, i['counter'], sty_table_data)
            sheet.write(row_data, 3, i['amount'], sty_table_data)
            sheet.write(row_data, 4, i['passenger'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Sales Mitra Keluarga Report Summary.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
