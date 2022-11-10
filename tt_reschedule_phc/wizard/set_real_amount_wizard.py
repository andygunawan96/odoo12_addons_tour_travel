from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class PHCSetRealAmountWizard(models.TransientModel):
    _name = "phc.reschedule.set.real.amount.wizard"
    _description = 'Reschedule Set Real Amount Wizard'

    reschedule_line_id = fields.Many2one('tt.reschedule.phc.line', 'Reschedule Line', readonly=True)
    real_reschedule_amount = fields.Integer('Real After Sales Amount from Vendor', default=0, required=True)

    def submit_real_amount(self):
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 90')
        self.reschedule_line_id.write({
            'real_reschedule_amount': self.real_reschedule_amount
        })
