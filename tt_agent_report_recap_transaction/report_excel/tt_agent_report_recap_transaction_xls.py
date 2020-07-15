from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime

class AgentReportRecapTransactionXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.transaction.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_recap_transaction.agent_report_recap']._prepare_values(
            data['form'])  # get values

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Booking Type', style.table_head_center)
        sheet.write('C9', 'Agent Type', style.table_head_center)
        sheet.write('D9', 'Agent Name', style.table_head_center)
        sheet.write('E9', 'create by', style.table_head_center)
        sheet.write('F9', 'issued by', style.table_head_center)
        sheet.write('G9', 'Issued Date', style.table_head_center)
        sheet.write('H9', 'Agent Email', style.table_head_center)
        sheet.write('I9', 'Provider', style.table_head_center)
        sheet.write('J9', 'Order Number', style.table_head_center)
        # sheet.write('I9', 'Origin', style.table_head_center)
        # sheet.write('J9', 'Sector', style.table_head_center)
        sheet.write('K9', 'Adult', style.table_head_center)
        sheet.write('L9', 'Child', style.table_head_center)
        sheet.write('M9', 'Infant', style.table_head_center)
        sheet.write('N9', 'State', style.table_head_center)
        sheet.write('O9', 'PNR', style.table_head_center)
        sheet.write('P9', 'Ledger Reference', style.table_head_center)
        sheet.write('Q9', 'Booking State', style.table_head_center)
        sheet.write('R9', 'Currency', style.table_head_center)
        sheet.write('S9', 'NTA Amount', style.table_head_center)
        sheet.write('T9', 'Total Commission', style.table_head_center)
        sheet.write('U9', 'Grand Total', style.table_head_center)
        sheet.merge_range('V9:W9', 'Keterangan', style.table_head_center)

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
        sheet.set_column('A:A', 6)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:F', 15)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:S', 15)

        # ============ void start() ======================
        row_data = 8
        first_data = True
        counter = 1
        multi_pnr = False
        temp_pnr = ''
        is_border = False
        last_data = ''
        pnr_list = []
        pnr = ''
        order_number = ''
        datas = values['lines']
        service_charge = values['second_lines']
        #proceed the data
        filtered_data = []
        temp_order_number = ''
        counter = 0
        airline_recaps = []
        hotel_recaps = []
        offline_recaps = []
        for i in datas:
            if temp_order_number != i['order_number']:
                #set checker for order number
                temp_order_number = i['order_number']
                parent_temp_charge = list(filter(lambda x: x['order_number'] == i['order_number'], service_charge))
                for x in parent_temp_charge:
                    if x['ledger_created'] == True:
                        # get pnr list
                        try:
                            pnr_list = i['pnr'].split(", ")
                        except:
                            if i['provider_type'].lower() == "offline":
                                pnr_list = []
                            else:
                                pnr_list = []
                                pass

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
                        # print first data
                        sheet.write(row_data, 0, counter, sty_table_data_center)
                        sheet.write(row_data, 1, i['provider_type'], sty_table_data)
                        sheet.write(row_data, 2, i['agent_type_name'], sty_table_data)
                        sheet.write(row_data, 3, i['agent_name'], sty_table_data)
                        sheet.write(row_data, 4, i['create_by'], sty_table_data)
                        sheet.write(row_data, 5, i['issued_by'], sty_table_data)
                        sheet.write(row_data, 6, i['issued_date'], sty_date)
                        sheet.write(row_data, 7, i['agent_email'], sty_table_data)
                        sheet.write(row_data, 8, i['provider_name'], sty_table_data)
                        sheet.write(row_data, 9, i['order_number'], sty_amount)
                        sheet.write(row_data, 10, i['adult'], sty_amount)
                        sheet.write(row_data, 11, i['child'], sty_amount)
                        sheet.write(row_data, 12, i['infant'], sty_amount)
                        sheet.write(row_data, 13, i['state'], sty_table_data)
                        sheet.write(row_data, 14, i['pnr'], sty_table_data)
                        sheet.write(row_data, 15, i['ledger_name'], sty_table_data)
                        sheet.write(row_data, 16, '', sty_table_data)
                        sheet.write(row_data, 17, i['currency_name'], sty_table_data_center)
                        sheet.write(row_data, 18, i['total_nta'], sty_amount)
                        sheet.write(row_data, 19, i['total_commission'], sty_amount)
                        sheet.write(row_data, 20, i['grand_total'], sty_amount)
                        sheet.write(row_data, 21, '', sty_table_data)
                        sheet.write(row_data, 22, '', sty_amount)

                        # filtered data
                        filtered_data = []

                        for j in pnr_list:
                            if j == '':
                                continue
                            temp_charge = list(filter(lambda x: x['booking_pnr'] == j, parent_temp_charge))
                            temp_book = list(
                                filter(lambda x: x['order_number'] == i['order_number'] and x['ledger_pnr'] == j,
                                       datas))
                            temp_dict = {
                                'order_number': i['order_number'],
                                'pnr': j
                            }
                            grand_total = 0
                            nta_total = 0
                            commission = 0
                            if temp_dict not in filtered_data:
                                filtered_data.append(temp_dict)
                                try:
                                    booking_state = temp_charge[0]['booking_state']
                                except:
                                    booking_state = ''
                                for k in temp_charge:
                                    if k['booking_charge_type'] == 'RAC':
                                        commission -= k['booking_charge_total']
                                        nta_total += k['booking_charge_total']
                                    else:
                                        if k['booking_charge_type'] != '' and k['booking_charge_total']:
                                            nta_total += k['booking_charge_total']
                                grand_total = nta_total + commission

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
                            sheet.write(row_data, 6, '', sty_date)
                            sheet.write(row_data, 7, '', sty_table_data)
                            if temp_book:
                                sheet.write(row_data, 8, temp_book[0]['ledger_provider'], sty_table_data)
                            else:
                                sheet.write(row_data, 8, '', sty_table_data)
                            sheet.write(row_data, 9, '', sty_amount)
                            sheet.write(row_data, 10, '', sty_amount)
                            sheet.write(row_data, 11, '', sty_amount)
                            sheet.write(row_data, 12, '', sty_amount)
                            sheet.write(row_data, 13, i['state'], sty_table_data)
                            sheet.write(row_data, 14, j, sty_table_data)
                            sheet.write(row_data, 15, '', sty_table_data_center)
                            sheet.write(row_data, 16, booking_state, sty_table_data)
                            sheet.write(row_data, 17, '', sty_table_data_center)
                            sheet.write(row_data, 18, nta_total, sty_amount)
                            sheet.write(row_data, 19, commission, sty_amount)
                            sheet.write(row_data, 20, grand_total, sty_amount)
                            sheet.write(row_data, 21, '', sty_table_data)
                            sheet.write(row_data, 22, '', sty_amount)

                            for k in temp_book:
                                if k['ledger_transaction_type'] == 3:
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
                                    sheet.write(row_data, 6, '', sty_date)
                                    sheet.write(row_data, 7, '', sty_table_data)
                                    sheet.write(row_data, 8, '', sty_table_data)
                                    sheet.write(row_data, 9, '', sty_amount)
                                    sheet.write(row_data, 10, '', sty_amount)
                                    sheet.write(row_data, 11, '', sty_amount)
                                    sheet.write(row_data, 12, '', sty_amount)
                                    sheet.write(row_data, 13, i['state'], sty_table_data)
                                    sheet.write(row_data, 14, '', sty_table_data)
                                    sheet.write(row_data, 15, '', sty_table_data)
                                    sheet.write(row_data, 16, '', sty_table_data_center)
                                    sheet.write(row_data, 17, '', sty_table_data_center)
                                    sheet.write(row_data, 18, '', sty_amount)
                                    sheet.write(row_data, 19, '', sty_amount)
                                    sheet.write(row_data, 20, '', sty_amount)
                                    sheet.write(row_data, 21, k['ledger_agent_name'], sty_table_data)
                                    sheet.write(row_data, 22, k['debit'], sty_amount)
                        break;
                    else:
                        continue

                #lets recap
                if i['provider_type'].lower() == 'airline':
                    data_index = next((index for (index, d) in enumerate(airline_recaps) if d["id"] == i['creator_id']), -1)
                    if data_index >= 0:
                        if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                            airline_recaps[data_index]['amadeus'] += 1
                        else:
                            airline_recaps[data_index]['non-amadeus'] += 1
                    else:
                        temp_dict = {
                            'id': i['creator_id'],
                            'name': i['create_by'],
                            'amadeus': 0,
                            'non-amadeus': 0
                        }
                        airline_recaps.append(temp_dict)
                        if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                            airline_recaps[data_index]['amadeus'] += 1
                        else:
                            airline_recaps[data_index]['non-amadeus'] += 1
                if i['provider_type'].lower() == 'hotel':
                    data_index = next((index for (index, d) in enumerate(hotel_recaps) if d["id"] == i['creator_id']),-1)
                    if data_index >= 0:
                        hotel_recaps[data_index]['counter'] += 1
                    else:
                        temp_dict = {
                            'id': i['creator_id'],
                            'name': i['create_by'],
                            'counter': 1
                        }
                        hotel_recaps.append(temp_dict)
                if i['provider_type'].lower() == 'offline':
                    if i['offline_provider'].lower() == 'airline':
                        data_index = next(
                            (index for (index, d) in enumerate(airline_recaps) if d["id"] == i['creator_id']), -1)
                        if data_index >= 0:
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                                airline_recaps[data_index]['amadeus'] += 1
                            else:
                                airline_recaps[data_index]['non-amadeus'] += 1
                        else:
                            temp_dict = {
                                'id': i['creator_id'],
                                'name': i['create_by'],
                                'amadeus': 0,
                                'non-amadeus': 0
                            }
                            airline_recaps.append(temp_dict)
                            if i['provider_name'] and 'amadeus' in i['provider_name'] or 'sabre' in i['provider_name']:
                                airline_recaps[data_index]['amadeus'] += 1
                            else:
                                airline_recaps[data_index]['non-amadeus'] += 1
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
        sheet.write(row_data, 6, '', sty_date)
        sheet.write(row_data, 7, '', sty_table_data)
        sheet.write(row_data, 8, '', sty_table_data)
        sheet.write(row_data, 9, '', sty_amount)
        sheet.write(row_data, 10, '', sty_amount)
        sheet.write(row_data, 11, '', sty_amount)
        sheet.write(row_data, 12, '', sty_amount)
        sheet.write(row_data, 13, '', sty_table_data)
        sheet.write(row_data, 14, '', sty_table_data)
        sheet.write(row_data, 15, '', sty_table_data)
        sheet.write(row_data, 16, '', sty_table_data_center)
        sheet.write(row_data, 17, '', sty_amount)
        sheet.write(row_data, 18, '', sty_amount)
        sheet.write(row_data, 19, '', sty_amount)
        sheet.write(row_data, 20, '', sty_table_data)
        sheet.write(row_data, 21, '', sty_amount)
        sheet.write(row_data, 22, '', sty_amount)

        row_data += 4
        if values['data_form']['provider_type'] == 'airline' or values['data_form']['provider_type'] == 'all' or values['data_form']['provider_type'] == 'offline':
            sheet.write(row_data, 0, 'AIRLINES', style.table_head_center)
            sheet.write(row_data, 1, 'Nama', style.table_head_center)
            sheet.write(row_data, 2, 'GDS', style.table_head_center)
            sheet.write(row_data, 3, 'Non-GDS', style.table_head_center)
            for i in airline_recaps:
                row_data += 1
                sheet.write(row_data, 1, i['name'], sty_table_data)
                sheet.write(row_data, 2, i['amadeus'], sty_table_data)
                sheet.write(row_data, 3, i['non-amadeus'], sty_table_data)
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
        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Agent Report Transaction Recap.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
