
from odoo import api,models,fields
import json

class TtSegmentAddonsAirline(models.Model):
    _name = 'tt.segment.addons.airline'
    _description = 'Segment Addons'

    detail_code = fields.Char('Detail Code')
    detail_type = fields.Char('Detail Type')
    detail_name = fields.Char('Detail Name')
    unit = fields.Char('Unit')
    amount = fields.Integer('Amount')
    sequence = fields.Integer('Sequence')
    segment_id = fields.Many2one('tt.segment.airline', 'Segment')
    description = fields.Text('Description')

    def to_dict(self):
        res = {
            'detail_code': self.detail_code,
            'detail_type': self.detail_type,
            'detail_name': self.detail_name,
            'amount': self.amount,
            'unit': self.unit,
            'description': self.description and json.dumps(self.description) or [],
            'sequence': self.sequence
        }
        return res
