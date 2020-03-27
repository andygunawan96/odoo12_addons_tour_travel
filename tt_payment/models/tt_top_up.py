from odoo import api,fields,models

class TtTopUpInh(models.Model):
    _inherit = 'tt.top.up'

    payment_id = fields.Many2one('tt.payment','Payment',readonly=True)
    acquirer_id = fields.Many2one('payment.acquirer','Acquirer', related="payment_id.acquirer_id")
    fees = fields.Monetary('Fees', default=0, help='Fees amount; set by the system because depends on the acquirer',
                           compute='_compute_fee_related_to_acqurier',store=True,
                           readonly=True, states={'draft': [('readonly', False)]})

    def get_total_amount(self):
        return self.validated_amount - self.fees

    def action_validate_top_up(self,validate_amount):
        self.validated_amount = validate_amount
        super(TtTopUpInh, self).action_validate_top_up()

    def action_cancel_top_up(self,context):
        super(TtTopUpInh, self).action_cancel_top_up(context)
        if self.payment_id:
            self.payment_id.action_cancel_payment(context)

    @api.depends('acquirer_id','acquirer_id.va_fee')
    def _compute_fee_related_to_acqurier(self):
        for rec in self:
            rec.fees = rec.acquirer_id