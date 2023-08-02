from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime
_logger = logging.getLogger(__name__)


class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_update_status_booking(self):
        ho_objs = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for ho_obj in ho_objs:
            try:
                cookie = ''
                booking_objs = self.env['tt.reservation.activity'].search([('state', 'not in', ['rejected', 'cancel', 'issued', 'cancel2', 'refund', 'fail_issued']),('ho_id','=',ho_obj.id)])
                for rec in booking_objs:
                    req = {
                        'provider': rec['provider_name'],
                        'uuid': rec['booking_uuid'],
                        'pnr': rec['pnr']
                    }
                    if req['uuid'] or req['pnr']:
                        if req['provider']:
                            res = self.env['tt.activity.api.con'].get_booking(req, rec.agent_id.ho_id.id)
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
                self.write_cron_log('Update status booking Activity', ho_id=ho_obj.id)

    def cron_auto_sync_activity(self):
        try:
            auto_sync_setups = self.env['tt.auto.sync.activity.setup'].search(['|',
                                                                               ('next_exec_time', '<=', datetime.now()),
                                                                               ('is_json_generated', '=', True)])
            for rec in auto_sync_setups:
                rec.execute_sync_products()
        except Exception as e:
            ## tidak tahu pakai context apa
            self.create_cron_log_folder()
            self.write_cron_log('Auto Sync Activity')
