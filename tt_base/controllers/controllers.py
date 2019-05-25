# -*- coding: utf-8 -*-
from odoo import http

# class TtBase(http.Controller):
#     @http.route('/tt_base/tt_base/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_base/tt_base/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_base.listing', {
#             'root': '/tt_base/tt_base',
#             'objects': http.request.env['tt_base.tt_base'].search([]),
#         })

#     @http.route('/tt_base/tt_base/objects/<model("tt_base.tt_base"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_base.object', {
#             'object': obj
#         })