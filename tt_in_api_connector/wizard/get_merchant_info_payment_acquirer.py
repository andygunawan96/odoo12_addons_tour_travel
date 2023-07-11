from odoo import api, fields, models, _
import logging,json,traceback
_logger = logging.getLogger(__name__)

class GetMerchantInfoPaymentAcquirer(models.TransientModel):
    _name = 'get.merchant.info.payment.acquirer'
    _description = 'Get Merchant Info Payment Acquirer'

    provider = fields.Selection([('espay','Espay')],'Provider', help="Please turn on cron Auto-top-up-validator")
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    def sync_info(self):
        try:
            if self.ho_id:
                ho_obj = self.ho_id
            else:
                ho_obj = self.env.user.agent_id.ho_id
            res = self.env['tt.payment.api.con'].get_merchant_info({'provider':self.provider, 'type': 'close'}, ho_obj.id)
            _logger.info(json.dumps(res))
            if res['error_code'] == 0:

                for bank_res in res['response']:
                    bank_obj = self.env['tt.bank'].search([('code','=',bank_res['bankCode'])], limit=1)
                    existing_payment_acquirer = self.env['payment.acquirer'].search([
                        ('type','=','payment_gateway'),
                        ('agent_id','=',ho_obj.id),
                        ('bank_id','=',bank_obj.id),
                        ('account_number','=',False),
                        ('name', '=', bank_res['productName'])
                    ])
                    if not existing_payment_acquirer:
                        self.env['payment.acquirer'].create({
                            'type': 'payment_gateway',
                            'name': bank_res['productName'],
                            'bank_id': bank_obj.id,
                            'agent_id': ho_obj.id,
                            'ho_id': ho_obj.id,
                            'website_published': True
                        })

            res = self.env['tt.payment.api.con'].get_merchant_info({'provider': self.provider, 'type': 'open'}, ho_obj.id)
            _logger.info(json.dumps(res))
            if res['error_code'] == 0:
                bank_code_list = [x['bankCode'] for x in res['response']]
                bank_code_list = set(bank_code_list)
                bank_code_list.discard('503')
                for bank_res in bank_code_list:
                    bank_obj = self.env['tt.bank'].search([('code', '=', bank_res)], limit=1)
                    if bank_obj:
                        existing_payment_acquirer = self.env['payment.acquirer'].search(
                            [('agent_id', '=', ho_obj.id), ('type', '=', 'va'), ('bank_id', '=', bank_obj.id)])
                        if not existing_payment_acquirer:
                            self.env['payment.acquirer'].create({
                                'type': 'va',
                                'bank_id': bank_obj.id,
                                'agent_id': ho_obj.id,
                                'ho_id': ho_obj.id,
                                'website_published': False,
                                'name': 'Your Virtual Account at %s' % (bank_obj.name),
                            })
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise Exception(str(e))
