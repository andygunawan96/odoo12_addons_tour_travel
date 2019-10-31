from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtAirlineApiCon(models.Model):
    _name = 'tt.customer.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.customer'

    def action_call(self,table_obj,action,data,context):

        if action == 'get_customer_list':
            res = table_obj.get_customer_list_api(data, context)
        elif action == 'create_customer':
            res = table_obj.create_or_update_customer_api(data['passengers'], context)
            # self.env['tt.reservation'].create_customer_api(data['passengers'],context)
        else:
            raise RequestException(999)
        return res

    def get_balance(self,provider):
        return self._send_request('%s/account/airline' % (self.url),{'provider': provider},'get_vendor_balance')

