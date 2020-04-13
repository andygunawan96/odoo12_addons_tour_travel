from odoo import api, fields, models, _
import json,random
import traceback,logging
from ...tools import variables
from ...tools import ERR,util
from ...tools.ERR import RequestException
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

PROVIDER_TYPE = {
    'AL': 'airline',
    'TN': 'train',
    'PS': 'passport',
    'VS': 'visa',
    'AT': 'activity',
    'TR': 'tour',
    'RESV': 'hotel'
}

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
    va_fee = fields.Float('VA Fee')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('pay.acq')
        return super(PaymentAcquirer, self).create(vals_list)
    # FUNGSI
    def generate_unique_amount(self,amount):
        # return int(self.env['ir.sequence'].next_by_code('tt.payment.unique.amount'))
        return self.env['unique.amount'].create({'amount':amount})

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
                'unique_amount': abs(uniq),
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

    def get_va_number(self, req, context):
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
        values = {
            'va': []
        }
        for acq in agent_obj.payment_acq_ids:
            if agent_obj.payment_acq_ids[0].state == 'open':
                values['va'].append(self.acquirer_format_VA(acq, 0, 0))
        return ERR.get_no_error(values)

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
                unique = self.generate_unique_amount(amount).upper_number
            elif req['transaction_type'] == 'billing':
                dom.append(('agent_id', '=', context['co_agent_id']))
                unique = 0

            values = {}
            if context['co_user_login'] != self.env.ref('tt_base.agent_b2c_user').login:
                for acq in self.sudo().search(dom):
                    if not values.get(acq.type) and acq.type != 'va' and acq.type != 'payment_gateway':
                        values[acq.type] = []
                    if acq.type != 'va' and acq.type != 'payment_gateway':
                        values[acq.type].append(acq.acquirer_format(amount,unique))
            #payment gateway
            if util.get_without_empty(req, 'order_number'):
                dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]
                dom.append(('agent_id', '=', self.env.ref('tt_base.rodex_ho').id))
                pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', req['order_number'])])
                if pay_acq_num:
                    unique = pay_acq_num[0].unique_amount * -1
                else:
                    unique = self.generate_unique_amount(amount).lower_number

                for acq in self.sudo().search(dom):
                    if not values.get(acq.type):
                        values[acq.type] = []
                    if acq.type == 'payment_gateway':
                        values[acq.type].append(acq.acquirer_format(amount, unique))
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
    unique_amount = fields.Float('Unique Amount')
    amount = fields.Float('Amount')
    state = fields.Selection([('open', 'Open'), ('close', 'Closed'), ('done','Done'), ('cancel','Expired')], 'Payment Type')
    display_name_payment = fields.Char('Display Name',compute="_compute_display_name_payment")

    @api.depends('number','payment_acquirer_id')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name_payment = "{} - {}".format(rec.payment_acquirer_id.name if rec.payment_acquirer_id.name != False else '',rec.number)

    def create_payment_acq_api(self, data):
        provider_type = 'tt.reservation.%s' % PROVIDER_TYPE[data['order_number'].split('.')[0]]
        booking_obj = self.env[provider_type].search([('name','=',data['order_number'])])

        if not booking_obj:
            raise RequestException(1001)

        payment_acq = self.search([('number', 'ilike', data['order_number'])])
        HO_acq = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id)
        if payment_acq:
            #check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq[len(payment_acq)-1].create_date
            if divmod(time_delta.seconds, 3600)[0] > 0:
                payment = self.env['payment.acquirer.number'].create({
                    'state': 'close',
                    'number': data['order_number'] + '.' + str(datetime.now().strftime('%Y%m%d%H:%M:%S')),
                    'unique_amount': data['unique_amount'],
                    'amount': data['amount'],
                    'payment_acquirer_id': HO_acq.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])]).id,
                    'res_model': provider_type,
                    'res_id': booking_obj.id
                })
                payment = {'order_number': payment.number}
            else:
                payment = {'order_number': payment_acq[len(payment_acq)-1].number}
        else:
            payment = self.env['payment.acquirer.number'].create({
                'state': 'close',
                'number': data['order_number'],
                'unique_amount': data['unique_amount'],
                'payment_acquirer_id': HO_acq.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])]).id,
                'amount': data['amount'],
                'res_model': provider_type,
                'res_id': booking_obj.id
            })
            payment = {'order_number': payment.number}
        return ERR.get_no_error(payment)

    def get_payment_acq_api(self, data):
        payment_acq = self.search([('number', '=', data['order_number'])])
        if payment_acq:
            res = {
                'order_number': data['order_number'],
                'create_date': payment_acq.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                'time_limit': (payment_acq.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                'nomor_rekening': self.env.ref('tt_base.payment_acquirer_ho_payment_gateway_bca').account_number,
                'amount': payment_acq.amount - payment_acq.unique_amount
            }
            return ERR.get_no_error(res)
        else:
            return ERR.get_error(additional_message='Order Number not found')


class PaymentUniqueAmount(models.Model):
    _name = 'unique.amount'
    _description = 'Rodex Model Unique Amount'

    amount = fields.Float('Amount', required=True)
    upper_number = fields.Integer('Up Number')
    lower_number = fields.Integer('Lower Number')
    active = fields.Boolean('Active',default=True)

    @api.model
    def create(self, vals_list):
        already_exist_on_same_amount = [rec.upper_number for rec in self.search([('amount', '=', vals_list['amount'])])]
        already_exist_on_lower_higher_amount = [abs(rec.lower_number) for rec in self.search([('amount', 'in', [int(vals_list['amount'])-1000,
                                                                                                    int(vals_list['amount'])+1000])])]
        already_exist = already_exist_on_same_amount+already_exist_on_lower_higher_amount
        unique_amount = None
        while (not unique_amount):
            number = random.randint(1,999)
            if number not in already_exist:
                unique_amount = number
        vals_list['upper_number'] = unique_amount
        vals_list['lower_number'] = unique_amount-1000
        new_unique = super(PaymentUniqueAmount, self).create(vals_list)
        return new_unique