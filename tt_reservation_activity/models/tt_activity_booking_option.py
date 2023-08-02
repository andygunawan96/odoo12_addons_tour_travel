from odoo import api, fields, models
from odoo.http import request
import logging
import json
_logger = logging.getLogger(__name__)

from ...tools import session
SESSION_NT = session.Session()


class MasterBookingOption(models.Model):
    _name = 'tt.activity.booking.option'
    _description = 'Activity Booking Option'

    uuid = fields.Char('Uuid')
    name = fields.Char('Name')
    description = fields.Html('Description')
    required = fields.Boolean('Required')
    formatRegex = fields.Char('Format Regex')
    inputType = fields.Integer('Input Type')
    minNumber = fields.Integer('Min Number', default=0)
    maxNumber = fields.Integer('Max Number', default=0)
    validFrom = fields.Char('Valid From')
    validTo = fields.Char('Valid To')
    items = fields.One2many('tt.activity.booking.option.line', 'booking_option_id', 'Booking Option Items')
    type = fields.Selection([('perBooking', 'Per Booking'), ('perPax', 'Per Pax')])
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency', 'Currency')


class BookingOptionLine(models.Model):
    _name = 'tt.activity.booking.option.line'
    _description = 'Activity Booking Option Line'

    booking_option_id = fields.Many2one('tt.activity.booking.option', 'Booking Option', ondelete="cascade")
    label = fields.Char('Label')
    value = fields.Char('Value')
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency', 'Currency')


class MasterTimeslot(models.Model):
    _name = 'tt.activity.master.timeslot'
    _description = 'Activity Master Timeslot'

    product_type_id = fields.Many2one('tt.master.activity.lines', 'Product Type', ondelete="cascade")
    uuid = fields.Char('Uuid')
    startTime = fields.Char('Start Time')
    endTime = fields.Char('End Time')
    active = fields.Boolean('Active', default=True)


class MasterLocations(models.Model):
    _name = 'tt.activity.master.locations'
    _description = 'Activity Master Location'

    city_id = fields.Many2one('res.city', 'City')
    city_name = fields.Char('City Name', related='city_id.name', store=True)
    state_id = fields.Many2one('res.country.state', 'State')
    state_name = fields.Char('State Name', related='state_id.name', store=True)
    country_id = fields.Many2one('res.country', 'Country')
    country_name = fields.Char('Country Name', related='country_id.name', store=True)


class MasterImages(models.Model):
    _name = 'tt.activity.master.images'
    _description = 'Activity Master Images'

    activity_id = fields.Many2one('tt.master.activity', 'Activity ID', ondelete="cascade")
    photos_url = fields.Char('Main Url')
    photos_path = fields.Char('Images Path')
    # type = fields.Selection([('thumbnail', 'Thumbnail'), ('fullSize', 'Full Size')])


class MasterVideos(models.Model):
    _name = 'tt.activity.master.videos'
    _description = 'Activity Master Videos'

    activity_id = fields.Many2one('tt.master.activity', 'Activity ID', ondelete="cascade")
    video_url = fields.Char('Video Url')

