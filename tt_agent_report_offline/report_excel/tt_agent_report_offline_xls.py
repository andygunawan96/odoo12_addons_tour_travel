from odoo import models, _
from odoo12_addons_tour_travel.tt_agent_report.report import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR


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
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Date', style.table_head_center)
        sheet.write('C9', 'Order Number', style.table_head_center)
        sheet.write('D9', 'Agent Name', style.table_head_center)
        sheet.write('E9', 'Contact Person', style.table_head_center)
        sheet.write('F9', 'Provider Type', style.table_head_center)
        sheet.write('G9', 'Provider', style.table_head_center)
        sheet.write('H9', 'PNR', style.table_head_center)
        sheet.write('I9', 'Description', style.table_head_center)
        sheet.write('J9', 'Confirm Date', style.table_head_center)
        sheet.write('K9', 'Confirm By', style.table_head_center)
        sheet.write('L9', 'Issued Date', style.table_head_center)
        sheet.write('M9', 'Issued By', style.table_head_center)
        sheet.write('N9', 'Total', style.table_head_center)
        sheet.write('O9', 'Agent Commission', style.table_head_center)
        sheet.write('P9', 'NTA Amount', style.table_head_center)
        sheet.write('Q9', 'State', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:E', 20)
        sheet.set_column('F:H', 14)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:P', 14)
        sheet.set_column('Q:Q', 12)

        row_data = 8
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

            sheet.write(row_data, 0, row_data - 8, sty_table_data_center)
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
