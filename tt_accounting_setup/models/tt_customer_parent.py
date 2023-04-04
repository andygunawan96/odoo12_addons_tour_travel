from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TtCustomerParentInh(models.Model):
    _inherit = 'tt.customer.parent'

    accounting_uid = fields.Char('Customer Parent ID in Ext. Accounting Software')
