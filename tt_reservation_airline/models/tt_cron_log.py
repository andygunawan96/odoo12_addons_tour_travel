from odoo import api,models,fields
from ...tools import variables
import logging,traceback
from datetime import datetime,timedelta
import pytz

_logger = logging.getLogger(__name__)

class TtCronLogInhResv(models.Model):
    _inherit = 'tt.cron.log'

    def cron_sync_booking(self):
        book_objs = self.env['tt.reservation.airline'].search([('is_hold_date_sync', '=', 'False'),
                                                               ('create_date','>=',datetime.now() - timedelta(1))])
        for rec in book_objs:
            req = {
                'order_number': rec.name,
                'user_id': rec.booked_uid.id
            }
            self.env['tt.airline.api.con'].send_get_booking_for_sync(req)