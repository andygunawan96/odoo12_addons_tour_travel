# -*- coding: utf-8 -*-
from odoo import http

# class TtTraveldoc(http.Controller):
#     @http.route('/tt_traveldoc/tt_traveldoc/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_traveldoc/tt_traveldoc/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_traveldoc.listing', {
#             'root': '/tt_traveldoc/tt_traveldoc',
#             'objects': http.request.env['tt_traveldoc.tt_traveldoc'].search([]),
#         })

#     @http.route('/tt_traveldoc/tt_traveldoc/objects/<model("tt_traveldoc.tt_traveldoc"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_traveldoc.object', {
#             'object': obj
#         })