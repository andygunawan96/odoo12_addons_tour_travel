import math

from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class Incremental:
    def __init__(self):
        self.num_value = 0

    def reset(self):
        self.num_value = 0

    def get_number(self):
        return self.num_value

    def get_ascii(self):
        return self.convert_num_value_to_ascii(self.num_value)

    def generate_number(self, increment_value=1):
        self.num_value += increment_value
        return self.num_value

    def generate_ascii(self, increment_value=1):
        self.num_value += increment_value
        return self.convert_num_value_to_ascii(self.num_value)

    def convert_to_ascii(self, value):
        return chr(int(value+64))

    def convert_num_value_to_ascii(self, num_value):
        if num_value <= 26:
            return self.convert_to_ascii(num_value)
        mod_value = num_value % 26
        remaining_value = num_value - mod_value
        ch_res = ""
        if remaining_value > 0:
            ch_res = self.convert_num_value_to_ascii(remaining_value/26)
        ch_res += self.convert_to_ascii(mod_value)
        return ch_res


class AgentReportRecapAfterSalesXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.aftersales.wizard'

    # this function handles recap transaction excel render
    # responsible to print the actual data to excel,
    # and do a little summary for airline and hotel
    # btw this is the function being called if you press print in recap transaction
    # and it also does the same for other _print_report_excel
    def _print_report_excel(self, data):
        stream = BytesIO()
        incr = Incremental()
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
        values = self.env['report.tt_agent_report_recap_aftersales.agent_report_recap']._prepare_values(
            data['form'])  # get values

        # next 4 lines of code handles excel dependencies
        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        # write to file in cols and row
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        incr.reset()
        # ======= TABLE HEAD ==========
        sheet.write('%s9' % incr.generate_ascii(), 'No.', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'After Sales Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Category', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Name', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Customer Parent Type', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Customer Parent Name', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Date', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Create by', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Finalized Date', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Finalized By', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Email', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'After Sales Number', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Referenced Order Number', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Referenced PNR', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'New PNR', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Ledger Reference', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'State', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Currency', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Expected Amount', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Admin Fee', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Agent Commission', style.table_head_center)
        ##ho commission
        if values['data_form']['is_ho']:
            sheet.write('%s9' % incr.generate_ascii(), 'HO Commission', style.table_head_center)
        sheet.write('%s9' % incr.generate_ascii(), 'Grand Total', style.table_head_center)
        sheet.merge_range('%s9:%s9' % (incr.generate_ascii(), incr.generate_ascii(3)), 'Keterangan', style.table_head_center)

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
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 8)
        sheet.set_column('B:B', 12)
        sheet.set_column('C:X', 15)
        if values['data_form']['is_ho']:
            sheet.set_column('AB:AB', 47)
        else:
            sheet.set_column('AA:AA', 47)

        # ============ void start() ======================
        # declare some constant dependencies
        row_data = 8
        counter = 0
        temp_order_number = ''

        # it's just to make things easier, rather than write values['lines'] over and over
        datas = values['lines']
        #proceed the data
        # it's for temporary purposes, declare it here so that the first data will be different than "current"
        current_ledger = ''

        # let's iterate the data YEY!
        for idx, i in enumerate(datas):
            if not values['data_form']['is_ho']:
                if i['ledger_agent_name'] == values['data_form']['ho_name']:
                    continue
            # check if order number == current number
            if temp_order_number == i['after_sales_number']:
                # declare view handler
                if i['ledger_transaction_type'] in [3, 10] and current_ledger != i['ledger_id']:
                    current_ledger = i['ledger_id']

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

                    incr.reset()
                    # add ledger info 1 row below (from the same line of data)
                    sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['referenced_document'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['ledger_agent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['debit'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['ledger_description'], sty_table_data)

            else:
                # current_number != iterate order number
                # set current order number to iterated number
                temp_order_number = i['after_sales_number']

                # lets do some preparation to print the first line (data basically)
                counter += 1
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

                incr.reset()
                # print the whole data of reservation
                sheet.write(row_data, incr.get_number(), counter, sty_table_data_center)
                sheet.write(row_data, incr.generate_number(), i['after_sales_type'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['after_sales_category'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['agent_type_name'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['agent_name'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['customer_parent_type_name'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['customer_parent_name'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['create_date'], sty_date)
                sheet.write(row_data, incr.generate_number(), i['create_by'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['finalized_date'], sty_date)
                sheet.write(row_data, incr.generate_number(), i['finalized_by'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['agent_email'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['after_sales_number'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['referenced_document'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['referenced_pnr'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i.get('pnr', '-'), sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                sheet.write(row_data, incr.generate_number(), i['currency_name'], sty_table_data_center)
                sheet.write(row_data, incr.generate_number(), i['expected_amount'], sty_amount)
                sheet.write(row_data, incr.generate_number(), i['admin_fee'], sty_amount)
                sheet.write(row_data, incr.generate_number(), i['agent_commission'], sty_amount)
                if values['data_form']['is_ho']:
                    sheet.write(row_data, incr.generate_number(), i['ho_commission'], sty_amount)
                sheet.write(row_data, incr.generate_number(), i['total_amount'], sty_amount)
                sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                sheet.write(row_data, incr.generate_number(), '', sty_amount)
                sheet.write(row_data, incr.generate_number(), '', sty_amount)
                sheet.write(row_data, incr.generate_number(), '', sty_table_data)

                if i['ledger_transaction_type'] in [3, 10] and current_ledger != i['ledger_id']:
                    current_ledger = i['ledger_id']

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

                    incr.reset()
                    # add ledger info 1 row below (from the same line of data)
                    sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_date)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['referenced_document'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['ledger_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['state'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    if values['data_form']['is_ho']:
                        sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['ledger_agent_name'], sty_table_data)
                    sheet.write(row_data, incr.generate_number(), i['debit'], sty_amount)
                    sheet.write(row_data, incr.generate_number(), '', sty_amount)
                    sheet.write(row_data, incr.generate_number(), i['ledger_description'], sty_table_data)

        row_data += 1
        # this is writing empty string, to print the bottom border
        sty_table_data_center = style.table_data_center_border
        sty_table_data = style.table_data_border
        sty_datetime = style.table_data_datetime_border
        sty_date = style.table_data_date_border
        sty_amount = style.table_data_amount_border
        incr.reset()
        sheet.write(row_data, incr.get_number(), '', sty_table_data_center)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_date)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_date)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data_center)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        if values['data_form']['is_ho']:
            sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_amount)
        sheet.write(row_data, incr.generate_number(), '', sty_table_data)

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
