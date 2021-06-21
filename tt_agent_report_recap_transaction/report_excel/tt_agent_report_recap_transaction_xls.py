from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime

class AgentReportRecapTransactionXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.transaction.wizard'

    # this function handles recap transaction excel render
    # responsible to print the actual data to excel,
    # and do a little summary for airline and hotel
    # btw this is the function being called if you press print in recap transaction
    # and it also does the same for other _print_report_excel
    def _print_report_excel(self, data):
        stream = BytesIO()
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
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Booking Type', style.table_head_center)
        sheet.write('C9', 'Carrier Name', style.table_head_center)
        sheet.write('D9', 'Agent Type', style.table_head_center)
        sheet.write('E9', 'Agent Name', style.table_head_center)
        sheet.write('F9', 'Customer Parent Type', style.table_head_center)
        sheet.write('G9', 'Customer Parent Name', style.table_head_center)
        sheet.write('H9', 'Create by', style.table_head_center)
        sheet.write('I9', 'Issued by', style.table_head_center)
        sheet.write('J9', 'Issued Date', style.table_head_center)
        sheet.write('K9', 'Agent Email', style.table_head_center)
        sheet.write('L9', 'Provider', style.table_head_center)
        sheet.write('M9', 'Order Number', style.table_head_center)
        # sheet.write('I9', 'Origin', style.table_head_center)
        # sheet.write('J9', 'Sector', style.table_head_center)
        sheet.write('N9', 'Adult', style.table_head_center)
        sheet.write('O9', 'Child', style.table_head_center)
        sheet.write('P9', 'Infant', style.table_head_center)
        sheet.write('Q9', 'State', style.table_head_center)
        sheet.write('R9', 'PNR', style.table_head_center)
        sheet.write('S9', 'Ledger Reference', style.table_head_center)
        sheet.write('T9', 'Booking State', style.table_head_center)
        sheet.write('U9', 'Currency', style.table_head_center)
        sheet.write('V9', 'Agent NTA Amount', style.table_head_center)
        sheet.write('W9', 'Agent Commission', style.table_head_center)
        ##middle agent commission
        ##ho commission
        sheet.write('X9', 'HO NTA Amount', style.table_head_center)
        sheet.write('Y9', 'Total Commission', style.table_head_center)
        sheet.write('Z9', 'Grand Total', style.table_head_center)
        sheet.merge_range('AA9:AD9', 'Keterangan', style.table_head_center)

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
        sheet.set_column('AD:AD', 30)

        # ============ void start() ======================
        # declare some constant dependencies
        row_data = 8
        counter = 0
        temp_order_number = ''

        # it's just to make things easier, rather than write values['lines'] over and over
        datas = values['lines']
        service_charge = values['second_lines']

        #proceed the data
        # it's for temporary purposes, declare it here so that the first data will be different than "current"
        current_pnr = ''

        # summary list declaration
        airline_recaps = []
        hotel_recaps = []
        offline_recaps = []

        # let's iterate the data YEY!
        for i in datas:

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

                    sheet.write(row_data, 0, '', sty_table_data_center)
                    sheet.write(row_data, 1, '', sty_table_data)
                    sheet.write(row_data, 2, '', sty_table_data)
                    sheet.write(row_data, 3, '', sty_table_data)
                    sheet.write(row_data, 4, '', sty_table_data)
                    sheet.write(row_data, 5, '', sty_table_data)
                    sheet.write(row_data, 6, '', sty_table_data)
                    sheet.write(row_data, 7, '', sty_table_data)
                    sheet.write(row_data, 8, '', sty_table_data)
                    sheet.write(row_data, 9, '', sty_date)
                    sheet.write(row_data, 10, '', sty_table_data)
                    sheet.write(row_data, 11, i['provider_name'], sty_table_data)
                    sheet.write(row_data, 12, '', sty_amount)
                    sheet.write(row_data, 13, '', sty_amount)
                    sheet.write(row_data, 14, '', sty_amount)
                    sheet.write(row_data, 15, '', sty_amount)
                    sheet.write(row_data, 16, i['state'], sty_table_data)
                    sheet.write(row_data, 17, i['ledger_pnr'], sty_table_data)
                    sheet.write(row_data, 18, i['ledger_name'], sty_table_data)
                    sheet.write(row_data, 19, '', sty_table_data)
                    sheet.write(row_data, 20, i['currency_name'], sty_table_data_center)
                    sheet.write(row_data, 21, this_pnr_agent_nta_total, sty_amount)
                    sheet.write(row_data, 22, this_pnr_agent_commission, sty_amount)
                    sheet.write(row_data, 23, nta_total, sty_amount)
                    sheet.write(row_data, 24, commission, sty_amount)
                    sheet.write(row_data, 25, grand_total, sty_amount)
                    sheet.write(row_data, 26, '', sty_table_data)
                    sheet.write(row_data, 27, '', sty_amount)
                    sheet.write(row_data, 28, '', sty_table_data)
                    sheet.write(row_data, 29, '', sty_table_data)

                    # if current reservation so happened to be an airline type (provider type i mean)
                    # then we'll try to make summary if the reservation is considered as GDS book or not
                    # and count how many passenger within the reservation
                    if i['provider_type'].lower() == 'airline':
                    # check if reservation is airline
                        # will return the index of "same" data based on user
                        data_index = next(
                            (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['creator_id']), -1)
                        # if data is bigger than 0 = there's data within airline recaps
                        if data_index >= 0:
                            # then lets update the data, by adding
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
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
                                'id': i['creator_id'],
                                'name': i['create_by'],
                                'GDS': 0,
                                'pax_GDS': 0,
                                'non_GDS': 0,
                                'pax_non_GDS': 0
                            }
                            # add to airline_recaps list
                            airline_recaps.append(temp_dict)
                            # add the first data
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                                airline_recaps[data_index]['GDS'] += 1
                                airline_recaps[data_index]['pax_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_GDS'] += i['child']
                                airline_recaps[data_index]['pax_GDS'] += i['infant']
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                                airline_recaps[data_index]['pax_non_GDS'] += i['adult']
                                airline_recaps[data_index]['pax_non_GDS'] += i['child']
                                airline_recaps[data_index]['pax_non_GDS'] += i['infant']

                # else condition if pnr is not yet change
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

                sheet.write(row_data, 0, '', sty_table_data_center)
                sheet.write(row_data, 1, '', sty_table_data)
                sheet.write(row_data, 2, '', sty_table_data)
                sheet.write(row_data, 3, '', sty_table_data)
                sheet.write(row_data, 4, '', sty_table_data)
                sheet.write(row_data, 5, '', sty_table_data)
                sheet.write(row_data, 6, '', sty_table_data)
                sheet.write(row_data, 7, '', sty_table_data)
                sheet.write(row_data, 8, '', sty_table_data)
                sheet.write(row_data, 9, '', sty_date)
                sheet.write(row_data, 10, '', sty_table_data)
                sheet.write(row_data, 11, i['provider_name'], sty_table_data)
                sheet.write(row_data, 12, '', sty_amount)
                sheet.write(row_data, 13, '', sty_amount)
                sheet.write(row_data, 14, '', sty_amount)
                sheet.write(row_data, 15, '', sty_amount)
                sheet.write(row_data, 16, i['state'], sty_table_data)
                sheet.write(row_data, 17, i['ledger_pnr'], sty_table_data)
                sheet.write(row_data, 18, i['ledger_name'], sty_table_data)
                sheet.write(row_data, 19, '', sty_table_data)
                sheet.write(row_data, 20, '', sty_table_data_center)
                sheet.write(row_data, 21, '', sty_amount)
                sheet.write(row_data, 22, '', sty_amount)
                sheet.write(row_data, 23, '', sty_amount)
                sheet.write(row_data, 24, '', sty_amount)
                sheet.write(row_data, 25, '', sty_amount)
                sheet.write(row_data, 26, i['ledger_agent_name'], sty_table_data)
                if i['ledger_transaction_type'] == 3:
                    sheet.write(row_data, 27, i['debit'], sty_amount)
                    sheet.write(row_data, 28, '', sty_amount)
                else:
                    sheet.write(row_data, 27, '', sty_amount)
                    sheet.write(row_data, 28, i['debit'], sty_amount)
                sheet.write(row_data, 29, i['ledger_description'], sty_table_data)

            else:
            # current_number != iterate order number
                # set current order number to iterated number
                temp_order_number = i['order_number']
                current_pnr = i['ledger_pnr']

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


                # print the whole data of reservation
                sheet.write(row_data, 0, counter, sty_table_data_center)
                sheet.write(row_data, 1, i['provider_type'], sty_table_data)
                sheet.write(row_data, 2, i['carrier_name'], sty_table_data)
                sheet.write(row_data, 3, i['agent_type_name'], sty_table_data)
                sheet.write(row_data, 4, i['agent_name'], sty_table_data)
                sheet.write(row_data, 5, i['customer_parent_type_name'], sty_table_data)
                sheet.write(row_data, 6, i['customer_parent_name'], sty_table_data)
                sheet.write(row_data, 7, i['create_by'], sty_table_data)
                sheet.write(row_data, 8, i['issued_by'], sty_table_data)
                sheet.write(row_data, 9, i['issued_date'], sty_date)
                sheet.write(row_data, 10, i['agent_email'], sty_table_data)
                sheet.write(row_data, 11, i['provider_name'], sty_table_data)
                sheet.write(row_data, 12, i['order_number'], sty_amount)
                sheet.write(row_data, 13, i['adult'], sty_amount)
                sheet.write(row_data, 14, i['child'], sty_amount)
                sheet.write(row_data, 15, i['infant'], sty_amount)
                sheet.write(row_data, 16, i['state'], sty_table_data)
                sheet.write(row_data, 17, i['pnr'], sty_table_data)
                sheet.write(row_data, 18, i['ledger_name'], sty_table_data)
                sheet.write(row_data, 19, '', sty_table_data)
                sheet.write(row_data, 20, i['currency_name'], sty_table_data_center)
                sheet.write(row_data, 21, this_resv_agent_nta_total, sty_amount)
                sheet.write(row_data, 22, this_resv_agent_commission, sty_amount)
                sheet.write(row_data, 23, i['total_nta'], sty_amount)
                sheet.write(row_data, 24, i['total_commission'], sty_amount)
                sheet.write(row_data, 25, i['grand_total'], sty_amount)
                sheet.write(row_data, 26, '', sty_table_data)
                sheet.write(row_data, 27, '', sty_amount)
                sheet.write(row_data, 28, '', sty_table_data)
                sheet.write(row_data, 29, '', sty_table_data)

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

                sheet.write(row_data, 0, '', sty_table_data_center)
                sheet.write(row_data, 1, '', sty_table_data)
                sheet.write(row_data, 2, '', sty_table_data)
                sheet.write(row_data, 3, '', sty_table_data)
                sheet.write(row_data, 4, '', sty_table_data)
                sheet.write(row_data, 5, '', sty_table_data)
                sheet.write(row_data, 6, '', sty_table_data)
                sheet.write(row_data, 7, '', sty_table_data)
                sheet.write(row_data, 8, '', sty_table_data)
                sheet.write(row_data, 9, '', sty_date)
                sheet.write(row_data, 10, '', sty_table_data)
                sheet.write(row_data, 11, i['provider_name'], sty_table_data)
                sheet.write(row_data, 12, '', sty_amount)
                sheet.write(row_data, 13, '', sty_amount)
                sheet.write(row_data, 14, '', sty_amount)
                sheet.write(row_data, 15, '', sty_amount)
                sheet.write(row_data, 16, i['state'], sty_table_data)
                sheet.write(row_data, 17, i['ledger_pnr'], sty_table_data)
                sheet.write(row_data, 18, i['ledger_name'], sty_table_data)
                sheet.write(row_data, 19, '', sty_table_data)
                sheet.write(row_data, 20, i['currency_name'], sty_table_data_center)
                sheet.write(row_data, 21, this_pnr_agent_nta_total, sty_amount)
                sheet.write(row_data, 22, this_pnr_agent_commission, sty_amount)
                sheet.write(row_data, 23, nta_total, sty_amount)
                sheet.write(row_data, 24, commission, sty_amount)
                sheet.write(row_data, 25, grand_total, sty_amount)
                sheet.write(row_data, 26, '', sty_table_data)
                sheet.write(row_data, 27, '', sty_amount)
                sheet.write(row_data, 28, '', sty_amount)
                sheet.write(row_data, 29, '', sty_table_data)

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

                # add ledger info 1 row below (from the same line of data)
                sheet.write(row_data, 0, '', sty_table_data_center)
                sheet.write(row_data, 1, '', sty_table_data)
                sheet.write(row_data, 2, '', sty_table_data)
                sheet.write(row_data, 3, '', sty_table_data)
                sheet.write(row_data, 4, '', sty_table_data)
                sheet.write(row_data, 5, '', sty_table_data)
                sheet.write(row_data, 6, '', sty_table_data)
                sheet.write(row_data, 7, '', sty_table_data)
                sheet.write(row_data, 8, '', sty_table_data)
                sheet.write(row_data, 9, '', sty_date)
                sheet.write(row_data, 10, '', sty_table_data)
                sheet.write(row_data, 11, i['provider_name'], sty_table_data)
                sheet.write(row_data, 12, '', sty_amount)
                sheet.write(row_data, 13, '', sty_amount)
                sheet.write(row_data, 14, '', sty_amount)
                sheet.write(row_data, 15, '', sty_amount)
                sheet.write(row_data, 16, i['state'], sty_table_data)
                sheet.write(row_data, 17, i['ledger_pnr'], sty_table_data)
                sheet.write(row_data, 18, i['ledger_name'], sty_table_data)
                sheet.write(row_data, 19, '', sty_table_data)
                sheet.write(row_data, 20, '', sty_table_data_center)
                sheet.write(row_data, 21, '', sty_amount)
                sheet.write(row_data, 22, '', sty_amount)
                sheet.write(row_data, 23, '', sty_amount)
                sheet.write(row_data, 24, '', sty_amount)
                sheet.write(row_data, 25, '', sty_amount)
                sheet.write(row_data, 26, i['ledger_agent_name'], sty_table_data)
                if i['ledger_transaction_type'] == 3:
                    sheet.write(row_data, 27, i['debit'], sty_amount)
                    sheet.write(row_data, 28, '', sty_amount)
                else:
                    sheet.write(row_data, 27, '', sty_amount)
                    sheet.write(row_data, 28, i['debit'], sty_amount)
                sheet.write(row_data, 29, i['ledger_description'], sty_table_data)

            # lets recap
                # see line 189 for code explanation of this if provider airline
                if i['provider_type'].lower() == 'airline':
                    data_index = next((index for (index, d) in enumerate(airline_recaps) if d["id"] == i['creator_id']), -1)
                    if data_index >= 0:
                        if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
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
                            'id': i['creator_id'],
                            'name': i['create_by'],
                            'GDS': 0,
                            'pax_GDS': 0,
                            'non_GDS': 0,
                            'pax_non_GDS': 0
                        }
                        airline_recaps.append(temp_dict)
                        if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
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
                    data_index = next((index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['creator_id']),-1)

                    # if data index >= 0 then there's data with match user
                    # we only need to update the data
                    if data_index >= 0:
                        hotel_recaps[data_index]['counter'] += 1
                    else:
                        # if data is not yet exist then create some temp dictionary
                        temp_dict = {
                            'id': i['creator_id'],
                            'name': i['create_by'],
                            'counter': 1
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
                            (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['creator_id']), -1)
                        if data_index >= 0:
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                                airline_recaps[data_index]['GDS'] += 1
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1
                        else:
                            temp_dict = {
                                'id': i['creator_id'],
                                'name': i['create_by'],
                                'pax_GDS': 0,
                                'GDS': 0,
                                'non_GDS': 0,
                                'pax_non_GDS': 0
                            }
                            airline_recaps.append(temp_dict)
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                                airline_recaps[data_index]['GDS'] += 1
                            else:
                                airline_recaps[data_index]['non_GDS'] += 1

                    # and see line 460 for if hotel code explanation
                    if i['provider_type'].lower() == 'hotel':
                        data_index = next(
                            (index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['creator_id']), -1)
                        if data_index >= 0:
                            hotel_recaps[data_index]['counter'] += 1
                        else:
                            temp_dict = {
                                'id': i['creator_id'],
                                'name': i['create_by'],
                                'counter': 1
                            }
                            hotel_recaps.append(temp_dict)


        row_data += 1
        # this is writing empty string, to print the bottom border
        sty_table_data_center = style.table_data_center_border
        sty_table_data = style.table_data_border
        sty_datetime = style.table_data_datetime_border
        sty_date = style.table_data_date_border
        sty_amount = style.table_data_amount_border
        sheet.write(row_data, 0, '', sty_table_data_center)
        sheet.write(row_data, 1, '', sty_table_data)
        sheet.write(row_data, 2, '', sty_table_data)
        sheet.write(row_data, 3, '', sty_table_data)
        sheet.write(row_data, 4, '', sty_table_data)
        sheet.write(row_data, 5, '', sty_table_data)
        sheet.write(row_data, 6, '', sty_table_data)
        sheet.write(row_data, 7, '', sty_table_data)
        sheet.write(row_data, 8, '', sty_table_data)
        sheet.write(row_data, 9, '', sty_date)
        sheet.write(row_data, 10, '', sty_table_data)
        sheet.write(row_data, 11, '', sty_table_data)
        sheet.write(row_data, 12, '', sty_amount)
        sheet.write(row_data, 13, '', sty_amount)
        sheet.write(row_data, 14, '', sty_amount)
        sheet.write(row_data, 15, '', sty_amount)
        sheet.write(row_data, 16, '', sty_table_data)
        sheet.write(row_data, 17, '', sty_table_data)
        sheet.write(row_data, 18, '', sty_table_data)
        sheet.write(row_data, 19, '', sty_table_data)
        sheet.write(row_data, 20, '', sty_table_data_center)
        sheet.write(row_data, 21, '', sty_amount)
        sheet.write(row_data, 22, '', sty_amount)
        sheet.write(row_data, 23, '', sty_amount)
        sheet.write(row_data, 24, '', sty_amount)
        sheet.write(row_data, 25, '', sty_amount)
        sheet.write(row_data, 26, '', sty_table_data)
        sheet.write(row_data, 27, '', sty_amount)
        sheet.write(row_data, 28, '', sty_table_data)
        sheet.write(row_data, 29, '', sty_table_data)

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
            for i in hotel_recaps:
                row_data += 1
                sheet.write(row_data, 1, i['name'], sty_table_data)
                sheet.write(row_data, 2, i['counter'], sty_table_data)
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
