from odoo import api, fields, models, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta


# class HotelServiceCharge(models.Model):
#     _inherit = 'tt.tb.service.charge'
#
#     resv_id = fields.Many2one('tt.reservation.hotel', 'Hotel Resv')


class HotelRoomDate(models.Model):
    _name = 'tt.room.date'
    _description = 'Detail Price Per Night Per room'

    detail_id = fields.Many2one('tt.hotel.reservation.details', 'Hotel Resv Details')
    date = fields.Datetime('Date')
    sale_price = fields.Monetary('Sale Price')
    commission_amount = fields.Monetary('Commission')
    meal_type = fields.Char('Meal Type')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)


class HotelReservationDetails(models.Model):
    _name = 'tt.hotel.reservation.details'
    _description = 'Contain 1 hotel and 1 room Packages if 1 hotel have 2 room package then will create 2 line'

    name = fields.Char('Resv. Number', help="Vendor Reservation number / Vendor Booking Code")
    issued_name = fields.Char('Issued Number', help="Vendor Issued number / Vendor Voucher Code")
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=lambda self: [("provider_type_id", "=", self.env.ref('tt_reservation_hotel.tt_provider_type_hotel').id )])
    prov_currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    prov_sale_price = fields.Monetary('Provider Price', currency_field='prov_currency_id')
    sale_price = fields.Monetary('Sale Price')
    qty = fields.Integer('Qty')
    commission_amount = fields.Monetary('Commission')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    special_request = fields.Text('Special request')
    room_info_id = fields.Many2one('tt.room.info', 'Room Info')
    room_rate_id = fields.Many2one('tt.room.rate', 'Room Rate')
    room_name = fields.Char('Room Name')
    room_vendor_code = fields.Char('Room Code')
    date = fields.Datetime('Date Start')
    date_end = fields.Datetime('Date End')
    room_type = fields.Char('Type')

    reservation_id = fields.Many2one('tt.reservation.hotel', 'Reservation No')
    payment_method = fields.Selection([('cash', 'Cash /  Saldo'), ('vou', 'Voucher')], string='Method', default='cash')
    voucher_id = fields.Many2one('product.product', 'Voucher')
    lot_id = fields.Many2one('stock.production.lot', 'Lot / Serial Number', domain="[('product_id','=',voucher_id)]")

    is_package = fields.Boolean('Is Package', default=False)
    room_date_ids = fields.One2many('tt.room.date', 'detail_id', 'Room per Date')
    supplementary_ids = fields.One2many('tt.hotel.reservation.supplementary', 'resv_detail_id', 'Service on Request',
                                        ondelete='cascade')

    meal_type = fields.Char('Meal Type')
    passenger_ids = fields.One2many('tt.reservation.passenger.hotel', 'room_id', string='Passengers')

    @api.onchange('room_rate_id')
    def set_domain_voucher(self):
        for line in self:
            domain = {'voucher_id': []}
            if line.room_rate_id:
                line.voucher_id = False
                domain = {'voucher_id': ['|', ('hotel_id', '=', line.room_info_id.hotel_id.id), ('room_ids', '=', line.room_info_id.id)]}
            return {'domain': domain}

    @api.depends('room_rate_id')
    def set_domain_voucher2(self):
        for a in self:
            a.set_domain_voucher()

    @api.multi
    def open_record(self):
        # first you need to get the id of your record
        # you didn't specify what you want to edit exactly
        rec_id = self.id
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref('tt_hotel.tt_hotel_reservation_detail_form')

        # then open the form
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation Details',
            'res_model': 'tt.hotel.reservation.details',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    @api.onchange('room_rate_id')
    def onchange_room_rate(self):
        res = {'domain': {'voucher_id': []}}
        if self.room_rate_id:
            res['domain']['voucher_id'] = self.room_rate_id.room_info_id.get_voucher_for_this_package()
            self.package_rate_id = False
        return res

    @api.onchange('room_info_id')
    def onchange_room_info(self):
        for my in self:
            if my.room_info_id:
                my.room_name = my.room_info_id.name

    @api.onchange('room_info_id', 'date')
    def onchange_get_room_rate(self):
        for my in self:
            if my.room_info_id and my.date:
                date = fields.Datetime.from_string(my.date)
                room_rate = my.room_info_id.get_price_by_date(1, date)[0]
                my.sale_price = room_rate['room_rate']
                my.commission_amount = room_rate['commision']


class HotelReservationSupplementary(models.Model):
    _name = 'tt.hotel.reservation.supplementary'
    _description = 'Supplementary cost'

    name = fields.Char('Name')
    reservation_id = fields.Many2one('tt.reservation.hotel', 'Reservation No')
    resv_detail_id = fields.Many2one('tt.hotel.reservation.details', 'Resv. Detail')
    req_date = fields.Datetime('Date', help='Request for date')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    qty = fields.Monetary('Qty')
    desc = fields.Text('Description')

    sale_price = fields.Monetary('Price')
    commission_amount = fields.Monetary('Commission')
    total_sale_price = fields.Monetary('Total Sale Price')
    currency_id = fields.Many2one('res.currency', 'Currency')

    @api.onchange('sale_price', 'qty')
    @api.depends('sale_price', 'qty')
    def calc_total_price(self):
        for rec in self:
            rec.total_sale_price = rec.sale_price * rec.qty


class HotelReservation(models.Model):
    _inherit = 'tt.reservation.hotel'

    room_detail_ids = fields.One2many('tt.hotel.reservation.details', 'reservation_id', 'Rooms'
                                      , readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, ondelete='cascade')
    supplementary_ids = fields.One2many('tt.hotel.reservation.supplementary', 'reservation_id', 'Supplement'
                                        , readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')

    @api.depends('supplementary_ids.qty', 'supplementary_ids.sale_price')
    def _get_total_supplement(self):
        for my in self:
            total = 0
            for suplement_id in my.supplementary_ids:
                total += suplement_id.qty * suplement_id.sale_price
            my.total_supplementary_price = total
