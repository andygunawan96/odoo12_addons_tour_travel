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


class TtAnalystSwabExpress(models.Model):
    _name = 'tt.analyst.swabexpress'
    _description = 'Orbis Model Analyst Swab Express'

    name = fields.Char('Analyst Name')
    analyst_id = fields.Char('Analyst ID')
    analyst_phone_number = fields.Char('Analyst Phone Number')
    booking_ids = fields.Many2many('tt.reservation.swabexpress', 'tt_reservation_swabexpress_analyst_rel', 'analyst_id',
                                   'booking_id', 'Booking(s)')
    active = fields.Boolean('Active',default=True)
