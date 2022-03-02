import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class ConfirmOrderSentraMedikaWizard(models.TransientModel):
    _name = "confirm.order.sentramedika.wizard"
    _description = 'Confirm Order Sentra Medika Wizard'

    booking_id = fields.Many2one('tt.reservation.sentramedika','Booking',readonly=True)
    analyst_ids = fields.Many2many('tt.analyst.sentramedika', 'tt_reservation_sentramedika_analyst_confirm_order_wizard_rel', 'wizard_id',
                                   'analyst_id', 'Analyst(s)')

    @api.onchange('booking_id')
    def _onchange_domain_picked_timeslot_id(self):
        return {'domain': {
                'picked_timeslot_id': [('id','in',self.booking_id.timeslot_ids.ids)]
            }}


    def confirm_order(self):
        if not self.analyst_ids:
            raise UserError("Please Pick Timeslot and Input Analyst")
        self.booking_id.write({
            'analyst_ids': [(6,0,self.analyst_ids.ids)],
            'state_vendor': 'confirmed_order'
        })

        try:
            self.env['tt.sentramedika.api.con'].send_confirm_order_notification(self.booking_id.name,
                                                                             self.env.user.name,
                                                                             self.booking_id.test_datetime.astimezone(pytz.timezone('Asia/Jakarta')).strftime("%d-%m-%Y %H:%M"),
                                                                             self.booking_id.test_address)
        except Exception as e:
            _logger.error("Confirm Order From Button Notification Telegram Error.\n%s" % (traceback.format_exc()))