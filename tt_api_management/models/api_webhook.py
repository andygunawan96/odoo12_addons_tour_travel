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
    _description = 'API Webhook Data'

    name = fields.Char('Name')
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')
    webhook_rel_ids = fields.One2many('tt.api.webhook','webhook_data_id','Webhook Rel',
                                      domain=['|', ('active', '=', True), ('active', '=', False)],
                                      context={'active_test': False})

    def notify_subscriber(self,req):
        try:
            _logger.info("Sending webhook data to children...")
            dom_search = []
            if req.get('provider_type'):
                dom_search.append(('provider_type_id.code','=',req['provider_type']))
            if req.get('actions_todo'):
                if req['actions_todo'] == 'sync_products_to_children_visa':
                    dom_search.append(('name', '=', 'Sync Master Data Visa'))
                elif req['actions_todo'] == 'sync_status_visa':
                    dom_search.append(('name', '=', 'Sync Visa Status'))
            webhook_data_obj = self.search(dom_search,limit=1)
            if webhook_data_obj:
                sent_data = []
                error_list = []
                # while len(sent_data) < len(webhook_data_obj[0].webhook_rel_ids.ids) and send_limit > 0:
                # 25 jan 2021 kalau error timeout kirim ke children yang sama terus" an padahal sudah masuk
                if req.get('child_id'):
                    children_list = webhook_data_obj[0].webhook_rel_ids.filtered(lambda x: x.credential_data_id.user_id.id == req['child_id'])
                else:
                    children_list = webhook_data_obj[0].webhook_rel_ids.filtered(lambda x: x.active == True)
                for rec in children_list:
                    send_limit = 1 # tiap child punya jatah 3x fail
                    while send_limit <= req.get('fail_send_limit',3):
                        try:
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
                                ## tambah context
                                res = self.env['tt.api.con'].send_webhook_to_children(vals)
                                _logger.info("Receive webhook data from children...")
                                _logger.info(json.dumps(res))
                                send_limit += 1
                                if not res.get('error_code'):
                                    sent_data.append(rec.id)
                                    break
                                else:
                                    _logger.info(res['error_msg'])

                        except Exception as e:
                            error_list.append('%s\n%s\n%s\n\n' % (send_limit, rec.credential_data_id.user_id.name, traceback.format_exc()))
            if len(error_list) != 0:
                raise Exception("\n".join(error_list))
            _logger.info('end webhook')
        except Exception as e:
            _logger.error(traceback.format_exc())

class ApiWebhook(models.Model):
    _name = 'tt.api.webhook'
    _description = 'API Webhook'

    webhook_data_id = fields.Many2one('tt.api.webhook.data')
    credential_data_id = fields.Many2one('tt.api.credential')
    url = fields.Text('URL')
    api_key = fields.Text('API Key', compute='_compute_api_key', store=True)
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',related='webhook_data_id.provider_type_id')
    active = fields.Boolean('Active', default=True)

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


