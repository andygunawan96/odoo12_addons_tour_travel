from odoo import api, models, fields
from ...tools import variables
from datetime import datetime, timedelta
import pytz
import json
import re
from ...tools.ERR import RequestException
from ...tools import ERR
import logging

_logger = logging.getLogger(__name__)

class TtBankAccount(models.Model):
    _name = 'tt.bank.accounts'
    _description = 'collections of bank accounts'
    _rec_name = 'bank_account_owner'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', default=lambda self: self.env.user.agent_id.id)
    bank_account_owner = fields.Char('Owner Name')
    bank_account_number = fields.Char('Bank Number')
    bank_account_number_without_dot = fields.Char("Bank Number Modified")
    currency_id = fields.Many2one('res.currency', 'Currency')
    bank_id = fields.Many2one('tt.bank', 'Bank ID')
    bank_transaction_date_ids = fields.One2many('tt.bank.transaction.date', "bank_account_id")
    bank_transaction_ids = fields.One2many('tt.bank.transaction', 'bank_account_id')
    is_get_transaction = fields.Boolean('Do Get Transaction')

    def create_bank_account(self, req):
        result = self.env['tt.bank.accounts'].create({
            'bank_account_owner': req['owner_name'],
            'bank_account_number': req['account_number'],
            'currency_id': req['currency_id'],
            'bank_id': req['bank_id']
        })

        return result

    def get_bank_mutation(self):
        data = {
            'account_id': self.id,
            'account_number': self.bank_account_number_without_dot,
            'provider': self.bank_id.code,
            'startdate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
            'enddate': datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d"),
        }
        # called function to proceed data and input in bank transaction
        self.env['tt.bank.transaction'].get_data(data, self.ho_id.id)
        self.env['tt.cron.log'].cron_auto_top_up_validator()

class TtBankDateTransaction(models.Model):
    _name = 'tt.bank.transaction.date'
    _description = "collections of date"
    _order = 'id DESC'
    _rec_name = 'date'

    bank_account_id = fields.Many2one('tt.bank.accounts', 'Bank Account')
    date = fields.Char("Date")
    transaction_ids = fields.One2many("tt.bank.transaction", "bank_transaction_date_id")

    def create_new_day(self, data):
        result = self.env['tt.bank.transaction.date'].create({
            'bank_account_id': int(data['bank_id']),
            'date': data['date'],
        })

        return result

class TtBankTransaction(models.Model):
    _name = 'tt.bank.transaction'
    _description = 'history and collections of bank statement'
    _rec_name = 'transaction_code'
    _order = 'id DESC'

    transaction_code = fields.Char('Document Number')
    bank_account_id = fields.Many2one('tt.bank.accounts', 'Bank Owners')
    bank_transaction_date_id = fields.Many2one("tt.bank.transaction.date", "Date Transactions")
    transaction_date = fields.Datetime("Transaction Date")
    currency_id = fields.Many2one('res.currency', "Currency")
    transaction_bank_branch = fields.Char("Bank Branch Code")
    transaction_type = fields.Char("Transaction Type")
    transaction_original = fields.Char("Transaction OG")
    transaction_amount = fields.Monetary("Amount")
    transaction_debit = fields.Monetary("Debit")                            ##duit keluar
    transaction_credit = fields.Monetary("Credit")                          ##duit masuk
    bank_balance = fields.Monetary("Balance")
    transaction_name = fields.Char("Transaction Name")
    transaction_message = fields.Char("Message")
    transaction_connection = fields.Selection(variables.BANK_STATEMENT)
    transaction_process = fields.Selection([('unprocess', 'Un-Process'), ('process', 'Processed')])
    top_up_id = fields.Many2one('tt.top.up', 'Top up')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)

    def create_bank_statement(self, req):
        bank_account_obj = self.env['tt.bank.accounts'].browse(req['bank_account_id'])
        ho_id = ''
        if bank_account_obj.ho_id:
            ho_id = bank_account_obj.ho_id.id
        elif bank_account_obj.agent_id:
            ho_id = bank_account_obj.agent_id.ho_id.id
        result = self.env['tt.bank.transaction'].create({
            'bank_account_id': req['bank_account_id'],
            'bank_transaction_date_id': req['date_id'],
            'transaction_date': req['transaction_date'],
            'currency_id': req['currency_id'],
            'transaction_bank_branch': req['transaction_bank_branch'],
            'transaction_type': req['transaction_type'],
            'transaction_original': str(req['transaction_amount']),
            'transaction_amount': float(req['transaction_amount']),
            'transaction_debit': float(req['transaction_debit']),
            'transaction_credit': float(req['transaction_credit']),
            'bank_balance': req['bank_balance'],
            'transaction_name': req['transaction_name'],
            'transaction_message': req['transaction_message'],
            'transaction_connection': "not_connect",
            'transaction_process': "unprocess",
            'ho_id': ho_id
        })

        return result

    def get_data(self, data, ho_id):
        result = self.env['tt.bank.api.con'].get_transaction(data, ho_id)
        if result['error_code'] != 0:
            raise Exception("Unable to get bank Transaction, %s" % (result['error_msg']))


        #look for currency_id
        currency_id = self.env['res.currency'].sudo().search([('name', 'ilike', result['response']['Currency'])]).read()
        bank_owner = self.env['tt.bank.accounts'].sudo().browse(int(data['account_id']))

        #get bank code
        bank_code = self.env['tt.bank'].sudo().browse(int(bank_owner[0]['bank_id'][0]))


        temp_day = datetime.now(pytz.timezone('Asia/Jakarta'))
        date = bank_owner.bank_transaction_date_ids.filtered(lambda x: x.date == temp_day.strftime("%Y-%m-%d"))

        if not date:
            new_day = {
                'bank_id': bank_owner.id,
                'date': temp_day.strftime("%Y-%m-%d")
            }
            date = self.env['tt.bank.transaction.date'].create_new_day(new_day)

        #get starting balance
        balance_modified = result['response']['StartBalance']

        #add data to transaction
        for i in result['response']['Data']:
            if not self.search([('transaction_message', '=', i['Trailer']), ('transaction_original', '=', i['TransactionAmount'])]):
                temp_date = i['TransactionDate'].split("-")

                debit_value = 0
                credit_value = 0
                if i['TransactionType'] == 'D':
                    balance_modified = float(balance_modified) + float(i['TransactionAmount'])
                    debit_value = float(i['TransactionAmount'])
                else:
                    balance_modified = float(balance_modified) + float(i['TransactionAmount'])
                    credit_value = float(i['TransactionAmount'])

                data = {
                    'bank_account_id': bank_owner[0]['id'],
                    'date_id': date.id,
                    'currency_id': currency_id[0]['id'],
                    'transaction_date': i['TransactionDate'],
                    'transaction_bank_branch': i['BranchCode'],
                    'transaction_type': i['TransactionType'],
                    'transaction_original': i['TransactionAmount'],
                    'transaction_amount': i['TransactionAmount'],
                    'transaction_debit': debit_value,
                    'transaction_credit': credit_value,
                    'bank_balance': balance_modified,
                    'transaction_name': i['TransactionName'],
                    'transaction_message': i['Trailer'],
                    'ho_id': self.ho_id.id
                }
                added = self.create_bank_statement(data)
                # create transaction code
                merge_date = "".join(temp_date)
                transaction_code = "MUT." + str(merge_date) + str(bank_code.code) + str(added.id)

                added.write({
                    'transaction_code': transaction_code
                })
                if i['TransactionType'] == 'D':
                    balance_modified = float(balance_modified) + float(i['TransactionAmount'])
                else:
                    balance_modified = float(balance_modified) + float(i['TransactionAmount'])

    def process_data(self):
        #get data from top up
        data = self.env['tt.top.up'].sudo().search([('state', '=', 'request')])
        transaction = self.env['tt.bank.transaction'].sudo().search([('transaction_process','=', 'unprocess'), ('transaction_type', '=', 'C')])

        #check if there's an exact number
        for i in data:
            for j in transaction:
                if i.total == j.get_transaction_amount():

                    #get payment data
                    payment_data = self.env['tt.payment'].sudo().browse(int(i.payment_id))
                    payment_data.reference = j.transaction_code
                    payment_data.payment_date = j.transaction_date
                    payment_data.action_validate_from_button()
                    # i.action_validate_top_up(j.get_transaction_amount())
                    j.top_up_validated(i.id)
                    break

        return 0

    def bank_date_passed(self):
        search = self.env['tt.bank.transaction'].sudo.search([('transaction_process', '=', 'unprocess')])
        for i in search:
            if i['transaction_date'] < datetime.today().strftime("%Y-%m-%d"):
                i.update({
                    'transaction_process': 'processed'
                })

    def get_transaction_amount(self):
        return self.transaction_amount

    def change_process_status(self):
        self.transaction_process = 'process'

    def top_up_validated(self, top_up_id):
        self.write({
            'transaction_connection': 'connect',
            'transaction_process': 'process',
            'top_up_id': top_up_id
        })

    def creates_top_up(self):
        data = {
            'currency_code': 'IDR',
            'amount': 24000000,
            'unique_amount': 78,
            'payment_seq_id': 'PQR.010109',
            'fees': 0
        }
        context = {
            'co_agent_id': 5,
            'co_uid': 12
        }

        self.env['tt.top.up'].create_top_up_api(data, context)

        return 0

    def get_transaction_api(self, data):
        number_checker = re.compile("^[0-9]*$")
        account_number = ""
        for acc_number in data['account_number']:
            if number_checker.match(acc_number):
                account_number += acc_number
        bank_account_obj = self.env['tt.bank.accounts'].search([('bank_account_number_without_dot', '=', account_number)])
        res = []
        if bank_account_obj:
            date_exist = bank_account_obj.bank_transaction_date_ids.filtered(
                lambda x: x.date == data['date'])
            if date_exist:
                if data.get('type') == 'D':
                    transaction_type = 'D'
                else:
                    transaction_type = 'C'
                result = date_exist.transaction_ids.filtered(lambda x: x.transaction_type == transaction_type)
                for rec in result:
                    res.append({
                        "date": rec.transaction_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "amount": rec.transaction_amount,
                        "transaction_message": rec.transaction_message != '' and rec.transaction_message or rec.transaction_name
                    })
        return ERR.get_no_error(res)
