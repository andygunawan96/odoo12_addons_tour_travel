from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json,random
import traceback,logging
from ...tools import variables
from ...tools import ERR,util
from ...tools.ERR import RequestException
from datetime import datetime, timedelta
import pytz
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
    va_fee = fields.Float('VA Fee')
    is_sunday_off = fields.Boolean('Sunday Off')
    is_specific_time = fields.Boolean('Specific Time')
    start_time = fields.Float(string='Start Time', help="Format: HH:mm Range 00:00 => 24:00")
    end_time = fields.Float(string='End Time', help="Format: HH:mm Range 00:00 => 24:00")

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

    @api.onchange('start_time', 'end_time')
    def check_start_end_time(self):
        # Opsi #1 Control klo user input 24 ++
        # self.start_time = self.start_time % 24
        # self.end_time = self.end_time % 24
        # Opsi #2 Notif alert
        if self.start_time > 24:
            raise UserError(_('Start Date range 00:00 -> 24:00'))
        if self.end_time > 24:
            raise UserError(_('End Date range 00:00 -> 24:00'))

        # Replace 00:05 => 24:10
        # self.start_time = self.start_time / 1 == 0 and self.start_time + 24
        if self.end_time == 0.0:
            self.end_time += 24
        # if self.start_time and self.end_time:
        #     if self.start_time > self.end_time:
        #         raise UserError(_('End Date cannot be lower than Start Time.'))

    def acquirer_format(self, amount, unique):
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

    def convert_time_to_float(self,time):
        str_time = time.strftime("%H:%M").split(':')
        float_time = int(str_time[0]) + (float(str_time[1])/60)
        return float_time

    def check_is_holiday(self,now_time):
        holiday_objs = self.env['tt.public.holiday'].search([('country_id','=',self.env.ref('base.id').id),
                                              ('date','=',now_time.strftime('%Y-%m-%d'))])
        if holiday_objs:
            return True
        return False

    def validate_time(self,acq,now_time):
        ## yang vlaid adalah yang tidak off mingu atau jika minggu of hari ini bukan hari minggu
        if acq.is_sunday_off == False or (acq.is_sunday_off == True and now_time.strftime("%a") != 'Sun'):
            ##pengecekan hari libur, di asumsikan yang hari minggu OFF juga OFF di hari libur
            if acq.is_sunday_off and self.check_is_holiday(now_time):
                return False

            ##jika check jam
            if acq.is_specific_time:
                #convert jam sekarang %M:%S ke float, 16:41 ke 16.0,683333333
                now_float_time = self.convert_time_to_float(now_time)
                overnight = acq.start_time > acq.end_time # jika overnight seperti jam 4 sore hingga 11 pagi, 16 - 11
                if overnight:
                    return not acq.end_time < now_float_time < acq.start_time #return True jika di luar jam 11 pagi hingga 16 sore
                else:
                    return acq.start_time <= now_float_time <= acq.end_time

            return True
        return False

    ## test function for payment acquirer
    def test_validate(self,acq):
        print(acq.name + " " + str(acq.start_time) + " " + str(acq.end_time))
        test_case = []
        for hour in range (24):
            for minute in range (60):
                cur_val = datetime.strptime("2020-08-03 %s:%s:30" % (hour,minute),'%Y-%m-%d %H:%M:%S')
                test_case.append(cur_val)
                print(str(cur_val) + " : " + str(self.validate_time(acq,cur_val)))
        print("######################\n\n")

    ##fixmee amount di cache
    def get_payment_acquirer_api(self, req, context):
        try:
            _logger.info("payment acq req\n" + json.dumps(req))

            agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
            if not agent_obj:
                # Return Error jika agent_id tidak ditemukan
                return ERR.get_error(1008)

            if util.get_without_empty(req, 'order_number'):
                book_obj = self.env['tt.reservation.%s' % req['provider_type']].search([('name', '=', req['order_number'])], limit=1)
                amount = book_obj.total
                co_agent_id = book_obj.agent_id.id ## untuk kalau HO issuedkan channel, supaya payment acquirerny tetap punya agentnya
            else:
                amount = req.get('amount', 0)
                co_agent_id = context['co_agent_id']

            dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]

            if req['transaction_type'] == 'top_up':
                # Kalau top up Ambil agent_id HO
                dom.append(('agent_id', '=', self.env.ref('tt_base.rodex_ho').id))
                unique = self.generate_unique_amount(amount).upper_number
            elif req['transaction_type'] == 'billing':
                dom.append(('agent_id', '=', co_agent_id))
                unique = 0

            values = {}
            now_time = datetime.now(pytz.timezone('Asia/Jakarta'))
            if context['co_user_login'] != self.env.ref('tt_base.agent_b2c_user').login:
                for acq in self.sudo().search(dom):
                    if acq.type != 'va' and acq.type != 'payment_gateway':
                        # self.test_validate(acq) utk testig saja
                        if self.validate_time(acq, now_time):
                            if not values.get(acq.type):
                                values[acq.type] = []
                            values[acq.type].append(acq.acquirer_format(amount, unique))

            # # payment gateway
            if util.get_without_empty(req, 'order_number'):
                dom = [('website_published', '=', True), ('company_id', '=', self.env.user.company_id.id)]
                dom.append(('agent_id', '=', self.env.ref('tt_base.rodex_ho').id))
                pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', req['order_number'])])
                if pay_acq_num:
                    unique = pay_acq_num[0].unique_amount * -1
                else:
                    unique = self.generate_unique_amount(amount).lower_number
                for acq in self.sudo().search(dom):
                    # self.test_validate(acq) utk testing saja
                    if acq.type == 'va' or acq.type == 'payment_gateway':
                        if self.validate_time(acq,now_time):
                            if not values.get(acq.type):
                                values[acq.type] = []
                            if acq.account_number != '':
                                values[acq.type].append(acq.acquirer_format(amount, unique))
                            else:
                                values[acq.type].append(acq.acquirer_format(amount, 0))

            res = {}
            res['non_member'] = values
            res['member'] = {}
            if req.get('booker_seq_id'):
                res['member']['credit_limit'] = self.generate_credit_limit(req['booker_seq_id'], amount) if util.get_without_empty(req, 'booker_seq_id') else []
            _logger.info("payment acq resp\n" + json.dumps(res))
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
    va_number = fields.Char('VA Number')
    unique_amount = fields.Float('Unique Amount')
    fee_amount = fields.Float('Fee Amount')
    amount = fields.Float('Amount')
    state = fields.Selection([('open', 'Open'), ('close', 'Closed'), ('done','Done'), ('cancel','Expired')], 'Payment Type')
    display_name_payment = fields.Char('Display Name',compute="_compute_display_name_payment")

    @api.depends('number','payment_acquirer_id')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name_payment = "{} - {}".format(rec.payment_acquirer_id.name if rec.payment_acquirer_id.name != False else '',rec.number)

    def create_payment_acq_api(self, data):
        provider_type = 'tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
        booking_obj = self.env[provider_type].search([('name','=',data['order_number'])])

        if not booking_obj:
            raise RequestException(1001)

        payment_acq_number = self.search([('number', 'ilike', data['order_number'])])
        HO_acq = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id)
        if payment_acq_number:
            #check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number)-1].create_date
            if divmod(time_delta.seconds, 3600)[0] > 0:
                for rec in payment_acq_number:
                    if rec.state == 'close':
                        rec.state = 'cancel'
                payment = self.env['payment.acquirer.number'].create({
                    'state': 'close',
                    'number': data['order_number'] + '.' + str(datetime.now().strftime('%Y%m%d%H:%M:%S')),
                    'unique_amount': data['unique_amount'],
                    'amount': data['amount'],
                    'payment_acquirer_id': HO_acq.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])]).id,
                    'res_model': provider_type,
                    'res_id': booking_obj.id
                })
                booking_obj.payment_acquirer_number_id = payment.id
                payment = {'order_number': payment.number}
            else:
                payment = {'order_number': payment_acq_number[len(payment_acq_number)-1].number}
                booking_obj.payment_acquirer_number_id = payment_acq_number[len(payment_acq_number)-1].id
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
            booking_obj.payment_acquirer_number_id = payment.id
            payment = {'order_number': payment.number}
        return ERR.get_no_error(payment)

    def get_payment_acq_api(self, data):
        payment_acq_number = self.search([('number', 'ilike', data['order_number'])], order='create_date desc', limit=1)
        if payment_acq_number:
            # check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number) - 1].create_date
            if divmod(time_delta.seconds, 3600)[0] == 0:
                res = {
                    'order_number': data['order_number'],
                    'create_date': payment_acq_number.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'time_limit': (payment_acq_number.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    'nomor_rekening': payment_acq_number.payment_acquirer_id.account_number,
                    'amount': payment_acq_number.amount - payment_acq_number.unique_amount
                }
                return ERR.get_no_error(res)
            else:
                return ERR.get_error(additional_message='Order Has Been Expired')
        else:
            return ERR.get_error(additional_message='Order Number not found')

    def set_va_number_api(self, data):
        payment_acq_number = self.search([('number', 'ilike', data['order_number'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.va_number = data['va_number']
            return ERR.get_no_error()
        else:
            return ERR.get_error(additional_message='Payment Acquirer not found')


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