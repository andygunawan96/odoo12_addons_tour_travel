# -*- coding: utf-8 -*-
from odoo import http

# class Odoo12AddonsTourTravel/ttAgentReportVisa(http.Controller):
#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_visa/odoo12_addons_tour_travel/tt_agent_report_visa/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_visa/odoo12_addons_tour_travel/tt_agent_report_visa/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_visa.listing', {
#             'root': '/odoo12_addons_tour_travel/tt_agent_report_visa/odoo12_addons_tour_travel/tt_agent_report_visa',
#             'objects': http.request.env['odoo12_addons_tour_travel/tt_agent_report_visa.odoo12_addons_tour_travel/tt_agent_report_visa'].search([]),
#         })

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_visa/odoo12_addons_tour_travel/tt_agent_report_visa/objects/<model("odoo12_addons_tour_travel/tt_agent_report_visa.odoo12_addons_tour_travel/tt_agent_report_visa"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_visa.object', {
#             'object': obj
#         })