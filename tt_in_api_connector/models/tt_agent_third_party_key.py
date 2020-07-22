from odoo import api,models,fields
from ...tools.ERR import RequestException



class EmailApiCon(models.Model):
    _name = 'tt.agent.third.party.key.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.agent.third.party.key'

    def action_call(self, table_obj, action, data, context):
        if action == 'connect_key':
            res = table_obj.external_connect_key_api(data,context)
        elif action == 'get_balance':
            res = table_obj.external_get_balance_api(data,context)
        elif action == 'payment':
            res = table_obj.external_payment_api(data,context)
        elif action == 'reverse_payment':
            res = table_obj.external_reverse_payment_api(data, context)
        else:
            raise RequestException(999)
        return res



