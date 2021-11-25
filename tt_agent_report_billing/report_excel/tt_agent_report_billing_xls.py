from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AgentReportBillingXls(models.TransientModel):
    _inherit = 'tt.agent.report.billing.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_agent_report_billing.agent_report_billing']._prepare_valued(data['form'])

        sheet_name = values['data_form']['subtitle']
        sheet = workbook.add_worksheet(sheet_name)
        sheet.set_landscape()
        sheet.hide_gridlines(2)

        # ================= TITLE & SUBTITLE ================
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%Y-%m-%d %H:%M'),
                    style.print_date)
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)
        sheet.freeze_panes(9, 0)

        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Billing Date', style.table_head_center)
        sheet.write('C9', 'Due Date', style.table_head_center)
        sheet.write('D9', 'Customer Type', style.table_head_center)
        sheet.write('E9', 'Agent', style.table_head_center)
        sheet.write('F9', 'Customer', style.table_head_center)
        sheet.write('G9', 'Invoice Document', style.table_head_center)
        sheet.write('H9', 'Invoice Amount', style.table_head_center)
        sheet.write('I9', 'Billing Number', style.table_head_center)
        sheet.write('J9', 'Payment', style.table_head_center)
        # sheet.write('J9', 'Acquirer', style.table_head_center)
        sheet.write('K9', 'State', style.table_head_center)

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
        billing_number = ''
        counter = 0
        for i in values['lines']:
            try:
                if billing_number != i['billing_number']:
                    counter += 1
                    billing_number = i['billing_number']
                    #count paid amount
                    filtered_data = filter(lambda x: x['billing_number'] == i['billing_number'], values['second_line'])
                    invoice_total = 0
                    for j in filtered_data:
                        try:
                            invoice_total += j['invoice_total']
                        except:
                            pass

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

                    sheet.write(row_data, 0, counter, sty_table_data)
                    sheet.write(row_data, 1, i['billing_date'], sty_date)
                    sheet.write(row_data, 2, i['billing_due_date'], sty_date)
                    sheet.write(row_data, 3, i['customer_type_name'], sty_table_data)
                    sheet.write(row_data, 4, i['agent_name'], sty_table_data)
                    sheet.write(row_data, 5, i['customer_name'], sty_table_data)
                    # sheet.write(row_data, 5, i['booker_type'], sty_table_data)
                    # sheet.write(row_data, 6, i['booker'], sty_table_data)
                    sheet.write(row_data, 6, '', sty_table_data)
                    sheet.write(row_data, 7, invoice_total, sty_amount)
                    sheet.write(row_data, 8, i['billing_number'], sty_table_data)
                    sheet.write(row_data, 9, '', sty_table_data)
                    sheet.write(row_data, 10, i['billing_state'], sty_table_data)

                #     to print per item
                    main_data = filter(lambda x: x['billing_number'] == i['billing_number'], values['lines'])
                    for j in main_data:
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

                        sheet.write(row_data, 0, '', sty_table_data)
                        sheet.write(row_data, 1, '', sty_table_data)
                        sheet.write(row_data, 2, '', sty_table_data)
                        sheet.write(row_data, 3, '', sty_table_data)
                        sheet.write(row_data, 4, '', sty_table_data)
                        sheet.write(row_data, 5, '', sty_table_data)
                        sheet.write(row_data, 6, j['invoice_number'], sty_table_data)
                        sheet.write(row_data, 7, j['invoice_amount'], sty_amount)
                        sheet.write(row_data, 8, '*Invoice Detail', sty_table_data)
                        sheet.write(row_data, 9, j['payment_number'], sty_table_data)
                        sheet.write(row_data, 10, j['billing_state'], sty_table_data)
                else:
                    continue
            except:
                _logger.error("Error Billing number {} ".format(i['billing_number']))
                raise UserError("Error Billing number {} ".format(i['billing_number']))


        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': '%s %s.xlsx' % (values['data_form']['agent_name'],values['data_form']['title']), 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

