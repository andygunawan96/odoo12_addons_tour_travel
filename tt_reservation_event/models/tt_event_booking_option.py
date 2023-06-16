from odoo import api, fields, models
from odoo.http import request
from ...tools import session
import logging
import json

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class MasterBookingOption(models.Model):
    _name = 'tt.event.booking.option'
    _description = 'Orbis Even Booking Model'

    uuid = fields.Char('Uuid')
    name = fields.Char('Name')
    description = fields.Html('Description')
    required = fields.Boolean('Required')
    formatRegex = fields.Char('Format Regex')
    inputType = fields.Integer('Input Type')
    items = fields.One2many('tt.event.booking.option.line', 'booking_option_id', 'Booking Option Items')
    type = fields.Selection([('perBooking', 'Per Booking'), ('perPax', 'Per Pax')])
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency', 'Currency')

class BookingOptionLine(models.Model):
    _name = 'tt.event.booking.option.line'
    _description = 'Orbis Event Model'

    booking_option_id = fields.Many2one('tt.event.booking.option', 'Booking Option', ondelete="cascade")
    label = fields.Char('label')
    value = fields.Char("Value")
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency', 'Currency')