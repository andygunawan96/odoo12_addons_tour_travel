from odoo import models, fields, api, _


class TtAgent(models.Model):
    _inherit = 'tt.agent'

    ledger_ids = fields.One2many('tt.ledger', 'agent_id', 'Ledger(s)')
    balance = fields.Monetary(string="Balance", compute="_compute_balance_agent",store=True)
    adjustment_ids = fields.One2many('tt.adjustment', 'res_id', 'Adjustment Balance',
                                     domain=[('res_model', '=', 'tt.agent')])

    def action_view_ledgers(self):
        return {
            'name': _('Ledger(s)'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'tt.ledger',
            'domain': [('agent_id', '=', self.id)],
            'context': {
                'form_view_ref': 'tt_accounting.tt_ledger_form_view',
                'tree_view_ref': 'tt_accounting.tt_ledger_tree_view_page'
            },
        }

    def compute_all_agent_balance(self):
        for rec in self.search([]):
            rec._compute_balance_agent()

    @api.depends('ledger_ids','ledger_ids.balance')
    def _compute_balance_agent(self):
        for rec in self:
            if len(rec.ledger_ids)>0:
                rec.balance = rec.ledger_ids[0].balance
            else:
                rec.balance = 0