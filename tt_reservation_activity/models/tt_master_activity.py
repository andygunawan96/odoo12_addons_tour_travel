from odoo import api, fields, models
from odoo.http import request
from .ApiConnector_Activity import ApiConnectorActivity
import logging, traceback
import json
import base64
import pickle

_logger = logging.getLogger(__name__)

from ...tools import session
SESSION_NT = session.Session()


class ActivitySyncProducts(models.TransientModel):
    _name = "activity.sync.product.wizard"

    provider_name = fields.Char(string="Provider")
    add_parameter_int = fields.Integer('Additional Parameter (Int)')
    add_parameter_char = fields.Char('Additional Parameter (Char)')


class MasterActivity(models.Model):
    _name = 'tt.master.activity'

    uuid = fields.Char('Uuid')
    name = fields.Char('Activity Name')
    # type_id = fields.Many2one('tt.activity.category', 'Type')
    type_ids = fields.Many2many('tt.activity.category', 'tt_activity_type_rel', 'activity_id', 'type_id', string='Types')
    category_ids = fields.Many2many('tt.activity.category', 'tt_activity_category_rel', 'activity_id', 'category_id', string='Categories')
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

    latitude = fields.Float('Latitude', digits=(11, 7))
    longitude = fields.Float('Longitude', digits=(11, 7))
    location_ids = fields.Many2many('tt.activity.master.locations', 'tt_activity_location_rel', 'product_id', 'location_id', string='Location')

    minPax = fields.Integer('Adult Min')
    maxPax = fields.Integer('Adult Max')
    reviewCount = fields.Integer('Review Count')
    reviewAverageScore = fields.Float('Review Average Score', digits=(10, 2))
    businessHoursFrom = fields.Char(string='Business Hours From')
    businessHoursTo = fields.Char(string='Business Hours To')
    hotelPickup = fields.Boolean('Hotel Pickup')
    airportPickup = fields.Boolean('Airport Pickup')

    line_ids = fields.One2many('tt.master.activity.lines', 'activity_id', 'Product Types')
    image_ids = fields.One2many('tt.activity.master.images', 'activity_id', 'Images Path')
    provider = fields.Char(string='Provider')
    active = fields.Boolean('Active', default=True)



