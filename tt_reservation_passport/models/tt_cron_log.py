from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking_passport(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                booking_objs = self.env['tt.reservation.passport'].search([('state_passport', 'in', ['delivered']), ('ho_id','=', ho_obj.id)])
                for rec in booking_objs:
                    if rec.state_passport == 'delivered':
                        if rec.delivered_date:
                            delivered_date = rec.delivered_date
                            if delivered_date < datetime.now() + timedelta(days=1):
                                for psg in rec.passenger_ids:
                                    psg.action_done()
                        else:
                            rec.delivered_date = datetime.now()
            except Exception as e:
                self.create_cron_log_folder()
                self.write_cron_log('Update status booking Passport', ho_id=ho_obj.id)
