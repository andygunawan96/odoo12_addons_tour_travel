from odoo import api,models,fields
import json

class TtSsrAirline(models.Model):
    _name = 'tt.fee.airline'
    _description = 'Fee Airline Model'

    name = fields.Char("Name")
    type = fields.Char("Type")
    code = fields.Char("Code")
    value = fields.Char("Value")
    category = fields.Char("Category")
    category_icon = fields.Char("Category Icon", compute="_compute_category_icon",store=True)
    description = fields.Text("Description")
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency","Currency",default=lambda self:self.env.user.company_id.currency_id)
    passenger_id = fields.Many2one("tt.reservation.passenger.airline","Currency")
    pnr = fields.Char('PNR', default='')
    # May 18, 2020 - SAM
    provider_id = fields.Many2one('tt.provider.airline', 'Provider', default=None)
    journey_code = fields.Char('Journey Code', default='')
    # END

    @api.depends('category')
    def _compute_category_icon(self):
        for rec in self:
            try:
                rec.category_icon = self.env['tt.ssr.category'].search([('key','=',rec.category)],limit=1).icon
            except:
                rec.category_icon = 'fa fa-suitcase'

    def to_dict(self):
        return {
            'fee_name': self.name,
            'fee_type': self.type,
            'fee_code': self.code,
            'fee_value': self.value,
            'fee_category': self.category,
            'description': json.loads(self.description),
            'amount': self.amount,
            'currency': self.currency_id.name,
            'journey_code': self.journey_code and self.journey_code or '',
            'pnr': self.provider_id and self.provider_id.pnr or '',
        }


class TtProviderAirlineInherit(models.Model):
    _inherit = 'tt.provider.airline'
    _description = 'Provider Airline Model Inherit'

    # May 18, 2020 - SAM
    fee_ids = fields.One2many('tt.fee.airline', 'provider_id', 'Fees')
    # END
