from odoo import models, _
from ...tools import tools_excel
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AgentReportRecapReservationXls(models.TransientModel):
    _inherit = 'tt.agent.report.recap.reservation.wizard'

    def _print_report_excel(self, data):
        stream = BytesIO()
        workbook = xlsxwriter.Workbook(stream)  # create a new workbook constructor
        style = tools_excel.XlsxwriterStyle(workbook)  # set excel style
        row_height = 13

        values = self.env['report.tt_agent_report_recap_reservation.agent_report_recap']._prepare_values(data['form'])  # get values

        sheet_name = values['data_form']['subtitle']  # get subtitle
        sheet = workbook.add_worksheet(sheet_name)  # add a new worksheet to workbook
        sheet.set_landscape()
        sheet.hide_gridlines(2)  # Hide screen and printed gridlines.

        # ======= TITLE & SUBTITLE ============
        sheet.merge_range('A1:G2', values['data_form']['agent_name'], style.title)  # set merge cells for agent name
        sheet.merge_range('A3:G4', values['data_form']['title'], style.title2)  # set merge cells for title
        sheet.write('G5', 'Printing Date :' + values['data_form']['date_now'].strftime('%d-%b-%Y %H:%M'),
                    style.print_date)  # print date print
        sheet.write('A5', 'State : ' + values['data_form']['state'], style.table_data)  # print state
        sheet.freeze_panes(9, 0)  # freeze panes mulai dari row 1-10

        # ======= TABLE HEAD ==========
        sheet.write('A9', 'No.', style.table_head_center)

        sheet.write('B9', 'Booking Type', style.table_head_center)
        sheet.write('C9', 'Agent Type', style.table_head_center)
        sheet.write('D9', 'Agent Name', style.table_head_center)
        sheet.write('E9', 'Issued Date', style.table_head_center)
        sheet.write('F9', 'Agent Email', style.table_head_center)
        sheet.write('G9', 'Provider', style.table_head_center)
        sheet.write('H9', 'Order Number', style.table_head_center)
        sheet.write('I9', 'PNR', style.table_head_center)
        sheet.write('J9', 'Adult', style.table_head_center)
        sheet.write('K9', 'Child', style.table_head_center)
        sheet.write('L9', 'Infant', style.table_head_center)
        sheet.write('M9', 'Currency', style.table_head_center)
        sheet.write('N9', 'NTA Amount', style.table_head_center)
        sheet.write('O9', 'Total Commission', style.table_head_center)
        sheet.write('P9', 'Grand Total', style.table_head_center)
        sheet.merge_range('Q9:R9', 'Keterangan', style.table_head_center)

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
        temp_dict = ''
        first_data = True
        counter = 1
        pnr_list = []
        multi_pnr = False
        temp_pnr = ''
        for rec in values['lines']:
            to_print = {}
            if first_data:
                first_data = False
                temp_dict = rec
                try:
                    pnr_list = rec['pnr'].split(", ")
                    temp_pnr = rec['ledger_pnr']
                    if len(pnr_list) > 1:
                        multi_pnr = True
                        to_print['pnr'] = rec['ledger_pnr']
                    else:
                        to_print['pnr'] = rec['pnr']
                except:
                    to_print['pnr'] = ''

                to_print.update({
                    'provider_type': rec['provider_type'],
                    'agent_type_name': rec['agent_type_name'],
                    'agent_name': rec['agent_name'],
                    'issued_date': rec['issued_date'],
                    'agent_email': rec['agent_email'],
                    'provider_name': rec['provider_name'],
                    'order_number': rec['order_number'],
                    'adult': rec['adult'],
                    'child': rec['child'],
                    'infant': rec['infant'],
                    'currency_name': rec['currency_name'],
                    'total_nta': rec['total_nta'],
                    'total_commission': rec['total_commission'],
                    'grand_total': rec['grand_total']
                })

                if rec['ledger_transaction_type'] == 3:
                    to_print.update({
                        'ledger_agent_name': rec['ledger_agent_name'],
                        'debit': rec['debit']
                    })
                else:
                    to_print.update({
                        'ledger_agent_name': '',
                        'debit': ''
                    })
            else:
                if temp_dict['order_number'] != rec['order_number']:
                    counter += 1
                    try:
                        pnr_list = rec['pnr'].split(", ")
                        temp_pnr = rec['ledger_pnr']
                        if len(pnr_list) > 1:
                            to_print['pnr'] = rec['ledger_pnr']
                            multi_pnr = True
                        else:
                            to_print['pnr'] = rec['pnr']
                            multi_pnr = False
                    except:
                        multi_pnr = False
                        to_print['pnr'] = ''

                    to_print.update({
                        'provider_type': rec['provider_type'],
                        'agent_type_name': rec['agent_type_name'],
                        'agent_name': rec['agent_name'],
                        'issued_date': rec['issued_date'],
                        'agent_email': rec['agent_email'],
                        'provider_name': rec['provider_name'],
                        'order_number': rec['order_number'],
                        'adult': rec['adult'],
                        'child': rec['child'],
                        'infant': rec['infant'],
                        'currency_name': rec['currency_name'],
                        'total_nta': rec['total_nta'],
                        'total_commission': rec['total_commission'],
                        'grand_total': rec['grand_total'],
                    })
                    temp_dict = rec
                else:
                    to_print.update({
                        'provider_type': '',
                        'agent_type_name': '',
                        'agent_name': '',
                        'issued_date': '',
                        'agent_email': '',
                        'provider_name': '',
                        'order_number': '',
                        'adult': '',
                        'child': '',
                        'infant': '',
                        'currency_name': '',
                        'total_nta': '',
                        'total_commission': '',
                        'grand_total': '',
                    })

                if rec['ledger_pnr'] != temp_pnr and rec['ledger_pnr'] in pnr_list and multi_pnr:
                    to_print['pnr'] = rec['ledger_pnr']
                    temp_pnr = rec['ledger_pnr']
                else:
                    try:
                        print(to_print['pnr'])
                    except:
                        to_print['pnr'] = ''



                if rec['ledger_transaction_type'] == 3:
                    to_print.update({
                        'ledger_agent_name': rec['ledger_agent_name'],
                        'debit': rec['debit']
                    })
                else:
                    if to_print['order_number'] == '':
                        to_print = {}
                    else:
                        to_print.update({
                            'ledger_agent_name': '',
                            'debit': ''
                        })

            #checker for data
            if to_print:
                row_data += 1
                sty_table_data_center = style.table_data_center
                sty_table_data = style.table_data
                sty_datetime = style.table_data_datetime
                sty_date = style.table_data_date
                sty_amount = style.table_data_amount


                sheet.write(row_data, 0, counter, sty_table_data_center)
                sheet.write(row_data, 1, to_print['provider_type'], sty_table_data)
                sheet.write(row_data, 2, to_print['agent_type_name'], sty_table_data)
                sheet.write(row_data, 3, to_print['agent_name'], sty_table_data)
                sheet.write(row_data, 4, to_print['issued_date'], sty_table_data)
                sheet.write(row_data, 5, to_print['agent_email'], sty_table_data)
                sheet.write(row_data, 6, to_print['provider_name'], sty_table_data)
                sheet.write(row_data, 7, to_print['order_number'], sty_table_data)
                sheet.write(row_data, 8, to_print['pnr'], sty_table_data)
                sheet.write(row_data, 9, to_print['adult'], sty_table_data)
                sheet.write(row_data, 10, to_print['child'], sty_table_data)
                sheet.write(row_data, 11, to_print['infant'], sty_table_data)
                sheet.write(row_data, 12, to_print['currency_name'], sty_table_data)
                sheet.write(row_data, 13, to_print['total_nta'], sty_table_data)
                sheet.write(row_data, 14, to_print['total_commission'], sty_table_data)
                sheet.write(row_data, 15, to_print['grand_total'], sty_table_data)
                sheet.write(row_data, 16, to_print['ledger_agent_name'], sty_table_data)
                sheet.write(row_data, 17, to_print['debit'], sty_table_data)

        workbook.close()

        attach_id = self.env['tt.agent.report.excel.output.wizard'].create(
            {'name': 'Agent Report Recap.xlsx', 'file_output': base64.encodebytes(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.agent.report.excel.output.wizard',
            'res_id': attach_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
