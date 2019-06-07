# -*- coding: utf-8 -*-
from odoo import http

# class TtAgentSalesVisa(http.Controller):
#     @http.route('/tt_agent_sales_visa/tt_agent_sales_visa/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_agent_sales_visa/tt_agent_sales_visa/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_agent_sales_visa.listing', {
#             'root': '/tt_agent_sales_visa/tt_agent_sales_visa',
#             'objects': http.request.env['tt_agent_sales_visa.tt_agent_sales_visa'].search([]),
#         })

#     @http.route('/tt_agent_sales_visa/tt_agent_sales_visa/objects/<model("tt_agent_sales_visa.tt_agent_sales_visa"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_agent_sales_visa.object', {
#             'object': obj
#         })