from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta
import base64

import json

_logger = logging.getLogger(__name__)


class ReservationPpob(models.Model):
    _name = "tt.reservation.ppob"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation PPOB"

    product_code = fields.Integer('Product Code', readonly=True)
    session_id = fields.Char('Session ID', readonly=True)
    customer_number = fields.Char('Customer Number', readonly=True)

    # segment_ids = fields.One2many('tt.bill.ppob', 'booking_id', string='Segments', readonly=True, states={'draft': [('readonly', False)]})
