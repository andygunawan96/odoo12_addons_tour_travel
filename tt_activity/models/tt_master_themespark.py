from odoo import api, fields, models
from odoo.http import request


class MasterThemespark(models.Model):
    _name = 'tt.master.themespark'

    uuid = fields.Char('Uuid')
    name = fields.Char('Activity Name')
    currency_id = fields.Many2one('res.currency', 'Currency')
    basePrice = fields.Float('Base Price', digits=(16, 2))
    priceIncludes = fields.Html('Price Includes')
    priceExcludes = fields.Html('Price Excludes')

    description = fields.Html('Description')
    highlights = fields.Html('Highlights')
    additionalInfo = fields.Html('Additional Info')
    itinerary = fields.Html('Itinerary')
    warnings = fields.Html('Warnings')
    safety = fields.Html('Safety')

    minPax = fields.Integer('Adult Min')
    maxPax = fields.Integer('Adult Max')
    reviewCount = fields.Integer('Review Count')
    reviewAverageScore = fields.Float('Review Average Score', digits=(10, 2))
    businessHoursFrom = fields.Char(string='Business Hours From')
    businessHoursTo = fields.Char(string='Business Hours To')
    hotelPickup = fields.Boolean('Hotel Pickup')
    airportPickup = fields.Boolean('Airport Pickup')