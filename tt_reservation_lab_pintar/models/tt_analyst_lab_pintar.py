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


class TtAnalystLabPintar(models.Model):
    _name = 'tt.analyst.lab.pintar'
    _description = 'Rodex Model Analyst Lab Pintar'

    name = fields.Char('Analyst Name')
    analyst_id = fields.Char('Analyst ID')
    analyst_phone_number = fields.Char('Analyst Phone Number')
    booking_ids = fields.Many2many('tt.reservation.lab.pintar', 'tt_reservation_lab_pintar_analyst_rel', 'analyst_id',
                                   'booking_id', 'Booking(s)')
    active = fields.Boolean('Active',default=True)
