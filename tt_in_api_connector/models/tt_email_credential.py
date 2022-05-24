from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtEmailCredentialApiCon(models.Model):
    _name = 'tt.email.credential.api.con'
    _inherit = 'tt.api.con'

    table_name = 'ir.mail_server'

    def action_call(self,table_obj,action,data,context):

        if action == 'set_email_credential':
            res = table_obj.set_email_from_gateway(data)
        else:
            raise RequestException(999)

        return res