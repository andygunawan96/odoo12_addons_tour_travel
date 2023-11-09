from odoo import api, fields, models, _
import base64,hmac,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class ForceIssuedWizard(models.TransientModel):
    _name = "force.issued.wizard.ppob"
    _description = 'PPOB Force Issued Wizard'

    provider_id = fields.Many2one('tt.provider.ppob', 'Provider', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', required=True, readonly=True, compute='_compute_booker_agent_id')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True, compute='_compute_booker_agent_id', default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True, compute='_compute_booker_agent_id')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', required=True, domain=[('id', '=', -1)])
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id', readonly=True)
    use_credit_limit = fields.Boolean('Use COR Credit Limit', default=False)
    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Method', domain="[('agent_id', '=', agent_id)]")
    is_using_pin = fields.Boolean('Is Using PIN', compute='_compute_is_using_pin', default=lambda self: self.env.user.is_using_pin)
    pin = fields.Char('PIN')

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _onchange_provider_id(self):
        dom_id_list = []
        for rec in self.booker_id.customer_parent_ids:
            if rec.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
                if rec.credit_limit != 0 and rec.state == 'done':
                    dom_id_list.append(rec.id)
            else:
                dom_id_list.append(rec.id)
        return {'domain': {
            'customer_parent_id': [('id', 'in', dom_id_list)]
        }}

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_booker_agent_id(self):
        for rec in self:
            provider_obj = self.env['tt.provider.ppob'].sudo().search([('id', '=', rec.provider_id.id)])
            rec.agent_id = provider_obj.booking_id.agent_id.id
            rec.ho_id = provider_obj.booking_id.ho_id.id
            rec.booker_id = provider_obj.booking_id.booker_id.id

    def _compute_is_using_pin(self):
        for rec in self:
            rec.is_using_pin = self.env.user.is_using_pin

    def submit_force_issued(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 259')
        if self.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
            payment_data = {
                'member': self.use_credit_limit,
                'acquirer_seq_id': self.use_credit_limit and self.customer_parent_id.seq_id or self.acquirer_id.seq_id
            }
        else:
            payment_data = {
                'member': False,
                'acquirer_seq_id': self.acquirer_id.seq_id
            }
        if self.env.user.is_using_pin:
            if not self.pin:
                raise UserError('Please input your PIN!')
            payment_data.update({
                'pin': hmac.new(str.encode('orbisgoldenway'), str.encode(self.pin), digestmod=hashlib.sha256).hexdigest()
            })
        provider_obj = self.env['tt.provider.ppob'].search([('id', '=', self.provider_id.id)])
        provider_obj.action_force_issued_from_button(payment_data)

    def submit_set_to_issued(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 260')
        if self.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
            payment_data = {
                'member': self.use_credit_limit,
                'acquirer_seq_id': self.use_credit_limit and self.customer_parent_id.seq_id or self.acquirer_id.seq_id
            }
        else:
            payment_data = {
                'member': False,
                'acquirer_seq_id': self.acquirer_id.seq_id
            }
        provider_obj = self.env['tt.provider.ppob'].search([('id', '=', self.provider_id.id)])
        provider_obj.action_set_to_issued_from_button(payment_data)
