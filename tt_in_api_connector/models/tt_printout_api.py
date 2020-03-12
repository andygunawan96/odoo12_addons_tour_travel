from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtPrintoutApiCon(models.Model):
    _name = 'tt.printout.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.airline'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_printout_api':
            if data['provider_type'] == 'top_up':
                book_obj = self.env['tt.top.up'].search([('name', '=', data['order_number'])], limit=1)
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
                    res = self.env['tt.top.up'].print_topup(data, context)
                else:
                    raise RequestException(1001)
            elif data['mode'] == 'invoice':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
                    res = self.env['tt.agent.invoice'].print_invoice_api(data, context)
                else:
                    raise RequestException(1001)
            elif data['provider_type'] == 'tour':
                pass
            elif data['provider_type'] == 'hotel':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
                    if data['mode'] == 'ticket':
                        res = self.env['tt.reservation.%s' % data['provider_type']].do_print_voucher(data, context)
                    # elif data['mode'] == 'itinerary':
                    #     res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
                else:
                    # if data['mode'] == 'ticket':
                    #     raise RequestException(1001)
                    if data['mode'] == 'itinerary':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
            else:
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
                    if data['mode'] == 'ticket':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket(data, context)
                    elif data['mode'] == 'ticket_price':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket_with_price(data, context)
                    elif data['mode'] == 'itinerary':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
                    elif data['mode'] == 'visa_cust':
                        res = self.env['tt.reservation.%s' % data['provider_type']].do_print_out_visa_cust(data, context)
                else:
                    raise RequestException(1001)
            if type(res) == list:
                temp = []
                for rec in res:
                    temp.append({'url':rec['url']})
                res = temp
            else:
                res = {
                    'url': res['url']
                }
        else:
            raise RequestException(999)

        return res