from odoo import api, fields, models, _
from ...tools import variables

class TbServiceCharge(models.Model):
    _name = 'tt.service.charge'

    charge_code = fields.Char('Charge Code', default='fare', required=True)
    charge_type = fields.Char('Charge Type')  # FARE, INF, TAX, SSR, CHR
    pax_type = fields.Selection(variables.PAX_TYPE, string='Pax Type')
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pax_count = fields.Integer('Pax Count', default=1)
    amount = fields.Monetary('Amount', currency_field='currency_id')
    total = fields.Monetary('Total', currency_field='currency_id')
    foreign_currency_id = fields.Many2one('res.currency', 'Foreign Currency',
                                          default=lambda self: self.env.user.company_id.currency_id)
    foreign_amount = fields.Monetary('Foreign Amount', currency_field='foreign_currency_id')

    sequence = fields.Integer('Sequence')
    description = fields.Text('Description')

    commission_agent_id = fields.Many2one('tt.agent', 'Agent ( Commission )', help='''Agent who get commission''')

    # @api.one
    # @api.depends('pax_count', 'amount')
    # def _compute_total(self):
    #     self.total = self.pax_count * self.amount