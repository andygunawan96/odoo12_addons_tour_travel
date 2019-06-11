# -*- coding: utf-8 -*-
from odoo import http

# class TtAgentSalesOffline(http.Controller):
#     @http.route('/tt_agent_sales_offline/tt_agent_sales_offline/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_agent_sales_offline/tt_agent_sales_offline/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_agent_sales_offline.listing', {
#             'root': '/tt_agent_sales_offline/tt_agent_sales_offline',
#             'objects': http.request.env['tt_agent_sales_offline.tt_agent_sales_offline'].search([]),
#         })

#     @http.route('/tt_agent_sales_offline/tt_agent_sales_offline/objects/<model("tt_agent_sales_offline.tt_agent_sales_offline"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_agent_sales_offline.object', {
#             'object': obj
#         })