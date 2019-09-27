# -*- coding: utf-8 -*-
from odoo import http

# class Odoo12AddonsTourTravel/ttAgentReportOffline(http.Controller):
#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_offline/odoo12_addons_tour_travel/tt_agent_report_offline/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_offline/odoo12_addons_tour_travel/tt_agent_report_offline/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_offline.listing', {
#             'root': '/odoo12_addons_tour_travel/tt_agent_report_offline/odoo12_addons_tour_travel/tt_agent_report_offline',
#             'objects': http.request.env['odoo12_addons_tour_travel/tt_agent_report_offline.odoo12_addons_tour_travel/tt_agent_report_offline'].search([]),
#         })

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_offline/odoo12_addons_tour_travel/tt_agent_report_offline/objects/<model("odoo12_addons_tour_travel/tt_agent_report_offline.odoo12_addons_tour_travel/tt_agent_report_offline"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_offline.object', {
#             'object': obj
#         })