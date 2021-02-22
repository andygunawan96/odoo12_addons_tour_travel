from odoo import api, fields, models, _
import logging, traceback

_logger = logging.getLogger(__name__)


class MasterTourPricing(models.Model):
    _name = "tt.master.tour.pricing"
    _description = 'Rodex Model'
    _rec_name = 'min_pax'
    _order = 'min_pax asc'

    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    min_pax = fields.Integer('Minimal Pax', default=1, required=True)
    is_infant_included = fields.Boolean('Include Infant in Pax Count', default=False)
    room_id = fields.Many2one('tt.master.tour.rooms', 'Room')
    adult_fare = fields.Monetary('Adult Fare', default=0)
    adult_commission = fields.Monetary('Adult Commission', default=0)
    child_fare = fields.Monetary('Child Fare', default=0)
    child_commission = fields.Monetary('Child Commission', default=0)
    infant_fare = fields.Monetary('Infant Fare', default=0)
    infant_commission = fields.Monetary('Infant Commission', default=0)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'min_pax': self.min_pax,
            'is_infant_included': self.is_infant_included,
            'currency_id': self.currency_id and self.currency_id.name or '',
            'adult_price': self.adult_fare + self.adult_commission,
            'child_price': self.child_fare + self.child_commission,
            'infant_price': self.infant_fare + self.infant_commission,
        }
