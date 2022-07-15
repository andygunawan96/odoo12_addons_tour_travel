from odoo import api,models,fields,_
from odoo.exceptions import UserError


class TtRefundType(models.Model):
    _name = "tt.refund.type"
    _inherit = 'tt.history'
    _description = "Refund Type Model"

    name = fields.Char('Name', default='New')
    days = fields.Integer('Amount of Days', default=40)
    active = fields.Boolean('Active', default=True)
