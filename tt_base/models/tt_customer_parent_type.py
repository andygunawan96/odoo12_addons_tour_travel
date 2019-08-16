from odoo import models, fields, api, _


class TtCustomerParentType(models.Model):
    _name = 'tt.customer.parent.type'
    # _inherit = ['tt.history']
    _description = 'Tour & Travel - Customer Parent Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, help='Fixed code, ex: COR, POR, for sale pricing')
    active = fields.Boolean('Active', default='True')