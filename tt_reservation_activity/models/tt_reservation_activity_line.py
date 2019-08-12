from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TransportBookActivityLine(models.Model):
    _name = 'tt.reservation.activity.line'

    reservation_activity_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')
    passenger_id = fields.Many2one('tt.customer', 'Passenger')
    pax_type = fields.Selection([('ADT', 'Adult'), ('CHD', 'Child'), ('INF', 'Infant')], string='Pax Type')
    pax_mobile = fields.Char('Mobile Number')
    api_data = fields.Text('API Data')
    # room_number = fields.Char('Room Number')
    # room_id = fields.Many2one('tt.activity.rooms', 'Room')
    # extra_bed_description = fields.Char('Extra Bed Description')
    # bed_type = fields.Selection([('double', 'Double/Twin'), ('triple', 'Triple')], 'Bed Type', related="room_id.bed_type")
    # description = fields.Char('Description')
    # pricelist_id = fields.Many2one('tt.activity.pricelist', 'activity Pricelist', related='reservation_activity_id.activity_id', store=True)
    # pricelist_id = fields.Many2one('tt.activity.pricelist', 'activity Pricelist', readonly=True)
    state = fields.Selection([], related='reservation_activity_id.state')


class TransportBookActivityPrice(models.Model):
    _name = 'tt.activity.booking.price'

    reservation_activity_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')
    charge_code = fields.Char('Charge Code')
    charge_type = fields.Char('Charge Type')  # FARE, INF, TAX, SSR, CHR
    pax_type = fields.Selection([('YCD', 'Senior'), ('ADT', 'Adult'), ('CHD', 'Child'), ('INF', 'Infant')], string='Pax Type')
    pax_count = fields.Integer('Pax Count')
    amount = fields.Monetary('Amount')
    total = fields.Monetary('Total', compute='_calc_total')
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    description = fields.Text('Description')
    foreign_currency = fields.Many2one('res.currency', required=True)
    foreign_amount = fields.Monetary('Foreign Amount')

    def _calc_total(self):
        for rec in self:
            rec.total = rec.amount


