from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
import json


class TtPromoCodeAirline(models.Model):
    _name = 'tt.promo.code.airline'
    _description = 'Rodex Model'

    promo_code = fields.Char('Promo Code')
    carrier_code = fields.Char('Carrier Code')
    provider_airline_booking_id = fields.Many2one('tt.provider.airline', 'Provider Booking ID')
    booking_airline_id = fields.Many2one('tt.reservation.airline', 'Booking')

    def to_dict(self):
        res = {
            'promo_code': self.promo_code,
            'carrier_code': self.carrier_code,
        }
        return res


class TtReservationAirlineInherit(models.Model):
    _inherit = 'tt.reservation.airline'
    _description = 'Rodex Model'

    promo_code_ids = fields.One2many('tt.promo.code.airline', 'booking_airline_id', 'Promo Codes')


class TtProviderAirlineInherit(models.Model):
    _inherit = 'tt.provider.airline'
    _description = 'Rodex Model'

    promo_code_ids = fields.One2many('tt.promo.code.airline', 'provider_airline_booking_id', 'Promo Codes')
