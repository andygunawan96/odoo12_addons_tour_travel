from odoo import api,fields,models

class TtTopUpInh(models.Model):
    _inherit = 'tt.top.up'

    payment_id = fields.Many2one('tt.payment','Payment',readonly=True)
    acquirer_id = fields.Many2one('payment.acquirer','Acquirer', related="payment_id.acquirer_id")

    def action_validate_top_up(self,validate_amount):
        self.validated_amount = validate_amount - self.fees
        super(TtTopUpInh, self).action_validate_top_up()

    def action_cancel_top_up(self,context):
        super(TtTopUpInh, self).action_cancel_top_up(context)
        if self.payment_id:
            self.payment_id.action_cancel_payment(context)