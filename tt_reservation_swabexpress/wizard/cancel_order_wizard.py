import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class CancelOrderSwabExpressWizard(models.TransientModel):
    _name = "cancel.order.swabexpress.wizard"
    _description = 'Cancel Order Swab Express Wizard'

    booking_id = fields.Many2one('tt.reservation.swabexpress','Booking',readonly=True)
    cancellation_reason = fields.Char('Cancellation Reason', required=True)

    def cancel_order(self):
        if not ({self.env.ref('tt_base.group_external_vendor_swabexpress_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 281')
        self.booking_id.write({
            'cancellation_reason': self.cancellation_reason
        })
        self.booking_id.action_cancel()
