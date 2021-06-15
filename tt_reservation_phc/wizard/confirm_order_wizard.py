import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class ConfirmOrderphcWizard(models.TransientModel):
    _name = "confirm.order.phc.wizard"
    _description = 'Confirm Order phc Wizard'

    booking_id = fields.Many2one('tt.reservation.phc','Booking',readonly=True)
    picked_timeslot_id = fields.Many2one('tt.timeslot.phc', 'Picked Timeslot')
    analyst_ids = fields.Many2many('tt.analyst.phc', 'tt_reservation_phc_analyst_confirm_order_wizard_rel', 'wizard_id',
                                   'analyst_id', 'Analyst(s)')

    @api.onchange('booking_id')
    def _onchange_domain_picked_timeslot_id(self):
        return {'domain': {
                'picked_timeslot_id': [('id','in',self.booking_id.timeslot_ids.ids)]
            }}


    def confirm_order(self):
        if not self.picked_timeslot_id or not self.analyst_ids:
            raise UserError("Please Pick Timeslot and Input Analyst")
        self.booking_id.write({
            'picked_timeslot_id': self.picked_timeslot_id.id,
            'analyst_ids': [(6,0,self.analyst_ids.ids)]
        })
        for provider_obj in self.booking_id.provider_booking_ids:
            provider_obj.action_issued_phc(self.env.user.id)

        self.booking_id.check_provider_state({'co_uid': self.env.user.id})


