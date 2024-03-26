from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json,random
import traceback,logging
from ...tools import variables
from ...tools import ERR,util
from ...tools.ERR import RequestException
from datetime import datetime, timedelta
import math
import pytz
_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    type = fields.Selection(variables.ACQUIRER_TYPE, 'Payment Type', help="Credit card for top up")
    provider_id = fields.Many2one('tt.provider', 'Provider')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    account_number = fields.Char('Account Number')
    account_name = fields.Char('Account Name')
    cust_fee = fields.Float('Customer Fee')
    bank_fee = fields.Float('Bank Fee')
    va_fee = fields.Float('Fee Flat') ## NAMA VA DI HAPUS KARENA UNTUK FEE CREDIT CARD ESPAY JUGA UNTUK FLAT NAMA FIELD SUDAH MASUK INI
    fee_percentage = fields.Float('Fee Percentage') ## NAMA VA DI HAPUS KARENA UNTUK FEE CREDIT CARD ESPAY JUGA
    online_wallet = fields.Boolean('Online Wallet', help="""For DANAPAY, OVO""")
    is_sunday_off = fields.Boolean('Sunday Off')
    is_specific_time = fields.Boolean('Specific Time')
    start_time = fields.Float(string='Start Time', help="Format: HH:mm Range 00:00 => 24:00")
    end_time = fields.Float(string='End Time', help="Format: HH:mm Range 00:00 => 24:00")
    description_msg = fields.Text('Description')
    show_device_type = fields.Selection([('web', 'Website'), ('mobile', 'Mobile'), ('all', 'All')], 'Show Device', default='all')
    save_url = fields.Boolean('Save URL', help="""For Shopee, Modern channel, linkAja, Credit Card""")
    is_calculate_credit_card_fee = fields.Boolean('Is Credit Card Fee (Espay)', help="""For Credit Card""")
    minimum_amount = fields.Float('Minimum Amount', help="""Minimum fee amount""")

    agent_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Agent Type Access Type', default='all')
    payment_acquirer_agent_type_eligibility_ids = fields.Many2many("tt.agent.type", "tt_agent_type_tt_payment_acquirer_rel","payment_acquirer_id", "tt_agent_type_id","Agent Type")  # type of agent that are able to use the voucher
    provider_type_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Provider Type Access Type', default='all')
    payment_acquirer_provider_type_eligibility_ids = fields.Many2many("tt.provider.type", "tt_provider_type_payment_acquirer_rel","payment_acquirer_id", "tt_provider_type_id","Provider Type")  # what product this voucher can be applied

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('pay.acq')
        return super(PaymentAcquirer, self).create(vals_list)

    def set_payment_provider(self):
        ### UPDATE DATA LAMA KE ESPAY
        provider_obj = self.env['tt.provider'].search([('code', '=', 'espay')], limit=1)
        payment_acq_objs = self.search([('type','in',['va', 'payment_gateway', 'creditcard_topup'])])
        for payment_acq_obj in payment_acq_objs:
            payment_acq_obj.provider_id = provider_obj.id

    # FUNGSI
    def generate_unique_amount_api(self, vals, context):
        return self.env['unique.amount'].create_unique_amount_api(vals, context)

    def generate_unique_amount(self,amount,downsell=False):
        # return int(self.env['ir.sequence'].next_by_code('tt.payment.unique.amount'))
        return self.env['unique.amount'].create({'amount':amount,'is_downsell':downsell})

    def compute_fee(self,amount,unique = 0):
        uniq = 0
        # if self.type == 'transfer':
        if self.type != 'cash':
            uniq = unique

        amount = int(amount)
        cust_fee = 0
        bank_fee = 0
        ##hitung fee karena EDC dll tidak pengaruh ke ledger invoice dll. hanya pencatatan
        if self.cust_fee:
            cust_fee = round(amount * self.cust_fee / 100)
        if self.bank_fee:
            bank_fee = round((amount+cust_fee) * self.bank_fee / 100)
        ##untuk VA fee, jika VA fee pasti bukan EDC jadi bisa replace

        if self.is_calculate_credit_card_fee: ## UNTUK CREDIT CARD ESPAY
            total_fee = int(round((amount + self.va_fee) / ((100-self.fee_percentage)/100) * (self.fee_percentage/100), 0)) + self.va_fee
            if total_fee > self.minimum_amount:
                return 0, total_fee, uniq
            else:
                return 0, self.minimum_amount, uniq
        elif self.va_fee or self.fee_percentage:
            total_fee = math.ceil(self.fee_percentage * (amount + self.va_fee) / 100 + self.va_fee)
            if total_fee > self.minimum_amount:
                return 0, total_fee, uniq
            else:
                return 0, self.minimum_amount, uniq
        else:
            lost_or_profit = cust_fee-bank_fee
            return lost_or_profit,cust_fee, uniq

    ## Freeze the browser when there are many payment acquirers
    # @api.onchange('start_time', 'end_time')
    # def check_start_end_time(self):
    #     # Opsi #1 Control klo user input 24 ++
    #     # self.start_time = self.start_time % 24
    #     # self.end_time = self.end_time % 24
    #     # Opsi #2 Notif alert
    #     if self.start_time > 24:
    #         raise UserError(_('Start Date range 00:00 -> 24:00'))
    #     if self.end_time > 24:
    #         raise UserError(_('End Date range 00:00 -> 24:00'))
    #
    #     # Replace 00:05 => 24:10
    #     # self.start_time = self.start_time / 1 == 0 and self.start_time + 24
    #     if self.end_time == 0.0:
    #         self.end_time += 24
    #     # if self.start_time and self.end_time:
    #     #     if self.start_time > self.end_time:
    #     #         raise UserError(_('End Date cannot be lower than Start Time.'))

    def acquirer_format(self, amount, unique, agent_obj=None, currency_name='', context={}):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        loss_or_profit,fee, uniq = self.compute_fee(amount,unique)
        minimum_amount = {
            "default": 0,
            "with_point": 0
        }
        minimum_amount_default = self.minimum_amount + uniq
        if self.type == 'credit':
            minimum_amount_default += fee
        elif self.type == 'creditcard_topup':
            uniq = 0
        minimum_amount['default'] = minimum_amount_default

        ###POINT
        amount_when_use_point = 0
        fee_point = 0
        uniq_point = 0
        website_use_point_reward = self.env['ir.config_parameter'].sudo().get_param('use_point_reward')
        if not currency_name:
            if context:
                agent_obj = self.env['tt.agent'].browse(context['co_ho_id'])
                if agent_obj:
                    currency_name = agent_obj.ho_id.currency_id.name
        res_payment_acq = {
            'acquirer_seq_id': self.seq_id,
            'name': self.name,
            'account_name': self.account_name or '-',
            'account_number': self.account_number or '',
            'bank': {
                'name': self.bank_id.name or '',
                'code': self.bank_id.code or '',
            },
            'type': self.type,
            'currency': currency_name,
            'price_component': {
                'amount': amount,
                'fee': fee,
                'unique_amount': uniq,
            },
            'provider': self.provider_id.code if self.provider_id else '',
            'online_wallet': self.online_wallet,
            'save_url': self.save_url,
            'show_device_type': self.show_device_type,
            'total_amount': float(amount) + uniq + fee,

            'image': self.bank_id.image_id and self.bank_id.image_id.url or '',
            'description_msg': self.description_msg or '',
            'minimum_amount': minimum_amount
        }
        if website_use_point_reward == 'True':
            point_reward = agent_obj.actual_point_reward
            minimum_amount_with_point = self.minimum_amount
            if point_reward - minimum_amount_with_point > amount:
                total_use_point = amount - minimum_amount_with_point
            else:
                total_use_point = point_reward
            amount_when_use_point = amount - total_use_point
            loss_or_profit_point, fee_point, uniq_point = self.compute_fee(amount_when_use_point, unique)

            with_point_minimum_amount = self.minimum_amount + uniq_point
            if self.type == 'credit':
                with_point_minimum_amount += fee_point
            minimum_amount['with_point'] = with_point_minimum_amount
            res_payment_acq.update({
                'total_amount_with_point': float(amount_when_use_point) + uniq_point + fee_point,
                'price_component_with_point': {
                    'amount': amount_when_use_point,
                    'fee': fee_point,
                    'unique_amount': uniq_point,
                },
            })
        return res_payment_acq

    def acquirer_format_VA(self, acq, amount,unique, currency_name='', context={}):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        payment_acq = self.env['payment.acquirer'].browse(acq.payment_acquirer_id.id)
        loss_or_profit, fee, uniq = acq.payment_acquirer_id.compute_fee(unique)
        if not currency_name:
            if context:
                agent_obj = self.env['tt.agent'].browse(context['co_ho_id'])
                if agent_obj:
                    currency_name = agent_obj.ho_id.currency_id.name
        return {
            'acquirer_seq_id': payment_acq.seq_id,
            'name': payment_acq.name,
            'account_name': acq.payment_acquirer_id.name or '-',
            'account_number': acq.number or '',
            'bank': {
                'name': payment_acq.bank_id.name or '',
                'code': payment_acq.bank_id.code or '',
            },
            'type': payment_acq.type,
            'currency': currency_name,
            'price_component': {
                'amount': amount,
                'fee': fee,
                'unique_amount': uniq,
            },
            'total_amount': float(amount) + fee + uniq,
            'image': payment_acq.bank_id.image_id and payment_acq.bank_id.image_id.url or '',
            'description_msg': payment_acq.description_msg or ''
        }

    def get_va_number(self, req, context):
        # get HO min_topup_amount juga disini
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
        payment_acq_open_ho = self.env['payment.acquirer'].search([('type','=','va'), ('ho_id','=', context['co_ho_id'])])
        if payment_acq_open_ho:
            is_ho_have_open_top_up = True
        else:
            is_ho_have_open_top_up = False
        values = {
            'va': [],
            'min_topup_amount': agent_obj.ho_id.min_topup_amount,
            'topup_increment_amount': agent_obj.ho_id.topup_increment_amount,
            'is_ho_have_open_top_up': is_ho_have_open_top_up
        }
        currency_name = agent_obj.ho_id.currency_id.name
        for acq in agent_obj.payment_acq_ids:
            if acq.state == 'open':
                values['va'].append(self.acquirer_format_VA(acq, 0, 0, currency_name, context))
        return ERR.get_no_error(values)

    def get_va_bank(self, req, context):
        ho_agent_obj = self.env['tt.agent'].search([('seq_id', '=', context['co_ho_seq_id'])], limit=1) #o3
        # ho_agent_obj = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id) #o2
        existing_payment_acquirer = self.env['payment.acquirer'].search([('agent_id', '=', ho_agent_obj.id), ('type', '!=', 'cash')])
        values = []
        for acq in existing_payment_acquirer:
            values.append({
                "acquirer_seq_id": acq.seq_id,
                "name": acq.name,
                "type": acq.type
            })
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
            res = {
                "agent": [],
                "customer": {
                    "member": {}
                }
            }

            book_obj = None
            user_obj = self.env['res.users'].browse(context['co_uid']) # untuk process channel booking 
            agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
            if not agent_obj:
                # Return Error jika agent_id tidak ditemukan
                return ERR.get_error(1008)

            if util.get_without_empty(req, 'order_number'):
                book_obj = self.env['tt.reservation.%s' % req['provider_type']].search([('name', '=', req['order_number'])], limit=1)
                amount = book_obj.total - book_obj.total_discount
                ## 19 JUN 2023 IVAN check partial_booking
                if book_obj.state == 'partial_booked':
                    for provider in book_obj.provider_booking_ids:
                        ## check jika ada yang fail_booked, total amount di kurangkan
                        if provider.state in ['fail_booked']: ## halt tetap di hitung
                            for svc in provider.cost_service_charge_ids:
                                if svc.charge_type != 'RAC':
                                    amount -= svc.total
                co_agent_id = book_obj.agent_id.id ## untuk kalau HO issuedkan channel, supaya payment acquirerny tetap punya agentnya
                currency = book_obj.currency_id.name
            else:
                amount = req.get('amount', 0)
                co_agent_id = context['co_agent_id']
                currency = req.get('currency', '')

            if not context.get('co_customer_parent_id'):  ## kalau bukan user corporate login sendiri
                dom = [
                    ('website_published', '=', True),
                    ('company_id', '=', self.env.user.company_id.id),
                    ('type', 'not in', ['va', 'payment_gateway'])
                ]
                can_use_payment_gateway_only = False #HANYA BOLEH PAYMENT GATEWAY
                if book_obj: #ASUMSI SELAMA BELUM BOOKING AGENT BOOK & YANG BAYAR SAMA
                    #BEDA AGENT & TIDAK PUNYA PROCESS CHANNEL BOOKING
                    if context['co_agent_id'] != book_obj.agent_id.id and self.env.ref('tt_base.group_tt_process_channel_bookings').id not in user_obj.groups_id.ids:
                        # CHECK PRODUCT PHC/PERIKSAIN & PUNYA PROCESS CHANNEL BOOKING MEDICAL
                        if req['provider_type'] in ['phc', 'periksain'] and self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids:
                            can_use_payment_gateway_only = False
                        else:
                            can_use_payment_gateway_only = True

                    if can_use_payment_gateway_only: ##YANG BAYAR BEDA AGAR SEMUA PAYMENT METHOD TIDAK DAPAT
                        dom.append(('type', '=', 'payment_gateway'))
                if req['transaction_type'] != 'top_up':
                    dom.append(('type', '!=', 'creditcard_topup'))
                unique = 0
                if req['transaction_type'] == 'top_up':
                    # Kalau top up Ambil agent_id HO
                    dom.append(('agent_id', '=', context['co_ho_id']))
                    unique = self.generate_unique_amount_api({'amount': amount, 'is_downsell': False}, context).get_unique_amount()
                elif req['transaction_type'] == 'billing':
                    dom.append(('agent_id', '=', co_agent_id))

                values = {}
                now_time = datetime.now(pytz.timezone('Asia/Jakarta'))
                # tanpa ORDER NUMBER
                if not self.env['tt.agent'].browse(co_agent_id).is_btc_agent or req['order_number'].split('.')[0] == 'PH' and self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids: #PHC pakai process channel operator
                    for acq in self.sudo().search(dom):
                        # self.test_validate(acq) utk testing saja
                        if self.validate_time(acq, now_time):
                            if not values.get(acq.type):
                                values[acq.type] = []
                            values[acq.type].append(acq.acquirer_format(amount, unique, self.env['tt.agent'].browse(co_agent_id), currency, context))

                # # payment gateway
                # dengan ORDER NUMBER
                if util.get_without_empty(req, 'order_number'):
                    ho_agent_obj = agent_obj.ho_id
                    dom = [
                        ('website_published', '=', True),
                        ('company_id', '=', self.env.user.company_id.id),
                        ('agent_id', '=', ho_agent_obj.id),
                        ('type', 'in', ['payment_gateway']),  ## search yg mutasi bca / creditcard espay
                    ]
                    # pay_acq_num = self.env['payment.acquirer.number'].search([('number', 'ilike', req['order_number']), ('state', '=', 'closed')])
                    # if pay_acq_num:
                    #     unique = pay_acq_num[0].unique_amount
                    # else:
                    #     unique = 0
                    #     if book_obj.unique_amount_id:
                    #         if book_obj.unique_amount_id.active:
                    #             unique = book_obj.unique_amount_id.get_unique_amount()
                    #     if not unique:
                    #         if book_obj.agent_id.agent_type_id == self.env.ref('tt_base.agent_b2c_user').agent_id.agent_type_id:
                    #             unique_obj = self.generate_unique_amount(amount, downsell=True)  #penjualan B2C
                    #         else:
                    #             unique_obj = self.generate_unique_amount(amount, downsell=False)  # penjualan B2B
                    #         book_obj.unique_amount_id = unique_obj.id
                    #         unique = unique_obj.get_unique_amount()

                    for acq in self.sudo().search(dom):
                        # self.test_validate(acq) utk testing saja
                        if self.validate_time(acq,now_time):
                            # if acq.account_number:
                            #     values[acq.type].append(acq.acquirer_format(amount, unique))
                            # else:
                            if acq.type == 'payment_gateway':
                                is_agent = False
                                is_provider_type = False
                                if acq.agent_type_access_type == 'all':
                                    is_agent = True
                                elif acq.agent_type_access_type == 'allow' and agent_obj.agent_type_id and agent_obj.agent_type_id in acq.payment_acquirer_agent_type_eligibility_ids:
                                    is_agent = True
                                elif acq.agent_type_access_type == 'restrict' and agent_obj.agent_type_id and agent_obj.agent_type_id not in acq.payment_acquirer_agent_type_eligibility_ids:
                                    is_agent = True

                                if acq.provider_type_access_type == 'all':
                                    is_provider_type = True
                                elif acq.provider_type_access_type == 'allow' and book_obj.provider_type_id and book_obj.provider_type_id in acq.payment_acquirer_provider_type_eligibility_ids:
                                    is_provider_type = True
                                elif acq.provider_type_access_type == 'restrict' and book_obj.provider_type_id and book_obj.provider_type_id not in acq.payment_acquirer_provider_type_eligibility_ids:
                                    is_provider_type = True
                                if is_agent and is_provider_type:
                                    if not values.get(acq.type):
                                        values[acq.type] = []
                                    values[acq.type].append(acq.acquirer_format(amount, 0, self.env['tt.agent'].browse(co_agent_id), currency, context))
                            else:
                                if not values.get(acq.type):
                                    values[acq.type] = []
                                values[acq.type].append(acq.acquirer_format(amount, 0, self.env['tt.agent'].browse(co_agent_id), currency, context))

                res['customer']['non_member'] = values
                can_use_cor_account = True
                if book_obj:
                    if req.get('booker_seq_id') and context['co_agent_id'] != book_obj.agent_id.id:
                        can_use_cor_account = False
                if can_use_cor_account:
                    res['customer']['member']['credit_limit'] = self.generate_credit_limit(amount,booker_seq_id=req['booker_seq_id']) if util.get_without_empty(req, 'booker_seq_id') else []
            else:#user corporate login sendiri
                if context.get('co_customer_parent_id') and (book_obj and context['co_agent_id'] == book_obj.agent_id.id or context.get('co_customer_parent_id')): #booking / force issued
                    res['customer']['member']['credit_limit'] = self.generate_credit_limit(amount,customer_parent_id=context.get('co_customer_parent_id')) if util.get_without_empty(context, 'co_customer_parent_id') else []

            ## payment agent

            ## CREDIT LIMIT AGENT
            try:
                ### GET BOOKING ###
                can_use_credit_limit = False
                if hasattr(book_obj,'agent_id'):
                    if book_obj.agent_id.credit_limit > 0:
                        can_use_credit_limit = False
                        is_provider_type = True
                        is_provider = True
                        if book_obj.provider_type_id.code in ['groupbooking', 'tour']:  ## if untuk product yg bisa installment, dibuat tidak bisa karena jika di pakai akan bug di payment harus rombak total
                            is_provider_type = False
                        ## asumsi kalau all pasti True
                        if book_obj.agent_id.agent_credit_limit_provider_type_access_type == 'allow' and book_obj.provider_type_id not in book_obj.agent_id.agent_credit_limit_provider_type_eligibility_ids or \
                                book_obj.agent_id.agent_credit_limit_provider_type_access_type == 'restrict' and book_obj.provider_type_id in book_obj.agent_id.agent_credit_limit_provider_type_eligibility_ids:
                            is_provider_type = False
                        for provider_booking in book_obj.provider_booking_ids:
                            if book_obj.agent_id.agent_credit_limit_provider_access_type == 'allow' and provider_booking.provider_id not in book_obj.agent_id.agent_credit_limit_provider_eligibility_ids or \
                                    book_obj.agent_id.agent_credit_limit_provider_access_type == 'restrict' and provider_booking.provider_id in book_obj.agent_id.agent_credit_limit_provider_eligibility_ids:
                                is_provider = False
                                break
                        if is_provider_type and is_provider:
                            can_use_credit_limit = True
                        if can_use_credit_limit:
                            credit_limit = self.generate_agent_payment(amount, book_obj.agent_id.id, 'credit_limit')
                            if credit_limit != {}:
                                res['agent'].append(credit_limit)
                    ## BALANCE
                    res['agent'].append(self.generate_agent_payment(amount, book_obj.agent_id.id, 'balance'))
                elif agent_obj.credit_limit > 0:
                    can_use_credit_limit = False
                    is_provider_type = True
                    is_provider = True
                    ## asumsi kalau all pasti True

                    provider_type_obj = self.env['tt.provider.type'].search([('code', '=', req['provider_type'])],
                                                                            limit=1)
                    if req['provider_type'] in ['groupbooking',
                                                'tour']:  ## if untuk product yg bisa installment, dibuat tidak bisa karena jika di pakai akan bug di payment harus rombak total
                        is_provider_type = False
                    if agent_obj.agent_credit_limit_provider_type_access_type == 'allow' and provider_type_obj not in agent_obj.agent_credit_limit_provider_type_eligibility_ids or \
                            agent_obj.agent_credit_limit_provider_type_access_type == 'restrict' and provider_type_obj in agent_obj.agent_credit_limit_provider_type_eligibility_ids:
                        is_provider_type = False
                    if req.get('provider_list'):
                        if len(req['provider_list']) > 0:
                            for provider_code in req['provider_list']:
                                provider_obj = self.env['tt.provider'].search([('code', '=', provider_code)], limit=1)
                                if agent_obj.agent_credit_limit_provider_access_type == 'allow' and provider_obj not in agent_obj.agent_credit_limit_provider_eligibility_ids or \
                                        agent_obj.agent_credit_limit_provider_access_type == 'restrict' and provider_obj in agent_obj.agent_credit_limit_provider_eligibility_ids:
                                    is_provider = False
                                    break
                        elif agent_obj.agent_credit_limit_provider_access_type != 'all':
                            is_provider = False
                    if is_provider_type and is_provider:
                        can_use_credit_limit = True
                    if can_use_credit_limit:
                        credit_limit = self.generate_agent_payment(amount, agent_obj.id, 'credit_limit')
                        if credit_limit != {}:
                            res['agent'].append(credit_limit)
                    ## BALANCE
                    res['agent'].append(self.generate_agent_payment(amount, agent_obj.id, 'balance'))
            except Exception as e:
                _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error()

    def generate_agent_payment(self, amount, agent_id, type):
        agent_obj = self.env['tt.agent'].browse(agent_id)
        if type == 'credit_limit':
            if agent_obj.actual_credit_balance >= amount:
                fee_credit_limit = ((agent_obj.tax_percentage / 100) * (amount))
                values = {
                    'payment_method': 'credit_limit',
                    'name': 'Credit Limit',
                    'actual_balance': agent_obj.actual_credit_balance,
                    'credit_limit': agent_obj.credit_limit,
                    'currency': agent_obj.currency_id.name,
                    'price_component': {
                        'amount': amount,
                        'fee': fee_credit_limit,
                        'unique_amount': 0
                    },
                    'total_amount': amount + fee_credit_limit
                }
            else:
                values = {}
        else:
            values = {
                'payment_method': 'balance',
                'name': 'Balance',
                'balance': agent_obj.balance,
                'currency': agent_obj.currency_id.name,
                'price_component': {
                    'amount': amount,
                    'fee': 0,
                    'unique_amount': 0
                },
                'total_amount': amount
            }
        return values

    def generate_credit_limit(self,amount,booker_seq_id=False,customer_parent_id=False):## booker_seq_id,amount,customer_parent_id
        if customer_parent_id: ## generate credit limit from specific customer parent
            parent_obj = self.env['tt.customer.parent'].browse(customer_parent_id)
            try:
                parent_obj.create_date
            except:
                raise Exception('Customer Parent not Found')
            parent_obj_list = [parent_obj]
        else: ## generate all of the booker customer parent
            booker_obj = self.env['tt.customer'].search([('seq_id','=',booker_seq_id)])
            if not booker_obj:
                raise Exception('Booker Not Found')
            # parent_obj_list = booker_obj.booker_parent_ids
            parent_obj_list = []
            for par in booker_obj.customer_parent_booker_ids:
                parent_obj_list.append(par.customer_parent_id)
        values = []
        for rec in parent_obj_list:
            if rec.state == 'done':
                if rec.check_use_ext_credit_limit():
                    ext_credit = rec.get_external_credit_limit()
                    values.append({
                        'name': rec.name,
                        'actual_balance': ext_credit,
                        'credit_limit': ext_credit,
                        'currency': rec.currency_id.name,
                        'acquirer_seq_id': rec.seq_id,
                        'price_component': {
                            'amount': amount,
                            'fee': 0,
                            'unique_amount': 0
                        },
                        'total_amount': amount
                    })
                elif rec.check_balance_limit():
                    bal_info = rec.get_balance_info()
                    values.append({
                        'name': rec.name,
                        'actual_balance': bal_info['actual_balance'],
                        'credit_limit': bal_info['credit_limit'],
                        'currency': bal_info['currency_name'],
                        'acquirer_seq_id': rec.seq_id,
                        'price_component': {
                            'amount': amount,
                            'fee': 0,
                            'unique_amount': 0
                        },
                        'total_amount': amount
                    })
        return values


class PaymentAcquirerNumber(models.Model):
    _inherit = ['tt.history']
    _name = 'payment.acquirer.number'
    _rec_name = 'display_name_payment'
    _description = 'Payment Acquirer Number'
    _order = 'id desc'

    res_id = fields.Integer('Res ID')
    res_model = fields.Char('Res Model')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True) # buat VA open biar ngga kembar
    payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Acquirer')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    number = fields.Char('Number')
    va_number = fields.Char('VA Number')
    url = fields.Char('URL')
    bank_name = fields.Char('Bank Name')
    unique_amount = fields.Float('Unique Amount')
    unique_amount_id = fields.Many2one('unique.amount','Unique Amount Obj',readonly=True)
    fee_amount = fields.Float('Fee Amount') ## HANYA UNTUK CLOSE VA
    time_limit = fields.Datetime('Time Limit', readonly=True)
    amount = fields.Float('Amount')
    state = fields.Selection([('open', 'Open'), ('close', 'Closed'), ('process', 'Process'), ('waiting', 'Waiting Next Cron'), ('done','Done'), ('cancel','Expired'), ('cancel2', 'Cancelled'), ('fail', 'Failed')], 'Payment Type', help="""
    OPEN FOR VA OPEN
    CLOSED FOR PAYMENT RESERVATION
    PROCESS FOR ONPROCESS RESERVATION
    WAITING NEXT CRON FOR ALREADY PAY BUT ERROR ISSUED DO ISSUED AUTOMATICALLY
    DONE FOR DONE PAYMENT RESERVATION
    EXPIRED FOR NO PAYMENT BEFORE MORE THAN TIME LIMIT
    CANCELLED FOR CANCEL FROM USER
    FAILED FOR ALREADY PAYMENT BUT ERROR ISSUED
    """)
    email = fields.Char(string="Email") # buat VA open biar ngga kembar
    display_name_payment = fields.Char('Display Name',compute="_compute_display_name_payment")
    is_using_point_reward = fields.Boolean('Is Using Point Reward', default=False)
    point_reward_amount = fields.Float('Point Reward Amount')
    currency_id = fields.Many2one('res.currency', 'Currency')

    @api.depends('number','payment_acquirer_id')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name_payment = "{} - {}".format(rec.payment_acquirer_id.name if rec.payment_acquirer_id.name != False else '',rec.number)

    def create_payment_acq_api(self, data, context):
        ### BAYAR PAKAI PAYMENT GATEWAY
        if variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]] != 'top.up':
            provider_type = 'tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
        else:
            provider_type = 'tt.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
        booking_obj = self.env[provider_type].search([('name','=',data['order_number']), ('ho_id','=', context['co_ho_id'])])
        is_use_point = data.get('use_point', False)
        if not booking_obj:
            raise RequestException(1001)

        ###MASUKKAN VOUCHER
        if data.get('voucher_reference'):
            booking_obj.voucher_code = data['voucher_reference']

        payment_acq_number = self.search([('number', 'ilike', data['order_number']), ('ho_id', '=', context['co_ho_id'])])
        if payment_acq_number:
            #check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number)-1].create_date
            if divmod(time_delta.seconds, 3600)[0] > 0 or payment_acq_number[len(payment_acq_number)-1].time_limit and datetime.now() > payment_acq_number[len(payment_acq_number)-1].time_limit or payment_acq_number[len(payment_acq_number)-1].state != 'close':
                for rec in payment_acq_number:
                    if rec.state == 'close':
                        rec.state = 'cancel'
                payment = self.create_payment_acq(data,booking_obj,provider_type, is_use_point, context)
                booking_obj.payment_acquirer_number_id = payment.id
                payment = {'order_number': payment.number}
            else:
                payment = {'order_number': payment_acq_number[len(payment_acq_number)-1].number}
                booking_obj.payment_acquirer_number_id = payment_acq_number[len(payment_acq_number)-1].id
        else:
            payment = self.create_payment_acq(data,booking_obj,provider_type, is_use_point, context)
            booking_obj.payment_acquirer_number_id = payment.id
            payment = {'order_number': payment.number}
        return ERR.get_no_error(payment)

    def create_payment_acq(self,data,booking_obj,provider_type, is_use_point, context):
        ## RULE TIME LIMIT PAYMENT ACQ < 1 jam, 10 menit = HOLD DATE - 10 menit
        ## UNTUK YG LEBIH DARI 1 JAM, 10 menit HOLE DATE HOLD DATE 60 menit
        currency_id = None
        if booking_obj._name != 'tt.top.up':
            ## RESERVASI
            currency_id = booking_obj.currency_id.id
            if booking_obj.hold_date < datetime.now() + timedelta(minutes=130):
                hold_date = booking_obj.hold_date - timedelta(minutes=10)
            elif data['order_number'].split('.')[0] == 'PH' or data['order_number'].split('.')[0] == 'PK':  # PHC 30 menit
                hold_date = datetime.now() + timedelta(minutes=30)
            else:
                hold_date = datetime.now() + timedelta(minutes=120)
        else:
            ## TOP UP
            currency_id = booking_obj.agent_id.ho_id.currency_id.id
            hold_date = booking_obj.due_date - timedelta(minutes=10)



        payment_acq_obj = self.env['payment.acquirer'].search([('seq_id', '=', data['acquirer_seq_id']), ('ho_id', '=', context['co_ho_id'])])

        amount = data['amount']
        point_amount = 0
        if is_use_point:
            if amount - payment_acq_obj.minimum_amount > booking_obj.agent_id.point_reward:
                point_amount = booking_obj.agent_id.point_reward
            else:
                point_amount = amount - payment_acq_obj.minimum_amount
            amount -= point_amount

        if payment_acq_obj.account_number: ## Transfer mutasi
            unique_obj = self.env['payment.acquirer'].generate_unique_amount_api({'amount': amount, 'is_downsell': False}, context)
                                                                             # booking_obj.agent_id.agent_type_id.id == self.env.ref(
                                                                             #     'tt_base.agent_type_btc').id)
                                                                             ## 7 July Request Kuamala ubah jadi fee bukan subsidy lagi

            unique_amount_id = unique_obj.id
            unique_amount = unique_obj.get_unique_amount()
        else:## VA Espay
            unique_amount_id = False
            unique_amount = 0
        ## ESPAY
        new_date = datetime.now().strftime('%y%m%d%H%M%S')
        new_order_id_espay = "%s.%s" % (data['order_number'], new_date)
        if len(new_order_id_espay) > 32:
            max_length_number_date = 32 - len(data['order_number']) - 1 ## max 32 digit - order_number - '.'
            new_order_id_espay = "%s.%s" % (data['order_number'], new_date[len(new_date)-max_length_number_date:len(new_date)])

        payment = self.env['payment.acquirer.number'].create({
            'state': 'close',
            'number': new_order_id_espay,
            'unique_amount': unique_amount,
            'unique_amount_id': unique_amount_id,
            'payment_acquirer_id': payment_acq_obj.id,
            'amount': amount,
            'res_model': provider_type,
            'res_id': booking_obj.id,
            'time_limit': hold_date,
            'provider_id': payment_acq_obj.provider_id.id if payment_acq_obj.provider_id else False,
            'is_using_point_reward': is_use_point,
            'point_reward_amount': point_amount,
            'agent_id': booking_obj.agent_id.id,
            'fee_amount': data['fee_amount'],
            'ho_id': context['co_ho_id'],
            'currency_id': currency_id
        })
        return payment

    def get_payment_acq_api(self, data, context):
        payment_acq_number = self.search([('number', 'ilike', data['order_number']), ('ho_id', '=', context['co_ho_id'])], order='create_date desc', limit=1)
        if payment_acq_number:
            # check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number) - 1].create_date
            if divmod(time_delta.seconds, 3600)[0] == 0 or datetime.now() < payment_acq_number[len(payment_acq_number)-1].time_limit and payment_acq_number[len(payment_acq_number)-1].time_limit and payment_acq_number[len(payment_acq_number) - 1].state == 'close':
                if data['provider'] != 'top.up':
                    book_obj = self.env['tt.reservation.%s' % data['provider']].search([('name', '=', '%s.%s' % (data['order_number'].split('.')[0],data['order_number'].split('.')[1])), ('ho_id', '=', context['co_ho_id'])], limit=1)
                else:
                    book_obj = self.env['tt.%s' % data['provider']].search([('name', '=', '%s.%s' % (data['order_number'].split('.')[0], data['order_number'].split('.')[1])), ('ho_id', '=', context['co_ho_id'])], limit=1)
                res = {
                    'order_number': data['order_number'],
                    'create_date': book_obj.create_date and book_obj.create_date.strftime("%Y-%m-%d %H:%M:%S") or '',
                    'time_limit': payment_acq_number.time_limit and payment_acq_number.time_limit.strftime("%Y-%m-%d %H:%M:%S") or (payment_acq_number.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    'nomor_rekening': payment_acq_number.payment_acquirer_id.account_number,
                    'account_name': payment_acq_number.payment_acquirer_id.account_name,
                    'amount': payment_acq_number.get_total_amount(),
                    'va_number': payment_acq_number.va_number,
                    'url': payment_acq_number.url,
                    'bank_name': payment_acq_number.bank_name,
                    'acquirer_seq_id': payment_acq_number.payment_acquirer_id.seq_id,
                    'currency': payment_acq_number.currency_id.name
                }
                return ERR.get_no_error(res)
            else:
                return ERR.get_error(additional_message='Order Has Been Expired')
        else:
            return ERR.get_error(additional_message='Order Number not found')

    def set_va_number_api(self, data, context):
        payment_acq_number = self.search([('number', 'ilike', data['order_number']), ('ho_id', '=', context['co_ho_id'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.va_number = data.get('va_number')
            payment_acq_number.bank_name = data.get('bank_name')
            # payment_acq_number.fee_amount = data.get('fee_amount') ## AMBIL DARI BACKEND
            payment_acq_number.time_limit = data.get('time_limit')
            payment_acq_number.url = data.get('url')
            return ERR.get_no_error()
        else:
            return ERR.get_error(additional_message='Payment Acquirer not found')

    def set_va_number_fail_api(self, data, context):
        payment_acq_number = self.search([('number', 'ilike', data['order_number']), ('ho_id', '=', context['co_ho_id'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.state = 'fail'
            provider_type = 'tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
            booking_obj = self.env[provider_type].search([('name', '=', data['order_number'])])
            if booking_obj:
                booking_obj.payment_acquirer_number_id = False

            return ERR.get_error(additional_message='Set payment acq number fail, error vendor')
        else:
            return ERR.get_error(additional_message='Payment Acquirer not found')

    def update_payment_acq_number(self, data, context):
        payment_acq_number = self.search([('number', '=', data['payment_acq_number']), ('ho_id', '=', context['co_ho_id'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.state = data['state']
            return ERR.get_no_error()
        else:
            return ERR.get_error(additional_message='Payment Acquirer Number not found')

    def get_total_amount(self):
        return self.amount + self.fee_amount + self.unique_amount

class PaymentUniqueAmount(models.Model):
    _name = 'unique.amount'
    _description = 'Unique Amount'
    # OLD segment
    #
    #     amount = fields.Float('Amount', required=True)
    #     upper_number = fields.Integer('Up Number')
    #     lower_number = fields.Integer('Lower Number')
    #     active = fields.Boolean('Active',default=True)
    #
    #     @api.model
    #     self, vals_list):
    #         already_exist_on_same_amount = [rec.upper_number for rec in self.search([('amount', '=', vals_list['amount'])])]
    #         already_exist_on_lower_higher_amount = [abs(rec.lower_number) for rec in self.search([('amount', 'in', [int(vals_list['amount'])-1000,
    #                                                                                                                 int(vals_list['amount'])+1000])])]
    #         already_exist = already_exist_on_same_amount+already_exist_on_lower_higher_amount
    #         unique_amount = None
    #         while (not unique_amount):
    #             number = random.randint(1,999)
    #             if number not in already_exist:
    #                 unique_amount = number
    #         vals_list['upper_number'] = unique_amount
    #         vals_list['lower_number'] = unique_amount-1000
    #         new_unique = super(PaymentUniqueAmount, self).create(vals_list)
    #         return new_unique

    display_name = fields.Char('Display Name', compute="_compute_name",store=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True,
                            default=lambda self: self.env.user.ho_id)
    is_downsell = fields.Boolean('Downsell')
    amount = fields.Float('Amount', required=True)
    unique_number = fields.Integer('Amount Unique')
    amount_total = fields.Float('Amount Total',compute="_compute_amount_total",store=True)
    active = fields.Boolean('Active', default=True)

    # @api.model
    # def create(self, vals_list):
    #     unique_amount = None
    #     while (not unique_amount):
    #         number = random.randint(1,999)
    #         already_exist = self.search([('amount_total','=',number+int(vals_list['amount']))])
    #         if not already_exist:
    #             unique_amount = number
    #     vals_list['unique_number'] = unique_amount
    #     new_unique = super(PaymentUniqueAmount, self).create(vals_list)
    #     return new_unique

    @api.model
    def create(self, vals_list):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 397')
        if not vals_list.get('unique_number') and self.env.user.ho_id:
            query = "SELECT unique_number FROM unique_amount WHERE unique_number != 0 and active IS TRUE and ho_id = %s;" % self.env.user.ho_id.id
            self.env.cr.execute(query)
            unique_amount_dict_list = self.env.cr.dictfetchall()
            used_unique_number = []
            for rec in unique_amount_dict_list:
                used_unique_number.append(rec['unique_number'])
            used_unique_number = set(used_unique_number)
            try:
                cut_off_min = self.env.user.ho_id.unique_amount_pool_min
                cut_off_amt = self.env.user.ho_id.unique_amount_pool_limit
                unique_amt_pool = variables.UNIQUE_AMOUNT_POOL
                if 0 < cut_off_min < cut_off_amt < 999:
                    unique_amt_pool = set(list(unique_amt_pool)[cut_off_min:cut_off_amt])
                elif cut_off_min > 0:
                    unique_amt_pool = set(list(unique_amt_pool)[cut_off_min:])
                elif cut_off_amt < 999:
                    unique_amt_pool = set(list(unique_amt_pool)[:cut_off_amt])
                unique_number = self.env.user.ho_id.default_unique_number + random.sample(unique_amt_pool - used_unique_number, 1).pop()
            except:
                unique_number = 0
            vals_list['unique_number'] = unique_number
        return super(PaymentUniqueAmount, self).create(vals_list)

    @api.multi
    def write(self, vals):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 398')
        return super(PaymentUniqueAmount, self).write(vals)

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 399')
        return super(PaymentUniqueAmount, self).unlink()

    def create_unique_amount_api(self, vals, context):
        query = "SELECT unique_number FROM unique_amount WHERE unique_number != 0 and active IS TRUE and ho_id = %s;" % context['co_ho_id']
        self.env.cr.execute(query)
        unique_amount_dict_list = self.env.cr.dictfetchall()
        used_unique_number = []
        for rec in unique_amount_dict_list:
            used_unique_number.append(rec['unique_number'])
        used_unique_number = set(used_unique_number)
        try:
            ho_obj = self.env['tt.agent'].browse(int(context['co_ho_id']))
            cut_off_min = ho_obj.unique_amount_pool_min
            cut_off_amt = ho_obj.unique_amount_pool_limit
            unique_amt_pool = variables.UNIQUE_AMOUNT_POOL
            if 0 < cut_off_min < cut_off_amt < 999:
                unique_amt_pool = set(list(unique_amt_pool)[cut_off_min:cut_off_amt])
            elif cut_off_min > 0:
                unique_amt_pool = set(list(unique_amt_pool)[cut_off_min:])
            elif cut_off_amt < 999:
                unique_amt_pool = set(list(unique_amt_pool)[:cut_off_amt])
            unique_number = ho_obj.default_unique_number + random.sample(unique_amt_pool - used_unique_number, 1).pop()
        except:
            unique_number = 0
        vals.update({
            'unique_number': unique_number,
            'ho_id': context['co_ho_id']
        })
        return self.create(vals)

    @api.depends('amount', 'unique_number')
    @api.multi
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.get_unique_amount() + rec.amount

    def get_unique_amount(self):
        return (self.is_downsell and self.unique_number * -1 or self.unique_number)

    @api.depends('amount','unique_number')
    @api.multi
    def _compute_name(self):
        for rec in self:
            rec.display_name = '%s - %s - %s' % (rec.amount or 0,rec.unique_number or 0, rec.amount_total or 0)
