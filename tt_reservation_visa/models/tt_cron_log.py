from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking_visa(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                cookie = ''
                booking_objs = self.env['tt.reservation.visa'].search([('state_visa', 'in', ['delivered']),('ho_id','=', ho_obj.id)])
                for rec in booking_objs:
                    if rec.state_visa == 'delivered':
                        if rec.delivered_date:
                            delivered_date = rec.delivered_date
                            if delivered_date < datetime.now() + timedelta(days=1):
                                for psg in rec.passenger_ids:
                                    psg.action_done()
                        else:
                            rec.delivered_date = datetime.now()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('Update status booking Visa', ho_id=ho_obj.id)

    def cron_check_visa_document_date(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                # doc_to_ho_date = self.env['tt.reservation.visa'].search([('state_visa', 'not in', ['expired', 'draft', 'confirm', 'partial_validate']), ('document_to_ho_date', '<', datetime.now())])
                validate_ho_date = self.env['tt.reservation.visa'].search([('state_visa', 'in', ['draft', 'confirm', 'partial_validate']), ('ho_validate_date', '<', datetime.now()), ('ho_id','=', ho_obj.id)])
                # for rec in doc_to_ho_date:
                #     rec.action_expired()
                for rec in validate_ho_date:
                    rec.action_expired()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('Update status booking Visa', ho_id=ho_obj.id)