from odoo import api,models,fields

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    smtp_user = fields.Char(string='Username', help="Optional username for SMTP authentication",
                            groups='base.group_erp_manager')
    smtp_pass = fields.Char(string='Password', help="Optional password for SMTP authentication",
                            groups='base.group_erp_manager')