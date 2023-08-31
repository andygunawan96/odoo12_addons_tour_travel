import traceback

from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
import logging
from odoo.exceptions import UserError
from datetime import datetime
_logger = logging.getLogger(__name__)

class HOReportInvoiceXls(models.TransientModel):
    _inherit = 'tt.ho.report.invoice.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_agent_report_invoice.ho_report_invoice']._prepare_valued(data['form'])

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
        sheet.write('C9', 'Head Office', style.table_head_center)
        sheet.write('D9', 'Agent Type', style.table_head_center)
        sheet.write('E9', 'Agent', style.table_head_center)
        sheet.write('F9', 'Booker', style.table_head_center)
        sheet.write('G9', 'Customer Type', style.table_head_center)
        sheet.write('H9', 'Customer Name', style.table_head_center)
        sheet.write('I9', 'Invoice Number', style.table_head_center)
        sheet.write('J9', 'Billing Statement', style.table_head_center)
        sheet.write('K9', 'Payment Acquirer', style.table_head_center)
        sheet.write('L9', 'Payment Ref', style.table_head_center)
        sheet.write('M9', 'Total', style.table_head_center)
        sheet.write('N9', 'State', style.table_head_center)
        sheet.merge_range('O9:Q9', 'Invoice Detail', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 6)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:G', 15)
        sheet.set_column('H:H', 12)
        sheet.set_column('I:J', 15)

        row_data = 8
        invoice_number = ''
        invoice_line_number = ''
        counter = 0
        summary = []
        for i in values['lines']:
            if invoice_number != i['invoice_number']:
                counter += 1
                row_data += 1
                sty_table_data_center = style.table_data_center_border_bold
                sty_table_data = style.table_data_border_bold
                sty_table_data_bold = style.table_data_bold
                sty_datetime = style.table_data_datetime_border_bold
                sty_date = style.table_data_date_border_bold
                sty_amount = style.table_data_amount_border_bold
                sty_amount_bold = style.table_data_amount_border_bold
                if row_data % 2 == 0:
                    sty_table_data_center = style.table_data_center_even_border_bold
                    sty_table_data = style.table_data_even_border_bold
                    sty_table_data_bold = style.table_data_even_bold
                    sty_datetime = style.table_data_datetime_even_border_bold
                    sty_date = style.table_data_date_even_border_bold
                    sty_amount = style.table_data_amount_even_border_bold
                    sty_amount_bold = style.table_data_amount_even_border_bold

                invoice_number = i['invoice_number']
                sheet.write(row_data, 0, counter, sty_table_data_center)
                sheet.write(row_data, 1, i['date_invoice'], sty_date)
                sheet.write(row_data, 2, i['ho_name'], sty_table_data)
                sheet.write(row_data, 3, i['agent_type'], sty_table_data)
                sheet.write(row_data, 4, i['agent_name'], sty_table_data)
                sheet.write(row_data, 5, i['booker_name'], sty_table_data)
                sheet.write(row_data, 6, i['customer_type'], sty_table_data)
                sheet.write(row_data, 7, i['customer_name'], sty_table_data)
                sheet.write(row_data, 8, i['invoice_number'], sty_table_data)
                sheet.write(row_data, 9, i['billing_statement'], sty_table_data)
                sheet.write(row_data, 10, '', sty_table_data)
                sheet.write(row_data, 11, '', sty_table_data)
                sheet.write(row_data, 12, i['invoice_total'], sty_amount_bold)
                sheet.write(row_data, 13, i['state'], sty_table_data)
                sheet.write(row_data, 14, '', sty_table_data)
                sheet.write(row_data, 15, '', sty_amount)
                sheet.write(row_data, 16, '', sty_amount)


                filtered_data = list(filter(lambda x: x['invoice_number'] == i['invoice_number'], values['lines']))
                try:
                    sort_by_payment = sorted(filtered_data, key=lambda x: x['payment_ref'])
                except:
                    sort_by_payment = []
                payment_ref = ''
                for j in sort_by_payment:
                    try:
                        row_data += 1
                        sty_table_data = style.table_data
                        sty_amount = style.table_data_amount
                        if row_data % 2 == 0:
                            sty_table_data = style.table_data_even
                            sty_amount = style.table_data_amount_even

                        if payment_ref != j['payment_ref']:
                            #check if bank is exist in summary
                            returning_index = self.returning_index(summary, {'payment_acquirer': j['payment_acquirer'], 'payment_account': j['payment_acquirer_account_number']})
                            if returning_index == -1:
                                temp_dict = {
                                    'payment_acquirer': j['payment_acquirer'],
                                    'payment_account': j['payment_acquirer_account_number'],
                                    'transaction_counter': 1,
                                    'total_amount': float(j.get('payment_pay_amount',0))
                                }
                                summary.append(temp_dict)
                            else:
                                summary[returning_index]['transaction_counter'] += 1
                                try:
                                    summary[returning_index]['total_amount'] += float(j.get('payment_pay_amount',0))
                                except:
                                    summary[returning_index]['total_amount'] += 0.0

                            sheet.write(row_data, 0, '', sty_table_data)
                            sheet.write(row_data, 1, '', sty_table_data)
                            sheet.write(row_data, 2, '', sty_table_data)
                            sheet.write(row_data, 3, '', sty_table_data)
                            sheet.write(row_data, 4, '', sty_table_data)
                            sheet.write(row_data, 5, '', sty_table_data)
                            sheet.write(row_data, 6, '', sty_table_data)
                            sheet.write(row_data, 7, '', sty_table_data)
                            sheet.write(row_data, 8, '', sty_table_data)
                            sheet.write(row_data, 9, '', sty_table_data)
                            to_print = ''
                            if str(j['payment_acquirer']) != 'None':
                                to_print += str(j['payment_acquirer'])
                            else:
                                to_print += 'No Data'
                            if str(j['payment_acquirer_account_number']) != 'None':
                                to_print += ' ' + str(j['payment_acquirer_account_number'])
                            sheet.write(row_data, 10, to_print, sty_table_data)
                            sheet.write(row_data, 11, j['payment_ref'], sty_table_data)
                            sheet.write(row_data, 12, j.get('payment_pay_amount',0), sty_amount)
                            sheet.write(row_data, 13, '', sty_table_data)
                            sheet.write(row_data, 14, '', sty_table_data)
                            sheet.write(row_data, 15, '', sty_table_data)
                            sheet.write(row_data, 16, '', sty_table_data)

                    except:
                        _logger.error("ERROR in Invoice Name : {}\n{}".format(i['invoice_number'],traceback.format_exc()))
                        raise UserError("ERROR in Invoice Name : {} ".format(i['invoice_number']))

                for j in filtered_data:
                    if invoice_line_number != j['invoice_line']:
                        try:
                            invoice_line_number = j['invoice_line']
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
                            sheet.write(row_data, 7, '', sty_table_data)
                            sheet.write(row_data, 8, '', sty_table_data)
                            sheet.write(row_data, 9, '', sty_table_data)
                            sheet.write(row_data, 10, '', sty_table_data)
                            sheet.write(row_data, 11, '', sty_table_data)
                            sheet.write(row_data, 12, '', sty_table_data)
                            sheet.write(row_data, 13, '', sty_table_data)
                            sheet.write(row_data, 14, j['invoice_line'], sty_table_data)
                            sheet.write(row_data, 15, j['invoice_line_reference'], sty_table_data)
                            sheet.write(row_data, 16, j['invoice_line_total'], sty_amount)
                        except:
                            _logger.error("ERROR in Invoice Name : {} , Invoice Line : {}\n{}".format(i['invoice_number'], j['invoice_line'],traceback.format_exc()))
                            raise UserError("ERROR in Invoice Name : {} , Invoice Line : {}".format(i['invoice_number'], j['invoice_line']))
            else:
                continue

        row_data += 3
        sheet.write(row_data, 13, 'Payment account', style.table_head_center)
        sheet.write(row_data, 14, 'total amount', style.table_head_center)
        try:
            for i in summary:
                row_data += 1
                sty_table_data = style.table_data
                sty_amount = style.table_data_amount
                if row_data % 2 == 0:
                    sty_table_data = style.table_data_even
                    sty_amount = style.table_data_amount_even

                if str(i['payment_acquirer']) == 'None':
                    sheet.write(row_data, 12, 'No Data', sty_table_data)
                elif str(i['payment_acquirer']) == 'Cash':
                    sheet.write(row_data, 12, 'Cash', sty_table_data)
                else:
                    sheet.write(row_data, 12, str(i['payment_acquirer']) + ' ' + str(i['payment_account']), sty_table_data)
                sheet.write(row_data, 13, i['total_amount'], sty_amount)
        except:
            _logger.error("ERROR when Print Invoice Summary")
            raise UserError("ERROR when Print Invoice Summary")

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
