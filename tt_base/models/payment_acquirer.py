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
    type = fields.Selection(variables.ACQUIRER_TYPE, 'Payment Type')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    agent_id = fields.Many2one('tt.agent', 'Agent')
    bank_id = fields.Many2one('tt.bank', 'Bank')
    account_number = fields.Char('Account Number')
    account_name = fields.Char('Account Name')
    cust_fee = fields.Float('Customer Fee')
    bank_fee = fields.Float('Bank Fee')
    va_fee = fields.Float('VA Fee')
    online_wallet = fields.Boolean('Online Wallet')
    is_sunday_off = fields.Boolean('Sunday Off')
    is_specific_time = fields.Boolean('Specific Time')
    start_time = fields.Float(string='Start Time', help="Format: HH:mm Range 00:00 => 24:00")
    end_time = fields.Float(string='End Time', help="Format: HH:mm Range 00:00 => 24:00")
    description_msg = fields.Text('Description')
    va_fee_type = fields.Selection([('flat', 'Flat'), ('percentage', 'Percentage')], 'Fee Type VA', default='flat')
    show_device_type = fields.Selection([('web', 'Website'), ('mobile', 'Mobile'), ('all', 'All')], 'Show Device', default='all')
    save_url = fields.Boolean('Save URL')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('pay.acq')
        return super(PaymentAcquirer, self).create(vals_list)

    # FUNGSI
    def generate_unique_amount_api(self,amount,downsell=False):
        res = self.env['unique.amount'].create({'amount': amount, 'is_downsell': downsell})
        return {
            "is_downsell": res.is_downsell,
            "amount": res.amount,
            "unique_number": res.unique_number,
            "active": res.active
        }  
    
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

        if self.va_fee:
            if self.va_fee_type == 'flat':
                return 0,self.va_fee,uniq
            else:
                return 0,math.ceil(self.va_fee*amount/100),uniq

        else:
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
                'unique_amount': uniq,
            },
            'online_wallet': self.online_wallet,
            'save_url': self.save_url,
            'show_device_type': self.show_device_type,
            'total_amount': float(amount) + uniq + fee,
            'image': self.bank_id.image_id and self.bank_id.image_id.url or '',
            'description_msg': self.description_msg or ''
        }

    def acquirer_format_VA(self, acq, amount,unique):
        # NB:  CASH /payment/cash/feedback?acq_id=41
        # NB:  BNI /payment/tt_transfer/feedback?acq_id=68
        # NB:  BCA /payment/tt_transfer/feedback?acq_id=27
        # NB:  MANDIRI /payment/tt_transfer/feedback?acq_id=28
        payment_acq = self.env['payment.acquirer'].browse(acq.payment_acquirer_id.id)
        loss_or_profit, fee, uniq = acq.payment_acquirer_id.compute_fee(unique)
        return {
            'seq_id': payment_acq.seq_id,
            'name': payment_acq.name,
            'account_name': acq.payment_acquirer_id.name or '-',
            'account_number': acq.number or '',
            'bank': {
                'name': payment_acq.bank_id.name or '',
                'code': payment_acq.bank_id.code or '',
            },
            'type': payment_acq.type,
            'provider_id': payment_acq.provider_id.id or '',
            'currency': 'IDR',
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
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
        values = {
            'va': []
        }
        for acq in agent_obj.payment_acq_ids:
            if acq.state == 'open':
                values['va'].append(self.acquirer_format_VA(acq, 0, 0))
        return ERR.get_no_error(values)

    def get_va_bank(self, req, context):
        ho_agent_obj = self.env['tt.agent'].browse(self.env.ref('tt_base.rodex_ho').id)
        existing_payment_acquirer = self.env['payment.acquirer'].search([('agent_id', '=', ho_agent_obj.id), ('type', '!=', 'cash')])
        values = []
        for acq in existing_payment_acquirer:
            values.append({
                "seq_id": acq.seq_id,
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
            res = {}
            res['member'] = {}
            user_obj = self.env['res.users'].browse(context['co_uid']) # untuk process channel booking 
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

            if not context.get('co_customer_parent_id'):  ## kalau bukan user corporate login sendiri
                dom = [
                    ('website_published', '=', True),
                    ('company_id', '=', self.env.user.company_id.id),
                    ('type', '!=', 'va'),  ## search yg bukan espay
                    ('type', '!=', 'payment_gateway')  ## search yg bukan mutasi bca
                ]
                unique = 0
                if req['transaction_type'] == 'top_up':
                    # Kalau top up Ambil agent_id HO
                    dom.append(('agent_id', '=', self.env.ref('tt_base.rodex_ho').id))
                    unique = self.generate_unique_amount(amount).get_unique_amount()
                elif req['transaction_type'] == 'billing':
                    dom.append(('agent_id', '=', co_agent_id))

                values = {}
                now_time = datetime.now(pytz.timezone('Asia/Jakarta'))
                if self.env['tt.agent'].browse(co_agent_id).agent_type_id != self.env.ref('tt_base.agent_type_btc') or req['order_number'].split('.')[0] == 'PH' and self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids: #PHC pakai process channel operator
                    for acq in self.sudo().search(dom):
                        # self.test_validate(acq) utk testig saja
                        if self.validate_time(acq, now_time):
                            if not values.get(acq.type):
                                values[acq.type] = []
                            values[acq.type].append(acq.acquirer_format(amount, unique))

                # # payment gateway
                # penjualan
                if util.get_without_empty(req, 'order_number'):
                    dom = [
                        ('website_published', '=', True),
                        ('company_id', '=', self.env.user.company_id.id),
                        ('agent_id', '=', self.env.ref('tt_base.rodex_ho').id),
                        '|',
                        ('type', '=', 'va'),  ## search yg espay
                        ('type', '=', 'payment_gateway')  ## search yg mutasi bca
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
                            if not values.get(acq.type):
                                values[acq.type] = []
                            # if acq.account_number:
                            #     values[acq.type].append(acq.acquirer_format(amount, unique))
                            # else:
                            values[acq.type].append(acq.acquirer_format(amount, 0))

                res['non_member'] = values
                if req.get('booker_seq_id'):
                    res['member']['credit_limit'] = self.generate_credit_limit(amount,booker_seq_id=req['booker_seq_id']) if util.get_without_empty(req, 'booker_seq_id') else []
            else:#user corporate login sendiri
                if context.get('co_customer_parent_id'):
                    res['member']['credit_limit'] = self.generate_credit_limit(amount,customer_parent_id=context.get('co_customer_parent_id')) if util.get_without_empty(context, 'co_customer_parent_id') else []
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error()

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
            parent_obj_list = booker_obj.booker_parent_ids

        values = []
        for rec in parent_obj_list:
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
    _description = 'Payment Acquirer Number'
    _order = 'id desc'

    res_id = fields.Integer('Res ID')
    res_model = fields.Char('Res Model')
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True) # buat VA open biar ngga kembar
    payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Acquirer')
    number = fields.Char('Number')
    va_number = fields.Char('VA Number')
    url = fields.Char('URL')
    bank_name = fields.Char('Bank Name')
    unique_amount = fields.Float('Unique Amount')
    unique_amount_id = fields.Many2one('unique.amount','Unique Amount Obj',readonly=True)
    unique_amount_state = fields.Boolean('Unique Amount State',compute="_compute_unique_amount_state",store=True)
    fee_amount = fields.Float('Fee Amount')
    time_limit = fields.Datetime('Time Limit', readonly=True)
    amount = fields.Float('Amount')
    state = fields.Selection([('open', 'Open'), ('close', 'Closed'), ('waiting', 'Waiting Next Cron'), ('done','Done'), ('cancel','Expired'), ('cancel2', 'Cancelled'), ('fail', 'Failed')], 'Payment Type')
    email = fields.Char(string="Email") # buat VA open biar ngga kembar
    display_name_payment = fields.Char('Display Name',compute="_compute_display_name_payment")

    @api.depends('number','payment_acquirer_id')
    def _compute_display_name_payment(self):
        for rec in self:
            rec.display_name_payment = "{} - {}".format(rec.payment_acquirer_id.name if rec.payment_acquirer_id.name != False else '',rec.number)

    @api.depends('state')
    def _compute_unique_amount_state(self):
        for rec in self:
            _logger.info("QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ %s %s" % (rec.id, rec.state))
            if rec.state not in ['open','close']:
                _logger.info("HMM BEFORE UNIQUE AMOUNT ID")
                if rec.unique_amount_id:
                    _logger.info("UBAH STATE FALSE")
                    rec.unique_amount_state = False
                    rec.unique_amount_id.active = False
            else:
                _logger.info("UBAH STATE TRUE")
                rec.unique_amount_state = True

    def create_payment_acq_api(self, data):
        provider_type = 'tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
        booking_obj = self.env[provider_type].search([('name','=',data['order_number'])])

        if not booking_obj:
            raise RequestException(1001)

        payment_acq_number = self.search([('number', 'ilike', data['order_number'])])
        if payment_acq_number:
            #check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number)-1].create_date
            if divmod(time_delta.seconds, 3600)[0] > 0 or payment_acq_number[len(payment_acq_number)-1].time_limit and datetime.now() > payment_acq_number[len(payment_acq_number)-1].time_limit or payment_acq_number[len(payment_acq_number)-1] != 'close':
                for rec in payment_acq_number:
                    if rec.state == 'close':
                        rec.state = 'cancel'
                payment = self.create_payment_acq(data,booking_obj,provider_type)
                booking_obj.payment_acquirer_number_id = payment.id
                payment = {'order_number': payment.number}
            else:
                payment = {'order_number': payment_acq_number[len(payment_acq_number)-1].number}
                booking_obj.payment_acquirer_number_id = payment_acq_number[len(payment_acq_number)-1].id
        else:
            payment = self.create_payment_acq(data,booking_obj,provider_type)
            booking_obj.payment_acquirer_number_id = payment.id
            payment = {'order_number': payment.number}
        return ERR.get_no_error(payment)

    def create_payment_acq(self,data,booking_obj,provider_type):
        if booking_obj.hold_date < datetime.now() + timedelta(minutes=45):
            hold_date = booking_obj.hold_date
        elif data['order_number'].split('.')[0] == 'PH' or data['order_number'].split('.')[0] == 'PK':  # PHC 30 menit
            hold_date = datetime.now() + timedelta(minutes=30)
        else:
            hold_date = datetime.now() + timedelta(minutes=45)



        payment_acq_obj = self.env['payment.acquirer'].search([('seq_id', '=', data['seq_id'])])
        if payment_acq_obj.account_number: ## Transfer mutasi
            unique_obj = self.env['payment.acquirer'].generate_unique_amount(data['amount'], False)
                                                                             # booking_obj.agent_id.agent_type_id.id == self.env.ref(
                                                                             #     'tt_base.agent_type_btc').id)
                                                                             ## 7 July Request Kuamala ubah jadi fee bukan subsidy lagi

            unique_amount_id = unique_obj.id
            unique_amount = unique_obj.get_unique_amount()
            amount = data['amount']
        else:## VA Espay
            unique_amount_id = False
            unique_amount = 0
            amount = data['amount']

        payment = self.env['payment.acquirer.number'].create({
            'state': 'close',
            'number': "%s.%s" %(data['order_number'], datetime.now().strftime('%Y%m%d%H%M%S')),
            'unique_amount': unique_amount,
            'unique_amount_id': unique_amount_id,
            'payment_acquirer_id': payment_acq_obj.id,
            'amount': amount,
            'res_model': provider_type,
            'res_id': booking_obj.id,
            'time_limit': hold_date
        })
        return payment

    def get_payment_acq_api(self, data):
        payment_acq_number = self.search([('number', 'ilike', data['order_number'])], order='create_date desc', limit=1)
        if payment_acq_number:
            # check datetime
            date_now = datetime.now()
            time_delta = date_now - payment_acq_number[len(payment_acq_number) - 1].create_date
            if divmod(time_delta.seconds, 3600)[0] == 0 or datetime.now() < payment_acq_number[len(payment_acq_number)-1].time_limit and payment_acq_number[len(payment_acq_number)-1].time_limit and payment_acq_number[len(payment_acq_number) - 1].state == 'close':
                book_obj = self.env['tt.reservation.%s' % data['provider']].search([('name', '=', '%s.%s' % (data['order_number'].split('.')[0],data['order_number'].split('.')[1]))], limit=1)
                res = {
                    'order_number': data['order_number'],
                    'create_date': book_obj.create_date and book_obj.create_date.strftime("%Y-%m-%d %H:%M:%S") or '',
                    'time_limit': payment_acq_number.time_limit and payment_acq_number.time_limit.strftime("%Y-%m-%d %H:%M:%S") or (payment_acq_number.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    'nomor_rekening': payment_acq_number.payment_acquirer_id.account_number,
                    'amount': payment_acq_number.get_total_amount(),
                    'va_number': payment_acq_number.va_number,
                    'url': payment_acq_number.url,
                    'bank_name': payment_acq_number.bank_name,
                    'seq_id': payment_acq_number.payment_acquirer_id.seq_id
                }
                return ERR.get_no_error(res)
            else:
                return ERR.get_error(additional_message='Order Has Been Expired')
        else:
            return ERR.get_error(additional_message='Order Number not found')

    def set_va_number_api(self, data):
        payment_acq_number = self.search([('number', 'ilike', data['order_number'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.va_number = data.get('va_number')
            payment_acq_number.bank_name = data.get('bank_name')
            payment_acq_number.fee_amount = data.get('fee_amount')
            payment_acq_number.time_limit = data.get('time_limit')
            payment_acq_number.url = data.get('url')
            return ERR.get_no_error()
        else:
            return ERR.get_error(additional_message='Payment Acquirer not found')

    def set_va_number_fail_api(self, data):
        payment_acq_number = self.search([('number', 'ilike', data['order_number'])], order='create_date desc', limit=1)
        if payment_acq_number:
            payment_acq_number.state = 'fail'
            provider_type = 'tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[data['order_number'].split('.')[0]]
            booking_obj = self.env[provider_type].search([('name', '=', data['order_number'])])
            if booking_obj:
                booking_obj.payment_acquirer_number_id = False

            return ERR.get_error(additional_message='Set payment acq number fail, error vendor')
        else:
            return ERR.get_error(additional_message='Payment Acquirer not found')

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
    is_downsell = fields.Boolean('Downsell')
    amount = fields.Float('Amount', required=True)
    unique_number = fields.Integer('Amount Unique',compute=False)
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
        query = "SELECT unique_number FROM unique_amount WHERE unique_number != 0 and active IS TRUE;"
        self.env.cr.execute(query)
        unique_amount_dict_list = self.env.cr.dictfetchall()
        used_unique_number = []
        for rec in unique_amount_dict_list:
            used_unique_number.append(rec['unique_number'])
        used_unique_number = set(used_unique_number)
        try:
            unique_number = 3000 + random.sample(variables.UNIQUE_AMOUNT_POOL - used_unique_number,1).pop()
        except:
            unique_number =  0
        vals_list['unique_number'] = unique_number
        new_unique = super(PaymentUniqueAmount, self).create(vals_list)
        return new_unique

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