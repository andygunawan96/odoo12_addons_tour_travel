from odoo import api,models,fields
import json
import logging
from ...tools.ERR import RequestException
_logger = logging.getLogger(__name__)
class TtPrintoutApiCon(models.Model):
    _name = 'tt.printout.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.reservation.airline'

    def action_call(self, table_obj, action, data, context):

        if action == 'get_printout_api':
            _logger.info(json.dumps(data)) #agar tau kalau ada error params printout apa
            user_obj = self.env['res.users'].browse(context['co_uid'])
            if data['provider_type'] == 'top_up':
                book_obj = self.env['tt.top.up'].search([('name', '=', data['order_number'])], limit=1)
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1):
                    res = self.env['tt.top.up'].print_topup(data, context)
                else:
                    raise RequestException(1001)
            elif data['mode'] == 'invoice':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or (self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids) or (self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids):
                    if data.get('reschedule_number'):
                        res = self.env['tt.agent.invoice'].print_reschedule_invoice_api(data, context)
                    else:
                        res = self.env['tt.agent.invoice'].print_invoice_api(data, context)
                else:
                    raise RequestException(1001)
            elif data.get('reschedule_number'):
                res = self.env['tt.reschedule'].print_reschedule_changes(data, context)
            elif data['mode'] == 'kwitansi':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or (self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids) or (self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids):
                    res = self.env['tt.agent.invoice'].print_kwitansi_api(data, context)
                else:
                    raise RequestException(1001)
            elif data['provider_type'] == 'hotel':
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or (self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids) or (self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids):
                    if data['mode'] == 'ticket':
                        res = self.env['tt.reservation.%s' % data['provider_type']].do_print_voucher(data, context)
                    elif data['mode'] == 'itinerary':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
                    elif data['mode'] == 'itinerary_price':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary_price(data, context)
                else:
                    # if data['mode'] == 'ticket':
                    #     raise RequestException(1001)
                    if data['mode'] == 'itinerary':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
                    elif data['mode'] == 'itinerary_price':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary_price(data)
            elif data['provider_type'] == 'event':
                if data['mode'] == 'ticket':
                    res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket(data, context)
                elif data['mode'] == 'ticket_price':
                    res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket_with_price(data, context)
                elif data['mode'] == 'itinerary':
                    res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data)
                elif data['mode'] == 'itinerary_price':
                    res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary_price(data)
            else:
                book_obj = self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])])
                if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or (self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids) or (self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids):
                    if data['mode'] == 'ticket':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket(data, context)
                    elif data['mode'] == 'ticket_price':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket_with_price(data, context)
                    elif data['mode'] == 'ticket_original':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_eticket_original(data, context)
                    elif data['mode'] == 'itinerary':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary(data, context)
                    elif data['mode'] == 'itinerary_price':
                        res = self.env['tt.reservation.%s' % data['provider_type']].print_itinerary_price(data, context)
                    elif data['mode'] == 'visa_cust':
                        res = self.env['tt.reservation.%s' % data['provider_type']].do_print_out_visa_cust(data, context)
                    elif data['mode'] == 'passport_cust':
                        res = self.env['tt.reservation.%s' % data['provider_type']].do_print_out_passport_cust(data, context)
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

        elif action == 'set_color_printout':
            res = self.env['tt.report.common.setting'].set_color_printout_api(data, context)
        elif action == 'get_color_printout':
            res = self.env['tt.agent'].get_printout_agent_color(context)
        elif action == 'get_list_report_footer':
            res = self.env['tt.report.common.setting'].get_list_report_footer_api(data, context)
        elif action == 'set_report_footer':
            res = self.env['tt.report.common.setting'].set_report_footer_api(data, context)
        else:
            raise RequestException(999)

        return res
