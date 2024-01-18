import math

from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class Incremental:
    def __init__(self):
        self.num_value = 0

    def reset(self):
        self.num_value = 0

    def get_number(self):
        return self.num_value

    def get_ascii(self):
        return self.convert_num_value_to_ascii(self.num_value)

    def generate_number(self, increment_value=1):
        self.num_value += increment_value
        return self.num_value

    def generate_ascii(self, increment_value=1):
        self.num_value += increment_value
        return self.convert_num_value_to_ascii(self.num_value)

    def convert_to_ascii(self, value):
        return chr(int(value+64))

    def convert_num_value_to_ascii(self, num_value):
        if num_value <= 26:
            return self.convert_to_ascii(num_value)
        mod_value = num_value % 26
        remaining_value = num_value - mod_value
        ch_res = ""
        if remaining_value > 0:
            ch_res = self.convert_num_value_to_ascii(remaining_value/26)
        ch_res += self.convert_to_ascii(mod_value)
        return ch_res


class AgentReportRecapTransactionXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.transaction.wizard'

    # this function handles recap transaction excel render
    # responsible to print the actual data to excel,
    # and do a little summary for airline and hotel
    # btw this is the function being called if you press print in recap transaction
    # and it also does the same for other _print_report_excel
    def _print_report_excel(self, data):
        stream = BytesIO()
        incr = Incremental()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        # this line of code responsible to call function who built the SQL query and actually connect to DB
        # after a little trim and little process like convert some date to string or vice versa
        # data will be return to this values variable
        # *in this recap report
        # values hold 3 main section
        # values['lines'] --> reservation data
        # valued['second_lines'] --> service charge data, within the same date range, this is needed to make sure revenue count and all is very accurate
        # values['data_form'] --> form that being past from GUI that user interact within odoo
        values = self.env['report.tt_agent_report_recap_transaction.agent_report_recap']._prepare_values(
            data['form'])  # get values

        # next 4 lines of code handles excel dependencies
        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        # write to file in cols and row
        if values['data_form'].get('is_corpor'):
            sheet.merge_range('A1:G2', values['data_form']['customer_parent_name'], style.title)  # set merge cells for COR name
        else:
            sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        incr.reset()
        # ======= TABLE HEAD ==========
        sheet.write('%s9' % incr.generate_ascii(), 'No.', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Booking Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Carrier Name', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Name', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Customer Parent Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Customer Parent Name', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Create by', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Issued by', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Issued Date', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Email', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Provider', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Order Number', style.table_head_center)
        # sheet.write('I9', 'Origin', style.table_head_center)
        # sheet.write('J9', 'Sector', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Adult', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Child', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Infant', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Direction', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'State', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'PNR', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Ledger Reference', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Booking State', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Ticket Numbers', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Currency', style.table_head_center)
        if not values['data_form'].get('is_corpor'):
            sheet.write('%s9' % incr.generate_ascii(), 'Agent NTA Amount', style.table_head_center)
            sheet.write('%s9' % incr.generate_ascii(), 'Agent Commission', style.table_head_center)
            sheet.write('%s9' % incr.generate_ascii(), 'Commission Booker', style.table_head_center)
            sheet.write('%s9' % incr.generate_ascii(), 'Upsell', style.table_head_center)
        ##middle agent commission
        ##ho commission
        if values['data_form']['is_ho']:
            sheet.write('%s9' % incr.generate_ascii(), 'HO NTA Amount', style.table_head_center)
            sheet.write('%s9' % incr.generate_ascii(), 'Total Commission', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Grand Total', style.table_head_center)
        sheet.merge_range('%s9:%s9' % (incr.generate_ascii(), incr.generate_ascii(3)), 'Keterangan', style.table_head_center)

        # sheet.write('B9', 'Date', style.table_head_center)
        # sheet.write('C9', 'Order Number', style.table_head_center)
        # sheet.write('D9', 'Agent', style.table_head_center)
        # sheet.write('E9', 'Agent Type', style.table_head_center)
        # sheet.write('F9', 'Provider', style.table_head_center)
        # sheet.write('G9', 'Total', style.table_head_center)
        # sheet.write('H9', 'State', style.table_head_center)
        # sheet.write('I9', 'Provider Type', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 8)
        sheet.set_column('B:B', 8)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:I', 15)
        sheet.set_column('J:J', 12)
        sheet.set_column('K:V', 15)
        if values['data_form']['is_ho']:
            sheet.set_column('AH:AH', 30)
        elif not values['data_form'].get('is_corpor'):
            sheet.set_column('AF:AF', 30)
        else:
            sheet.set_column('AB:AB', 30)

        # ============ void start() ======================
        # declare some constant dependencies
        row_data = 8
        counter = 0
        temp_order_number = ''

        # it's just to make things easier, rather than write values['lines'] over and over
        datas = values['lines']
        service_charge = values['second_lines']
        channel_pricing = values['third_lines']
        #proceed the data
        # it's for temporary purposes, declare it here so that the first data will be different than "current"
        current_pnr = ''
        current_ledger = ''

        # to check for single PNR in case of RT
        rt_single_pnr_idx = []
        ord_number_popped = False

        # summary list declaration
        airline_recaps = []
        hotel_recaps = []
        offline_recaps = []

        total_all_agent_nta = 0
        total_all_agent_commission = 0
        total_all_ho_nta = 0
        total_all_total_commission = 0
        total_all_grand_total = 0

        # let's iterate the data YEY!
        for idx, i in enumerate(datas):
            if not values['data_form']['is_ho']:
                if i['ledger_agent_name'] == values['data_form']['ho_name'] and values['data_form']['ho_name'] != values['data_form']['agent_name']:
                    continue
            if i.get('ledger_pnr'):
                # check if order number == current number
                if temp_order_number == i['order_number']:
                    # check if pnr is different than previous pnr
                    if current_pnr != i['ledger_pnr']:
                        # update current pnr
                        current_pnr = i['ledger_pnr']

                        # product total corresponding to particular pnr
                        # filter from service charge data
                        temp_charge = list(
                            filter(lambda x: x['booking_pnr'] == current_pnr and x['order_number'] == i['order_number'],
                                   service_charge))

                        # okay after filtering service charge data to respected reservation
                        # we need to count revenue and comission
                        # hence declaration of this variables
                        nta_total = 0
                        commission = 0
                        this_pnr_agent_nta_total = 0
                        this_pnr_agent_commission = 0

                        # lets count the service charge
                        for k in temp_charge:
                            if k['booking_charge_type'] == 'RAC':
                                commission -= k['booking_charge_total']
                                nta_total += k['booking_charge_total']
                                if k['booking_charge_code'] == 'rac':
                                    this_pnr_agent_commission -= k['booking_charge_total']
                                    this_pnr_agent_nta_total += k['booking_charge_total']
                            else:
                                if k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                                    nta_total += k['booking_charge_total']
                                    this_pnr_agent_nta_total += k['booking_charge_total']
                        grand_total = nta_total + commission

                        # declare view handler
                        row_data += 1
                        sty_table_data_center = style.table_data_center
                        sty_table_data = style.table_data
                        sty_datetime = style.table_data_datetime
                        sty_date = style.table_data_date
                        sty_amount = style.table_data_amount
                        if row_data % 2 == 0:
                            sty_table_data_center = style.table_data_center_even
                            sty_table_data = style.table_data_even
                            sty_datetime = style.table_data_datetime_even
                            sty_date = style.table_data_date_even
                            sty_amount = style.table_data_amount_even

                        incr.reset()
                        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_date)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_pnr'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i.get('ticket_numbers', ''), sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                        if not values['data_form'].get('is_corpor'):
                            sheet.write(row_data, incr.generate_number(), this_pnr_agent_nta_total, sty_amount)
                            sheet.write(row_data, incr.generate_number(), this_pnr_agent_commission, sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        if values['data_form']['is_ho']:
                            sheet.write(row_data, incr.generate_number(), nta_total, sty_amount)
                            sheet.write(row_data, incr.generate_number(), commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), grand_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                        # if current reservation so happened to be an airline type (provider type i mean)
                        # then we'll try to make summary if the reservation is considered as GDS book or not
                        # and count how many passenger within the reservation
                        if i['provider_type'].lower() == 'airline':
                        # check if reservation is airline
                            # different PNR in one reservation, pop from single PNR list
                            if i['direction'] == 'RT' and not ord_number_popped and len(rt_single_pnr_idx) > 0:
                                ord_number_popped = True
                                rt_single_pnr_idx.pop()
                            # will return the index of "same" data based on user
                            data_index = next(
                                (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']), -1)
                            # if data is bigger than 0 = there's data within airline recaps
                            if data_index >= 0:
                                # then lets update the data, by adding
                                if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                    airline_recaps[data_index]['pax_GDS'] += i['adult']
                                    airline_recaps[data_index]['pax_GDS'] += i['child']
                                    airline_recaps[data_index]['pax_GDS'] += i['infant']
                                else:
                                    airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                    airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                    airline_recaps[data_index]['pax_non_GDS'] += i['infant']
                            else:
                                # if data is not yet exist
                                # we'll declare the data first then we'll add to airline recaps list
                                temp_dict = {
                                    'id': i['issued_uid'],
                                    'name': i['issued_by'],
                                    'GDS': 0,
                                    'pax_GDS': 0,
                                    'non_GDS': 0,
                                    'pax_non_GDS': 0
                                }
                                # add to airline_recaps list
                                airline_recaps.append(temp_dict)
                                # add the first data
                                if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                    airline_recaps[data_index]['GDS'] += 1
                                    airline_recaps[data_index]['pax_GDS'] += i['adult']
                                    airline_recaps[data_index]['pax_GDS'] += i['child']
                                    airline_recaps[data_index]['pax_GDS'] += i['infant']
                                else:
                                    airline_recaps[data_index]['non_GDS'] += 1
                                    airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                    airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                    airline_recaps[data_index]['pax_non_GDS'] += i['infant']

                    if i['ledger_transaction_type'] in [3, 10] and current_ledger != i['ledger_id'] and not values['data_form'].get('is_corpor'):
                        current_ledger = i['ledger_id']

                        row_data += 1
                        sty_table_data_center = style.table_data_center
                        sty_table_data = style.table_data
                        sty_datetime = style.table_data_datetime
                        sty_date = style.table_data_date
                        sty_amount = style.table_data_amount
                        if row_data % 2 == 0:
                            sty_table_data_center = style.table_data_center_even
                            sty_table_data = style.table_data_even
                            sty_datetime = style.table_data_datetime_even
                            sty_date = style.table_data_date_even
                            sty_amount = style.table_data_amount_even

                        incr.reset()
                        # add ledger info 1 row below (from the same line of data)
                        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_date)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_pnr'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        if not values['data_form'].get('is_corpor'):
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        if values['data_form']['is_ho']:
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['ledger_agent_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['debit'], sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['ledger_description'], sty_table_data)

                else:
                    # current_number != iterate order number
                    # set current order number to iterated number
                    temp_order_number = i['order_number']
                    current_pnr = i['ledger_pnr']
                    ord_number_popped = False

                    upsell = 0
                    for svc_csc in channel_pricing:
                        if svc_csc['order_number'] == temp_order_number and svc_csc['charge_type'] == 'CSC' and isinstance(
                                svc_csc['service_charge_amount'], float):  # check order number sama & upsell int
                            upsell += svc_csc['service_charge_amount']
                    # lets do some preparation to print the first line (data basically)
                    counter += 1
                    row_data += 1
                    sty_table_data_center = style.table_data_center_border
                    sty_table_data = style.table_data_border
                    sty_datetime = style.table_data_datetime_border
                    sty_date = style.table_data_date_border
                    sty_amount = style.table_data_amount_border
                    if row_data % 2 == 0:
                        sty_table_data_center = style.table_data_center_even_border
                        sty_table_data = style.table_data_even_border
                        sty_datetime = style.table_data_datetime_even_border
                        sty_date = style.table_data_date_even_border
                        sty_amount = style.table_data_amount_even_border

                    # filter from service charge data
                    temp_charge_agent = list(filter(lambda x: x['order_number'] == i['order_number'], service_charge))
                    temp_charge = list(filter(lambda x: x['booking_pnr'] == current_pnr, temp_charge_agent))

                    # see line 134 for explenation of this next few lines of code
                    nta_total = 0
                    commission = 0
                    this_resv_agent_nta_total = 0
                    this_resv_agent_commission = 0
                    this_pnr_agent_nta_total = 0
                    this_pnr_agent_commission = 0

                    for k in temp_charge:
                        if k['booking_charge_type'] == 'RAC':
                            commission -= k['booking_charge_total']
                            nta_total += k['booking_charge_total']
                            if k['booking_charge_code'] == 'rac':
                                this_pnr_agent_commission -= k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                        else:
                            if k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                                nta_total += k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                    grand_total = nta_total + commission

                    for k in temp_charge_agent:
                        if k['booking_charge_type'] == 'RAC':
                            if k['booking_charge_code'] == 'rac':
                                this_resv_agent_commission -= k['booking_charge_total']
                                this_resv_agent_nta_total += k['booking_charge_total']
                        elif k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                            this_resv_agent_nta_total += k['booking_charge_total']

                    total_all_agent_nta += this_resv_agent_nta_total
                    total_all_agent_commission += this_resv_agent_commission
                    total_all_ho_nta += i['total_nta']
                    total_all_total_commission += i['total_commission']
                    total_all_grand_total += i['grand_total']

                    incr.reset()
                    # print the whole data of reservation
                    sheet.write(row_data, incr.get_number(), counter, sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), i['provider_type'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['carrier_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['agent_type_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['agent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['customer_parent_type_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['customer_parent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['create_by'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['issued_by'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['issued_date'], sty_date)
                    sheet.write(row_data, incr.generate_number(), i['agent_email'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['order_number'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['adult'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['child'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['infant'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i.get('direction', '-'), sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['pnr'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                    if not values['data_form'].get('is_corpor'):
                        sheet.write(row_data, incr.generate_number(), this_resv_agent_nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), this_resv_agent_commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), i.get('commission_booker', 0), sty_amount)
                        sheet.write(row_data, incr.generate_number(), upsell, sty_amount) ### IVAN 22 dec 2022 untuk data lama upsell tidak masuk ke komisi data baru upsell sudah masuk ke komisi, aftersales recap belum masuk
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), i['total_nta'], sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['total_commission'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['grand_total'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                    # print total by provider under the reservation data, before the "peripherals" data
                    row_data += 1
                    sty_table_data_center = style.table_data_center_border
                    sty_table_data = style.table_data_border
                    sty_datetime = style.table_data_datetime_border
                    sty_date = style.table_data_date_border
                    sty_amount = style.table_data_amount_border
                    if row_data % 2 == 0:
                        sty_table_data_center = style.table_data_center_even_border
                        sty_table_data = style.table_data_even_border
                        sty_datetime = style.table_data_datetime_even_border
                        sty_date = style.table_data_date_even_border
                        sty_amount = style.table_data_amount_even_border

                    incr.reset()
                    sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['ledger_pnr'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i.get('ticket_numbers', ''), sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                    if not values['data_form'].get('is_corpor'):
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), commission, sty_amount)
                    sheet.write(row_data, incr.generate_number(), grand_total, sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                    if i['ledger_transaction_type'] in [3, 10] and current_ledger != i['ledger_id'] and not values['data_form'].get('is_corpor'):
                        current_ledger = i['ledger_id']

                        row_data += 1
                        sty_table_data_center = style.table_data_center
                        sty_table_data = style.table_data
                        sty_datetime = style.table_data_datetime
                        sty_date = style.table_data_date
                        sty_amount = style.table_data_amount
                        if row_data % 2 == 0:
                            sty_table_data_center = style.table_data_center_even
                            sty_table_data = style.table_data_even
                            sty_datetime = style.table_data_datetime_even
                            sty_date = style.table_data_date_even
                            sty_amount = style.table_data_amount_even

                        incr.reset()
                        # add ledger info 1 row below (from the same line of data)
                        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_date)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_pnr'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                        sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        if not values['data_form'].get('is_corpor'):
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        if values['data_form']['is_ho']:
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                            sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['ledger_agent_name'], sty_table_data)
                        sheet.write(row_data, incr.generate_number(), i['debit'], sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['ledger_description'], sty_table_data)

                    # lets recap
                    # see line 189 for code explanation of this if provider airline
                    if i['provider_type'].lower() == 'airline':
                        if i['direction'] == 'RT':
                            rt_single_pnr_idx.append(idx)
                        data_index = next((index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']), -1)
                        if data_index >= 0:
                            if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']
                        else:
                            temp_dict = {
                                'id': i['issued_uid'],
                                'name': i['issued_by'],
                                'GDS': 0,
                                'pax_GDS': 0,
                                'non_GDS': 0,
                                'pax_non_GDS': 0
                            }
                            airline_recaps.append(temp_dict)
                            if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']

                    # if provider is hotel
                    # we'll make a little summary too
                    # so check if reservation happened to be a hotel reservation
                    # then
                    if i['provider_type'].lower() == 'hotel':
                        # using the same logic of getting user in a list, but this time is hotel recaps list
                        # instead of airline_recaps list
                        data_index = next((index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['issued_uid']),-1)

                        # if data index >= 0 then there's data with match user
                        # we only need to update the data
                        if data_index >= 0:
                            hotel_recaps[data_index]['counter'] += 1
                            hotel_recaps[data_index]['room_night'] += i.get('room_count', 0) * i.get('nights', 0)
                        else:
                            # if data is not yet exist then create some temp dictionary
                            temp_dict = {
                                'id': i['issued_uid'],
                                'name': i['issued_by'],
                                'counter': 1,
                                'room_night': i.get('room_count', 0) * i.get('nights', 0)
                            }
                            # and add to hotel recaps list
                            hotel_recaps.append(temp_dict)

                    # okay so special case for offline
                    # since offline is not a provider rather how the reservation issued process
                    # and within offline provider, there's a note of what kind provider of reservation data being issued manually a.k.a offline
                    if i['provider_type'].lower() == 'offline':
                        # if data is offline then we'll do another check if reservation is airline or hotel
                        # see line 189 for explanation of airline code explanation
                        if i['offline_provider'].lower() == 'airline':
                            data_index = next(
                                (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']), -1)
                            if data_index >= 0:
                                if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                    airline_recaps[data_index]['GDS'] += 1
                                else:
                                    airline_recaps[data_index]['non_GDS'] += 1
                            else:
                                temp_dict = {
                                    'id': i['issued_uid'],
                                    'name': i['issued_by'],
                                    'pax_GDS': 0,
                                    'GDS': 0,
                                    'non_GDS': 0,
                                    'pax_non_GDS': 0
                                }
                                airline_recaps.append(temp_dict)
                                if i['provider_name'] and ('amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                    airline_recaps[data_index]['GDS'] += 1
                                else:
                                    airline_recaps[data_index]['non_GDS'] += 1

                        # and see line 460 for if hotel code explanation
                        if i['provider_type'].lower() == 'hotel':
                            data_index = next(
                                (index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['issued_uid']), -1)
                            if data_index >= 0:
                                hotel_recaps[data_index]['counter'] += 1
                                hotel_recaps[data_index]['room_night'] += i.get('room_count', 0) * i.get('nights', 0)
                            else:
                                temp_dict = {
                                    'id': i['issued_uid'],
                                    'name': i['issued_by'],
                                    'counter': 1,
                                    'room_night': i.get('room_count', 0) * i.get('nights', 0)
                                }
                                hotel_recaps.append(temp_dict)
            else:
                if temp_order_number == i['order_number']:
                    # check if pnr is different than previous pnr
                    if current_pnr != i['provider_pnr']:
                        # update current pnr
                        current_pnr = i['provider_pnr']

                    # product total corresponding to particular pnr
                    # filter from service charge data
                    temp_charge = list(
                        filter(lambda x: x['booking_pnr'] == current_pnr and x['order_number'] == i['order_number'],
                               service_charge))

                    # okay after filtering service charge data to respected reservation
                    # we need to count revenue and comission
                    # hence declaration of this variables
                    nta_total = 0
                    commission = 0
                    this_pnr_agent_nta_total = 0
                    this_pnr_agent_commission = 0

                    # lets count the service charge
                    for k in temp_charge:
                        if k['booking_charge_type'] == 'RAC':
                            commission -= k['booking_charge_total']
                            nta_total += k['booking_charge_total']
                            if k['booking_charge_code'] == 'rac':
                                this_pnr_agent_commission -= k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                        else:
                            if k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                                nta_total += k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                    grand_total = nta_total + commission

                    # declare view handler
                    row_data += 1
                    sty_table_data_center = style.table_data_center
                    sty_table_data = style.table_data
                    sty_datetime = style.table_data_datetime
                    sty_date = style.table_data_date
                    sty_amount = style.table_data_amount
                    if row_data % 2 == 0:
                        sty_table_data_center = style.table_data_center_even
                        sty_table_data = style.table_data_even
                        sty_datetime = style.table_data_datetime_even
                        sty_date = style.table_data_date_even
                        sty_amount = style.table_data_amount_even

                    incr.reset()
                    sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_pnr'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['order_number'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i.get('ticket_numbers', ''), sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                    if not values['data_form'].get('is_corpor'):
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), commission, sty_amount)
                    sheet.write(row_data, incr.generate_number(), grand_total, sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                    # if current reservation so happened to be an airline type (provider type i mean)
                    # then we'll try to make summary if the reservation is considered as GDS book or not
                    # and count how many passenger within the reservation
                    if i['provider_type'].lower() == 'airline':
                        # check if reservation is airline
                        # different PNR in one reservation, pop from single PNR list
                        if i['direction'] == 'RT' and not ord_number_popped and len(rt_single_pnr_idx) > 0:
                            ord_number_popped = True
                            rt_single_pnr_idx.pop()
                        # will return the index of "same" data based on user
                        data_index = next(
                            (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']), -1)
                        # if data is bigger than 0 = there's data within airline recaps
                        if data_index >= 0:
                            # then lets update the data, by adding
                            if i['provider_name'] and (
                                    'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i[
                                'provider_name']):
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']
                        else:
                            # if data is not yet exist
                            # we'll declare the data first then we'll add to airline recaps list
                            temp_dict = {
                                'id': i['issued_uid'],
                                'name': i['issued_by'],
                                'GDS': 0,
                                'pax_GDS': 0,
                                'non_GDS': 0,
                                'pax_non_GDS': 0
                            }
                            # add to airline_recaps list
                            airline_recaps.append(temp_dict)
                            # add the first data
                            if i['provider_name'] and (
                                    'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i[
                                'provider_name']):
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']
                else:
                    # current_number != iterate order number
                    # set current order number to iterated number
                    temp_order_number = i['order_number']
                    current_pnr = i['provider_pnr']
                    ord_number_popped = False

                    upsell = 0
                    for svc_csc in channel_pricing:
                        if svc_csc['order_number'] == temp_order_number and svc_csc['charge_type'] == 'CSC' and isinstance(svc_csc['service_charge_amount'], float):  # check order number sama & upsell int
                            upsell += svc_csc['service_charge_amount']
                    # lets do some preparation to print the first line (data basically)
                    counter += 1
                    row_data += 1
                    sty_table_data_center = style.table_data_center_border
                    sty_table_data = style.table_data_border
                    sty_datetime = style.table_data_datetime_border
                    sty_date = style.table_data_date_border
                    sty_amount = style.table_data_amount_border
                    if row_data % 2 == 0:
                        sty_table_data_center = style.table_data_center_even_border
                        sty_table_data = style.table_data_even_border
                        sty_datetime = style.table_data_datetime_even_border
                        sty_date = style.table_data_date_even_border
                        sty_amount = style.table_data_amount_even_border

                    # filter from service charge data
                    temp_charge_agent = list(filter(lambda x: x['order_number'] == i['order_number'], service_charge))
                    temp_charge = list(filter(lambda x: x['booking_pnr'] == current_pnr, temp_charge_agent))

                    # see line 134 for explenation of this next few lines of code
                    nta_total = 0
                    commission = 0
                    this_resv_agent_nta_total = 0
                    this_resv_agent_commission = 0
                    this_pnr_agent_nta_total = 0
                    this_pnr_agent_commission = 0

                    for k in temp_charge:
                        if k['booking_charge_type'] == 'RAC':
                            commission -= k['booking_charge_total']
                            nta_total += k['booking_charge_total']
                            if k['booking_charge_code'] == 'rac':
                                this_pnr_agent_commission -= k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                        else:
                            if k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                                nta_total += k['booking_charge_total']
                                this_pnr_agent_nta_total += k['booking_charge_total']
                    grand_total = nta_total + commission

                    for k in temp_charge_agent:
                        if k['booking_charge_type'] == 'RAC':
                            if k['booking_charge_code'] == 'rac':
                                this_resv_agent_commission -= k['booking_charge_total']
                                this_resv_agent_nta_total += k['booking_charge_total']
                        elif k['booking_charge_type'] != 'DISC' and k['booking_charge_total']:
                            this_resv_agent_nta_total += k['booking_charge_total']

                    total_all_agent_nta += this_resv_agent_nta_total
                    total_all_agent_commission += this_resv_agent_commission
                    total_all_ho_nta += i['total_nta']
                    total_all_total_commission += i['total_commission']
                    total_all_grand_total += i['grand_total']

                    incr.reset()
                    # print the whole data of reservation
                    sheet.write(row_data, incr.get_number(), counter, sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), i['provider_type'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['carrier_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['agent_type_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['agent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['customer_parent_type_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['customer_parent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['create_by'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['issued_by'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['issued_date'], sty_date)
                    sheet.write(row_data, incr.generate_number(), i['agent_email'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['order_number'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['adult'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['child'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['infant'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i.get('direction', '-'), sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['pnr'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['order_number'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                    if not values['data_form'].get('is_corpor'):
                        sheet.write(row_data, incr.generate_number(), this_resv_agent_nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), this_resv_agent_commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), i.get('commission_booker', 0), sty_amount)
                        sheet.write(row_data, incr.generate_number(), upsell, sty_table_data)  ### IVAN 22 dec 2022 untuk data lama upsell tidak masuk ke komisi data baru upsell sudah masuk ke komisi, aftersales recap belum masuk
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), i['total_nta'], sty_amount)
                        sheet.write(row_data, incr.generate_number(), i['total_commission'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['grand_total'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                    # print total by provider under the reservation data, before the "peripherals" data
                    row_data += 1
                    sty_table_data_center = style.table_data_center_border
                    sty_table_data = style.table_data_border
                    sty_datetime = style.table_data_datetime_border
                    sty_date = style.table_data_date_border
                    sty_amount = style.table_data_amount_border
                    if row_data % 2 == 0:
                        sty_table_data_center = style.table_data_center_even_border
                        sty_table_data = style.table_data_even_border
                        sty_datetime = style.table_data_datetime_even_border
                        sty_date = style.table_data_date_even_border
                        sty_amount = style.table_data_amount_even_border

                    incr.reset()
                    sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['provider_pnr'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['order_number'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i.get('ticket_numbers', ''), sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                    if not values['data_form'].get('is_corpor'):
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), this_pnr_agent_commission, sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), nta_total, sty_amount)
                        sheet.write(row_data, incr.generate_number(), commission, sty_amount)
                    sheet.write(row_data, incr.generate_number(), grand_total, sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                    # lets recap
                    # see line 189 for code explanation of this if provider airline
                    if i['provider_type'].lower() == 'airline':
                        if i['direction'] == 'RT':
                            rt_single_pnr_idx.append(idx)
                        data_index = next((index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']),
                                          -1)
                        if data_index >= 0:
                            if i['provider_name'] and (
                                    'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']
                        else:
                            temp_dict = {
                                'id': i['issued_uid'],
                                'name': i['issued_by'],
                                'GDS': 0,
                                'pax_GDS': 0,
                                'non_GDS': 0,
                                'pax_non_GDS': 0
                            }
                            airline_recaps.append(temp_dict)
                            if i['provider_name'] and (
                                    'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']

                    # if provider is hotel
                    # we'll make a little summary too
                    # so check if reservation happened to be a hotel reservation
                    # then
                    if i['provider_type'].lower() == 'hotel':
                        # using the same logic of getting user in a list, but this time is hotel recaps list
                        # instead of airline_recaps list
                        data_index = next((index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['issued_uid']),
                                          -1)

                        # if data index >= 0 then there's data with match user
                        # we only need to update the data
                        if data_index >= 0:
                            hotel_recaps[data_index]['counter'] += 1
                            hotel_recaps[data_index]['room_night'] += i.get('room_count', 0) * i.get('nights', 0)
                        else:
                            # if data is not yet exist then create some temp dictionary
                            temp_dict = {
                                'id': i['issued_uid'],
                                'name': i['issued_by'],
                                'counter': 1,
                                'room_night': i.get('room_count', 0) * i.get('nights', 0)
                            }
                            # and add to hotel recaps list
                            hotel_recaps.append(temp_dict)

                    # okay so special case for offline
                    # since offline is not a provider rather how the reservation issued process
                    # and within offline provider, there's a note of what kind provider of reservation data being issued manually a.k.a offline
                    if i['provider_type'].lower() == 'offline':
                        # if data is offline then we'll do another check if reservation is airline or hotel
                        # see line 189 for explanation of airline code explanation
                        if i['offline_provider'].lower() == 'airline':
                            data_index = next(
                                (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['issued_uid']), -1)
                            if data_index >= 0:
                                if i['provider_name'] and (
                                        'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i['provider_name']):
                                    airline_recaps[data_index]['GDS'] += 1
                                else:
                                    airline_recaps[data_index]['non_GDS'] += 1
                            else:
                                temp_dict = {
                                    'id': i['issued_uid'],
                                    'name': i['issued_by'],
                                    'pax_GDS': 0,
                                    'GDS': 0,
                                    'non_GDS': 0,
                                    'pax_non_GDS': 0
                                }
                                airline_recaps.append(temp_dict)
                                if i['provider_name'] and (
                                        'amadeus' in i['provider_name'] or 'sabre' in i['provider_name'] or 'sia' in i[
                                    'provider_name']):
                                    airline_recaps[data_index]['GDS'] += 1
                                else:
                                    airline_recaps[data_index]['non_GDS'] += 1

                        # and see line 460 for if hotel code explanation
                        if i['provider_type'].lower() == 'hotel':
                            data_index = next(
                                (index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['issued_uid']), -1)
                            if data_index >= 0:
                                hotel_recaps[data_index]['counter'] += 1
                                hotel_recaps[data_index]['room_night'] += i.get('room_count', 0) * i.get('nights', 0)
                            else:
                                temp_dict = {
                                    'id': i['issued_uid'],
                                    'name': i['issued_by'],
                                    'counter': 1,
                                    'room_night': i.get('room_count', 0) * i.get('nights', 0)
                                }
                                hotel_recaps.append(temp_dict)

        # check if there are indexes marked for being RT with single PNR
        for sing_pnr in rt_single_pnr_idx:
            # if yes, add pax count once more
            data_index = next((index for (index, d) in enumerate(airline_recaps) if d["id"] == datas[sing_pnr]['issued_uid']), -1)
            if data_index >= 0:
                if datas[sing_pnr]['provider_name'] and ('amadeus' in datas[sing_pnr]['provider_name'] or 'sabre' in datas[sing_pnr]['provider_name'] or 'sia' in datas[sing_pnr]['provider_name']):
                    # asumsi jumlah reservation tidak di hitung lagi kalo RT dgn 1 PNR
                    # airline_recaps[data_index]['GDS'] += 1
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['adult']
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['child']
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['infant']
                else:
                    # airline_recaps[data_index]['non_GDS'] += 1
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['adult']
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['child']
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['infant']
            else:
                temp_dict = {
                    'id': datas[sing_pnr]['issued_uid'],
                    'name': datas[sing_pnr]['issued_by'],
                    'GDS': 0,
                    'pax_GDS': 0,
                    'non_GDS': 0,
                    'pax_non_GDS': 0
                }
                airline_recaps.append(temp_dict)
                if datas[sing_pnr]['provider_name'] and ('amadeus' in datas[sing_pnr]['provider_name'] or 'sabre' in datas[sing_pnr]['provider_name'] or 'sia' in datas[sing_pnr]['provider_name']):
                    # asumsi jumlah reservation tidak di hitung lagi kalo RT dgn 1 PNR
                    # airline_recaps[data_index]['GDS'] += 1
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['adult']
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['child']
                    airline_recaps[data_index]['pax_GDS'] += datas[sing_pnr]['infant']
                else:
                    # airline_recaps[data_index]['non_GDS'] += 1
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['adult']
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['child']
                    airline_recaps[data_index]['pax_non_GDS'] += datas[sing_pnr]['infant']

        row_data += 1
        sty_table_data_center = style.table_data_center_total_footer
        sty_table_data = style.table_data_total_footer
        sty_datetime = style.table_data_datetime_total_footer
        sty_date = style.table_data_date_total_footer
        sty_amount = style.table_data_amount_total_footer
        incr.reset()
        # print the whole data of reservation
        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_date)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), 'Total', sty_table_data_center)
        if not values['data_form'].get('is_corpor'):
            sheet.write(row_data, incr.generate_number(), total_all_agent_nta, sty_amount)
            sheet.write(row_data, incr.generate_number(), total_all_agent_commission, sty_amount)
            sheet.write(row_data, incr.generate_number(), '', sty_table_data)
            sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        if values['data_form']['is_ho']:
            sheet.write(row_data, incr.generate_number(), total_all_ho_nta, sty_amount)
            sheet.write(row_data, incr.generate_number(), total_all_total_commission, sty_amount)
        sheet.write(row_data, incr.generate_number(), total_all_grand_total, sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)

        row_data += 1
        # this is writing empty string, to print the bottom border
        sty_table_data_center = style.table_data_center_border
        sty_table_data = style.table_data_border
        sty_datetime = style.table_data_datetime_border
        sty_date = style.table_data_date_border
        sty_amount = style.table_data_amount_border
        incr.reset()
        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_date)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
        if not values['data_form'].get('is_corpor'):
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
        if values['data_form']['is_ho']:
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)

        # this section responsible to draw summary both airline recaps and hotel recaps
        # airline recaps
        row_data += 4
        if values['data_form']['provider_type'] == 'airline' or values['data_form']['provider_type'] == 'all' or values['data_form']['provider_type'] == 'offline':
            sheet.write(row_data, 0, 'AIRLINES', style.table_head_center)
            sheet.write(row_data, 1, 'Nama', style.table_head_center)
            sheet.write(row_data, 2, 'GDS reservation', style.table_head_center)
            sheet.write(row_data, 3, 'GDS pax', style.table_head_center)
            sheet.write(row_data, 4, 'Non-GDS reservation', style.table_head_center)
            sheet.write(row_data, 5, 'Non-GDS pax', style.table_head_center)
            for i in airline_recaps:
                row_data += 1
                sheet.write(row_data, 1, i['name'], sty_table_data)
                sheet.write(row_data, 2, i['GDS'], sty_table_data)
                sheet.write(row_data, 3, i['pax_GDS'], sty_table_data)
                sheet.write(row_data, 4, i['non_GDS'], sty_table_data)
                sheet.write(row_data, 5, i['pax_non_GDS'], sty_table_data)
        # hotel recaps
        row_data += 2
        if values['data_form']['provider_type'] == 'hotel' or values['data_form']['provider_type'] == 'all' or values['data_form']['provider_type'] == 'offline':
            sheet.write(row_data, 0, 'HOTELS', style.table_head_center)
            sheet.write(row_data, 1, 'Nama', style.table_head_center)
            sheet.write(row_data, 2, 'Number of booked', style.table_head_center)
            sheet.write(row_data, 3, 'Total Room x Night', style.table_head_center)
            for i in hotel_recaps:
                row_data += 1
                sheet.write(row_data, 1, i['name'], sty_table_data)
                sheet.write(row_data, 2, i['counter'], sty_table_data)
                sheet.write(row_data, 3, i['room_night'], sty_table_data)
            #proceed

        # close the file
        workbook.close()

        # finalize and print!
        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': '%s %s.xlsx' % (values['data_form']['agent_name'],values['data_form']['title']), 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
