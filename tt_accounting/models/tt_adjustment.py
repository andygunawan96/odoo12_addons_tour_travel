from odoo import api,models,fields
from ...tools import variables

class TtAdjustment(models.Model):
    _name = "tt.adjustment"
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
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True,
                               default=lambda self: self.env.user.agent_id, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    adj_type = fields.Selection(variables.ADJUSTMENT_TYPE+[('payment_transaction', 'Payment Transaction'),
                                 ('balance', 'Balance')], 'Adjustment Type', required=True, readonly=True,
                                states={'draft': [('readonly', False)]})

    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    component_amount = fields.Monetary('Initial Amount', store=True)#compute='onchange_component_type',

    #ini apa?
    # vendor_amount_offline = fields.Monetary('Vendor Amount', readonly=True)
    # ho_amount_offline = fields.Monetary('HO Amount', readonly=True)
    # final_vendor_amount_offline = fields.Monetary('Final Vendor Amount', readonly=True)
    # final_ho_amount_offline = fields.Monetary('Final HO Amount', readonly=True)

    amount = fields.Monetary('Adjusted Amount', readonly=True, states={'draft': [('readonly', False)]},
                             help="Amount to be adjusted")
    agent_commission = fields.Monetary('Agent Amount')#, compute='onchange_amount'
    parent_agent_commission = fields.Monetary('Parent Agent Amount')#, compute='onchange_amount'
    ho_commission = fields.Monetary('HO Amount')#, compute='onchange_amount'

    final_amount = fields.Monetary('Final Amount')#, compute='onchange_amount'

    description = fields.Text('Description', readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger','res_id',domain={'res_model':'tt.adjustment'})

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

