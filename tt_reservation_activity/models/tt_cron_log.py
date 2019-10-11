from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking(self):
        try:
            cookie = ''
            booking_objs = self.env['tt.reservation.activity'].search([('state', 'not in', ['rejected', 'cancel', 'done', 'cancel2', 'refund', 'fail_issued'])])
            for rec in booking_objs:
                req = {
                    'provider': rec['provider_name'],
                    'uuid': rec['booking_uuid'],
                    'pnr': rec['pnr']
                }
                if req['uuid'] or req['pnr']:
                    if req['provider']:
                        res = self.env['tt.activity.api.con'].get_booking(req)
                        if res['response']:
                            values = res['response']
                            method_name = 'action_%s' % values['status']
                            if hasattr(rec, method_name):
                                getattr(rec, method_name)()
                        else:
                            rec.action_failed_sync()
                            values = {
                                'status': 'fail_issued',
                            }
                        if rec['state'] != values['status']:
                            self.env['tt.reservation.activity'].send_notif_update_status_activity(rec, values['status'])
                    else:
                        pass
                else:
                    if rec['state'] != 'failed':
                        rec.action_failed_sync()
                        self.env['tt.reservation.activity'].send_notif_update_status_activity(rec, 'failed')

        except Exception as e:
            self.create_cron_log_folder()
            self.write_cron_log('Update status booking Activity')
