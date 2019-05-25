# -*- coding: utf-8 -*-
from odoo import http

# class TtReservation(http.Controller):
#     @http.route('/tt_reservation/tt_reservation/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_reservation/tt_reservation/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_reservation.listing', {
#             'root': '/tt_reservation/tt_reservation',
#             'objects': http.request.env['tt_reservation.tt_reservation'].search([]),
#         })

#     @http.route('/tt_reservation/tt_reservation/objects/<model("tt_reservation.tt_reservation"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_reservation.object', {
#             'object': obj
#         })