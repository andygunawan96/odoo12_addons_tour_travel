from odoo import api,models,fields
from datetime import datetime,timedelta
from odoo.exceptions import UserError
from io import BytesIO
import xlrd,xlwt
from urllib.request import urlretrieve
import requests
import base64,json
import logging,traceback

_logger = logging.getLogger()

class TtXlsPnrMatchingWizard(models.TransientModel):
    _name = "tt.xls.pnr.matching.wizard"
    _description = 'Orbis Wizard XLS PNR Matching'

    xls_file = fields.Many2one('tt.upload.center', 'Original XLS File')

    def get_xls_file_with_pnr(self):
        if not self.xls_file:
            raise UserError('Please upload / choose XLS File!')
        if self.xls_file.filename.split('.')[-1] not in ['xls', 'xlsx', 'csv']:
            raise UserError('Please upload only Excel supported formats!')
        # file_resp, headers = urlretrieve(self.xls_file.url)
        file_resp = requests.get(self.xls_file.url)
        # file_resp = requests.get('https://static.rodextrip.com/2023/07/20/c6bf/ad96/fb26/20230715.xlsx')
        dataframe = xlrd.open_workbook(file_contents=file_resp.content)
        sheet = dataframe.sheet_by_index(0)

        row_list = []
        for i in range(34, sheet.nrows):
            col_list = []
            for j in range(sheet.ncols):
                if sheet.cell_value(i, j):
                    col_list.append(sheet.cell_value(i, j))
            if len(col_list) >= 10:
                row_list.append(col_list)

        final_res = {}
        for rec in row_list:
            try:
                ticket_search = '%s%s' % (str(rec[0]).split('.')[0], str(rec[2]).split('.')[0])
                airline_tickets = self.env['tt.ticket.airline'].search([('ticket_number', '=', ticket_search)])
                airline_ticket = False
                for ticket in airline_tickets:
                    if ticket.provider_id.issued_date.strftime('%d%b%y').upper() == rec[3] and ticket.provider_id.booking_id.ho_id.id == self.env.user.ho_id.id:
                        airline_ticket = ticket
                if airline_ticket:
                    if not final_res.get(airline_ticket.provider_id.provider_id.code):
                        final_res.update({
                            airline_ticket.provider_id.provider_id.code: {}
                        })
                    is_first_pnr_counter = False
                    if not final_res[airline_ticket.provider_id.provider_id.code].get(airline_ticket.provider_id.pnr):
                        final_res[airline_ticket.provider_id.provider_id.code].update({
                            airline_ticket.provider_id.pnr: []
                        })
                        is_first_pnr_counter = True
                    final_res[airline_ticket.provider_id.provider_id.code][airline_ticket.provider_id.pnr].append({
                        'date': airline_ticket.provider_id.issued_date.strftime('%d-%b-%y'),
                        'code': str(rec[0]).split('.')[0],
                        'ticket_number': str(rec[2]).split('.')[0],
                        'pnr': airline_ticket.provider_id.pnr,
                        'per_ticket_nta': float(rec[-1].replace(',', '')),
                        'total_nta': is_first_pnr_counter and float(airline_ticket.provider_id.total_price) or 0,
                        'total_nta_03': is_first_pnr_counter and float(airline_ticket.provider_id.total_price) * 100.3 / 100 or 0,
                        'order_number': airline_ticket.provider_id.booking_id.name,
                    })
            except Exception as e:
                _logger.info('XLS PNR Matching skipping line: %s\nError: %s' % (json.dumps(rec), traceback.format_exc()))
                continue

        if not final_res:
            raise UserError('No matching data found.')

        workbook = xlwt.Workbook(encoding="UTF-8")
        for key, val in final_res.items():
            sheet = workbook.add_sheet(key.upper())
            header_bold = xlwt.easyxf("font: bold on;")
            field_list = ['Tanggal', 'Kode Maskapai', 'No. Tiket', 'PNR', 'NTA per Tiket', 'Total NTA', 'Total NTA + 0.3%', 'Order Number']
            for idx, field in enumerate(field_list):
                sheet.write(0, idx, field, style=header_bold)
            idx2 = 1
            for key2, val2 in val.items():
                for rec in val2:
                    sheet.write(idx2, 0, rec['date'])
                    sheet.write(idx2, 1, rec['code'])
                    sheet.write(idx2, 2, rec['ticket_number'])
                    sheet.write(idx2, 3, rec['pnr'])
                    sheet.write(idx2, 4, rec['per_ticket_nta'])
                    sheet.write(idx2, 5, rec['total_nta'])
                    sheet.write(idx2, 6, rec['total_nta_03'])
                    sheet.write(idx2, 7, rec['order_number'])
                    idx2 += 1
        stream = BytesIO()
        workbook.save(stream)

        res = self.env['tt.upload.center.wizard'].upload_file_api(
            {
                'filename': 'iata_data_%s.xls' % datetime.now().strftime('%y%m%d_%H%M%S'),
                'file_reference': 'IATA Data Convert Result (from %s)' % self.xls_file.filename,
                'file': base64.encodebytes(stream.getvalue()),
                'delete_date': datetime.today() + timedelta(minutes=10)
            },
            {
                'co_agent_id': self.env.user.agent_id.id,
                'co_uid': self.env.user.id,
            }
        )
        upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout IATA Data",
            'target': 'new',
            'url': upc_id.url,
        }
        stream.close()
        return url
