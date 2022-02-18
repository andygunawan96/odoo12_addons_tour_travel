from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, date
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_groupbooking_update_installment_invoice(self):
        try:
            installment_objs = self.env['tt.installment.invoice.groupbooking'].sudo().search([('state_invoice', 'in', ['open', 'trouble'])])
            for rec in installment_objs:
                if rec.agent_invoice_id.state == 'paid':
                    rec.action_set_to_done()
                elif rec.due_date == date.today():
                    res = rec.action_pay_now()
                    if res.get('error_code') and rec.state_invoice != 'trouble':
                        rec.action_trouble()
                elif rec.due_date < date.today() and rec.state_invoice != 'trouble':
                    rec.action_trouble()

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Update installment invoice Group Booking')

    def cron_groupbooking_send_installment_reminder_email(self):
        try:
            installment_objs = self.env['tt.installment.invoice.groupbooking'].sudo().search([('state_invoice', 'in', ['open', 'trouble'])])
            for rec in installment_objs:
                if rec.due_date > date.today() and (rec.due_date - date.today()).days == 3:
                    mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', rec.id), ('res_model', '=', rec._name), ('type', '=', 'tour_installment_reminder')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'tour_installment',
                            'res_id': rec.id,
                            'res_model': rec._name,
                            'type': 'reminder',
                        }
                        temp_context = {
                            'co_agent_id': rec.booking_id.agent_id.id
                        }
                        self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                    else:
                        _logger.info('Installment Reminder email for {} is already created!'.format(rec.booking_id.name))
                        raise Exception('Installment Reminder email for {} is already created!'.format(rec.booking_id.name))
                elif rec.due_date < date.today() and (date.today() - rec.due_date).days == 1:
                    mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', rec.id), ('res_model', '=', rec._name), ('type', '=', 'tour_installment_overdue')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'groupbooking_installment',
                            'res_id': rec.id,
                            'res_model': rec._name,
                            'type': 'overdue',
                        }
                        temp_context = {
                            'co_agent_id': rec.booking_id.agent_id.id
                        }
                        self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                    else:
                        _logger.info(
                            'Installment Overdue email for {} is already created!'.format(rec.booking_id.name))
                        raise Exception(
                            'Installment Overdue email for {} is already created!'.format(rec.booking_id.name))

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Send installment reminder Group Booking')
