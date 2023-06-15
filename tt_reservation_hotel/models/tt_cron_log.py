from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_mail_hotel_confirmation(self):
        mail_type = 'hotel_confirmation'
        # list_provider = ['test_internal']
        list_provider = ['Quantum']
        try:
            for to_send in self.env['tt.reservation.hotel'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=1)),('create_date', '>', datetime.today() - timedelta(days=2)),('provider_name', 'in', list_provider)]):
            # for to_send in self.env['tt.reservation.hotel'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=1)),('provider_name', 'in', list_provider)]):
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', to_send.id), ('res_model', '=', to_send._name),('type', '=', mail_type)], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': mail_type,
                        'order_number': to_send.name,
                        'res_id': to_send.id,
                        'res_model': to_send._name,
                        'type': '',
                    }
                    temp_context = {
                        'co_agent_id': to_send.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Update ' + mail_type)

    def cron_mail_hotel_spc_request(self):
        mail_type = 'hotel_spc_request'
        # list_provider = ['test_internal']
        list_provider = ['Quantum']
        try:
            for to_send in self.env['tt.reservation.hotel'].sudo().search([('create_date', '<=', datetime.today() - timedelta(days=1)),('create_date', '>', datetime.today() - timedelta(days=2)),('provider_name', 'in', list_provider)]):
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', to_send.id), ('res_model', '=', to_send._name),('type', '=', mail_type)], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': mail_type,
                        'order_number': to_send.name,
                        'res_id': to_send.id,
                        'res_model': to_send._name,
                        'type': '',
                    }
                    temp_context = {
                        'co_agent_id': to_send.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Update ' + mail_type)

    def cron_mail_hotel_retrieve_booking(self):
        list_provider = ['TBO Holidays']
        try:
            for to_send in self.env['tt.reservation.hotel'].sudo().search([('create_date', '<=', datetime.today() - timedelta(minutes=2)),('create_date', '>', datetime.today() - timedelta(minutes=4)),('provider_name', 'in', list_provider)]):
                to_send.check_booking_status()

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Retrieve Booking Hotel : TBO')

    def cron_hotel_prepare(self):
        try:
            if int(self.env['ir.config_parameter'].sudo().get_param('last.gw.render.idx')):
                self.env['tt.hotel'].v2_prepare_gateway_cache()

        except Exception as e:
            pass
