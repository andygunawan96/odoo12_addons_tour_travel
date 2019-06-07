# -*- coding: utf-8 -*-
from odoo import http

# class TtVisa(http.Controller):
#     @http.route('/tt_visa/tt_visa/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_visa/tt_visa/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_visa.listing', {
#             'root': '/tt_visa/tt_visa',
#             'objects': http.request.env['tt_visa.tt_visa'].search([]),
#         })

#     @http.route('/tt_visa/tt_visa/objects/<model("tt_visa.tt_visa"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_visa.object', {
#             'object': obj
#         })