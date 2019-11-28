from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class TtPaymentApiCon(models.Model):
    _name = 'tt.payment.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.payment.con'

    def set_VA(self, req):
        data = {
            'phone_number': req['number'],
            'name': req['name'],
            'email': req['email'],
            'provider': 'espay'
        }
        return self._send_request('%s/payment' % (self.url), data,'set_va')
