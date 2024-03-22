from odoo import api,models,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime
from ...tools.db_connector import GatewayConnector
from ...tools import variables
import logging,pytz

_logger = logging.getLogger(__name__)

# class TtAdjustmentType(models.Model):
#     _name = 'tt.adjustment.type'
#     _description = 'Adjustment Type Model'
#     _order = 'id DESC'
#
#     name = fields.Char('Name')
#     code = fields.Char('Code')
#     provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')

SOURCE_OF_FUNDS_TYPE = [
    ('balance', 'Balance'),
    ('point', 'Point Reward'),
    ('credit_limit', 'Credit Limit')
]

class TtAdjustment(models.Model):
    _name = "tt.adjustment"
    _inherit = 'tt.history'
    _description = "Adjustment Model"
    _order = 'id DESC'

    name = fields.Char('Name', readonly=True, default='New', copy=False)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('validate', 'Validated'), ('approve', 'Approved'),
                              ('cancel', 'Canceled')], 'Status', default='draft',
                             help=" * The 'Draft' status is used for All HO to make adjustment transaction request.\n"
                                  " * The 'Confirmed' status is used for All HO to confirm the request.\n"
                                  " * The 'Validated' status is used for Ticketing Manager to validate the request.\n"
                                  " * The 'Approved' status is used for Accounting & Finance Adviser to approve the request, then ledger is created.\n"
                                  " * The 'Canceled' status is used for Accounting & Finance Adviser to cancel the request.\n")

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True,
                               default=lambda self: self.env.user.ho_id, states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    # adj_type = fields.Many2one('tt.adjustment.type', 'Adjustment Type', required=True, readonly=True,
    #                             states={'draft': [('readonly', False)]})

    adj_type = fields.Selection(lambda self: self.get_adjustment_type(), 'Adjustment Type', required=True, readonly=True,
                                states={'draft': [('readonly', False)]})

    referenced_document = fields.Char('Ref. Document')

    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    component_type = fields.Selection([('total', 'Grand Total'), ('commission', 'Total Commission')],
                                      readonly=True, states={'draft': [('readonly', False)]})

    adjust_side = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], 'Side', default='debit', readonly=True, states={'draft': [('readonly',False)]})

    adjust_amount = fields.Monetary('Amount', readonly=True, states={'draft': [('readonly', False)]},
                             help="Amount to be adjusted")

    description = fields.Text('Description', readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger','adjustment_id')

    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    validate_date = fields.Datetime('Validate Date', readonly=True)
    validate_uid = fields.Many2one('res.users', 'Validated by', readonly=True)
    approve_date = fields.Datetime('Approve Date', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Canceled by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    cancel_message = fields.Text('Cancelation Message', readonly=True, states={'approve': [('readonly', False)]})

    adj_reason = fields.Selection([('sys', 'Error by System'), ('usr', 'Error by User')], 'Reason',
                                  readonly=True, states={'draft': [('readonly', False)]})
    reason_uid = fields.Many2one('res.users', 'Responsible User', readonly=True,
                                 states={'draft': [('readonly', False)]})

    source_of_funds_type = fields.Selection(SOURCE_OF_FUNDS_TYPE, string='Source of Funds', default='balance')

    def get_form_id(self):
        return self.env.ref("tt_accounting.tt_adjustment_form_view")

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.adjustment')
        if 'adj_type' in vals_list:
            if type(vals_list['adj_type']) == int:
                vals_list['adj_type'] = self.parse_adjustment_type(vals_list['adj_type'])
        return super(TtAdjustment, self).create(vals_list)
        
    def parse_adjustment_type(self,type):
        if type == -1:
            return 'balance'
        elif type == -2:
            return 'payment_transaction'
        elif type == -3:
            return 'refund'
        elif type == -4:
            return 'after_sales'
        elif type == -5:
            return 'invoice'
        else:
            return self.env['tt.provider.type'].browse(int(type)).code
        
    def get_adjustment_type(self):
        return [(rec,rec.capitalize()) for rec in self.env['tt.provider.type'].get_provider_type()]+[('payment_transaction', 'Payment Transaction'),
                 ('refund', 'Refund'), ('after_sales', 'After Sales'), ('balance', 'Balance'), ('invoice', 'Invoice')]

    def confirm_adj_from_button(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 2')
        if self.state != 'draft':
            raise UserError("Cannot Approve because state is not 'draft'.")

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now()
        })

    def validate_adj_from_button(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 3')
        if self.state != 'confirm':
            raise UserError("Cannot Approve because state is not 'Confirm'.")

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now()
        })

    def approve_adj_from_button(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 4')
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'Validate'.")
        debit = 0
        credit = 0
        if self.adjust_side == 'debit':
            debit = self.adjust_amount
        else:
            credit = self.adjust_amount

        ledger_type = 5
        if self.component_type == 'total':
            ledger_type = 2
        elif self.component_type == 'commission':
            ledger_type = 3

        ## 3 May 2021 Joshua
        ## pop context default dari wizard adjustment, karena otomatis ke isi waktu create_ledger yang tidak di val_list dan ada di context
        this_context = self.env.context.copy()
        if this_context.get('default_agent_id'):
            this_context.pop('default_agent_id')

        self.with_context(this_context).env['tt.ledger'].create_ledger_vanilla(
            self.res_model,
            self.res_id,
            'Adjustment : for %s' % (self.name),
            self.referenced_document,
            ledger_type,
            self.currency_id.id,
            self.env.user.id,
            self.agent_id.id,
            self.customer_parent_id.id,
            debit,
            credit,
            'Adjustment for %s, by %s%s' % (self.referenced_document,self.name,self.description and '\nReason: %s' % self.description or ''),
            self.source_of_funds_type,
            **{
                'adjustment_id': self.id,
                'refund_id': self.res_model == 'tt.refund' and self.res_id or False,
                'reschedule_id': self.res_model == 'tt.reschedule' and self.res_id or False,
            }
        )

        self.write({
            'state': 'approve',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

        try:
            data = {
                'code': 9901,
                'title': 'ADJUSTMENT',
                'message': 'Adjustment Approved: %s\nUser: %s\nAction: (%s) %s %s\n' % (
                self.name, self.env.user.name, self.adjust_side, self.currency_id.name, str(self.adjust_amount))
            }
            context = {
                "co_ho_id": self.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "adjustment" telegram notification: ' + str(e))

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_accounting.tt_adjustment_action').id
        menu_num = self.env.ref('tt_accounting.menu_transaction_adjustment').id
        return {
            'type': 'ir.actions.act_url',
            'name': self.name,
            'target': 'new',
            'url': base_url + "/web#id=" + str(self.id) + "&action=" + str(action_num) + "&model=tt.refund&view_type=form&menu_id=" + str(menu_num),
        }

    def cancel_adj_from_button(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 5')
        for rec in self.ledger_ids:
            rec.reverse_ledger()

        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    # def approve_all_adjustment(self):
    #     for rec in self.search([('state','=','draft'),
    #                             ('create_date','>','2020-02-18 09:30:00')]):
    #         _logger.info(rec.name)
    #         rec.confirm_adj_from_button()
    #         rec.validate_adj_from_button()
    #         rec.approve_adj_from_button()
    #
    # def approve_all_adjustment_test(self):
    #     for rec in self.search([('state','=','draft'),
    #                             ('create_date','>','2020-02-20 09:30:00')]):
    #         _logger.info(rec.name)

    def multi_action_approve_adjustment(self):
        for rec in self:
            rec.confirm_adj_from_button()
            rec.validate_adj_from_button()
            rec.approve_adj_from_button()