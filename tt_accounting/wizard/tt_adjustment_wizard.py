from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


SOURCE_OF_FUNDS_TYPE = [
    ('balance', 'Balance'),
    ('point', 'Point Reward'),
    ('credit_limit', 'Credit Limit')
]

class TtAdjustmentWizard(models.TransientModel):
    _name = "tt.adjustment.wizard"
    _description = 'Adjustment Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent')

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)

    currency_id = fields.Many2one('res.currency', readonly=True)
    adj_type = fields.Integer('Adjustment Type', required=True, readonly=True)

    referenced_document = fields.Char('Ref. Document',required=True,readonly=True)

    res_model = fields.Char(
        'Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource',readonly=True)

    component_type = fields.Selection([('total', 'Grand Total'), ('commission', 'Total Commission')])

    adjust_side = fields.Selection([('debit','Debit'),('credit','Credit')],'Side',default='debit')

    adjust_amount = fields.Monetary('Debit Amount')  # compute='onchange_component_  type',

    adj_reason = fields.Selection([('sys', 'Error by System'), ('usr', 'Error by User')], 'Reason')

    reason_uid = fields.Many2one('res.users', 'Responsible User')

    description = fields.Text('Description')

    source_of_funds_type = fields.Selection(SOURCE_OF_FUNDS_TYPE, string='Source of Funds', default='balance')

    def submit_adjustment(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 26')

        if self.adj_reason == 'sys':
            self.reason_uid = False

        adjustment_obj = self.env['tt.adjustment'].create({
            'ho_id': self.ho_id.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'adj_type': self.adj_type,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'component_type': self.component_type,
            'source_of_funds_type': self.source_of_funds_type,
            'referenced_document': self.referenced_document,
            'adjust_side': self.adjust_side,
            'adjust_amount': self.adjust_amount,
            'adj_reason': self.adj_reason,
            'reason_uid': self.reason_uid.id,
            'description': self.description
        })
        return adjustment_obj

    def submit_and_force_approve_adjustment(self):
        if not self.env.user.has_group('tt_base.group_adjustment_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 27')

        adj_obj = self.submit_adjustment()
        adj_obj.confirm_adj_from_button()
        adj_obj.validate_adj_from_button()
        adj_obj.approve_adj_from_button()

        #
        # form_id = self.env['tt.adjustment'].get_form_id()
        #
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Split Wizard',
        #     'res_model': 'tt.adjustment',
        #     'res_id': adjustment_obj.id,
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'view_id': form_id.id,
        #     'context': {},
        #     'flags': {'form': {'action_buttons': True, 'options': {'mode': 'browse'}}},
        #     'target': 'new',
        # }
