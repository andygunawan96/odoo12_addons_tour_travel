from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsersInh(models.Model):
    _inherit = 'res.users'

    accounting_uid = fields.Char('User ID in Ext. Accounting Software')
