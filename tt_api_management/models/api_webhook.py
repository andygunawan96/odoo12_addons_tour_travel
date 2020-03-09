from odoo import api,models,fields
import logging,traceback

_logger = logging.getLogger(__name__)

class ApiWebhookData(models.Model):
    _name = 'tt.api.webhook.data'
    _description = 'Rodex Model API Webhook'

    name = fields.Char('Name')
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')
    action = fields.Char('Action')
    webhook_rel_ids = fields.One2many('tt.api.webhook','webhook_data_id','Webhook Rel')

    def notify_subscriber(self,req):
        try:
            webhook_data_obj = self.search([('provider_type_id.code','=',req['provider']),('action','=',req['action'])],limit=1)
            for rec in webhook_data_obj:
                ##send to each url here
                pass
                #send to rec.url(requestnya apa)

        except Exception as e:
            _logger.error(traceback.format_exc())

class ApiWebhook(models.Model):
    _name = 'tt.api.webhook'
    _description = 'Rodex Model API Webhook data'

    webhook_data_id = fields.Many2one('tt.api.webhook.data')
    credential_data_id = fields.Many2one('tt.api.credential')
    url = fields.Text('URL')
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',related='webhook_data_id.provider_type_id')
    action = fields.Char('Action',related='webhook_data_id.action')

class ApiCredentialWebhookInherit(models.Model):
    _inherit = 'tt.api.credential'

    webhook_rel_ids = fields.One2many('tt.api.webhook', 'credential_data_id', 'Webhook Rel')


