from odoo import models
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64

class CustomerReportPerformanceXls(models.TransientModel):
    _inherit = 'tt.customer.report.performance.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)
        style = tools_excel.XlsxwriterStyle(workbook)
        row_height = 13

        values = self.env['report.tt_customer_report_performance.cust_report_prf']._prepare_valued(data['form'])

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

        customer_names = self.get_customer_names(values)

        result = []
        for i in customer_names:
            temp_array = list(filter(lambda x: x['customer_name'] == i, values['lines']))
            temp_result = {
                'customer_name': i,
                'number_of_sales': 0,
                'total_spent': 0,
                'average_spent_per_order': 0,
                'airline_order': 0,
                'airline_spent': 0,
                'average_airline_spent_per_order': 0,
                'train_order': 0,
                'train_spent': 0,
                'average_train_spent_per_order': 0,
                'activity_order': 0,
                'activity_spent': 0,
                'average_activity_spent_per_order': 0,
                'tour_order': 0,
                'tour_spent': 0,
                'average_tour_spent_per_order': 0
            }
            for j in temp_array:
                if j['provider_type_name'].lower() == 'airline':
                    temp_result['airline_order'] += 1
                    try:
                        temp_result['airline_spent'] += float(j['charge_total'])
                    except:
                        temp_result['airline_spent'] += 0.0
                if j['provider_type_name'].lower() == 'train':
                    temp_result['train_order'] += 1
                    try:
                        temp_result['train_spent'] += float(j['charge_total'])
                    except:
                        temp_result['airline_spent'] += 0.0
                if j['provider_type_name'].lower() == 'activity':
                    temp_result['activity_order'] += 1
                    try:
                        temp_result['activity_spent'] += float(j['charge_total'])
                    except:
                        temp_result['airline_spent'] += 0.0
                if j['provider_type_name'].lower() == 'tour':
                    temp_result['tour_order'] += 1
                    try:
                        temp_result['tour_spent'] += float(j['charge_total'])
                    except:
                        temp_result['airline_spent'] += 0.0
                temp_result['number_of_sales'] += 1
                try:
                    temp_result['total_spent'] += float(j['charge_total'])
                except:
                    temp_result['airline_spent'] += 0.0
            if temp_result['number_of_sales'] > 0:
                temp_result['average_spent_per_order'] = temp_result['total_spent'] / float(temp_result['number_of_sales'])
            else:
                temp_result['average_spent_per_order'] = 0

            if temp_result['airline_order'] > 0:
                temp_result['average_airline_spent_per_order'] = temp_result['airline_spent'] / float(temp_result['airline_order'])
            else:
                temp_result['average_airline_spent_per_order'] = 0

            if temp_result['train_order'] > 0:
                temp_result['average_train_spent_per_order'] = temp_result['train_spent'] / float(temp_result['train_order'])
            else:
                temp_result['average_train_spent_per_order'] = 0

            if temp_result['activity_order'] > 0:
                temp_result['average_activity_spent_per_order'] = temp_result['activity_spent'] / float(temp_result['activity_order'])
            else:
                temp_result['average_tour_spent_per_order'] = 0

            if temp_result['tour_order'] > 0:
                temp_result['average_tour_spent_per_order'] = temp_result['tour_spent'] / float(temp_result['tour_order'])
            else:
                temp_result['average_tour_spent_per_order'] = 0
                
            result.append(temp_result)

        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Customer name', style.table_head_center)
        sheet.write('C9', 'Number of sales', style.table_head_center)
        sheet.write('D9', 'Total Spent', style.table_head_center)
        sheet.write('E9', 'Average spent', style.table_head_center)
        sheet.write('F9', 'Airline ordered', style.table_head_center)
        sheet.write('G9', 'Airline Spent', style.table_head_center)
        sheet.write('H9', 'Average airline spent', style.table_head_center)
        sheet.write('I9', 'Train ordered', style.table_head_center)
        sheet.write('J9', 'Train Spent', style.table_head_center)
        sheet.write('K9', 'Average train spent', style.table_head_center)
        sheet.write('L9', 'Activity ordered', style.table_head_center)
        sheet.write('M9', 'Activity Spent', style.table_head_center)
        sheet.write('N9', 'Average activity spent', style.table_head_center)
        sheet.write('O9', 'Tour ordered', style.table_head_center)
        sheet.write('P9', 'Tour spent', style.table_head_center)
        sheet.write('Q9', 'Average tour spent', style.table_head_center)

        row_data = 8
        for i in result:
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
            sheet.write(row_data, 1, i['customer_name'], sty_table_data)
            sheet.write(row_data, 2, i['number_of_sales'], sty_amount)
            sheet.write(row_data, 3, i['total_spent'], sty_amount)
            sheet.write(row_data, 4, i['average_spent_per_order'], sty_amount)
            sheet.write(row_data, 5, i['airline_order'], sty_amount)
            sheet.write(row_data, 6, i['airline_spent'], sty_amount)
            sheet.write(row_data, 7, i['average_airline_spent_per_order'], sty_amount)
            sheet.write(row_data, 8, i['train_order'], sty_amount)
            sheet.write(row_data, 9, i['train_spent'], sty_amount)
            sheet.write(row_data, 10, i['average_train_spent_per_order'], sty_amount)
            sheet.write(row_data, 11, i['activity_order'], sty_amount)
            sheet.write(row_data, 12, i['activity_spent'], sty_amount)
            sheet.write(row_data, 13, i['average_activity_spent_per_order'], sty_amount)
            sheet.write(row_data, 14, i['tour_order'], sty_amount)
            sheet.write(row_data, 15, i['tour_spent'], sty_amount)
            sheet.write(row_data, 16, i['average_tour_spent_per_order'], sty_amount)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Customer Performance.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def get_customer_names(self, array):
        customer_names = []
        for i in array['lines']:
            if i['customer_name'] not in customer_names:
                customer_names.append(i['customer_name'])

        return customer_names