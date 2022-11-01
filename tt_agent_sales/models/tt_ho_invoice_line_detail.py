from odoo import api,models,fields

class AgentInvoiceLineDetail(models.Model):
    _name = 'tt.ho.invoice.line.detail'
    _inherit = 'tt.agent.invoice.line.detail'
    _rec_name = 'desc'
    _description = 'HO Invoice Line Detail'

    invoice_line_id = fields.Many2one('tt.ho.invoice.line', 'HO Invoice Line')

    commission_agent_id = fields.Many2one('tt.agent', 'Agent ( Commission )', help='''Agent who get commission''')
    is_commission = fields.Boolean(default=False)

