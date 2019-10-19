from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime
from ...tools.variables import BOOKING_STATE_STR


class AgentReportPassportXls(models.TransientModel):
    _inherit = 'tt.agent.report.passport.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_passport.agent_report_passport']._prepare_values(data['form'])  # get values

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:R2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:R4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('Q5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(10, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Order Number', style.table_head_center)
        sheet.write('C9', 'Contact Person', style.table_head_center)
        sheet.write('D9', 'Country', style.table_head_center)
        sheet.write('E9', 'Passport Type', style.table_head_center)
        sheet.write('F9', 'Departure Date', style.table_head_center)
        sheet.write('G9', 'Immigration Consulate', style.table_head_center)
        sheet.write('H9', 'Passenger Name', style.table_head_center)
        sheet.write('I9', 'Passenger Age', style.table_head_center)
        sheet.write('J9', 'Issued By', style.table_head_center)
        sheet.write('K9', 'Issued Date', style.table_head_center)
        sheet.write('L9', 'In Process Date', style.table_head_center)
        sheet.write('M9', 'Ready Date', style.table_head_center)
        sheet.write('N9', 'Done Date', style.table_head_center)
        sheet.write('O9', 'Commission', style.table_head_center)
        sheet.write('P9', 'Grand Total', style.table_head_center)
        sheet.write('Q9', 'NTA Amount', style.table_head_center)
        sheet.write('R9', 'State', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 4)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 12)
        sheet.set_column('E:E', 10)
        sheet.set_column('F:F', 11)
        sheet.set_column('G:G', 10)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 9)
        sheet.set_column('J:J', 13)
        sheet.set_column('K:K', 13)
        sheet.set_column('L:L', 13)
        sheet.set_column('M:M', 13)
        sheet.set_column('N:N', 13)
        sheet.set_column('O:O', 11)
        sheet.set_column('P:P', 11)
        sheet.set_column('Q:Q', 11)
        sheet.set_column('R:R', 8)

        # ======= TABLE DATA ==========
        row_data = 8
        for rec in values['lines']:
            row_data += 1
            sty_table_data_center = style.table_data_center  # data di table memiliki align 'center'
            sty_table_data = style.table_data  # data di table memiliki align 'left'
            sty_datetime = style.table_data_datetime  # style content untuk datetime
            sty_date = style.table_data_date  # style content untuk date
            sty_amount = style.table_data_amount  # style content untuk amount
            if row_data % 2 == 1:  # Why need even style?
                sty_table_data_center = style.table_data_center_even
                sty_table_data = style.table_data_even
                sty_datetime = style.table_data_datetime_even
                sty_date = style.table_data_date_even
                sty_amount = style.table_data_amount_even

            sheet.write(row_data, 0, row_data - 8, sty_table_data_center)  # No.
            sheet.write(row_data, 1, rec['name'], sty_table_data)  # Order Number
            sheet.write(row_data, 2, rec['contact_person'], sty_table_data_center)  # Contact Person
            sheet.write(row_data, 3, rec['country_name'], sty_table_data_center)  # Country
            sheet.write(row_data, 4, rec['passport_type'], sty_table_data_center)  # Passport Type
            sheet.write(row_data, 5,
                        datetime.strptime(rec['departure_date'][:10], "%Y/%m/%d") if rec['departure_date'] else '',
                        sty_date)  # Departure Date
            sheet.write(row_data, 6, rec['immigration_consulate'], sty_table_data)  # Immigration Consulate
            sheet.write(row_data, 7, rec['pass_name'], sty_table_data)  # Passenger Name
            sheet.write(row_data, 8, rec['age'], sty_table_data)  # Passenger Age | rec['age']
            sheet.write(row_data, 9, rec['issued_name'], sty_table_data)  # Issued By
            if rec['issued_date']:  # Issued Date
                sheet.write(row_data, 10, rec['issued_date'].strftime("%Y-%m-%d %H:%M:%S"), sty_datetime)
            else:
                sheet.write(row_data, 10, '', sty_datetime)
            if rec['in_process_date']:  # In Process Date
                sheet.write(row_data, 11, rec['in_process_date'].strftime("%Y-%m-%d %H:%M:%S"), sty_datetime)
            else:
                sheet.write(row_data, 11, '', sty_datetime)
            if rec['ready_date']:  # Ready Date
                sheet.write(row_data, 12, rec['ready_date'].strftime("%Y-%m-%d %H:%M:%S"), sty_datetime)
            else:
                sheet.write(row_data, 12, '', sty_datetime)
            if rec['done_date']:  # Done Date
                sheet.write(row_data, 13, rec['done_date'].strftime("%Y-%m-%d %H:%M:%S"), sty_datetime)
            else:
                sheet.write(row_data, 13, '', sty_datetime)
            sheet.write(row_data, 14, rec['commission'], sty_table_data_center)  # Commission
            sheet.write(row_data, 15, rec['total'], sty_table_data_center)  # Grand Total
            sheet.write(row_data, 16, rec['total_nta'], sty_table_data_center)  # NTA Amount
            sheet.write(row_data, 17, BOOKING_STATE_STR[rec['state']] if rec['state'] else '', sty_table_data_center)  # State
            sheet.set_row(row_data, row_height)  # Set new row

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Passport Report.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
