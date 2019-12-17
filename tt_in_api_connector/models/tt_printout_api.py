from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPrintoutApiCon(models.Model):
    _name = 'tt.printout.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.airline'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_printout_api':
            if data['provider_type'] == 'visa':
                if data['mode'] == 'invoice':
                    pass
            elif data['provider_type'] == 'tour':
                if data['mode'] == 'invoice':
                    pass
            elif data['provider_type'] == 'hotel':
                if data['mode'] == 'invoice':
                    pass
            else:
                if data['mode'] == 'invoice':
                    pass
                elif data['mode'] == 'ticket':
                    res = self.env['tt.reservation.airline'].print_eticket(data, context)
                elif data['mode'] == 'ticket_price':
                    res = self.env['tt.reservation.airline'].print_eticket_with_price(data, context)

        else:
            raise RequestException(999)

        return res