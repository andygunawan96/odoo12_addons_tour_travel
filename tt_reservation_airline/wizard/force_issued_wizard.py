from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class ForceIssuedWizard(models.TransientModel):
    _name = "force.issued.wizard"
    _description = 'Airline Force Issued Wizard'

    provider_id = fields.Many2one('tt.provider.airline', 'Provider', readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True, compute='_compute_agent_id')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True)
    cor_membership = fields.Selection([('member', 'Member'), ('non_member', 'Non-Member')], 'Corporate Membership', required=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', domain="[('parent_agent_id', '=', agent_id)]")
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id', readonly=True)
    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Method', domain="[('agent_id', '=', agent_id)]")

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_agent_id(self):
        for rec in self:
            provider_obj = self.env['tt.provider.airline'].sudo().search([('id', '=', rec.provider_id.id)])
            rec.agent_id = provider_obj.booking_id.agent_id.id

    def submit_force_issued(self):
        provider_obj = self.env['tt.provider.airline'].sudo().search([('id', '=', self.provider_id.id)])
        payment_data = {
            'member': self.cor_membership == 'member' and True or False,
            'acquirer_seq_id': self.cor_membership == 'member' and self.customer_parent_id.id or self.acquirer_id.id
        }
        provider_obj.action_force_issued_from_button(payment_data)

    def submit_set_to_issued(self):
        provider_obj = self.env['tt.provider.airline'].sudo().search([('id', '=', self.provider_id.id)])
        payment_data = {
            'member': self.cor_membership == 'member' and True or False,
            'acquirer_seq_id': self.cor_membership == 'member' and self.customer_parent_id.id or self.acquirer_id.id
        }
        provider_obj.action_set_to_issued_from_button(payment_data)
