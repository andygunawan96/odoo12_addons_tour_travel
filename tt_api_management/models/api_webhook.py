from odoo import api,models,fields
import logging,traceback
from datetime import datetime
import hashlib
from ...tools import util

_logger = logging.getLogger(__name__)

class ApiWebhookData(models.Model):
    _name = 'tt.api.webhook.data'
    _description = 'Rodex Model API Webhook'

    name = fields.Char('Name')
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')
    webhook_rel_ids = fields.One2many('tt.api.webhook','webhook_data_id','Webhook Rel')

    def notify_subscriber(self,req):
        try:
            webhook_data_obj = self.search([('provider_type_id.code','=',req['provider_type'])],limit=1)
            if webhook_data_obj:
                for rec in webhook_data_obj[0].webhook_rel_ids:
                    temp_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    temp_sha = rec.api_key + temp_date
                    headers = {

                    }
                    vals = {
                        'action': req['action'],
                        'signature': hashlib.sha256(temp_sha.encode()),
                        'datetime': temp_date,
                        'data': req['data']
                    }
                    pass
                    # send request to gateway
                    # res = util.send_request(rec.url, vals, headers, content_type='json', timeout=5 * 60, method='POST')
                    # mekanisme kalau server ga nerima
        except Exception as e:
            _logger.error(traceback.format_exc())

class ApiWebhook(models.Model):
    _name = 'tt.api.webhook'
    _description = 'Rodex Model API Webhook data'

    webhook_data_id = fields.Many2one('tt.api.webhook.data')
    credential_data_id = fields.Many2one('tt.api.credential')
    url = fields.Text('URL')
    api_key = fields.Text('API Key', compute='_compute_api_key', store=True)
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',related='webhook_data_id.provider_type_id')

    @api.multi
    @api.depends('credential_data_id')
    @api.onchange('credential_data_id')
    def _compute_api_key(self):
        for rec in self:
            if rec.credential_data_id:
                rec.api_key = rec.credential_data_id.api_key

class ApiCredentialWebhookInherit(models.Model):
    _inherit = 'tt.api.credential'

    webhook_rel_ids = fields.One2many('tt.api.webhook', 'credential_data_id', 'Webhook Rel')


