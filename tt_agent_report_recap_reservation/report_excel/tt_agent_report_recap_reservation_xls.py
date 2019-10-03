from odoo import models, _
from odoo12_addons_tour_travel.tt_agent_report.report import tools_excel
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
        sheet.freeze_panes(10, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.merge_range('A9:A10', 'No.', style.table_head_center)
        sheet.merge_range('B9:B10', 'Date', style.table_head_center)
        sheet.merge_range('C9:C10', 'Order Number', style.table_head_center)
        sheet.merge_range('D9:D10', 'Agent', style.table_head_center)
        sheet.merge_range('E9:E10', 'Agent Type', style.table_head_center)
        sheet.merge_range('F9:F10', 'Provider', style.table_head_center)
        sheet.merge_range('G9:G10', 'Total', style.table_head_center)
        sheet.merge_range('H9:H10', 'State', style.table_head_center)
        sheet.merge_range('I9:I10', 'Provider Type', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_column('A:A', 6)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:F', 15)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:I', 15)

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
            sheet.write(row_data, 2, rec['order_number'], sty_table_data)
            sheet.write(row_data, 3, rec['agent_name'], sty_table_data)
            sheet.write(row_data, 4, rec['agent_type'], sty_table_data)
            sheet.write(row_data, 5, rec['provider'], sty_table_data)
            sheet.write(row_data, 6, rec['total'], sty_table_data)
            sheet.write(row_data, 7, rec['state'], sty_table_data)
            sheet.write(row_data, 8, rec['provider_type'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Agent Report Recap.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
