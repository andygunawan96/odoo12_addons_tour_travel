from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import date

months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December'
]

class CustomerReportPassportExpiration(models.TransientModel):
    _inherit = 'tt.customer.report.passport.expiration.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_customer_passport_expiration.passport_expiration']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ================= TITLE & SUBTITLE ================
        sheet.merge_range('A2:G3', values['data_form']['title'], style.title2)
        sheet.write('G4', 'Printing Date :' + values['data_form']['date_now'].strftime('%Y-%m-%d %H:%M'),
                    style.print_date)
        sheet.freeze_panes(5, 0)

        sheet.set_row(0, row_height)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(5, 30)
        sheet.set_column('A:A', 4)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 7)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 10)
        sheet.set_column('G:G', 15)

        sheet.write('A6', 'No.', style.table_head_center)
        sheet.write('B6', 'Customer Seq ID', style.table_head_center)
        sheet.write('C6', 'Customer Name', style.table_head_center)
        sheet.write('D6', 'Identity Type', style.table_head_center)
        sheet.write('E6', 'Identity Number', style.table_head_center)
        sheet.write('F6', 'Identity Expdate', style.table_head_center)
        sheet.write('G6', 'Agent Name', style.table_head_center)

        row_data = 5
        today_date = date.today()
        for i in values['lines']:
            row_data += 1

            if row_data % 2 == 0:
                if i['identity_expdate'] < today_date:
                    sty_table_data_center = style.table_data_center_red_even
                    sty_table_data = style.table_data_red_even
                    sty_date = style.table_data_date_red_even
                else:
                    sty_table_data_center = style.table_data_center_even
                    sty_table_data = style.table_data_even
                    sty_date = style.table_data_date_even
            else:
                if i['identity_expdate'] < today_date:
                    sty_table_data_center = style.table_data_center_red
                    sty_table_data = style.table_data_red
                    sty_date = style.table_data_date_red
                else:
                    sty_table_data_center = style.table_data_center
                    sty_table_data = style.table_data
                    sty_date = style.table_data_date
            sheet.write(row_data, 0, row_data - 5, sty_table_data)
            sheet.write(row_data, 1, i['customer_seq_id'], sty_table_data)
            sheet.write(row_data, 2, i['customer_name'], sty_table_data)
            sheet.write(row_data, 3, i['identity_type'],sty_table_data)
            sheet.write(row_data, 4, i['identity_number'],sty_table_data)
            sheet.write(row_data, 5, i['identity_expdate'],sty_date)
            sheet.write(row_data, 6, i['agent_name'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Customer Passport Expiration.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }