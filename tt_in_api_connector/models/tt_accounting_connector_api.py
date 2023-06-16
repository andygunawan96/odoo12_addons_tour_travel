from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAccountingConnectorApiCon(models.Model):
    _name = 'tt.accounting.connector.api.con'
    _inherit = 'tt.api.con'

    def send_notif_reverse_ledger(self, transport_type, ref_number, vendor_list_str, ho_id):

        request = {
            'code': 9909,
            'message': '%s Journal Entry with reference number [%s] has been edited. Affected vendors: %s' % (transport_type, ref_number, vendor_list_str),
            'title': '<b>Accounting Connector</b>'
        }
        return self.send_request_to_gateway('%s/notification' % (self.url), request, 'notification_code', ho_id=ho_id)
