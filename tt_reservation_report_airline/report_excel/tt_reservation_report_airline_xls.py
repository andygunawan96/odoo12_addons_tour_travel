from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime

class ReservationReportAirlineXls(models.TransientModel):
    _inherit = 'tt.reservation.report.airline.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_reservation_report_airline.reservation_rpt_airline']._prepare_valued(data['form'])

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

        sheet.write('B9', 'Order Number', style.table_head_center)
        sheet.write('C9', 'State', style.table_head_center)
        sheet.write('D9', 'Issued date', style.table_head_center)
        sheet.write('E9', 'Booker name', style.table_head_center)
        sheet.write('F9', 'Adult', style.table_head_center)
        sheet.write('G9', 'Child', style.table_head_center)
        sheet.write('H9', 'Infant', style.table_head_center)
        sheet.write('I9', 'Departure Date', style.table_head_center)
        sheet.write('J9', 'Return Date', style.table_head_center)
        sheet.write('K9', 'Provider', style.table_head_center)
        sheet.write('L9', 'Carrier', style.table_head_center)
        sheet.write('M9', 'Departure', style.table_head_center)
        sheet.write('N9', 'Departure City', style.table_head_center)
        sheet.write('O9', 'Departure Country', style.table_head_center)
        sheet.write('P9', 'Destination', style.table_head_center)
        sheet.write('Q9', 'Destination City', style.table_head_center)
        sheet.write('R9', 'Destination Country', style.table_head_center)
        sheet.write('S9', 'PNR', style.table_head_center)
        sheet.write('T9', 'Currency', style.table_head_center)
        sheet.write('U9', 'Total', style.table_head_center)
        sheet.merge_range('V9:W9', 'Detail', style.table_head_center)

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
        sheet.set_column('H:W', 15)

        row_data = 8
        datas = values['lines']
        counter = 0
        airline_number = ''
        for i in datas:

            if airline_number != i['airline_number']:
                airline_number = i['airline_number']
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

                #print the title
                sheet.write(row_data, 0, counter, sty_table_data_center)
                sheet.write(row_data, 1, i['airline_number'], sty_table_data)
                sheet.write(row_data, 2, i['airline_state'], sty_table_data)
                sheet.write(row_data, 3, i['airline_issued_date'], sty_date)
                sheet.write(row_data, 4, i['booker_name'], sty_table_data)
                sheet.write(row_data, 5, i['adult'], sty_amount)
                sheet.write(row_data, 6, i['child'], sty_amount)
                sheet.write(row_data, 7, i['infant'], sty_amount)
                sheet.write(row_data, 8, i['departure_date'], sty_date)
                sheet.write(row_data, 9, i['return_date'], sty_date)
                sheet.write(row_data, 10, i['provider_name'], sty_table_data)
                sheet.write(row_data, 11, i['carrier_name'], sty_table_data)
                sheet.write(row_data, 12, i['departure_name'], sty_table_data)
                sheet.write(row_data, 13, i['departure_city'], sty_table_data)
                sheet.write(row_data, 14, i['departure_country'], sty_table_data)
                sheet.write(row_data, 15, i['destination_name'], sty_table_data)
                sheet.write(row_data, 16, i['destination_city'], sty_table_data)
                sheet.write(row_data, 17, i['destination_country'], sty_table_data)
                sheet.write(row_data, 18, i['airline_pnr'], sty_table_data)
                sheet.write(row_data, 19, i['currency_name'], sty_table_data)
                sheet.write(row_data, 20, i['total_fare'], sty_amount)
                sheet.write(row_data, 21, '', sty_table_data)
                sheet.write(row_data, 22, '', sty_table_data)

                #loop print
                filtered_data = filter(lambda x: x['airline_number'] == i['airline_number'], datas)
                for j in filtered_data:
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

                    # print the title
                    sheet.write(row_data, 0, '', sty_table_data_center)
                    sheet.write(row_data, 1, '', sty_table_data)
                    sheet.write(row_data, 2, '', sty_table_data)
                    sheet.write(row_data, 3, '', sty_date)
                    sheet.write(row_data, 4, '', sty_table_data)
                    sheet.write(row_data, 5, '', sty_amount)
                    sheet.write(row_data, 6, '', sty_amount)
                    sheet.write(row_data, 7, '', sty_amount)
                    sheet.write(row_data, 8, '', sty_date)
                    sheet.write(row_data, 9, '', sty_date)
                    sheet.write(row_data, 10, '', sty_table_data)
                    sheet.write(row_data, 11, '', sty_table_data)
                    sheet.write(row_data, 12, '', sty_table_data)
                    sheet.write(row_data, 13, '', sty_table_data)
                    sheet.write(row_data, 14, '', sty_table_data)
                    sheet.write(row_data, 15, '', sty_table_data)
                    sheet.write(row_data, 16, '', sty_table_data)
                    sheet.write(row_data, 17, '', sty_table_data)
                    sheet.write(row_data, 18, '', sty_table_data)
                    sheet.write(row_data, 19, i['currency_name'], sty_table_data)
                    sheet.write(row_data, 20, '', sty_table_data)
                    sheet.write(row_data, 21, j['charge_type'], sty_amount)
                    sheet.write(row_data, 22, j['service_charge_total'], sty_amount)

            else:
                continue

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Report Airline.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
