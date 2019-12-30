from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtMasterAdminFee(models.Model):
    _inherit = 'tt.history'
    _name = "tt.master.admin.fee"
    _description = 'Master Admin Fee'

    name = fields.Char('Name')
    type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type', default='amount')
    amount = fields.Float('Amount')
    min_amount = fields.Float('Minimum Amount', default=0)

    def get_final_adm_fee(self, total=0, multiplier=1):
        if self.type == 'amount':
            return self.amount * multiplier
        else:
            result = ((self.amount / 100) * total) * multiplier
            if result >= self.min_amount:
                return result
            else:
                return self.min_amount
