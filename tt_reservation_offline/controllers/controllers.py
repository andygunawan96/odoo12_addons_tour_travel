# -*- coding: utf-8 -*-
from odoo import http

# class TtReservationOffline(http.Controller):
#     @http.route('/tt_reservation_offline/tt_reservation_offline/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_reservation_offline/tt_reservation_offline/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_reservation_offline.listing', {
#             'root': '/tt_reservation_offline/tt_reservation_offline',
#             'objects': http.request.env['tt_reservation_offline.tt_reservation_offline'].search([]),
#         })

#     @http.route('/tt_reservation_offline/tt_reservation_offline/objects/<model("tt_reservation_offline.tt_reservation_offline"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_reservation_offline.object', {
#             'object': obj
#         })