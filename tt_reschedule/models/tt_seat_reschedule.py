from odoo import api, fields, models, _


class TtSeatReschedule(models.Model):
    _name = 'tt.seat.reschedule'
    _inherit = 'tt.seat.airline'

    segment_id = fields.Many2one('tt.segment.reschedule', 'Segment')
