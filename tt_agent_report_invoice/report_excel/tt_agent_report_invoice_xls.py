from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime

class AgentReportInvoiceXls(models.TransientModel):
    _inherit = 'tt.agent.report.invoice.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_agent_report_invoice.agent_report_invoice']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ============== TITLE & SUBTITLE ============
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%Y-%m-%d %H:%M'), style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        sheet.freeze_panes(9,0)

        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Invoice Date', style.table_head_center)
        sheet.write('C9', 'Customer Type', style.table_head_center)
        sheet.write('D9', 'Customer', style.table_head_center)
        sheet.write('E9', 'Booker', style.table_head_center)
        sheet.write('F9', 'Invoice Number', style.table_head_center)
        sheet.write('G9', 'Billing Statement', style.table_head_center)
        sheet.merge_range('H9:I9', 'Invoice Detail', style.table_head_center)
        sheet.write('J9', 'Payment Acquirer', style.table_head_center)
        sheet.write('K9', 'Payment Ref', style.table_head_center)
        sheet.write('L9', 'Total', style.table_head_center)
        sheet.write('M9', 'State', style.table_head_center)

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
        sheet.set_column('H:I', 15)

        row_data = 8
        invoice_number = ''
        invoice_line_number = ''
        counter = 0
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

            if invoice_number != i['invoice_number']:
                counter += 1
                invoice_number = i['invoice_number']
                sheet.write(row_data, 0, counter, sty_table_data_center)
                sheet.write(row_data, 1, i['date_invoice'], sty_date)
                sheet.write(row_data, 2, i['agent_type'], sty_table_data)
                sheet.write(row_data, 3, i['agent_name'], sty_table_data)
                sheet.write(row_data, 4, i['customer_name'], sty_table_data)
                sheet.write(row_data, 5, i['invoice_number'], sty_table_data)
                sheet.write(row_data, 6, i['billing_statement'], sty_table_data)
                sheet.write(row_data, 7, '', sty_table_data)
                sheet.write(row_data, 8, '', sty_amount)
                sheet.write(row_data, 9, i['payment_acquirers'], sty_table_data)
                sheet.write(row_data, 10, i['payment_ref'], sty_table_data)
                sheet.write(row_data, 11, i['invoice_total'], sty_amount)
                sheet.write(row_data, 12, i['state'], sty_table_data)

                filtered_data = filter(lambda x: x['invoice_number'] == i['invoice_number'], values['lines'])
                for j in filtered_data:
                    if invoice_line_number != i['invoice_line']:
                        invoice_line_number = i['invoice_line']
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
                        sheet.write(row_data, 1, '', sty_date)
                        sheet.write(row_data, 2, '', sty_table_data)
                        sheet.write(row_data, 3, '', sty_table_data)
                        sheet.write(row_data, 4, '', sty_table_data)
                        sheet.write(row_data, 5, '', sty_table_data)
                        sheet.write(row_data, 6, '', sty_table_data)
                        sheet.write(row_data, 7, i['invoice_line'], sty_table_data)
                        sheet.write(row_data, 8, i['invoice_line_total'], sty_amount)
                        sheet.write(row_data, 9, i['payment_acquirer'], sty_table_data)
                        sheet.write(row_data, 10, i['payment_ref'], sty_table_data)
                        sheet.write(row_data, 11, '', sty_amount)
                        sheet.write(row_data, 12, i['state'], sty_table_data)
            else:
                continue

        workbook.close()
        # sheet.write('B9', 'Invoice Date', style.table_head_center)
        # sheet.write('C9', 'Customer Type', style.table_head_center)
        # sheet.write('D9', 'Customer', style.table_head_center)
        # sheet.write('E9', 'Booker Type', style.table_head_center)
        # sheet.write('F9', 'Contact/Booker', style.table_head_center)
        # sheet.write('G9', 'Source Document', style.table_head_center)
        # sheet.write('H9', 'Issued By', style.table_head_center)
        # sheet.write('I9', 'Invoice Number', style.table_head_center)
        # sheet.write('J9', 'Invoice Amount', style.table_head_center)
        # sheet.write('K9', 'Billing Number', style.table_head_center)
        # sheet.write('L9', 'Payment', style.table_head_center)
        # sheet.write('M9', 'Acquirer', style.table_head_center)
        # sheet.write('N9', 'Payment Amount', style.table_head_center)
        # sheet.write('O9', 'Validate By', style.table_head_center)
        # sheet.write('P9', 'Additional Information', style.table_head_center)
        # sheet.write('Q9', 'State', style.table_head_center)

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Agent Report Invoice.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }











