import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class ConfirmOrderPeriksainWizard(models.TransientModel):
    _name = "confirm.order.periksain.wizard"
    _description = 'Confirm Order Periksain Wizard'

    booking_id = fields.Many2one('tt.reservation.periksain','Booking',readonly=True)
    picked_timeslot_id = fields.Many2one('tt.timeslot.periksain', 'Picked Timeslot', domain="[('id','in',booking_id.ids)]")
    analyst_ids = fields.Many2many('tt.analyst.periksain', 'tt_reservation_periksain_analyst_confirm_order_wizard_rel', 'wizard_id',
                                   'analyst_id', 'Analyst(s)')

    def _confirm_order(self):
        if not self.picked_timeslot_id or not self.analyst_ids:
            raise UserError("Please Pick Timeslot and Input Analyst")
        self.booking_id.write({
            'picked_timeslot_id': self.picked_timeslot_id.id,
            'analyst_ids': [(6,0,self.analyst_ids.ids)]
        })
        self.action_issued_periksain(self.env.user.id)


