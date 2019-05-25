# -*- coding: utf-8 -*-
from odoo import http

# class TtActivity(http.Controller):
#     @http.route('/tt_activity/tt_activity/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_activity/tt_activity/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_activity.listing', {
#             'root': '/tt_activity/tt_activity',
#             'objects': http.request.env['tt_activity.tt_activity'].search([]),
#         })

#     @http.route('/tt_activity/tt_activity/objects/<model("tt_activity.tt_activity"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_activity.object', {
#             'object': obj
#         })