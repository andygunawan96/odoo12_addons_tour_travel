import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class ConfirmOrderMitraKeluargaWizard(models.TransientModel):
    _name = "confirm.order.mitrakeluarga.wizard"
    _description = 'Confirm Order Swab Express Wizard'

    booking_id = fields.Many2one('tt.reservation.mitrakeluarga','Booking',readonly=True)
    analyst_ids = fields.Many2many('tt.analyst.mitrakeluarga', 'tt_reservation_mitrakeluarga_analyst_confirm_order_wizard_rel', 'wizard_id',
                                   'analyst_id', 'Analyst(s)')

    @api.onchange('booking_id')
    def _onchange_domain_picked_timeslot_id(self):
        return {'domain': {
                'picked_timeslot_id': [('id','in',self.booking_id.timeslot_ids.ids)]
            }}


    def confirm_order(self):
        if not ({self.env.ref('tt_base.group_external_vendor_mitrakeluarga_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 194')
        if not self.analyst_ids:
            raise UserError("Please Pick Timeslot and Input Analyst")
        self.booking_id.write({
            'analyst_ids': [(6,0,self.analyst_ids.ids)],
            'state_vendor': 'confirmed_order'
        })

        ho_id = self.booking_id.agent_id.ho_id.id
        try:
            self.env['tt.mitrakeluarga.api.con'].send_confirm_order_notification(self.booking_id.name,
                                                                             self.env.user.name,
                                                                             self.booking_id.test_datetime.astimezone(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y %H:%M"),
                                                                             self.booking_id.test_address, ho_id)
        except Exception as e:
            _logger.error("Confirm Order From Button Notification Telegram Error.\n%s" % (traceback.format_exc()))