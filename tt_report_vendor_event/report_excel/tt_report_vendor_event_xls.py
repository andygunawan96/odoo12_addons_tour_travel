from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64


class ReportVendorEvent(models.TransientModel):
    _inherit = 'tt.report.vendor.event.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_report_vendor_event.report_vendor_event']._prepared_valued(data['form'])

        sheet_name = values['data_form']['event_name']
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
        sheet.set_column('A:A', 6)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:F', 15)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:I', 15)

        sheet.write('A6', 'No.', style.table_head_center)
        sheet.write('B6', 'Date', style.table_head_center)
        sheet.write('C6', 'PNR', style.table_head_center)
        sheet.write('D6', 'Price', style.table_head_center)
        sheet.write('E6', 'Quantity', style.table_head_center)
        sheet.write('F6', 'Total', style.table_head_center)

        row_data = 5
        for i in values['lines']:
            row_data += 1
            sty_table_data_center = style.table_data_center
            sty_table_data = style.table_data
            sty_date = style.table_data_date
            if row_data % 2 == 0:
                sty_table_data_center = style.table_data_center_even
                sty_table_data = style.table_data_even
                sty_date = style.table_data_date_even

            sheet.write(row_data, 0, row_data - 4, sty_table_data)
            sheet.write(row_data, 1, i['transaction_sales_date'], sty_table_data)
            sheet.write(row_data, 2, i['transaction_pnr'], sty_table_data)
            sheet.write(row_data, 3, i['event_option_price'], sty_table_data)
            sheet.write(row_data, 4, i['quantity'], sty_table_data)
            
        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Transaction Report.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

















