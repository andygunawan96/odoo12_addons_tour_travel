from odoo import api,fields,models
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback
import json,os

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
    _order = 'id desc'
    _description = 'Top Up'

    name = fields.Char('Document Number', required='True', readonly=True,
                       index=True, default=lambda self: 'New')
    due_date = fields.Datetime('Due Date', readonly=True)
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
    total = fields.Monetary('Total', compute='_compute_amount', store=True, readonly=True)
    total_with_fees = fields.Monetary('Total + fees', compute='_compute_amount', store=False)
    ledger_id = fields.Many2one('tt.ledger', string='Ledger', readonly=True, copy=False)
    # payment_acquirer_id = fields.Many2one('payment.acquirer','Payment Type')
    request_uid = fields.Many2one('res.users','Request By')
    request_date = fields.Datetime('Request Date')
    approve_uid = fields.Many2one('res.users','Approve By')
    approve_date = fields.Datetime('Approve Date')
    cancel_uid = fields.Many2one('res.users', 'Cancel By')
    cancel_date = fields.Datetime('Cancel Date')

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.top.up')
        vals_list['due_date'] = datetime.now() + timedelta(hours=3)
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
                'total_with_fees': tp.amount + tp.unique_amount + tp.fees,
            })

    def get_help_by(self):
        return self.approve_uid and self.approve_uid.name or \
               self.cancel_uid and self.cancel_uid.name or ''

    def action_reject_from_button(self):
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
        self.write({
            'state': 'draft'
        })

    def test_set_as_request(self):
        self.write({
            'state': 'request'
        })

    def action_expired_top_up(self):
        self.write({
            'state': 'expired'
        })

    def action_validate_top_up(self):
        print("validate")
        if self.state != 'request':
            raise UserError('Can only validate [request] state Top Up.')
        self.write({
            'state': 'validated'
        })
    def action_approve_top_up(self):
        print("approve")
        if self.state != 'validated':
            raise UserError('Can only approve [validate] state Top Up.')

        ledger_obj = self.env['tt.ledger']
        vals = ledger_obj.prepare_vals(self._name,self.id,'Top Up : %s' % (self.name),self.name,datetime.now(),1,self.currency_id.id,self.env.user.id,self.get_total_amount(),description='Top Up Ledger for %s' % self.name)
        vals['agent_id'] = self.agent_id.id
        new_aml = ledger_obj.create(vals)
        self.write({
            'state': 'approved',
            'ledger_id': new_aml.id,
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

        try:
            self.env['tt.top.up.api.con'].send_approve_notification(self.name,self.env.user.name,self.get_total_amount())
        except Exception as e:
            _logger.error("Send TOP UP Approve Notification Telegram Error")



    def get_total_amount(self):
        return self.total

    def to_dict(self):
        res = {
            'name': self.name,
            'currency_code': self.currency_id and self.currency_id.name or '',
            'date': self.request_date and self.request_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'due_date': self.due_date and self.due_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'total': self.total or '',
            'state': self.state,
            'state_description': TOP_UP_STATE_STR[self.state],
            'payment_method': self.payment_id.acquirer_id.name,
            'help_by': self.get_help_by()
        }
        return res

    def create_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                raise RequestException(1008)
            print(json.dumps(data))

            ##check apakah ada 3 active request

            top_up_objs = self.search([('agent_id','=',context['co_agent_id']),('state','in',['request','confirm'])])
            if len(top_up_objs.ids) >= 3:
                raise RequestException(1019)

            data.update({
                'state': 'confirm',
                'agent_id': agent_obj.id,
                'currency_id': self.env['res.currency'].search([('name','=',data.pop('currency_code'))]).id,
                # 'amount_id': self.env['tt.top.up.amount'].search([('seq_id','=',data.pop('amount_seq_id'))]).id,
                'request_uid': context['co_uid'],
                'request_date': datetime.now()
            })
            new_top_up = self.create(data)

            acquirer_obj = self.env['payment.acquirer'].search([('seq_id', '=', data['payment_seq_id'])],limit=1)
            if len(acquirer_obj.ids)<1:
                raise RequestException(1017)
            ##make payment
            new_payment = self.env['tt.payment'].create({
                'real_total_amount': new_top_up.total_with_fees,
                'currency_id': new_top_up.currency_id.id,
                'agent_id': new_top_up.agent_id.id,
                'acquirer_id': acquirer_obj.id,
                'top_up_id': new_top_up.id
            })

            new_top_up.payment_id = new_payment.id

            return ERR.get_no_error({
                'name': new_top_up.name
            })
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(1015)

    def get_top_up_api(self,data,context):
        try:
            print(json.dumps(data))
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                raise RequestException(1008)

            res = []
            dom = [('agent_id','=',agent_obj.id)]
            if data.get('name'):
                dom.append(('name','=',data['name']))
            if data.get('date_from'):
                dom.append(('booked_date', '>=', data['date_from']))
            if data.get('date_to'):
                dom.append(('booked_date', '<=', data['date_to']))
            if data.get('state'):
                if data.get('state') != 'all':
                    dom.append(('state', '=', data['state']))

            for rec in self.search(dom):
                res.append(rec.to_dict())

            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1014)

    def request_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                raise RequestException(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                raise RequestException(1010)
            if top_up_obj.state != 'confirm':
                raise RequestException(1018,additional_message="State not confirm")

            top_up_obj.action_request_top_up(context) # ubah ke status cancel

            return ERR.get_no_error({'amount':top_up_obj.total_with_fees})
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1018)

    def cancel_top_up_api(self,data,context):
        try:
            agent_obj = self.browse(context['co_agent_id'])
            if not agent_obj:
                raise RequestException(1008)

            top_up_obj = self.search([('name','=',data['name'])])
            if not top_up_obj:
                raise RequestException(1010)
            if top_up_obj.state not in ['request','confirm']:
                raise RequestException(1016,additional_message="State not request or confirm")

            top_up_obj.action_cancel_top_up(context) # ubah ke status cancel

            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1016)

    def print_topup(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('tt_report_common.action_report_printout_topup').report_action(self, data=datas)