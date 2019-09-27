# -*- coding: utf-8 -*-
from odoo import http

# class Odoo12AddonsTourTravel/ttAgentReport(http.Controller):
#     @http.route('/odoo12_addons_tour_travel/tt_agent_report/odoo12_addons_tour_travel/tt_agent_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report/odoo12_addons_tour_travel/tt_agent_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report.listing', {
#             'root': '/odoo12_addons_tour_travel/tt_agent_report/odoo12_addons_tour_travel/tt_agent_report',
#             'objects': http.request.env['odoo12_addons_tour_travel/tt_agent_report.odoo12_addons_tour_travel/tt_agent_report'].search([]),
#         })

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report/odoo12_addons_tour_travel/tt_agent_report/objects/<model("odoo12_addons_tour_travel/tt_agent_report.odoo12_addons_tour_travel/tt_agent_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report.object', {
#             'object': obj
#         })