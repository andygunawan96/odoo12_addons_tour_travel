from odoo import models, fields, api
from datetime import date, datetime, timedelta

from .ApiConnector_Hotel import ApiConnectorHotels
API_CN_HOTEL = ApiConnectorHotels()


class ProviderData(models.Model):
    _name = "tt.hotel.provider.data"
    _description = 'Get Hotel Data (Ex: Country Name, City, Hotel Detail, Facility)'

    name = fields.Char('Name')
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    sync_type = fields.Selection([('country','Country'), ('province','Province'), ('city','City'), ('facility','Facility'),
                                  ('hotel','Hotel'), ('meal','Meal Type')], 'Sync Type', required=True)
    state = fields.Selection([('draft','Draft'),('confirm','Confirmed'),('error','Error'),('done','Done')], 'State',
                             default='draft',
                             help='Draft: new Build;'
                                  'Confirm: Waiting for schedule action or manually run;'
                                  'Error: Error during sync proccess;'
                                  'Done: Sync Success')
    schedule_date = fields.Datetime('Next Execution Date')
    start = fields.Integer('Start Sync Record', default=0)
    limit = fields.Integer('Limit Sync Record', default=20)

    all_result = fields.Integer('All Result', compute='')
    process_result = fields.Integer('Processed', compute='')
    unprocess_result = fields.Integer('Need to Processed', compute='')

    line_ids = fields.One2many('tt.temporary.record', 'sync_id', 'Line(s)')

    def action_draft(self):
        self.state = 'draft'
        return True

    def action_confirm(self):
        self.state = 'confirm'
        return True

    def action_sync(self):
        # Rubah state ke Error
        self.state = 'error'
        # Panggil fungsi sync ke GW
        codes = ''

        search_req = {
            'provider': self.provider_id.name,
            'type': self.sync_type,
            'start': self.start,
            'limit': self.limit,
            'offset': 1,
            'codes': codes,
        }
        res = API_CN_HOTEL.get_record_by_api(search_req)
        # Simpan Hasil sync ke Lines(temporary record)
        for new_rec in res['response']:
            self.env[''].create({
                '': new_rec,
            })
        # Untuk setiap hasil nya lakukan komputasi search ke database
        # Hitung total record, record yg bisa di proses dan yg perlu proses manual
        # Rubah state ke Done
        return True

    # Cman di panggil ketika state error
    def action_resync(self):
        # Panggil fungsi sync ke GW
        # Cek apakah hasil sudah ada
            # Jika sdah ada lompati
            # Jika blum Hasil sync ke Lines(temporary record)
        return True


class TtTemporaryRecord(models.Model):
    _inherit = 'tt.temporary.record'

    sync_id = fields.Many2one('tt.hotel.provider.data', 'Sync')

