from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from ...tools import variables
import json
from datetime import datetime


class TtSegmentReschedule(models.Model):
    _name = 'tt.segment.reschedule'
    _inherit = 'tt.segment.airline'

    pnr = fields.Char('PNR', readonly=False, related='')
    seat_ids = fields.One2many('tt.seat.reschedule', 'segment_id', 'Seat')
    segment_addons_ids = fields.One2many('tt.segment.addons.reschedule', 'segment_id', 'Addons')
