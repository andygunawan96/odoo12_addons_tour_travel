from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime

class AgentReportRecapTransactionXls(models.TransientModel):
    _inherit = 'tt.medical.vendor.report.recap.transaction.wizard'

    # this function handles recap transaction excel render
    # responsible to print the actual data to excel,
    # and do a little summary for airline and hotel
    # btw this is the function being called if you press print in recap transaction
    # and it also does the same for other _print_report_excel
    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        # this line of code responsible to call function who built the SQL query and actually connect to DB
        # after a little trim and little process like convert some date to string or vice versa
        # data will be return to this values variable
        # *in this recap report
        # values hold 3 main section
        # values['lines'] --> reservation data
        # valued['second_lines'] --> service charge data, within the same date range, this is needed to make sure revenue count and all is very accurate
        # values['data_form'] --> form that being past from GUI that user interact within odoo
        values = self.env['report.tt_medical_vendor_report_recap_transaction.medical_vendor_report_recap']._prepare_values(
            data['form'])  # get values

        # next 4 lines of code handles excel dependencies
        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        # write to file in cols and row
        sheet.merge_range('A1:G2', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G3', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A3', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A7', 'No.', style.table_head_center)
        sheet.write('B7', 'Provider', style.table_head_center)
        sheet.write('C7', 'Carrier', style.table_head_center)
        sheet.write('D7', 'Order Number', style.table_head_center)
        sheet.write('E7', 'Test Datetime', style.table_head_center)
        sheet.write('F7', 'Adult', style.table_head_center)
        sheet.write('G7', 'State', style.table_head_center)
        sheet.write('H7', 'State Vendor', style.table_head_center)

        # sheet.write('B9', 'Date', style.table_head_center)
        # sheet.write('C9', 'Order Number', style.table_head_center)
        # sheet.write('D9', 'Agent', style.table_head_center)
        # sheet.write('E9', 'Agent Type', style.table_head_center)
        # sheet.write('F9', 'Provider', style.table_head_center)
        # sheet.write('G9', 'Total', style.table_head_center)
        # sheet.write('H9', 'State', style.table_head_center)
        # sheet.write('I9', 'Provider Type', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(6, 30)
        sheet.set_column('A:A', 8)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:F', 15)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:S', 15)
        sheet.set_column('AA:AA', 30)

        # ============ void start() ======================
        # declare some constant dependencies
        row_data = 8
        counter = 0
        temp_order_number = ''

        # it's just to make things easier, rather than write values['lines'] over and over
        datas = values['lines']

        # let's iterate the data YEY!
        for i in datas:
            # declare view handler
            row_data += 1
            counter += 1
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

            sheet.write(row_data, 0, counter, sty_table_data_center)
            sheet.write(row_data, 1, i['provider_name'], sty_table_data)
            sheet.write(row_data, 2, i['carrier_name'], sty_table_data)
            sheet.write(row_data, 3, i['order_number'], sty_table_data)
            sheet.write(row_data, 4, i['test_datetime'], sty_date)
            sheet.write(row_data, 5, i['adult'], sty_table_data)
            sheet.write(row_data, 6, i['state'], sty_table_data)
            sheet.write(row_data, 7, i['state_vendor'], sty_table_data)

        row_data += 1
        # this is writing empty string, to print the bottom border
        sty_table_data_center = style.table_data_center_border
        sty_table_data = style.table_data_border
        sty_datetime = style.table_data_datetime_border
        sty_date = style.table_data_date_border
        sty_amount = style.table_data_amount_border
        sheet.write(row_data, 0, '', sty_table_data_center)
        sheet.write(row_data, 1, '', sty_table_data)
        sheet.write(row_data, 2, '', sty_table_data)
        sheet.write(row_data, 3, '', sty_table_data)
        sheet.write(row_data, 4, '', sty_date)
        sheet.write(row_data, 5, '', sty_table_data)
        sheet.write(row_data, 6, '', sty_table_data)
        sheet.write(row_data, 7, '', sty_table_data)

        # close the file
        workbook.close()

        # finalize and print!
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
