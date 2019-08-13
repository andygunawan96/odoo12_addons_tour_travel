# -*- coding: utf-8 -*-
from odoo import http

# class TtReservationGroupBooking(http.Controller):
#     @http.route('/tt_reservation_group_booking/tt_reservation_group_booking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_reservation_group_booking/tt_reservation_group_booking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_reservation_group_booking.listing', {
#             'root': '/tt_reservation_group_booking/tt_reservation_group_booking',
#             'objects': http.request.env['tt_reservation_group_booking.tt_reservation_group_booking'].search([]),
#         })

#     @http.route('/tt_reservation_group_booking/tt_reservation_group_booking/objects/<model("tt_reservation_group_booking.tt_reservation_group_booking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_reservation_group_booking.object', {
#             'object': obj
#         })