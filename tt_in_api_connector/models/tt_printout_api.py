from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPrintoutApiCon(models.Model):
    _name = 'tt.printout.api.con'
    _inherit = 'tt.api.con'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_printout_api':
            if data['mode'] == 'invoice':
                if data['provider_type'] == 'airline':
                    pass
                elif data['provider_type'] == 'airline':
                    pass
                elif data['provider_type'] == 'train':
                    pass
                elif data['provider_type'] == 'activity':
                    pass
                elif data['provider_type'] == 'tour':
                    pass
                elif data['provider_type'] == 'hotel':
                    pass
                elif data['provider_type'] == 'visa':
                    pass
                res = self.env['tt.reservation.visa.pricelist'].search_api(data)
            elif data['mode'] == 'ticket':
                pass
                res = self.env['tt.reservation.visa.pricelist'].search_api(data)
            elif data['mode'] == 'ticket_price':
                pass
                res = self.env['tt.reservation.visa.pricelist'].search_api(data)
            elif data['mode'] == 'form':
                pass
                res = self.env['tt.reservation.visa.pricelist'].search_api(data)
        else:
            raise RequestException(999)

        return res