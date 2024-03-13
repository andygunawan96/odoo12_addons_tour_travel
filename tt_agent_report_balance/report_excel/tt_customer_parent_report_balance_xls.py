from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64

class CustomerParentReportBalanceXls(models.TransientModel):
    _inherit = 'tt.customer.parent.report.balance.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_agent_report_balance.customer_parent_report_balance']._search_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ================= TITLE & SUBTITLE ================
        sheet.merge_range('A1:G2', values['data_form']['customer_parent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('H5', 'Printing Date :' + values['data_form']['date_now'].strftime('%Y-%m-%d %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        sheet.freeze_panes(9, 0)

        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 6)
        sheet.set_column('B:H', 15)
        sheet.set_column('I:I', 10)
        sheet.set_column('J:K', 12)

        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Customer Parent Type', style.table_head_center)
        sheet.write('C9', 'Customer Parent Name', style.table_head_center)
        sheet.write('D9', 'Currency', style.table_head_center)
        sheet.write('E9', 'Balance', style.table_head_center)
        sheet.write('F9', 'Credit Limit', style.table_head_center)
        sheet.write('G9', 'Remaining Credit Limit', style.table_head_center)
        sheet.write('H9', 'Credit Unprocessed Amount', style.table_head_center)
        sheet.write('I9', 'Is Active', style.table_head_center)

        row_data = 8
        for i in values['lines']:
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

            sheet.write(row_data, 0, row_data - 8, sty_table_data)
            sheet.write(row_data, 1, i['customer_parent_type_name'], sty_table_data)
            sheet.write(row_data, 2, i['customer_parent_name'], sty_table_data)
            sheet.write(row_data, 3, i['currency_name'], sty_table_data)
            sheet.write(row_data, 4, i['customer_parent_balance'], sty_amount)
            sheet.write(row_data, 5, i['customer_parent_credit_limit'], sty_amount)
            sheet.write(row_data, 6, i['customer_parent_actual_balance'], sty_amount)
            sheet.write(row_data, 7, i['customer_parent_credit_unprocessed'], sty_amount)
            sheet.write(row_data, 8, i['customer_parent_status'], sty_table_data)

        workbook.close()

        if data['form'].get('logging_daily'):
            return base64.encodebytes(stream.getvalue())
        else:
            attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
                {'name': '%s %s.xlsx' % (values['data_form']['customer_parent_name'],values['data_form']['title']), 'file_output': base64.encodebytes(stream.getvalue())})
            return {
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tt.agent.report.excel.output.wizard',
                'res_id': attach_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
