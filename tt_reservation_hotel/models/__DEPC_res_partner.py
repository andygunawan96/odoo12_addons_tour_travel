from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, date, timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    booking_hotel_count = fields.Integer('Hotel Booking Count', compute='_booking_hotel_count', readonly=True)
    reservation_history_ids = fields.One2many('tt.reservation.hotel', 'customer_id', 'Booking History')
    hotel_ids = fields.One2many('tt.hotel', 'hotel_management_id', 'Hotel(s)')
    hotel_count = fields.Integer('Hotel Owned', compute='_hotel_count')

    @api.multi
    def _hotel_count(self):
        for partner in self:
            partner.hotel_count = len(partner.hotel_ids._ids)

    @api.multi
    def _booking_hotel_count(self):
        # to get 1 month from transaction
        today = datetime.now()
        date_start, date_end = self.get_one_month(today)
        for partner in self:
            partner.booking_hotel_count = self.env['tt.reservation.hotel'].search_count([
                ('agent_id', '=', partner.id), ('date', '>=', str(date_start)), ('date', '<=', str(date_end))
            ])

    def open_hotel_booking_history(self):
        action = self.env.ref('tt_hotel.tt_hotel_reservation_action_issued')
        result = action.read()[0]
        result['domain'] = [('agent_id', '=', self.id)]
        result['context'] = {'search_default_sale_this_month': 1}
        return result

    @api.multi
    def action_open_hotel_owned(self):
        action = self.env.ref('tt_hotel.tt_hotel_view_action_rodex').read()[0]
        action['domain'] = [('id', 'in', self.hotel_ids.ids)]
        return action