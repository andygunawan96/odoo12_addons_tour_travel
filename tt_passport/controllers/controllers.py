# -*- coding: utf-8 -*-
from odoo import http

# class TtPassport(http.Controller):
#     @http.route('/tt_passport/tt_passport/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_passport/tt_passport/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_passport.listing', {
#             'root': '/tt_passport/tt_passport',
#             'objects': http.request.env['tt_passport.tt_passport'].search([]),
#         })

#     @http.route('/tt_passport/tt_passport/objects/<model("tt_passport.tt_passport"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_passport.object', {
#             'object': obj
#         })