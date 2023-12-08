from odoo import api, fields, models, _
import logging,json,traceback
_logger = logging.getLogger(__name__)

PROVIDER_PAYMENT = [('espay','Espay'), ('snapespay', 'Snap Espay')]
class GetMerchantInfoPaymentAcquirer(models.TransientModel):
    _name = 'get.merchant.info.payment.acquirer'
    _description = 'Get Merchant Info Payment Acquirer'

    def get_domain(self):
        domain_id = self.env.ref('tt_base.tt_provider_type_payment').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=False, domain=get_domain)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    def sync_info(self):
        try:
            if self.ho_id:
                ho_obj = self.ho_id
            else:
                ho_obj = self.env.user.agent_id.ho_id
            res = self.env['tt.payment.api.con'].get_merchant_info({'provider':self.provider_id.code, 'type': 'close'}, ho_obj.id)
            _logger.info(json.dumps(res))
            if res['error_code'] == 0:
                for bank_res in res['response']:
                    bank_obj = self.env['tt.bank'].search([('code','=',bank_res['bankCode'])], limit=1)
                    existing_payment_acquirer = self.env['payment.acquirer'].search([
                        ('provider_id.code', '=', self.provider),
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
                            'website_published': True,
                            'provider_id': self.provider_id.id
                        })

            res = self.env['tt.payment.api.con'].get_merchant_info({'provider': self.provider_id.code, 'type': 'open'}, ho_obj.id)
            _logger.info(json.dumps(res))
            if res['error_code'] == 0:
                bank_code_list = [x['bankCode'] for x in res['response']]
                bank_code_list = set(bank_code_list)
                bank_code_list.discard('503')
                for bank_res in bank_code_list:
                    bank_obj = self.env['tt.bank'].search([('code', '=', bank_res)], limit=1)
                    if bank_obj:
                        existing_payment_acquirer = self.env['payment.acquirer'].search([
                            ('agent_id', '=', ho_obj.id),
                            ('type', '=', 'va'),
                            ('bank_id', '=', bank_obj.id),
                            ('provider_id', '=', self.provider_id.id)
                        ])
                        if not existing_payment_acquirer:
                            self.env['payment.acquirer'].create({
                                'type': 'va',
                                'bank_id': bank_obj.id,
                                'agent_id': ho_obj.id,
                                'ho_id': ho_obj.id,
                                'website_published': False,
                                'name': 'Your Virtual Account at %s' % (bank_obj.name),
                                'provider_id': self.provider_id.id
                            })
        except Exception as e:
            _logger.error(traceback.format_exc())
            raise Exception(str(e))
