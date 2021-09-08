import pytz

from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime,date, timedelta
import base64
import json


_logger = logging.getLogger(__name__)


class TtAnalystmedical(models.Model):
    _name = 'tt.analyst.medical'
    _description = 'Rodex Model Analyst medical'

    name = fields.Char('Analyst Name')
    analyst_id = fields.Char('Analyst ID')
    analyst_phone_number = fields.Char('Analyst Phone Number')
    booking_ids = fields.Many2many('tt.reservation.medical', 'tt_reservation_medical_analyst_rel', 'analyst_id',
                                   'booking_id', 'Booking(s)')
    active = fields.Boolean('Active',default=True)

    user_id = fields.Many2one('res.users','User')