from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging, traceback


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.activity'
    _inherit = 'tt.reservation.passenger'
    _description = 'Rodex Model'

    reservation_activity_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')
    pax_type = fields.Selection([('ADT', 'Adult'), ('YCD', 'Senior'), ('CHD', 'Child'), ('INF', 'Infant')],
                                string='Pax Type')
    activity_sku_id = fields.Many2one('tt.master.activity.sku', 'Activity SKU')
    api_data = fields.Text('API Data')


class TransportBookActivityPrice(models.Model):
    _name = 'tt.activity.booking.price'
    _description = 'Rodex Model'

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


