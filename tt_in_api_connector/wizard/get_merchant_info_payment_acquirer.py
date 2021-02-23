from odoo import api, fields, models, _
import logging,json,traceback
_logger = logging.getLogger(__name__)

class GetMerchantInfoPaymentAcquirer(models.TransientModel):
    _name = 'get.merchant.info.payment.acquirer'
    _description = 'Get Merchant Info Payment Acquirer'

    provider = fields.Selection([('espay','Espay')],'Provider')

    def sync_info(self):
        try:
            res = self.env['tt.payment.api.con'].get_merchant_info({'provider':self.provider})
            _logger.info(json.dumps(res))
            if res['error_code'] == 0:
                ho_obj = self.env.ref('tt_base.rodex_ho')
                for bank_res in res['response']:
                    bank_obj = self.env['tt.bank'].search([('code','=',bank_res['bankCode'])], limit=1)
                    existing_payment_acquirer = self.env['payment.acquirer'].search([
                        ('type','=','payment_gateway'),
                        ('agent_id','=',ho_obj.id),
                        ('bank_id','=',bank_obj.id),
                        ('account_number','=',False)
                    ])
                    if not existing_payment_acquirer:
                        self.env['payment.acquirer'].create({
                            'type': 'payment_gateway',
                            'name': bank_res['productName'],
                            'bank_id': bank_obj.id,
                            'agent_id': ho_obj.id,
                            'website_published': True
                        })
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise Exception(str(e))
