from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtMasterAdminFee(models.TransientModel):
    _inherit = 'tt.history'
    _name = "tt.master.admin.fee"
    _description = 'Master Admin Fee'

    name = fields.Char('Name')
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True, index=True)
    type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type')
    amount = fields.Float('Amount')
    min_amount = fields.Float('Minimum Amount', default=0)

    def _compute_display_name(self):
        self.display_name = self.name + ': ' + self.type == 'amount' and 'IDR ' or '' + self.amount + self.type == 'percentage' and '%' or ''

    def get_final_adm_fee(self, total=0, multiplier=1):
        if self.type == 'amount':
            return self.amount * multiplier
        else:
            result = ((self.amount / 100) * total) * multiplier
            if result >= self.min_amount:
                return result
            else:
                return self.min_amount
