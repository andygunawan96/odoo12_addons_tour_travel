from odoo import api, fields, models, _
import json


class TtLegReschedule(models.Model):
    _name = 'tt.leg.reschedule'
    _inherit = 'tt.leg.airline'

    segment_id = fields.Many2one('tt.segment.reschedule', 'Segment', ondelete='cascade')


class TtSegmentRescheduleInherit(models.Model):
    _inherit = 'tt.segment.reschedule'

    leg_ids = fields.One2many('tt.leg.reschedule', 'segment_id', 'Legs')
