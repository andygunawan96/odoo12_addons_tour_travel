from odoo import api, fields, models
from odoo.http import request
from ...tools import session
import logging
import json

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class temporaryPayment(models.Model):
    _name = "tt.event.reservation.temporary.payment"
    _description = "Rodex Event Module"

    event_reservation_id = fields.Many2one('tt.event.reservation', 'Event Reservation')