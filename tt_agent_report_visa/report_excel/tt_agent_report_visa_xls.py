from odoo import models, api, fields, _
from odoo12_addons_tour_travel.tt_agent_report.report import tools_excel
from io import StringIO, BytesIO
import io
import xlsxwriter
import base64
from datetime import datetime


class AgentReportVisa(models.TransientModel):
    _inherit = 'tt.agent.report.visa.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_visa.agent_report_visa']._prepare_values(data['form'])  # get values

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:R2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:R4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('Q5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(10, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.merge_range('A9:A10', 'No.', style.table_head_center)
        sheet.merge_range('B9:B10', 'Order Number', style.table_head_center)
        sheet.merge_range('C9:C10', 'Contact Person', style.table_head_center)
        sheet.merge_range('D9:D10', 'Country', style.table_head_center)
        sheet.merge_range('E9:E10', 'Visa Type', style.table_head_center)
        sheet.merge_range('F9:F10', 'Departure Date', style.table_head_center)
        sheet.merge_range('G9:G10', 'Immigration Consulate', style.table_head_center)
        sheet.merge_range('H9:H10', 'Passenger Name', style.table_head_center)
        sheet.merge_range('I9:I10', 'Passenger Age', style.table_head_center)
        sheet.merge_range('J9:J10', 'Issued By', style.table_head_center)
        sheet.merge_range('K9:K10', 'Issued Date', style.table_head_center)
        sheet.merge_range('L9:L10', 'In Process Date', style.table_head_center)
        sheet.merge_range('M9:M10', 'Ready Date', style.table_head_center)
        sheet.merge_range('N9:N10', 'Done Date', style.table_head_center)
        sheet.merge_range('O9:O10', 'Commission', style.table_head_center)
        sheet.merge_range('P9:P10', 'Grand Total', style.table_head_center)
        sheet.merge_range('Q9:Q10', 'NTA Amount', style.table_head_center)
        sheet.merge_range('R9:R10', 'State', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 14)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 12)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:H', 30)
        sheet.set_column('I:I', 12)
        sheet.set_column('J:J', 30)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 14)
        sheet.set_column('P:P', 14)
        sheet.set_column('Q:Q', 14)
        sheet.set_column('R:R', 10)

        # ======= TABLE DATA ==========
        row_data = 9
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

            sheet.write(row_data, 0, row_data - 9, sty_table_data_center)  # No.
            sheet.write(row_data, 1, rec['name'], sty_table_data)  # Order Number
            sheet.write(row_data, 2, rec['contact_person'], sty_table_data_center)  # Contact Person
            sheet.write(row_data, 3, rec['country_name'], sty_table_data_center)  # Country
            sheet.write(row_data, 4, rec['visa_type'], sty_table_data_center)  # Visa Type
            sheet.write(row_data, 5,
                        datetime.strptime(rec['departure_date'][:10], "%Y-%m-%d") if rec['departure_date'] else '',
                        sty_date)  # Departure Date
            sheet.write(row_data, 6, rec['immigration_consulate'], sty_table_data)  # Immigration Consulate
            sheet.write(row_data, 7, rec['pass_name'], sty_table_data)  # Passenger Name
            sheet.write(row_data, 8, rec['age'], sty_table_data)  # Passenger Age
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
            sheet.write(row_data, 17, rec['state'], sty_table_data_center)  # State
            sheet.set_row(row_data, row_height)  # Set new row

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Visa Report.xlsx', 'file_output': base64.encodestring(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
