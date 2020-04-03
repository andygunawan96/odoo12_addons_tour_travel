from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback
from ...tools.api import Response
import json


class EmailApiCon(models.Model):
    _name = 'email.api.con'
    _inherit = 'tt.api.con'

    def action_call(self, table_obj, action, data, context):
        if action == 'send_email':
            res = table_obj.create_email_queue(data,context)
        else:
            raise RequestException(999)
        return res



