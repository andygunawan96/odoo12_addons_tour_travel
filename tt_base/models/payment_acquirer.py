from odoo import api, fields, models, _
from random import randint
import json
import traceback,logging
from ...tools import ERR,util

_logger = logging.getLogger(__name__)

TYPE = [
    ('cash', 'Cash'),
    ('transfer', 'Transfer'),
    ('installment', 'Installment'),
    ('va', 'Virtual Account')
]


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    seq_id = fields.Char('Sequence ID')
    type = fields.Selection(TYPE, 'Payment Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    account_number = fields.Char('Account Number')
    account_name = fields.Char('Account Name')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('pay.acq')
        return super(PaymentAcquirer, self).create(vals_list)
    # FUNGSI
    def generate_unique_amount(self):
        return int(self.env['ir.sequence'].next_by_code('tt.payment.unique.amount'))

    def compute_fee(self, amount):
        fee = uniq= 0
        if self.type == 'transfer':
            uniq = self.generate_unique_amount()
        elif self.type != 'cash':
            # TODO perhitungan per acquirer (Charge dari agent brapa, charge dari rodex brpa)
            fee = 5000
        return fee, uniq

    def acquirer_format(self, amount):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        fee, uniq = self.compute_fee(amount)
        return {
            'seq_id': self.seq_id,
            'name': self.name,
            'account_name': self.account_name or '-',
            'account_number': self.account_number or '',
            'bank': {
                'name': self.bank_id.name or '',
                'code': self.bank_id.code or '',
            },
            'type': self.type,
            'provider_id': self.provider_id.id or '',
            'currency': 'IDR',
            'price_component': {
                'amount': amount,
                'fee': fee,
                'unique_amount': uniq,
            },
            'total_amount': amount + fee + uniq,
            'image': self.image or '',
            'return_url': '/payment/' + str(self.type) + '/feedback?acq_id=' + str(self.id)
        }

    def button_test_acquirer(self):
        print(self.env['ir.sequence'].next_by_code('tt.payment.unique.amount'))
        # self.env['tt.cron.log'].create_cron_log_folder()
        # self.get_payment_acquirer_api({
        #     'transaction_type': 'billing',
        #     'amount': 16000,
        #     'booker_seq_id': 'CU.010101'
        # },{
        #     'agent_id': 5
        # })

    ##fixmee amount di cache
    def get_payment_acquirer_api(self, req,context):
        try:
            _logger.info("payment acq req\n"+json.dumps(req))

            agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
            if not agent_obj:
                # Return Error jika agent_id tidak ditemukan
                return ERR.get_error(1008)

            if util.get_without_empty(req,'order_number'):
                amount = self.env['tt.reservation.%s' % req['provider_type']].search([('name','=',req['order_number'])],limit=1).total
            else:
                amount = req.get('amount')

            dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]
            # Ambil agent_id Parent nya (Citranya corpor tsb)
            # if agent_obj.agent_type_id.id in (self.env.ref('tt_base_rodex.agent_type_cor').id,
            #                                   self.env.ref('tt_base_rodex.agent_type_por').id):
            if req['transaction_type'] == 'top_up':
                # Kalau top up Ambil agent_id HO
                dom.append(('agent_id', '=', self.env['tt.agent'].sudo().search([('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id )], limit=1).id))
                amount = self.env['tt.top.up'].sudo().search([('name','=',req['top_up_name'])]).total
            elif req['transaction_type'] == 'billing':
                dom.append(('agent_id', '=', context['agent_id']))

            values = {}
            for acq in self.sudo().search(dom):
                if not values.get(acq.type):
                    values[acq.type] = []
                values[acq.type].append(acq.acquirer_format(amount))
            res = {}
            res['non_member'] = values
            res['member'] = {}
            if req.get('booker_seq_id'):
                res['member']['credit_limit'] = self.generate_credit_limit(req['booker_seq_id']) if util.get_without_empty(req,'booker_seq_id') else []
            _logger.info("payment acq resp\n"+ json.dumps(res))
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error()

    def generate_credit_limit(self,booker_seq_id):
        booker_obj = self.env['tt.customer'].search([('seq_id','=',booker_seq_id)])
        if not booker_obj:
            raise Exception('Booker not found')
        values = []
        for rec in booker_obj.customer_parent_ids:
            if rec.credit_limit != 0:
                values.append({
                    'name': rec.name,
                    'actual_balance': rec.actual_balance,
                    'credit_limit': rec.credit_limit,
                    'currency': rec.currency_id.name,
                    'seq_id': rec.seq_id
                })
        return values