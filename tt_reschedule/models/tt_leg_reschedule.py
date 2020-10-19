from odoo import api, fields, models, _
import json


class TtLegReschedule(models.Model):
    _name = 'tt.leg.reschedule'
    _inherit = 'tt.leg.airline'

    segment_id = fields.Many2one('tt.segment.reschedule', 'Segment', ondelete='cascade')
