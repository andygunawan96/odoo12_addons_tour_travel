from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime
from ...tt_reservation_offline.models.tt_reservation_offline import STATE_OFFLINE_STR


class AgentReportOfflineXls(models.TransientModel):
    _inherit = 'tt.agent.report.offline.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_offline.agent_report_offline']._prepare_values(data['form'])  # get values

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:R2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:R4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('Q5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        if values['data_form']['provider_type'] == 'airline' or values['data_form']['provider_type'] == 'train':
            # ======= TABLE HEAD ==========
            sheet.write('A9', 'No.', style.table_head_center)
            sheet.write('B9', 'Date', style.table_head_center)
            sheet.write('C9', 'Order Number', style.table_head_center)
            sheet.write('D9', 'Agent Name', style.table_head_center)
            sheet.write('E9', 'Contact Person', style.table_head_center)
            sheet.write('F9', 'Provider Type', style.table_head_center)
            sheet.write('G9', 'Provider', style.table_head_center)
            sheet.write('H9', 'Journey', style.table_head_center)
            sheet.write('I9', 'PNR', style.table_head_center)
            sheet.write('J9', 'Description', style.table_head_center)
            sheet.write('K9', 'Confirm Date', style.table_head_center)
            sheet.write('L9', 'Confirm By', style.table_head_center)
            sheet.write('M9', 'Issued Date', style.table_head_center)
            sheet.write('N9', 'Issued By', style.table_head_center)
            sheet.write('O9', 'Total', style.table_head_center)
            sheet.write('P9', 'Agent Commission', style.table_head_center)
            sheet.write('Q9', 'NTA Amount', style.table_head_center)
            sheet.write('R9', 'State', style.table_head_center)
        else:
            # ======= TABLE HEAD ==========
            sheet.write('A9', 'No.', style.table_head_center)
            sheet.write('B9', 'Date', style.table_head_center)
            sheet.write('C9', 'Order Number', style.table_head_center)
            sheet.write('D9', 'Agent Name', style.table_head_center)
            sheet.write('E9', 'Contact Person', style.table_head_center)
            sheet.write('F9', 'Provider Type', style.table_head_center)
            sheet.write('G9', 'Provider', style.table_head_center)
            sheet.write('H9', 'PNR', style.table_head_center)
            sheet.write('I9', 'Description', style.table_head_center)
            sheet.write('J9', 'Confirm Date', style.table_head_center)
            sheet.write('K9', 'Confirm By', style.table_head_center)
            sheet.write('L9', 'Issued Date', style.table_head_center)
            sheet.write('M9', 'Issued By', style.table_head_center)
            sheet.write('N9', 'Total', style.table_head_center)
            sheet.write('O9', 'Agent Commission', style.table_head_center)
            sheet.write('P9', 'NTA Amount', style.table_head_center)
            sheet.write('Q9', 'State', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:E', 20)
        sheet.set_column('F:H', 14)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:P', 14)
        sheet.set_column('Q:Q', 12)

        row_data = 8
        if values['data_form']['provider_type'] == 'airline' or values['data_form']['provider_type'] == 'train':
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

                sheet.write(row_data, 0, row_data - 8, sty_table_data_center)
                sheet.write(row_data, 1, datetime.strptime(i['create_date'], "%Y-%m-%d %H:%M:%S") if i['create_date'] else '', sty_date)
                sheet.write(row_data, 2, i['ro_name'], sty_table_data)
                sheet.write(row_data, 3, i['agent_name'], sty_table_data)
                sheet.write(row_data, 4, (i['customer_first_name'] if i['customer_first_name'] else '') + ' ' +
                            (i['customer_last_name'] if i['customer_last_name'] else ''), sty_table_data)
                sheet.write(row_data, 5, i['provider_type_name'] + ' - ' + i['ro_offline_provider_type'], sty_table_data)
                if values['data_form']['provider_type'] == 'airline':
                    sheet.write(row_data, 6, (i['provider_name'] if i['provider_name'] else '') + '/' +
                                (i['carrier_name'] if i['carrier_name'] else ''), sty_table_data)
                else:
                    sheet.write(row_data, 6, (i['provider_name'] if i['provider_name'] else ''), sty_table_data)
                sheet.write(row_data, 7, (i['start_point'] if i['start_point'] else '') + ' - ' +
                            (i['end_point'] if i['end_point'] else ''), sty_table_data)
                sheet.write(row_data, 8, (i['ro_pnr'] if i['ro_pnr'] else ''), sty_table_data)
                sheet.write(row_data, 9, (i['ro_description'] if i['ro_description'] else ''), sty_table_data)
                if i['ro_confirm_date']:  # Confirm Date
                    sheet.write(row_data, 10, i['ro_confirm_date'], sty_datetime)
                else:
                    sheet.write(row_data, 10, '', sty_datetime)
                sheet.write(row_data, 11, (i['confirm_name'] if i['confirm_name'] else ''), sty_table_data)
                if i['ro_issued_date']:  # Issued Date
                    sheet.write(row_data, 12, i['ro_issued_date'], sty_datetime)
                else:
                    sheet.write(row_data, 12, '', sty_datetime)
                sheet.write(row_data, 13, (i['issuer_name'] if i['issuer_name'] else ''), sty_table_data)
                sheet.write(row_data, 14, (i['ro_total'] if i['ro_total'] else ''), sty_amount)
                sheet.write(row_data, 15, (i['ro_total_commission'] if i['ro_total_commission'] else ''), sty_amount)
                # sheet.write(row_data, 15, '', sty_amount)
                sheet.write(row_data, 16, (i['ro_total_nta'] if i['ro_total_nta'] else ''), sty_amount)
                sheet.write(row_data, 17, (i['ro_state'] if i['ro_state'] else ''), sty_table_data_center)
                sheet.set_row(row_data, row_height)

        else:
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

                sheet.write(row_data, 0, row_data - 8, sty_table_data_center)
                sheet.write(row_data, 1,
                            datetime.strptime(i['create_date'], "%Y-%m-%d %H:%M:%S") if i['create_date'] else '',
                            sty_date)
                sheet.write(row_data, 2, i['ro_name'], sty_table_data)
                sheet.write(row_data, 3, i['agent_name'], sty_table_data)
                sheet.write(row_data, 4, (i['customer_first_name'] if i['customer_first_name'] else '') + ' ' +
                            (i['customer_last_name'] if i['customer_last_name'] else ''), sty_table_data)
                sheet.write(row_data, 5, (i['provider_type_name'] if i['provider_type_name'] else ''), sty_table_data)
                sheet.write(row_data, 6, (i['provider_name'] if i['provider_name'] else ''), sty_table_data)
                sheet.write(row_data, 7, (i['ro_pnr'] if i['ro_pnr'] else ''), sty_table_data)
                sheet.write(row_data, 8, (i['ro_description'] if i['ro_description'] else ''), sty_table_data)
                if i['ro_confirm_date']:  # Confirm Date
                    sheet.write(row_data, 9, i['ro_confirm_date'], sty_datetime)
                else:
                    sheet.write(row_data, 9, '', sty_datetime)
                sheet.write(row_data, 10, i['confirm_name'], sty_table_data)
                if i['ro_issued_date']:  # Issued Date
                    sheet.write(row_data, 11, i['ro_issued_date'], sty_datetime)
                else:
                    sheet.write(row_data, 11, '', sty_datetime)
                sheet.write(row_data, 12, (i['issuer_name'] if i['issuer_name'] else ''), sty_table_data)
                sheet.write(row_data, 13, (i['ro_total'] if i['ro_total'] else ''), sty_amount)
                sheet.write(row_data, 14, (i['ro_total_commission'] if i['ro_total_commission'] else ''), sty_amount)
                # sheet.write(row_data, 14, '', sty_amount)
                sheet.write(row_data, 15, (i['ro_total_nta'] if i['ro_total_nta'] else ''), sty_amount)
                sheet.write(row_data, 16, (i['ro_state'] if i['ro_state'] else ''), sty_table_data_center)
                sheet.set_row(row_data, row_height)
        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Reservation Offline Report.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
