import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class CancelOrderSwabExpressWizard(models.TransientModel):
    _name = "cancel.order.swab.express.wizard"
    _description = 'Cancel Order Swab Express Wizard'

    booking_id = fields.Many2one('tt.reservation.swab.express','Booking',readonly=True)
    cancellation_reason = fields.Char('Cancellation Reason', required=True)

    def cancel_order(self):
        self.booking_id.write({
            'cancellation_reason': self.cancellation_reason
        })
        self.booking_id.action_cancel()
