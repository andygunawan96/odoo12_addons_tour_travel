from odoo import api, fields, models, _
# import odoo.addons.decimal_precision as dp
from ...tools import variables
import json
from datetime import datetime


class TtBannerAirline(models.Model):
    _name = 'tt.banner.airline'
    _rec_name = 'name'
    _description = 'Banner Airline'

    name = fields.Char('Name')
    banner_color = fields.Char('Banner Color (Hex Code)', required=True)
    description = fields.Text('Description')
    text_color = fields.Char('Text Color (Hex Code)', required=True)
    journey_id = fields.Many2one('tt.journey.airline', 'Journey', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='journey_id.booking_id', store=True)
    minimum_days = fields.Integer('Minimum Days')

    def to_dict(self):
        res = {
            "name": self.name,
            "banner_color": self.banner_color,
            "description": self.description,
            "text_color": self.text_color,
            "minimun_days": self.minimum_days
        }

        return res