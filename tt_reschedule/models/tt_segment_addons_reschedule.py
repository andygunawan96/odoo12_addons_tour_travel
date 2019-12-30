from odoo import api,models,fields
import json

class TtSegmentAddonsReschedule(models.Model):
    _name = 'tt.segment.addons.reschedule'
    _inherit = 'tt.segment.addons.airline'

    segment_id = fields.Many2one('tt.segment.reschedule', 'Segment')
