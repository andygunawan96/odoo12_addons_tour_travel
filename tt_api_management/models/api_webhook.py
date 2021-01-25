from odoo import api,models,fields
import odoo.tools as tools
import logging,traceback
from datetime import datetime
import hashlib
import json
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
            _logger.info("Sending webhook data to children...")
            webhook_data_obj = self.search([('provider_type_id.code','=',req['provider_type'])],limit=1)
            if webhook_data_obj:
                sent_data = []
                send_limit = 3
                while len(sent_data) < len(webhook_data_obj[0].webhook_rel_ids.ids) and send_limit > 0:
                    if req.get('child_id'):
                        children_list = webhook_data_obj[0].webhook_rel_ids.filtered(lambda x: x.credential_data_id.user_id.id == req['child_id'])
                    else:
                        children_list = webhook_data_obj[0].webhook_rel_ids
                    for rec in children_list:
                        _logger.info("children name %s" % rec.credential_data_id.user_id.name)
                        if rec.id not in sent_data:
                            temp_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            temp_sha = rec.api_key + temp_date
                            vals = {
                                'action': req['action'],
                                'url': rec.url,
                                'signature': hashlib.sha256(temp_sha.encode()).hexdigest(),
                                'datetime': temp_date,
                                'data': req['data'],
                                'timeout': req.get('timeout', 300)
                            }
                            res = self.env['tt.api.con'].send_webhook_to_children(vals)
                            _logger.info("Receive webhook data from children...")
                            _logger.info(json.dumps(res))
                            if not res.get('error_code'):
                                sent_data.append(rec.id)
                            else:
                                _logger.info(res['error_msg'])
                            send_limit -= 1
            _logger.info('end webhook')
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


