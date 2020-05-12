from odoo import models
from ...tools import tools_excel, variables
from io import BytesIO
import xlsxwriter
import base64

class AgentReportPerformanceXls(models.TransientModel):
    _inherit = 'tt.agent.report.performance.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_agent_report_performance.agt_report_prf']._prepare_valued(data['form'])

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

        sheet.write('A9', 'No', style.table_head_center)
        sheet.write('B9', 'Agent Type', style.table_head_center)
        sheet.write('C9', 'Agent Name', style.table_head_center)
        sheet.write('D9', 'Parent Agent', style.table_head_center)
        sheet.write('E9', 'Email', style.table_head_center)
        sheet.write('F9', 'Total Revenue', style.table_head_center)
        # sheet.write('G9', 'Revenue with Tax', style.table_head_center)
        sheet.write('G9', 'Number of Sales', style.table_head_center)

        to_print = []
        current_id = ""
        for i in values['lines']:
            temp_total_wo_tax = 0
            temp_total_w_tax = 0
            number_of_sales = 0
            if current_id != i['agent_id']:
                filtered_data = filter(lambda x: x['agent_id'] == i['agent_id'], values['lines'])
                for j in filtered_data:
                    temp_total_w_tax += j['sales_total_after_tax']
                    temp_total_wo_tax += j['sales_total']
                    number_of_sales += 1
                dictionary = {
                    'agent_name': i['agent_name'],
                    'agent_type': i['agent_type_name'],
                    'email': i['agent_email'],
                    'total': temp_total_wo_tax,
                    'total_tax': temp_total_w_tax,
                    'number_of_sales': number_of_sales,
                    'parent': i['parent_agent_name'],
                }
                to_print.append(dictionary)
                current_id = i['agent_id']

        to_print.sort(key=lambda x: x['number_of_sales'], reverse=True)
        row_data = 8
        counter = 0
        for i in to_print:
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

            sheet.write(row_data, 0, counter, sty_table_data)
            sheet.write(row_data, 1, i['agent_type'], sty_table_data)
            sheet.write(row_data, 2, i['agent_name'], sty_table_data)
            sheet.write(row_data, 3, i['parent'], sty_table_data)
            sheet.write(row_data, 4, i['email'], sty_table_data)
            sheet.write(row_data, 5, i['total'], sty_amount)
            # sheet.write(row_data, 6, i['total_tax'], sty_amount)
            sheet.write(row_data, 6, i['number_of_sales'], sty_amount)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Agent Performance.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }