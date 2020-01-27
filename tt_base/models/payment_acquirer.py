from odoo import api, fields, models, _
import json
import traceback,logging
from ...tools import variables
from ...tools import ERR,util

_logger = logging.getLogger(__name__)

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    type = fields.Selection(variables.ACQUIRER_TYPE, 'Payment Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    account_number = fields.Char('Account Number')
    account_name = fields.Char('Account Name')
    cust_fee = fields.Float('Customer Fee')
    bank_fee = fields.Float('Bank Fee')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('pay.acq')
        return super(PaymentAcquirer, self).create(vals_list)
    # FUNGSI
    def generate_unique_amount(self):
        return int(self.env['ir.sequence'].next_by_code('tt.payment.unique.amount'))

    def compute_fee(self,amount,unique = 0):
        uniq = 0
        # if self.type == 'transfer':
        if self.type != 'cash':
            uniq = unique

        amount = int(amount)
        cust_fee = 0
        bank_fee = 0
        if self.cust_fee:
            cust_fee = round(amount * self.cust_fee / 100)
        if self.bank_fee:
            bank_fee = round((amount+cust_fee) * self.bank_fee / 100)

        lost_or_profit = cust_fee-bank_fee

        return lost_or_profit,cust_fee, uniq

    def acquirer_format(self, amount,unique):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        loss_or_profit,fee, uniq = self.compute_fee(amount,unique)
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
            'total_amount': float(amount) + fee + uniq,
            'image': self.bank_id.image_id and self.bank_id.image_id.url or '',
            'return_url': '/payment/' + str(self.type) + '/feedback?acq_id=' + str(self.id)
        }

    def acquirer_format_VA(self, acq, amount,unique):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        payment_acq = self.env['payment.acquirer'].browse(acq.payment_acquirer_id)
        loss_or_profit, fee, uniq = self.compute_fee(unique)
        return {
            'seq_id': payment_acq.id.seq_id,
            'name': payment_acq.id.name,
            'account_name': acq.payment_acquirer_id.name or '-',
            'account_number': acq.number or '',
            'bank': {
                'name': payment_acq.id.bank_id.name or '',
                'code': payment_acq.id.bank_id.code or '',
            },
            'type': payment_acq.id.type,
            'provider_id': payment_acq.id.provider_id.id or '',
            'currency': 'IDR',
            'price_component': {
                'amount': amount,
                'fee': fee,
                'unique_amount': uniq,
            },
            'total_amount': float(amount) + fee + uniq,
            'image': payment_acq.id.bank_id.image_id and payment_acq.id.bank_id.image_id.url or '',
            'return_url': '/payment/' + str(payment_acq.id.type) + '/feedback?acq_id=' + str(payment_acq.id.id)
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
                amount = req.get('amount',0)

            dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]

            if req['transaction_type'] == 'top_up':
                # Kalau top up Ambil agent_id HO
                dom.append(('agent_id', '=', self.env.ref('tt_base.rodex_ho').id))
                unique = self.generate_unique_amount()
            elif req['transaction_type'] == 'billing':
                dom.append(('agent_id', '=', context['co_agent_id']))
                unique = 0


            values = {}
            for acq in self.sudo().search(dom):
                if not values.get(acq.type):
                    values[acq.type] = []
                values[acq.type].append(acq.acquirer_format(amount,unique))
            if req['transaction_type'] == 'top_up':
                for acq in agent_obj.payment_acq_ids:
                    if not values.get('va'):
                        values['va'] = []
                    if agent_obj.payment_acq_ids[0].state == 'open':
                        values['va'].append(self.acquirer_format_VA(acq, amount, unique))
            res = {}
            res['non_member'] = values
            res['member'] = {}
            if req.get('booker_seq_id'):
                res['member']['credit_limit'] = self.generate_credit_limit(req['booker_seq_id'], amount) if util.get_without_empty(req,'booker_seq_id') else []
            _logger.info("payment acq resp\n"+ json.dumps(res))
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error()

    def generate_credit_limit(self,booker_seq_id, amount):
        booker_obj = self.env['tt.customer'].search([('seq_id','=',booker_seq_id)])
        if not booker_obj:
            raise Exception('Booker not found')
        values = []
        for rec in booker_obj.customer_parent_ids:
            if rec.credit_limit != 0 and rec.state == 'done':
                values.append({
                    'name': rec.name,
                    'actual_balance': rec.actual_balance,
                    'credit_limit': rec.credit_limit,
                    'currency': rec.currency_id.name,
                    'seq_id': rec.seq_id,
                    'price_component': {
                        'amount': amount,
                        'fee': 0,
                        'unique_amount': 0
                    },
                    'total_amount': amount
                })
        return values

class PaymentAcquirerNumber(models.Model):
    _name = 'payment.acquirer.number'
    _rec_name = 'display_name_payment'
    _description = 'Rodex Model Payment Acquirer Number'

    res_id = fields.Integer('Res ID')
    res_model = fields.Char('Res Model')
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Acquirer')
    number = fields.Char('Number')
    state = fields.Selection([('open', 'Open'), ('close', 'Closed'), ('done','Done')], 'Payment Type')
    display_name_payment = fields.Char('Display Name',compute="_compute_display_name_payment")

    @api.depends('number','payment_acquirer_id')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name_payment = "{} - {}".format(rec.payment_acquirer_id.name,rec.number)