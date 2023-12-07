from odoo import api,fields,models
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback
import json
import base64,pytz

_logger = logging.getLogger(__name__)

TOP_UP_STATE = [
    ("draft", "Draft"),
    ("confirm","Confirmed"),
    ("request", "Request"),
    ("validated", "Validated"),
    ("approved","Approved"),
    ("cancel", "Cancelled"),
    ("expired","Expired")
]

TOP_UP_STATE_STR = {
    "draft": "Draft",
    "request": "Request",
    "confirm": "Confirmed",
    "validated": "Validated",
    "approved": "Approved",
    "cancel": "Cancelled",
    "expired":"Expired"
}

class TtTopUp(models.Model):
    _name = 'tt.top.up'
    _inherit = 'tt.history'
    _order = 'id desc'
    _description = 'Top Up'

    name = fields.Char('Document Number', required='True', readonly=True,
                       index=True, default=lambda self: 'New')
    due_date = fields.Datetime('Due Date', readonly=True)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True,
                               default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', string="Agent", required=True, readonly=True,
                               default=lambda self: self.env.user.agent_id)
    state = fields.Selection(TOP_UP_STATE,
                             string='State', default='draft',
                             help='''
                             Draft, new top up
                             Request, requested top-up by agent
                             Validate, top-up approved by top-up receiver
                             Cancelled, top-up cancelled
                             Expired, top-up expired
                             ''')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.company_id.currency_id.id, store=True)
    amount = fields.Monetary('Input Amount',readonly=True)
    unique_amount = fields.Monetary('Unique Amount', default=0,
                                    states={'draft': [('readonly', False)]},
                                    help='''Unique amount for identification agent top-up via wire transfer''')
    fees = fields.Monetary('Fees',  default=0, help='Fees amount; set by the system because depends on the acquirer',readonly=True, states={'draft': [('readonly', False)]})
    validated_amount = fields.Monetary('Validated Amount', readonly=True)
    subsidy = fields.Monetary('Subsidy',readonly=True, default=0)
    total = fields.Monetary('Total', compute='_compute_amount', store=True, readonly=True)
    total_with_fees = fields.Monetary('Total + fees', compute='_compute_amount', store=True)
    ledger_id = fields.Many2one('tt.ledger', string='Ledger', readonly=True, copy=False)
    # payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Type')
    request_uid = fields.Many2one('res.users','Request By')
    request_date = fields.Datetime('Request Date')
    approve_uid = fields.Many2one('res.users','Approve By')
    approve_date = fields.Datetime('Approve Date')
    cancel_uid = fields.Many2one('res.users', 'Cancel By')
    cancel_date = fields.Datetime('Cancel Date')

    printout_top_up_id = fields.Many2one('tt.upload.center', 'Printout Top Up', readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.top.up')
        vals_list['due_date'] = datetime.now() + timedelta(hours=48)
        return super(TtTopUp, self).create(vals_list)

    @api.depends('amount', 'unique_amount', 'fees')#'amount_fix_va'
    def _compute_amount(self):
        for tp in self:
            # if tp.amount_fix_va:
            #     tp.update({
            #         'total': tp.amount_fix_va,
            #         'total_with_fees': tp.amount_fix_va + tp.fees,
            #     })
            # else:
            tp.update({
                'total': tp.amount + tp.unique_amount,
                'total_with_fees': tp.amount + tp.unique_amount - tp.fees,
            })

    def get_help_by(self):
        return self.approve_uid and self.approve_uid.name or \
               self.cancel_uid and self.cancel_uid.name or ''

    def action_set_back_to_request(self):
        if not self.env.user.has_group('tt_base.group_top_up_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 22')
        if self.state not in ["expired","cancel"]:
            raise UserError("Can only set to request [Expired] state top up.")
        self.write({
            'state': 'request'
        })

    def action_reject_from_button(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 23')
        self.action_cancel_top_up({
            'co_uid':self.env.user.id
        })

    def action_request_top_up(self,context):
        self.write({
            'state': 'request'
        })

    def action_cancel_top_up(self,context):
        self.write({
            'state' : 'cancel',
            'cancel_uid': context['co_uid'],
            'cancel_date': datetime.now(),
        })

    def test_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 24')
        self.write({
            'state': 'draft'
        })

    def test_set_as_request(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 25')
        self.write({
            'state': 'request'
        })

    def action_expired_top_up(self):
        self.write({
            'state': 'expired'
        })

    def action_validate_top_up(self):
        if self.state != 'request':
            raise UserError('Can only validate [request] state Top Up.')
        self.write({
            'state': 'validated'
        })

    def action_approve_top_up(self):
        if self.state != 'validated':
            raise UserError('Can only approve [validate] state Top Up.')
        if self.total_with_fees != self.validated_amount and not self.env.user.has_group('tt_base.group_payment_level_4'):
            _logger.info('Insufficient permission to approve Top Up with modified validated amount. Top Up: %s, User: %s' % (self.name, self.env.user.name))
            raise UserError('Insufficient permission to approve Top Up with modified validated amount.')

        ledger_obj = self.env['tt.ledger']
        vals = ledger_obj.prepare_vals(self._name,
                                       self.id,
                                       'Top Up : %s' % (self.name),
                                       self.name,
                                       datetime.now(),
                                       1,
                                       self.currency_id.id,
                                       self.env.user.id,
                                       self.validated_amount + abs(self.subsidy), ## Buat Ledger Amount sejumlah payment yg di validated + subsidy unique amount jika ada, ABS supaya selalu +
                                       description='Top Up Ledger for %s' % self.name)
        vals['agent_id'] = self.agent_id.id

        ho_obj = self.agent_id.ho_id
        if ho_obj:
            vals['ho_id'] = ho_obj.id
        new_aml = ledger_obj.create(vals)
        self.write({
            'state': 'approved',
            'ledger_id': new_aml.id,
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

        try:
            self.env['tt.top.up.api.con'].send_approve_notification(self.name,self.env.user.name,
                                                                    self.validated_amount,self.agent_id.name, self.agent_id.ho_id.id)
        except Exception as e:
            _logger.error("Send TOP UP Approve Notification Telegram Error")

        ## KIRIM EMAIL KE AGENT
        template = self.env.ref('tt_accounting.template_mail_approve_top_up', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)


    def get_company_name(self):
        company_obj = self.env['res.company'].search([],limit=1)
        return company_obj.name

    def action_va_top_up(self, data, context, payment_acq_number_id=False):
        #update pay
        top_up = self.search([('name', '=', data['name'])])
        top_up.state = 'request'
        top_up.fees = data['fee']
        # top_up.fees = 6666
        if top_up.total != top_up.payment_id.real_total_amount:
            _logger.info("Error: Payment 'Adjusting Amount' has been modified. Top Up: %s" % self.name)
            raise RequestException(1011)
        top_up.payment_id.reference = data['payment_ref']
        if payment_acq_number_id:
            top_up.payment_id.payment_acq_number_id = payment_acq_number_id
        top_up.payment_id.action_validate_from_button()
        top_up.payment_id.action_approve_from_button()

        return ERR.get_no_error({'top_up_id':top_up.id})

    def to_dict(self):
        res = {
            'name': self.name,
            'currency_code': self.currency_id and self.currency_id.name or '',
            'date': self.request_date and self.request_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'due_date': self.due_date and self.due_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'total': self.total or 0,
            'state': self.state,
            'state_description': TOP_UP_STATE_STR[self.state],
            'payment_method': self.payment_id.acquirer_id.name,
            'help_by': self.get_help_by()
        }
        return res

    def to_dict_acc(self):
        res = {
            'name': self.name,
            'agent_id': self.agent_id and self.agent_id.id or '',
            'currency': self.currency_id and self.currency_id.name or '',
            'date': self.request_date and self.request_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'due_date': self.due_date and self.due_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'amount': self.amount or 0,
            'unique_amount': self.unique_amount or 0,
            'fees': self.fees or 0,
            'total': self.total or 0,
            'total_with_fees': self.total_with_fees or 0,
            'state': self.state,
            'payment_acquirer': self.payment_id.acquirer_id.jasaweb_name,
            'help_by': self.get_help_by()
        }
        return res

    def create_top_up_api(self,data,context, admin=False):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            ##check apakah ada 3 active request

            top_up_objs = self.search([('agent_id','=',context['co_agent_id']),('state','in',['request','confirm'])])
            if len(top_up_objs.ids) >= 3 and admin == False:
                raise RequestException(1019)

            data.update({
                'state': 'confirm',
                'agent_id': agent_obj.id,
                'currency_id': self.env['res.currency'].search([('name','=',data.pop('currency_code'))]).id,
                # 'amount_id': self.env['tt.top.up.amount'].search([('seq_id','=',data.pop('amount_seq_id'))]).id,
                'request_uid': context['co_uid'],
                'request_date': datetime.now()
            })
            ho_obj = agent_obj.ho_id
            if ho_obj:
                data.update({
                    'ho_id': ho_obj.id
                })
            new_top_up = self.create(data)

            acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', data['payment_seq_id'])],limit=1)
            if len(acquirer_obj.ids)<1:
                raise RequestException(1017)

            ## kalau pake credit card amount di update + fees
            if acquirer_obj.type == 'creditcard_topup':
                new_top_up.amount = new_top_up.amount + (new_top_up.fees) ## amount + (fee*2) agar tampilan harga sesuai dengan frontend

            ##make payment
            new_payment = self.env['tt.payment'].create({
                'real_total_amount': new_top_up.total,
                'currency_id': new_top_up.currency_id.id,
                'agent_id': new_top_up.agent_id.id,
                'ho_id': new_top_up.ho_id.id,
                'acquirer_id': acquirer_obj.id,
                'top_up_id': new_top_up.id,
                'confirm_uid': context['co_uid'],
                'confirm_date': datetime.now()
            })

            new_top_up.payment_id = new_payment.id

            res = {
                'name': new_top_up.name
            }
            res.update(new_top_up.request_top_up())

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(1015)

    def get_top_up_api(self,data,context):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            res = []
            dom = [('agent_id','=',agent_obj.id)]
            if data.get('name'):
                dom.append(('name','=',data['name']))
            if data.get('date_from'):
                dom.append(('request_date', '>=', data['date_from']))
            if data.get('date_to'):
                dom.append(('request_date', '<=', data['date_to']))
            if data.get('state'):
                if data.get('state') != 'all':
                    dom.append(('state', '=', data['state']))

            for rec in self.search(dom):
                res.append(rec.to_dict())
                if rec.acquirer_id.type == 'creditcard_topup':
                    payment_acq_number_obj = self.env['payment.acquirer.number'].search([('number', 'ilike', rec.name), ('state', 'in', ['close'])],limit=1)
                    if payment_acq_number_obj:
                        res[-1].update({
                            "url": payment_acq_number_obj.url
                        })
            quota = [rec.to_dict() for rec in self.env['tt.pnr.quota'].search([('agent_id', '=', context['co_agent_id'])])]
            res = {
                'top up': res,
                'quota': quota
            }

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1014)

    def request_top_up_api(self,data,context):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                raise RequestException(1010)
            if top_up_obj.state != 'confirm':
                raise RequestException(1018,additional_message="State not confirm")

            top_up_obj.action_request_top_up(context) # ubah ke status cancel
            next_cron = False
            try:
                next_cron = False
                is_get_bank_transaction = False
                if top_up_obj.acquirer_id.is_specific_time:
                    if top_up_obj.acquirer_id.start_time <= datetime.now(pytz.timezone('Asia/Jakarta')).hour < top_up_obj.acquirer_id.end_time:
                        is_get_bank_transaction = True
                else:
                    is_get_bank_transaction = True
                if is_get_bank_transaction:
                    cron_bank_transaction_obj = self.env.ref("tt_bank_transaction.cron_auto_get_bank_transaction")
                    if cron_bank_transaction_obj.active:
                        d_time = cron_bank_transaction_obj.nextcall - datetime.now()
                        if d_time < timedelta():
                            d_time = timedelta()
                        list_d_time = str(d_time).split(':')
                        next_cron = "{} minutes {} seconds".format(int(list_d_time[1]),int(list_d_time[2][:2]))
            except Exception as e:
                _logger.error("{}\n{}".format("Top Up Request Next Cron Call Error",traceback.format_exc()))

            return ERR.get_no_error({
                'amount':top_up_obj.total_with_fees,
                'payment_acquirer':top_up_obj.payment_id.acquirer_id.name,
                'next_cron': next_cron
            })

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1018)

    def request_top_up(self):
        try:
            self.action_request_top_up({}) # ubah ke status cancel
            next_cron = False
            try:
                next_cron = False
                is_get_bank_transaction = False
                if self.acquirer_id.is_specific_time:
                    if self.acquirer_id.start_time <= datetime.now(pytz.timezone('Asia/Jakarta')).hour < self.acquirer_id.end_time:
                        is_get_bank_transaction = True
                else:
                    is_get_bank_transaction = True
                if is_get_bank_transaction:
                    cron_bank_transaction_obj = self.env.ref("tt_bank_transaction.cron_auto_get_bank_transaction")
                    if cron_bank_transaction_obj.active:
                        d_time = cron_bank_transaction_obj.nextcall - datetime.now()
                        if d_time < timedelta():
                            d_time = timedelta()
                        list_d_time = str(d_time).split(':')
                        next_cron = "{} minutes {} seconds".format(int(list_d_time[1]),int(list_d_time[2][:2]))
            except Exception as e:
                _logger.error("{}\n{}".format("Top Up Request Next Cron Call Error",traceback.format_exc()))

            return {
                'amount': self.total_with_fees,
                'payment_acquirer': self.payment_id.acquirer_id.name,
                'next_cron': next_cron
            }

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1018)

    def cancel_top_up_api(self,data,context):
        try:
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            try:
                agent_obj.create_date
            except:
                raise RequestException(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                raise RequestException(1010)
            if top_up_obj.state not in ['request','confirm']:
                raise RequestException(1016,additional_message="State not request or confirm")

            top_up_obj.action_cancel_top_up(context) # ubah ke status cancel
            if top_up_obj.acquirer_id.type == 'creditcard_topup':
                payment_acq_number_objs = self.env['payment.acquirer.number'].search([('number', 'ilike', top_up_obj.name)])
                for payment_acq_number_obj in payment_acq_number_objs:
                    payment_acq_number_obj.state = 'cancel2'
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1016)

    def print_topup(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name

        book_obj = self.env['tt.top.up'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        top_up_id = book_obj.env.ref('tt_report_common.action_report_printout_topup')

        if not book_obj.printout_top_up_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = book_obj.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = book_obj.env.user.id

            pdf_report = top_up_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = top_up_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Top Up %s.pdf' % book_obj.name,
                    'file_reference': 'Printout Top Up',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_top_up_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_top_up_id.url,
        }
        return url
