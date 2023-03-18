from odoo import models, fields, api, _
import logging, traceback,pytz
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)


class TtAutoSyncActivitySetup(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.auto.sync.activity.setup'
    _rec_name = 'provider_id'
    _description = 'Tour & Travel - Auto Sync Activity Setup'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_activity.tt_provider_type_activity').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    json_file_range = fields.Integer('Json File Range', default=3, required=True, help='Amount of Json files to read per rotation.')
    item_amt_per_json = fields.Integer('Item Amount Per Json', default=100, required=True)
    is_json_generated = fields.Boolean('Is Json Files Generated')
    latest_file_idx = fields.Integer('Latest Json File Index', default=0)
    exec_delay_days = fields.Integer('Delay Between Executions (Days)', default=7)
    next_exec_time = fields.Datetime('Next Execution Start Time', default=datetime.now())
    active = fields.Boolean('Active', default=True)

    def execute_sync_products(self):
        if not self.is_json_generated:
            self.env['tt.master.activity'].action_generate_json(self.provider_id.code, self.item_amt_per_json)
            _logger.info('Auto Sync Activity: Generating Json for provider %s. Will start to sync products on next execution.' % self.provider_id.name)
            self.write({
                'is_json_generated': True,
                'next_exec_time': datetime.now() + timedelta(days=self.exec_delay_days)
            })
        else:
            file_ext = 'json'
            json_length = self.env['tt.master.activity'].action_check_json_length(self.provider_id.code, file_ext)

            start_num = self.latest_file_idx + 1
            if start_num + self.json_file_range >= json_length:
                end_num = json_length
                write_vals = {
                    'latest_file_idx': 0,
                    'is_json_generated': False
                }
            else:
                end_num = start_num + self.json_file_range
                write_vals = {
                    'latest_file_idx': end_num
                }
            self.write(write_vals)
            _logger.info('Auto Sync Activity: Syncing products for provider %s. Json file %s to %s out of %s.' % (self.provider_id.name, str(start_num), str(end_num), str(json_length)))
            self.env['tt.master.activity'].action_sync_products(self.provider_id.code, start_num, end_num)
