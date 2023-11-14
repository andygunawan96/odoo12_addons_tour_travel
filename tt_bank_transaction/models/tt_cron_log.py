from odoo import api,models,fields
from ...tools import variables
import logging,traceback
import re
import json,pytz
from datetime import datetime, timedelta
from ...tools.db_connector import GatewayConnector
_logger = logging.getLogger(__name__)

class ttCronTopUpValidator(models.Model):
    _inherit = 'tt.cron.log'

    def cron_auto_top_up_validator(self,start_time="03:00",end_time="23:00"):
        start_time_obj = datetime.strptime(start_time,"%H:%M")
        end_time_obj = datetime.strptime(end_time,"%H:%M")
        if start_time_obj.time() <= datetime.now(pytz.timezone('Asia/Jakarta')).time() < end_time_obj.time():
            try:
                # get data from top up
                top_up_objs = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
                number_checker = re.compile("^[0-9]*$")
                for top_up_obj in top_up_objs:
                    account_number = ""
                    if top_up_obj.payment_id.acquirer_id.account_number:
                        for acc_number in top_up_obj.payment_id.acquirer_id.account_number:
                            if number_checker.match(acc_number):
                                account_number += acc_number
                    transaction = self.env['tt.bank.accounts'].search([('bank_account_number_without_dot', '=', account_number)])
                    if transaction:
                        date_exist = transaction.bank_transaction_date_ids.filtered(lambda x: x.date == datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"))
                        if date_exist:
                            result = date_exist.transaction_ids.filtered(lambda x: x.transaction_amount == top_up_obj.total and x.transaction_amount == top_up_obj.payment_id.real_total_amount and x.transaction_type == 'C' and x.transaction_connection != 'connect' and transaction.ho_id == x.ho_id) #check mutasi bank yg belum connect saja && check ho_id yg sama
                            if result:
                                if result.transaction_message == '':
                                    reference_code = result.transaction_code
                                else:
                                    reference_code = result.transaction_message
                                transaction_date = result.transaction_date

                                # get payment data
                                # payment_data = self.env['tt.payment'].browse(int(top_up_obj.payment_id))
                                payment_data = top_up_obj.payment_id

                                # set value for payment data
                                payment_data.reference = reference_code
                                payment_data.payment_date = transaction_date

                                # validate payment
                                payment_data.action_validate_from_button()
                                payment_data.action_approve_from_button()

                                result.top_up_validated(top_up_obj.id)
                            else:
                                _logger.error("%s ID, is not found within transaction" % top_up_obj.id)
                                continue
                        else:
                            _logger.error("%s is not found within date inside date" % datetime.today().strftime("%Y-%m-%d"))
                            continue
                    else:
                        _logger.error("%s ID, bank not found" % top_up_obj.id)
                        continue
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto top-up validator by system')
            #payment reservation
            ## UNTUK YG BAYAR BCA
            payment_acq_number_objs = self.env['payment.acquirer.number'].search([('state','=','close'), ('unique_amount','!=',0)])
            for payment_acq_number_obj in payment_acq_number_objs:
                try:
                    transaction = self.env['tt.bank.accounts'].search([])
                    if transaction:
                        for transaction_data in transaction:
                            date_exist = transaction_data.bank_transaction_date_ids.filtered(lambda x: x.date == datetime.today().strftime("%Y-%m-%d"))
                            if date_exist:
                                result = date_exist.transaction_ids.filtered(lambda x: x.transaction_amount == payment_acq_number_obj.amount + payment_acq_number_obj.unique_amount + payment_acq_number_obj.fee_amount and x.transaction_type == 'C')
                                if result:
                                    result = result[0]
                                    if result.transaction_message == '':
                                        reference_code = result.transaction_code
                                    else:
                                        reference_code = result.transaction_message
                                    resv_obj = self.env['tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[payment_acq_number_obj.number.split('.')[0]]].search([('name', '=', '%s.%s' %(payment_acq_number_obj.number.split('.')[0], payment_acq_number_obj.number.split('.')[1])), ('ho_id','=', payment_acq_number_obj.ho_id.id)])
                                    if not self.env['tt.payment'].search([('reference', '=', reference_code),('total_amount','=', payment_acq_number_obj.amount + payment_acq_number_obj.unique_amount)]): #update
                                        # topup
                                        context = {
                                            'co_agent_id': resv_obj.agent_id.id,
                                            'co_uid': self.env.user.id
                                            # 'co_uid': self.env.ref('base.user_root').id
                                        }
                                        request = {
                                            'amount': payment_acq_number_obj.amount + payment_acq_number_obj.unique_amount,
                                            'currency_code': result.currency_id.name,
                                            'payment_ref': reference_code,
                                            'payment_seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id,
                                            'subsidy': payment_acq_number_obj.unique_amount if payment_acq_number_obj.unique_amount < 0 else 0,
                                            'fee': payment_acq_number_obj.unique_amount if payment_acq_number_obj.unique_amount > 0 else 0
                                        }

                                        res = self.env['tt.top.up'].create_top_up_api(request, context, True)
                                        if res['error_code'] == 0:
                                            request = {
                                                'virtual_account': '',
                                                'name': res['response']['name'],
                                                'payment_ref': reference_code,##jangan di ubah nanti ngebug top up approved dobule dengan case, 2 payment acq number status closed dari agent yg sama kemudian di trf 2 2nya, confurrent update
                                                'fee': 0
                                            }
                                            _logger.info("###5")
                                            res = self.env['tt.top.up'].action_va_top_up(request, context, payment_acq_number_obj.id)
                                            result.top_up_validated(res['response']['top_up_id'])
                                            payment_acq_number_obj.state = 'process'
                                            self._cr.commit()
                                    book_obj = self.env['tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[payment_acq_number_obj.number.split('.')[0]]].search([('name', '=', '%s.%s' % (payment_acq_number_obj.number.split('.')[0], payment_acq_number_obj.number.split('.')[1])), ('state', 'in', ['booked','issued','halt_booked'])], limit=1)

                                    if book_obj:
                                        #login gateway, payment
                                        if book_obj.state in ['booked', 'halt_booked']:
                                            seq_id = ''
                                            if book_obj.payment_acquirer_number_id:
                                                seq_id = book_obj.payment_acquirer_number_id.payment_acquirer_id.seq_id
                                            req = {
                                                'order_number': book_obj.name,
                                                'user_id': book_obj.user_id.id,
                                                'provider_type': variables.PROVIDER_TYPE_PREFIX[book_obj.name.split('.')[0]],
                                                'member': False, # kalo bayar pake BCA / MANDIRI PASTI MEMBER FALSE
                                                'acquirer_seq_id': seq_id,
                                                'force_issued': True,
                                                'use_point': book_obj.payment_acquirer_number_id.is_using_point_reward,
                                                'ho_id': book_obj.agent_id.ho_id.id
                                            }
                                            res = self.env['tt.payment.api.con'].send_payment(req)
                                            _logger.info('Cron Top Up Validator Send Payment REQ %s.%s \n%s' % (payment_acq_number_obj.number.split('.')[0], payment_acq_number_obj.number.split('.')[1], json.dumps(res)))
                                            if res['error_code'] == 0 and res['response']['state'] == 'issued':
                                                # tutup payment acq number
                                                payment_acq_number_obj.state = 'done'
                                            else:
                                                payment_acq_number_obj.state = 'waiting'
                                                if book_obj.agent_type_id.code == 'btc':
                                                    different_price = res['response']['agent_nta'] - payment_acq_number_obj.amount
                                                    if different_price > 0:
                                                        ##b2c beda harga top up selisih harga
                                                        context = {
                                                            'co_agent_id': resv_obj.agent_id.id,
                                                            'co_uid': self.env.ref('base.user_root').id
                                                        }
                                                        request = {
                                                            'amount': different_price,
                                                            'currency_code': result.currency_id.name,
                                                            'payment_ref': '%s_autotopup' % reference_code,
                                                            'payment_seq_id': payment_acq_number_obj.payment_acquirer_id.seq_id,
                                                            'subsidy': 0,
                                                            'fee': 0
                                                        }

                                                        res = self.env['tt.top.up'].create_top_up_api(request, context,True)
                                                        if res['error_code'] == 0:
                                                            request = {
                                                                'virtual_account': '',
                                                                'name': res['response']['name'],
                                                                'payment_ref': '%s_autotopup' % reference_code,
                                                            ##jangan di ubah nanti ngebug top up approved dobule dengan case, 2 payment acq number status closed dari agent yg sama kemudian di trf 2 2nya, confurrent update
                                                                'fee': 0
                                                            }
                                                            _logger.info("###5")
                                                            res = self.env['tt.top.up'].action_va_top_up(request,context,payment_acq_number_obj.id)
                                                            result.top_up_validated(res['response']['top_up_id'])
                                                            self._cr.commit()
                                                    res = self.env['tt.payment.api.con'].send_payment(req)
                                                    if res['error_code'] in [0, 1009, 4034]:
                                                        # tutup payment acq number
                                                        payment_acq_number_obj.state = 'done'
                                                    else:
                                                        ## NOTIF TELE
                                                        data = {
                                                            'code': 9903,
                                                            'title': 'ERROR ISSUED using BCA',
                                                            'message': 'Error issued BCA order number %s\n%s' % (book_obj.name, res['error_msg']),
                                                        }
                                                        context = {
                                                            "co_ho_id": book_obj.agent_id.ho_id.id
                                                        }
                                                        GatewayConnector().telegram_notif_api(data, context)

                                                else:
                                                    ## NOTIF TELE
                                                    data = {
                                                        'code': 9903,
                                                        'title': 'ERROR ISSUED',
                                                        'message': 'Error issued bca mutation, order number %s\n%s' % (
                                                        book_obj.name, res['error_msg']),
                                                    }
                                                    context = {
                                                        "co_ho_id": book_obj.agent_id.ho_id.id
                                                    }
                                                    GatewayConnector().telegram_notif_api(data, context)
                                        elif book_obj.state == 'issued':
                                            payment_acq_number_obj.state = 'done'
                                            _logger.info('Cron Top Up Validator Already issued for order number %s.%s change payment acquirer number status' % (payment_acq_obj.number.split('.')[0], payment_acq_obj.number.split('.')[1]))
                                        self._cr.commit()
                                else:
                                    _logger.error("%s ID, is not found within transaction" % payment_acq_number_obj.id)
                                    continue

                except Exception as e:
                    self.create_cron_log_folder()
                    self.write_cron_log('auto top-up validator by system (payment close)', ho_id=payment_acq_number_obj.ho_id.id)
        else:
            # _logger.error("Cron only works between 0300 to 2100 UTC +7")
            _logger.error("Outside of Cron work time")

        ## UNTUK STATE WAITING SELALU JALAN WAKTU CRON JALAN KARENA SUDAH BAYAR HANYA KURANG ISSUED
        ## UNTUK CRON YG SUDAH BAYAR TAPI BELUM ISSUED PAYMENT BY BCA & Espay STATE WAITING
        payment_acq_objs = self.env['payment.acquirer.number'].search([('state', '=', 'waiting')])
        for payment_acq_obj in payment_acq_objs:
            try:
                book_obj = self.env['tt.reservation.%s' % variables.PROVIDER_TYPE_PREFIX[payment_acq_obj.number.split('.')[0]]].search([('name','=','%s.%s' % (payment_acq_obj.number.split('.')[0],payment_acq_obj.number.split('.')[1])),('state','in',['booked','issued','halt_booked'])],limit=1)
                if book_obj:
                    if book_obj.state in ['issued', 'done']:
                        payment_acq_obj.state = 'done'
                    # login gateway, payment
                    elif book_obj.state in ['booked', 'halt_booked']:
                        seq_id = ''
                        if book_obj.payment_acquirer_number_id:
                            seq_id = book_obj.payment_acquirer_number_id.payment_acquirer_id.seq_id
                        req = {
                            'order_number': book_obj.name,
                            'user_id': book_obj.user_id.id,
                            'provider_type': variables.PROVIDER_TYPE_PREFIX[book_obj.name.split('.')[0]],
                            'member': False,  # kalo bayar pake BCA / MANDIRI PASTI MEMBER FALSE
                            'acquirer_seq_id': seq_id,
                            'force_issued': True,
                            'use_point': book_obj.payment_acquirer_number_id.is_using_point_reward,
                            'ho_id': book_obj.agent_id.ho_id.id
                        }
                        res = self.env['tt.payment.api.con'].send_payment(req)
                        _logger.info('Cron Top Up Validator Send Payment REQ %s.%s \n%s' % (
                            payment_acq_obj.number.split('.')[0], payment_acq_obj.number.split('.')[1],
                            json.dumps(res)))
                        if res['error_code'] != 0:
                            # payment_acq_obj.state = 'waiting' ## update state waktu next cron agar tidak concurrent
                            if book_obj.agent_type_id.code == 'btc':
                                different_price = res['response']['agent_nta'] - payment_acq_obj.amount
                                if different_price > 0:
                                    ##b2c beda harga top up selisih harga
                                    context = {
                                        'co_agent_id': book_obj.agent_id.id,
                                        'co_uid': self.env.ref('base.user_root').id
                                    }
                                    request = {
                                        'amount': different_price,
                                        'currency_code': book_obj.currency,
                                        'payment_ref': '%s_autotopup' % payment_acq_obj.number,
                                        'payment_seq_id': payment_acq_obj.payment_acquirer_id.seq_id,
                                        'subsidy': 0,
                                        'fee': 0
                                    }

                                    res = self.env['tt.top.up'].create_top_up_api(request, context, True)
                                    if res['error_code'] == 0:
                                        request = {
                                            'virtual_account': '',
                                            'name': res['response']['name'],
                                            'payment_ref': '%s_autotopup' % payment_acq_obj.number,
                                            ##jangan di ubah nanti ngebug top up approved dobule dengan case, 2 payment acq number status closed dari agent yg sama kemudian di trf 2 2nya, confurrent update
                                            'fee': 0
                                        }
                                        _logger.info("###5")
                                        res = self.env['tt.top.up'].action_va_top_up(request, context,
                                                                                     payment_acq_obj.id)
                                        self.env['tt.bank.accounts'].top_up_validated(res['response']['top_up_id'])
                                        self._cr.commit()
                                res = self.env['tt.payment.api.con'].send_payment(req)
                                if res['error_code'] == 0:
                                    # tutup payment acq number
                                    payment_acq_obj.state = 'done'
                                else:
                                    ## NOTIF TELE
                                    if payment_acq_obj.unique_amount == 0:
                                        payment_vendor_name = 'BCA'
                                    else:
                                        payment_vendor_name = 'Espay'
                                    data = {
                                        'code': 9903,
                                        'title': 'ERROR ISSUED using %s' % payment_vendor_name,
                                        'message': 'Error issued %s order number %s\n%s' % (
                                        payment_vendor_name, book_obj.name, res['error_msg']),
                                    }
                                    context = {
                                        "co_ho_id": book_obj.agent_id.ho_id.id
                                    }
                                    GatewayConnector().telegram_notif_api(data, context)

                            else:
                                ## NOTIF TELE
                                if payment_acq_obj.unique_amount == 0:  ## PAYMENT GATEWAY ESPAY
                                    payment_vendor_name = 'Espay'
                                else:  ## TRANSFER MANUAL
                                    payment_vendor_name = 'BCA mutation'
                                data = {
                                    'code': 9903,
                                    'title': 'ERROR ISSUED',
                                    'message': 'Error issued %s, order number %s\n%s' % (
                                        payment_vendor_name, book_obj.name, res['error_msg']),
                                }
                                context = {
                                    "co_ho_id": book_obj.agent_id.ho_id.id
                                }
                                GatewayConnector().telegram_notif_api(data, context)
                    elif book_obj.state == 'issued':
                        payment_acq_obj.state = 'done'
                        _logger.info('Cron Top Up Validator Already issued for order number %s change payment acquirer number status' % (payment_acq_obj.number))
                        self._cr.commit()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('auto top-up validator by system (payment waiting)', ho_id=payment_acq_obj.ho_id.id)

    def cron_auto_get_bank_transaction(self,start_time="03:00",end_time="22:00"):
        start_time_obj = datetime.strptime(start_time,"%H:%M")
        end_time_obj = datetime.strptime(end_time,"%H:%M")
        now_time_obj = datetime.strptime(datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M"), "%H:%M")
        if start_time > end_time:
            end_time_obj += timedelta(days=1)
        if start_time_obj <= now_time_obj < end_time_obj:
            account_objs = self.env['tt.bank.accounts'].search([('is_get_transaction','=',True)])
            for rec in account_objs:
                if rec.ho_id:
                    try:
                        # get_bank_account = self.env.ref('tt_bank_transaction.bank_account_bca_1')
                        #can be modified to respected account
                        # data = {
                        #     'account_id': rec.id,
                        #     'account_number': rec.bank_account_number_without_dot,
                        #     'provider': rec.bank_id.code,
                        #     'startdate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
                        #     'enddate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
                        # }
                        # #called function to proceed data and input in bank transaction
                        # self.env['tt.bank.transaction'].get_data(data, rec.ho_id.id)
                        rec.get_bank_mutation()
                        self.cron_auto_top_up_validator()
                    except Exception as e:
                        self.create_cron_log_folder()
                        self.write_cron_log('auto get bank transaction',rec.bank_account_number, ho_id=rec.ho_id.id)
                else:
                    error_log = ''
                    if rec.bank_id:
                        error_log += rec.bank_id.name
                    elif rec.bank_account_owner:
                        error_log += rec.bank_account_owner
                    if rec.bank_account_number:
                        error_log += ' ' + rec.bank_account_number
                    _logger.error("Please set HO ID for %s" % error_log)
        else:
            # _logger.error("Cron only works between 0300 AM to 2100 PM UTC+7")
            _logger.error("Outside of Cron work time")

    def cron_auto_proceed_bank_transaction(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                bank_transaction_data = self.env['tt.bank.transaction'].search([('transaction_date', '<', datetime.today()), ('transaction_process', '=', 'unprocess'), ('bank_account_id.ho_id','=',ho_obj.id)])
                for i in bank_transaction_data:
                    i.change_process_status()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log("auto proceed yesterday transaction data",ho_id=ho_obj.id)

    def cron_auto_change_nextcall_get_bank_transaction(self,int_values=30):
        try:
            self.env.ref('tt_bank_transaction.cron_auto_get_bank_transaction').interval_number = int_values
        except Exception as e:
            self.create_cron_log_folder()
            ## tidak tahu pakai context apa
            self.write_cron_log('auto change nexctcall get bank transaction')

