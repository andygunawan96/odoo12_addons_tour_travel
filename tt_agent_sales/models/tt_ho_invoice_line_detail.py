from odoo import api,models,fields

class AgentInvoiceLineDetailInh(models.Model):
    _name = 'tt.ho.invoice.line.detail'
    _inherit = 'tt.agent.invoice.line.detail'
    _rec_name = 'desc'
    _description = 'HO Invoice Line Detail'

    invoice_line_id = fields.Many2one('tt.ho.invoice.line', 'HO Invoice Line')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    commission_agent_id = fields.Many2one('tt.agent', 'Agent ( Commission )', help='''Agent who get commission''')
    is_commission = fields.Boolean(default=False)
    is_point_reward = fields.Boolean(default=False)

