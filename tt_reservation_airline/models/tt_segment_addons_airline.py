from odoo import api,models,fields
from ...tools import variables
import json
import logging,traceback

_logger = logging.getLogger(__name__)

class TtSegmentAddonsAirline(models.Model):
    _name = 'tt.segment.addons.airline'
    _description = 'Segment Addons'

    detail_code = fields.Char('Detail Code')
    detail_type = fields.Char('Detail Type')
    detail_name = fields.Char('Detail Name')
    pax_type_json = fields.Char('Pax Type', default=json.dumps(['ADT', 'CHD', 'YCD']))
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
            'pax_type_json': self.pax_type_json,
            'amount': self.amount,
            'unit': self.unit,
            'description': self.description and json.dumps(self.description) or [],
            'sequence': self.sequence
        }
        return res

    def get_pax_type(self):
        final_ret = []
        try:
            if self.pax_type_json:
                final_ret = json.loads(self.pax_type_json)
        except Exception as e:
            _logger.info('Error loads JSON')
            _logger.error(traceback.format_exc())
        return final_ret
