from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TtCustomerParentType(models.Model):
    _name = 'tt.customer.parent.type'
    _inherit = ['tt.history']
    _description = 'Tour & Travel - Customer Parent Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, help='Fixed code, ex: COR, POR, for sale pricing')
    active = fields.Boolean('Active', default='True')

    @api.model
    def create(self, vals):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_customer_parent_type_level_2').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Action failed due to security restriction. Required Customer Parent Type Level 2 permission.')
        return super(TtCustomerParentType, self).create(vals)

    @api.multi
    def unlink(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_customer_parent_type_level_5').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Action failed due to security restriction. Required Customer Parent Type Level 5 permission.')
        return super(TtCustomerParentType, self).unlink()
