from odoo import models, _
from odoo12_addons_tour_travel.tt_agent_report.report import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AgentReportOfflineXls(models.TransientModel):
    _inherit = 'tt.agent.report.offline.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_offline.agent_report_offline']._prepare_values(data['form'])  # get values

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
        sheet.merge_range('A9:A10', 'No.', style.table_head_center)
        sheet.merge_range('B9:B10', 'Date', style.table_head_center)
        sheet.merge_range('C9:C10', 'Order Number', style.table_head_center)
        sheet.merge_range('D9:D10', 'Agent Name', style.table_head_center)
        sheet.merge_range('E9:E10', 'Contact Person', style.table_head_center)
        sheet.merge_range('F9:F10', 'Provider Type', style.table_head_center)
        sheet.merge_range('G9:G10', 'Provider', style.table_head_center)
        sheet.merge_range('H9:H10', 'PNR', style.table_head_center)
        sheet.merge_range('I9:I10', 'Description', style.table_head_center)
        sheet.merge_range('J9:J10', 'Confirm Date', style.table_head_center)
        sheet.merge_range('K9:K10', 'Confirm By', style.table_head_center)
        sheet.merge_range('L9:L10', 'Issued Date', style.table_head_center)
        sheet.merge_range('M9:M10', 'Issued By', style.table_head_center)
        sheet.merge_range('N9:N10', 'Total', style.table_head_center)
        sheet.merge_range('O9:O10', 'Agent Commission', style.table_head_center)
        sheet.merge_range('P9:P10', 'NTA Amount', style.table_head_center)
        sheet.merge_range('Q9:Q10', 'State', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:E', 20)
        sheet.set_column('F:H', 14)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:P', 14)
        sheet.set_column('Q:Q', 12)

        row_data = 9
        for rec in values['lines']:
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

            sheet.write(row_data, 0, row_data - 9, sty_table_data_center)
            sheet.write(row_data, 1,
                        datetime.strptime(rec['create_date'], "%Y-%m-%d %H:%M:%S") if rec['create_date'] else '',
                        sty_date)
            sheet.write(row_data, 2, rec['name'], sty_table_data)
            sheet.write(row_data, 3, rec['agent_name'], sty_table_data)
            sheet.write(row_data, 4, rec['contact_person'], sty_table_data)
            sheet.write(row_data, 5, rec['provider_type'], sty_table_data)
            sheet.write(row_data, 6, rec['provider'], sty_table_data)
            sheet.write(row_data, 7, rec['pnr'], sty_table_data)
            sheet.write(row_data, 8, rec['description'], sty_table_data)
            if rec['confirm_date']:  # Confirm Date
                sheet.write(row_data, 9, rec['confirm_date'].strftime("%d-%b-%Y %H:%m"), sty_datetime)
            else:
                sheet.write(row_data, 9, '', sty_datetime)
            sheet.write(row_data, 10, rec['confirm_by'], sty_table_data)
            if rec['issued_date']:  # Issued Date
                sheet.write(row_data, 11, rec['issued_date'].strftime("%d-%b-%Y %H:%m"), sty_datetime)
            else:
                sheet.write(row_data, 11, '', sty_datetime)
            sheet.write(row_data, 12, rec['issued_by'], sty_table_data)
            sheet.write(row_data, 13, rec['total'], sty_amount)
            sheet.write(row_data, 14, rec['commission'], sty_amount)
            sheet.write(row_data, 15, rec['nta_amount'], sty_amount)
            sheet.write(row_data, 16, rec['state'], sty_table_data_center)
            sheet.set_row(row_data, row_height)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Reservation Offline Report.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
