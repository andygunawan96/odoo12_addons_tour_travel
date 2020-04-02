from odoo import models, fields, api, _


class AgentRegistration(models.Model):

    _inherit = 'tt.agent.registration'

    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True)  # , compute='set_agent_invoice_state'

    invoice_line_ids = fields.One2many('tt.agent.registration.invoice.line', 'res_id_resv', 'Invoice')
