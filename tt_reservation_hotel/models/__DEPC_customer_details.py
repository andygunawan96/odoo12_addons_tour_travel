from odoo import api, fields, models, _
from datetime import datetime, timedelta


class CustomerDetails(models.Model):
    _inherit = 'tt.customer.details'

    hotel_reservation_id = fields.Many2one('tt.reservation.hotel', 'Hotel Book ID')

    booking_hotel_count = fields.Integer('Booking Count', compute='_booking_hotel_count', readonly=True)

    @api.model
    def create(self, values):
        hotel_id = values.get('hotel_reservation_id')
        if hotel_id:
            hotel_book_id = self.env['tt.reservation.hotel'].search([('id', '=', hotel_id)])
            agent_id = hotel_book_id.agent_id.id
            values['agent_id'] = agent_id
        return super(CustomerDetails, self).create(values)

    @api.multi
    def _booking_hotel_count(self):
        date_start, date_end = self.env['res.partner'].get_one_month(datetime.now())
        type = 'count(*)'
        for customer in self:
            count = self.count_booking_hotel(type, date_start, date_end, customer.id)
            customer.booking_hotel_count = count and count[0][0] or 0

    def count_booking_hotel(self, type, date_start, date_end, passager_id):
        sql = """SELECT %s
            FROM tt_hotel_reservation tb JOIN tt_customer_details cd ON cd.hotel_reservation_id = tb.id
            WHERE cd.id=%s AND date>='  %s' AND date<='%s'""" % (type, passager_id, date_start, date_end)
        self.env.cr.execute(sql)
        hasil = self.env.cr.fetchall()
        return hasil

    def open_hotel_reservation_history(self):
        action = self.env.ref('tt_hotel.tt_hotel_reservation_action')
        result = action.read()[0]
        type = 'tb.id'
        date_start, date_end = self.env['res.partner'].get_one_month(datetime.now())
        count = self.count_booking_hotel(type, date_start, date_end, self.id)
        result['domain'] = [('id', 'in', [count[0]])]
        return result