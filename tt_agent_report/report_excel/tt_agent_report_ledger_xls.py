from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AgentReportLedgerXls(models.TransientModel):
    _inherit = 'tt.agent.report.ledger.wizard'

    def _print_report_excel(self, data):
        values = self.env['report.tt_agent_report.agent_report_ledger']._prepare_values(data['form'])  # get values

        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:R2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:R4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('Q5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        # if values['data_form']['agent_type'] == 'ho':
        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Date', style.table_head_center)
        sheet.write('C9', 'Reference', style.table_head_center)
        sheet.write('D9', 'Service Type', style.table_head_center)
        sheet.write('E9', 'PNR', style.table_head_center)
        sheet.write('F9', 'Provider', style.table_head_center)
        sheet.write('G9', 'Agent Name', style.table_head_center)
        sheet.write('H9', 'Agent Type', style.table_head_center)
        sheet.write('I9', 'Description', style.table_head_center)
        sheet.write('J9', 'Issued By', style.table_head_center)
        sheet.write('K9', 'Type', style.table_head_center)
        sheet.write('L9', 'Debit', style.table_head_center)
        sheet.write('M9', 'Credit', style.table_head_center)
        sheet.write('N9', 'Balance', style.table_head_center)
        # else:
        #     sheet.write('A9', 'No.', style.table_head_center)
        #     sheet.write('B9', 'Date', style.table_head_center)
        #     sheet.write('C9', 'Reference', style.table_head_center)
        #     sheet.write('D9', 'Service Type', style.table_head_center)
        #     sheet.write('E9', 'PNR', style.table_head_center)
        #     sheet.write('F9', 'Agent Name', style.table_head_center)
        #     sheet.write('G9', 'Agent Type', style.table_head_center)
        #     sheet.write('H9', 'Description', style.table_head_center)
        #     sheet.write('I9', 'Issued By', style.table_head_center)
        #     sheet.write('J9', 'Type', style.table_head_center)
        #     sheet.write('K9', 'Debit', style.table_head_center)
        #     sheet.write('L9', 'Credit', style.table_head_center)
        #     sheet.write('M9', 'Balance', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        # if values['data_form']['agent_type'] == 'ho':
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 13)
        sheet.set_column('C:C', 19)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 25)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:J', 25)
        sheet.set_column('K:K', 24)
        sheet.set_column('L:L', 18)
        sheet.set_column('M:M', 18)
        sheet.set_column('N:N', 18)
        # else:
        #     sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        #     sheet.set_row(1, row_height)
        #     sheet.set_row(2, row_height)
        #     sheet.set_row(3, row_height)
        #     sheet.set_row(4, row_height)
        #     sheet.set_row(8, 30)
        #     sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        #     sheet.set_column('B:A', 13)
        #     sheet.set_column('C:C', 19)
        #     sheet.set_column('D:D', 15)
        #     sheet.set_column('E:E', 25)
        #     sheet.set_column('F:F', 25)
        #     sheet.set_column('G:G', 15)
        #     sheet.set_column('H:H', 25)
        #     sheet.set_column('I:I', 25)
        #     sheet.set_column('J:J', 24)
        #     sheet.set_column('K:K', 18)
        #     sheet.set_column('L:L', 18)
        #     sheet.set_column('M:M', 18)

        row_data = 8
        starting_balance = 0
        end_balance = 0
        total_debit = 0
        total_credit = 0

        #initiate start balance
        if len(values['lines']) > 0:
            if values['lines'][0]['debit'] > 0:
                starting_balance = values['lines'][0]['balance'] - values['lines'][0]['debit']
                end_balance = starting_balance
            else:
                starting_balance = values['lines'][0]['balance'] + values['lines'][0]['credit']
                end_balance = starting_balance

        mapped_provider_alias = {}

        def extract_provider_alias(provider_name):
            if not provider_name:
                provider_name = ''
            prov_alias_list = []
            prov_code_list = provider_name.split(',')
            for prov in prov_code_list:
                current_prov = prov.lower().strip()
                mapped_alias = mapped_provider_alias.get(current_prov)
                if mapped_alias:
                    prov_alias_list.append(mapped_alias)
                else:
                    prov_obj = self.env['tt.provider'].search([('code', '=', current_prov)], limit=1)
                    if prov_obj:
                        alias = prov_obj.report_alias and prov_obj.report_alias or prov_obj.name
                        prov_alias_list.append(alias)
                        mapped_provider_alias[current_prov] = alias
                    else:
                        # kalo ga ketemu, return apa adanya, lalu tetap di map supaya tidak search ulang
                        prov_alias_list.append(prov)
                        mapped_provider_alias[current_prov] = prov
            return ', '.join(prov_alias_list)

        for rec in values['lines']:
            if rec['debit'] > 0:
                total_debit += rec['debit']
                end_balance += rec['debit']
            if rec['credit'] > 0:
                total_credit += rec['credit']
                end_balance -= rec['credit']

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

            # if values['data_form']['agent_type'] == 'ho':
            sheet.write(row_data, 0, row_data - 8, sty_table_data_center)
            sheet.write(row_data, 1,
                        datetime.strptime(str(rec['date']), "%Y-%m-%d").strftime("%d-%m-%Y") if rec['date'] else '',
                        sty_date)
            sheet.write(row_data, 2, rec['ref'], sty_table_data)
            sheet.write(row_data, 3, rec['provider_type'], sty_table_data)
            sheet.write(row_data, 4, rec['pnr'], sty_table_data)
            sheet.write(row_data, 5, extract_provider_alias(rec['display_provider_name']), sty_table_data)
            sheet.write(row_data, 6, rec['agent'], sty_table_data)
            sheet.write(row_data, 7, rec['agent_type'], sty_table_data)
            sheet.write(row_data, 8, rec['description'], sty_table_data)
            sheet.write(row_data, 9, rec['issued_by'], sty_table_data)
            sheet.write(row_data, 10, rec['transaction_type'], sty_table_data)
            sheet.write(row_data, 11, rec['debit'], sty_amount)
            sheet.write(row_data, 12, rec['credit'], sty_amount)
            sheet.write(row_data, 13, rec['balance'], sty_amount)
            sheet.set_row(row_data, row_height)
            # else:
            #     sheet.write(row_data, 0, row_data - 8, sty_table_data_center)
            #     sheet.write(row_data, 1,
            #                 datetime.strptime(str(rec['date']), "%Y-%m-%d").strftime("%d-%m-%Y") if rec['date'] else '',
            #                 sty_date)
            #     sheet.write(row_data, 2, rec['ref'], sty_table_data)
            #     sheet.write(row_data, 3, rec['provider_type'], sty_table_data)
            #     sheet.write(row_data, 4, rec['pnr'], sty_table_data)
            #     sheet.write(row_data, 5, rec['agent'], sty_table_data)
            #     sheet.write(row_data, 6, rec['agent_type'], sty_table_data)
            #     sheet.write(row_data, 7, rec['description'], sty_table_data)
            #     sheet.write(row_data, 8, rec['issued_by'], sty_table_data)
            #     sheet.write(row_data, 9, rec['transaction_type'], sty_table_data)
            #     sheet.write(row_data, 10, rec['debit'], sty_amount)
            #     sheet.write(row_data, 11, rec['credit'], sty_amount)
            #     sheet.write(row_data, 12, rec['balance'], sty_amount)
            #     sheet.set_row(row_data, row_height)

        if values['data_form']['agent_id'] != '':
            sty_table_data = style.table_data
            sty_amount = style.table_data_amount
            sty_table_data_even = style.table_data_even
            sty_amount_even = style.table_data_amount_even

            row_data += 3
            sheet.write(row_data, 12, 'Starting Balance', sty_table_data)
            sheet.write(row_data, 13, starting_balance, sty_amount)
            sheet.write(row_data+1, 12, 'Total Debit', sty_table_data_even)
            sheet.write(row_data+1, 13, total_debit, sty_amount_even)
            sheet.write(row_data+2, 12, 'Total Credit', sty_table_data)
            sheet.write(row_data+2, 13, total_credit, sty_amount)
            sheet.write(row_data+3, 12, "End Balance", sty_table_data_even)
            sheet.write(row_data+3, 13, end_balance, sty_amount_even)


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

    def _print_ho(self, values):
        pass
        # if values['data_form']['agent_type'] == 'ho':
        #     self._print_ho(values)
        # else:
        #     self._print_agent(values)

    def _print_agent(self, values):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:R2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:R4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('Q5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)
        sheet.write('B9', 'Date', style.table_head_center)
        sheet.write('C9', 'Reference', style.table_head_center)
        sheet.write('D9', 'Service Type', style.table_head_center)
        sheet.write('E9', 'Provider', style.table_head_center)
        sheet.write('F9', 'PNR', style.table_head_center)
        sheet.write('G9', 'Agent Name', style.table_head_center)
        sheet.write('H9', 'Agent Type', style.table_head_center)
        sheet.write('I9', 'Description', style.table_head_center)
        sheet.write('J9', 'Issued By', style.table_head_center)
        sheet.write('K9', 'Type', style.table_head_center)
        sheet.write('L9', 'Debit', style.table_head_center)
        sheet.write('M9', 'Credit', style.table_head_center)
        sheet.write('N9', 'Balance', style.table_head_center)

        # ====== SET WIDTH AND HEIGHT ==========
        sheet.set_row(0, row_height)  # set_row(row, height) -> row 0-4 (1-5)
        sheet.set_row(1, row_height)
        sheet.set_row(2, row_height)
        sheet.set_row(3, row_height)
        sheet.set_row(4, row_height)
        sheet.set_row(8, 30)
        sheet.set_column('A:A', 5)  # set_column(first_col, last_col, width)
        sheet.set_column('B:B', 13)
        sheet.set_column('C:C', 19)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:J', 25)
        sheet.set_column('K:K', 24)
        sheet.set_column('L:L', 18)
        sheet.set_column('M:M', 18)
        sheet.set_column('N:N', 18)

        mapped_provider_alias = {}

        def extract_provider_alias(provider_name):
            if not provider_name:
                provider_name = ''
            prov_alias_list = []
            prov_code_list = provider_name.split(',')
            for prov in prov_code_list:
                current_prov = prov.lower().strip()
                mapped_alias = mapped_provider_alias.get(current_prov)
                if mapped_alias:
                    prov_alias_list.append(mapped_alias)
                else:
                    prov_obj = self.env['tt.provider'].search([('code', '=', current_prov)], limit=1)
                    if prov_obj:
                        alias = prov_obj.report_alias and prov_obj.report_alias or prov_obj.name
                        prov_alias_list.append(alias)
                        mapped_provider_alias[current_prov] = alias
                    else:
                        # kalo ga ketemu, return apa adanya, lalu tetap di map supaya tidak search ulang
                        prov_alias_list.append(prov)
                        mapped_provider_alias[current_prov] = prov
            return ', '.join(prov_alias_list)

        row_data = 8
        for rec in values['lines']:
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
                        datetime.strptime(str(rec['date']), "%Y-%m-%d").strftime("%d-%m-%Y") if rec['date'] else '',
                        sty_date)
            sheet.write(row_data, 2, rec['ref'], sty_table_data)
            sheet.write(row_data, 3, rec['provider_type'], sty_table_data)
            sheet.write(row_data, 4, rec['pnr'], sty_table_data)
            sheet.write(row_data, 5, extract_provider_alias(rec['display_provider_name']), sty_table_data)
            sheet.write(row_data, 6, rec['agent'], sty_table_data)
            sheet.write(row_data, 7, rec['agent_type'], sty_table_data)
            sheet.write(row_data, 8, rec['description'], sty_table_data)
            sheet.write(row_data, 9, rec['issued_by'], sty_table_data)
            sheet.write(row_data, 10, rec['transaction_type'], sty_table_data)
            sheet.write(row_data, 11, rec['debit'], sty_amount)
            sheet.write(row_data, 12, rec['credit'], sty_amount)
            sheet.write(row_data, 13, rec['balance'], sty_amount)
            sheet.set_row(row_data, row_height)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Ledger Report.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
