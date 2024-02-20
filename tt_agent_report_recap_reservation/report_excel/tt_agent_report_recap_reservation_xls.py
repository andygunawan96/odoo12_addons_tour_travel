from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AgentReportRecapReservationXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.reservation.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_recap_reservation.agent_report_recap']._prepare_values(data['form'])  # get values

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
        sheet.write('E9', 'Issued Date', style.table_head_center)
        sheet.write('F9', 'Agent Email', style.table_head_center)
        sheet.write('G9', 'Provider', style.table_head_center)
        sheet.write('H9', 'Order Number', style.table_head_center)
        # sheet.write('I9', 'Origin', style.table_head_center)
        # sheet.write('J9', 'Sector', style.table_head_center)
        sheet.write('I9', 'Adult', style.table_head_center)
        sheet.write('J9', 'Child', style.table_head_center)
        sheet.write('K9', 'Infant', style.table_head_center)
        sheet.write('L9', 'State', style.table_head_center)
        sheet.write('M9', 'PNR', style.table_head_center)
        sheet.write('N9', 'Booking State', style.table_head_center)
        sheet.write('O9', 'Currency', style.table_head_center)
        sheet.write('P9', 'NTA Amount', style.table_head_center)
        sheet.write('Q9', 'Total Commission', style.table_head_center)
        sheet.write('R9', 'Commission Booker', style.table_head_center)
        sheet.write('S9', 'Upsell', style.table_head_center)
        sheet.write('T9', 'Grand Total', style.table_head_center)
        sheet.merge_range('U9:V9', 'Keterangan', style.table_head_center)


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
        sheet.set_column('H:V', 15)

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
        channel_pricing = values['third_lines']
        #proceed the data

        filtered_data = []
        temp_order_number = ''
        counter = 0
        for i in datas:
            if temp_order_number != i['order_number']:
                #set checker for order number
                temp_order_number = i['order_number']
                upsell = 0
                for svc_csc in channel_pricing:
                    if svc_csc['order_number'] == temp_order_number and isinstance(svc_csc['service_charge_amount'], float): #check order number sama & upsell int
                        upsell += svc_csc['service_charge_amount']
                #get pnr list
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
                sheet.write(row_data, 4, i['issued_date'], sty_date)
                sheet.write(row_data, 5, i['agent_email'], sty_table_data)
                sheet.write(row_data, 6, i['provider_alias'], sty_table_data)
                sheet.write(row_data, 7, i['order_number'], sty_amount)
                sheet.write(row_data, 8, i['adult'], sty_amount)
                sheet.write(row_data, 9, i['child'], sty_amount)
                sheet.write(row_data, 10, i['infant'], sty_amount)
                sheet.write(row_data, 11, i['state'], sty_table_data)
                sheet.write(row_data, 12, i['pnr'], sty_table_data)
                sheet.write(row_data, 13, '', sty_table_data)
                sheet.write(row_data, 14, i['currency_name'], sty_table_data_center)
                sheet.write(row_data, 15, i['total_nta'], sty_amount)
                sheet.write(row_data, 16, i['total_commission'], sty_amount)
                sheet.write(row_data, 17, i.get('commission_booker', 0), sty_amount)
                sheet.write(row_data, 18, upsell, sty_amount)
                sheet.write(row_data, 19, i['grand_total'], sty_amount)
                sheet.write(row_data, 20, '', sty_table_data)
                sheet.write(row_data, 21, '', sty_amount)

                # filtered data
                filtered_data = []

                for j in pnr_list:
                    if j == '':
                        continue
                    temp_charge = list(filter(lambda x: x['order_number'] == i['order_number'] and x['booking_pnr'] == j, service_charge))
                    temp_book = list(filter(lambda x: x['order_number'] == i['order_number'] and x['ledger_pnr'] == j, datas))
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
                    sheet.write(row_data, 4, '', sty_date)
                    sheet.write(row_data, 5, '', sty_table_data)
                    if temp_book:
                        sheet.write(row_data, 6, temp_book[0]['ledger_provider'], sty_table_data)
                    else:
                        sheet.write(row_data, 6, '', sty_table_data)
                    sheet.write(row_data, 7, '', sty_amount)
                    sheet.write(row_data, 8, '', sty_amount)
                    sheet.write(row_data, 9, '', sty_amount)
                    sheet.write(row_data, 10, '', sty_amount)
                    sheet.write(row_data, 11, i['state'], sty_table_data)
                    sheet.write(row_data, 12, j, sty_table_data)
                    sheet.write(row_data, 13, booking_state, sty_table_data)
                    sheet.write(row_data, 14, '', sty_table_data_center)
                    sheet.write(row_data, 15, nta_total, sty_amount)
                    sheet.write(row_data, 16, commission, sty_amount)
                    sheet.write(row_data, 17, '', sty_amount)
                    sheet.write(row_data, 18, '', sty_amount)
                    sheet.write(row_data, 19, grand_total, sty_amount)
                    sheet.write(row_data, 20, '', sty_table_data)
                    sheet.write(row_data, 21, '', sty_amount)

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
                            sheet.write(row_data, 4, '', sty_date)
                            sheet.write(row_data, 5, '', sty_table_data)
                            sheet.write(row_data, 6, i['ledger_provider'], sty_table_data)
                            sheet.write(row_data, 7, '', sty_amount)
                            sheet.write(row_data, 8, '', sty_amount)
                            sheet.write(row_data, 9, '', sty_amount)
                            sheet.write(row_data, 10, '', sty_amount)
                            sheet.write(row_data, 11, i['state'], sty_table_data)
                            sheet.write(row_data, 12, '', sty_table_data)
                            sheet.write(row_data, 13, '', sty_table_data)
                            sheet.write(row_data, 14, '', sty_table_data_center)
                            sheet.write(row_data, 15, '', sty_amount)
                            sheet.write(row_data, 16, '', sty_amount)
                            sheet.write(row_data, 17, '', sty_amount)
                            sheet.write(row_data, 18, '', sty_amount)
                            sheet.write(row_data, 19, '', sty_amount)
                            sheet.write(row_data, 20, k['ledger_agent_name'], sty_table_data)
                            sheet.write(row_data, 21, k['debit'], sty_amount)

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
        sheet.write(row_data, 4, '', sty_date)
        sheet.write(row_data, 5, '', sty_table_data)
        sheet.write(row_data, 6, '', sty_table_data)
        sheet.write(row_data, 7, '', sty_amount)
        sheet.write(row_data, 8, '', sty_amount)
        sheet.write(row_data, 9, '', sty_amount)
        sheet.write(row_data, 10, '', sty_amount)
        sheet.write(row_data, 11, '', sty_table_data)
        sheet.write(row_data, 12, '', sty_table_data)
        sheet.write(row_data, 13, '', sty_table_data)
        sheet.write(row_data, 14, '', sty_table_data_center)
        sheet.write(row_data, 15, '', sty_amount)
        sheet.write(row_data, 16, '', sty_amount)
        sheet.write(row_data, 17, '', sty_amount)
        sheet.write(row_data, 18, '', sty_amount)
        sheet.write(row_data, 19, '', sty_amount)
        sheet.write(row_data, 20, '', sty_table_data)
        sheet.write(row_data, 21, '', sty_amount)
            #proceed
        workbook.close()

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
