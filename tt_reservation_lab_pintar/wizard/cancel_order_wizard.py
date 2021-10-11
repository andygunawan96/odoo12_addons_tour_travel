import pytz

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)


class CancelOrderLabPintarWizard(models.TransientModel):
    _name = "cancel.order.lab.pintar.wizard"
    _description = 'Cancel Order Lab Pintar Wizard'

    booking_id = fields.Many2one('tt.reservation.lab.pintar','Booking',readonly=True)
    cancellation_reason = fields.Char('Cancellation Reason', required=True)

    def cancel_order(self):
        self.booking_id.write({
            'cancellation_reason': self.cancellation_reason
        })
        self.booking_id.action_cancel()
