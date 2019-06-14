# -*- coding: utf-8 -*-
from odoo import http

# class TtAgentSalesPassport(http.Controller):
#     @http.route('/tt_agent_sales_passport/tt_agent_sales_passport/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_agent_sales_passport/tt_agent_sales_passport/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_agent_sales_passport.listing', {
#             'root': '/tt_agent_sales_passport/tt_agent_sales_passport',
#             'objects': http.request.env['tt_agent_sales_passport.tt_agent_sales_passport'].search([]),
#         })

#     @http.route('/tt_agent_sales_passport/tt_agent_sales_passport/objects/<model("tt_agent_sales_passport.tt_agent_sales_passport"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_agent_sales_passport.object', {
#             'object': obj
#         })