from odoo import api,fields,models

class TtTopUpInh(models.Model):
    _inherit = 'tt.top.up'

    payment_id = fields.Many2one('tt.payment','Payment',readonly=True)
    validated_amount = fields.Monetary('Validated Amount',readonly=True)

    def get_total_amount(self):
        return self.validated_amount - self.fees

    def action_validate_top_up(self,validate_amount):
        self.validated_amount = validate_amount
        super(TtTopUpInh, self).action_validate_top_up()
