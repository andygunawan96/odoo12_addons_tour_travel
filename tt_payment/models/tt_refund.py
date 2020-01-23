from odoo import api,models,fields,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class TtRefund(models.Model):
    _inherit = 'tt.refund'

    def refund_cor_payment(self):
        super(TtRefund, self).refund_cor_payment()
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'real_total_amount': self.total_amount_cust,
            'customer_parent_id': self.customer_parent_id.id,
            'state': 'confirm',
            'payment_date': datetime.now(),
            'reference': self.name,
            'confirm_uid': self.confirm_uid.id
        })
