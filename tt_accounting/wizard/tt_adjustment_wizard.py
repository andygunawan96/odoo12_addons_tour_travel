from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)

class TtAdjustmentWizard(models.TransientModel):
    _name = "tt.adjustment.wizard"
    _description = 'Adjustment Wizard'


    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)

    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    readonly=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True)

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type', related='customer_parent_id.customer_parent_type_id',
                                    readonly=True)

    currency_id = fields.Many2one('res.currency', readonly=True)
    adj_type = fields.Char('Adjustment Type', required=True, readonly=True)

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

    def submit_adjustment(self):
        if self.adj_reason == 'sys':
            self.reason_uid = False

        self.env['tt.adjustment'].create({
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'currency_id': self.currency_id.id,
            'adj_type': self.adj_type,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'component_type': self.component_type,
            'adjust_side': self.adjust_side,
            'adjust_amount': self.adjust_amount,
            'ajd_reason': self.adj_type,
            'reason_uid': self.reason_uid.id,
            'description': self.description
        })
