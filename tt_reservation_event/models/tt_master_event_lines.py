from odoo import api, fields, models
from odoo.http import request
from ...tools import session
import logging
import json

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class MasterEventLines(models.Model):
    _name = "tt.master.event.lines"
    _description = 'Orbis Event Master Lines'

    event_id = fields.Many2one("tt.master.event", 'Event Name', ondelete="cascade")
    uuid = fields.Char('Uuid')
    name = fields.Char('Type name')
    description = fields.Html('Description')

    # durationDays = fields.Integer('Duration Days')
    # durationHours = fields.Integer('Duration Hours')
    # durationMinutes = fields.Integer('Duration Minutes')

    isNonRefundable = fields.Boolean(' is Non Refundable')

    minPax = fields.Integer('Min Passenger')
    maxPax = fields.Integer("Max Passenger")

    voucherUse = fields.Html("Voucher Use")
    voucherRedemptionAddress = fields.Html('Voucher Redemption Address')
    voucherRequiresPrinting = fields.Boolean("Voucher Requires Printing")
    cancellationPolicies = fields.Text("Cancellation Policies")

    voucher_validity_type = fields.Selection([('only_visit_date', 'Only Visit Date'), ('from_travel_date', 'From Travel Date'), ('after_issue_date', 'After Issue Date'), ('until_date', 'Until Date')])
    voucher_validity_days = fields.Integer("Voucher Validity Days")
    voucher_validity_date = fields.Datetime("Voucher Validity Date")

    meetingLocation = fields.Char("Meeting Location")
    meetingAddress = fields.Char("Meeting Address")
    meetingTime = fields.Char("Meeting Time")
    instantConfirmation = fields.Boolean("Instant Confirmation")

    option_ids = fields.Many2many("tt.event.booking.option", 'tt_event_booking_option_rel', 'event_line_id', "option_id")
    timeslot_ids = fields.One2many("tt.master.event.timeslot", 'even_line_id')

    advanceBookingDays = fields.Integer("Advance Booking Days", default=0)
    minimumSellingPrice = fields.Integer("Minimum Selling Price", default=0)
    sku_ids = fields.One2many("tt.master.event.sku", 'event_line_id', '')
    active = fields.Boolean('Active', default=True)

class MasterEventSKU(models.Model):
    _name = 'tt.master.event.sku'
    _rec_name = 'title'
    _description = 'Orbis Event SKU Model'

    sku_id = fields.Char('SKU ID')
    title = fields.Char('SKU Title')
    minPax = fields.Integer('Min Passengers')
    maxPax = fields.Integer('Max Passengers')
    minAge = fields.Integer('Min Passenger Age')
    maxAge = fields.Integer('Max Passenger Age')
    add_information = fields.Text('Additional Information')
    pax_type = fields.Char('Passenger Type')
    event_line_id = fields.Many2one('tt.master.event.lines', 'Event ID', ondelete="cascade")
    active = fields.Boolean('Active', default=True)

