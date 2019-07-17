# -*- coding: utf-8 -*-
from odoo import http

# class TtPassport(http.Controller):
#     @http.route('/tt_reservation_passport/tt_reservation_passport/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_reservation_passport/tt_reservation_passport/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_reservation_passport.listing', {
#             'root': '/tt_reservation_passport/tt_reservation_passport',
#             'objects': http.request.env['tt_reservation_passport.tt_reservation_passport'].search([]),
#         })

#     @http.route('/tt_reservation_passport/tt_reservation_passport/objects/<model("tt_reservation_passport.tt_reservation_passport"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_reservation_passport.object', {
#             'object': obj
#         })