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