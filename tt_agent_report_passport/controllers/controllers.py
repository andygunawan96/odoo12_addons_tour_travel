# -*- coding: utf-8 -*-
from odoo import http

# class Odoo12AddonsTourTravel/ttAgentReportPassport(http.Controller):
#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_passport/odoo12_addons_tour_travel/tt_agent_report_passport/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_passport/odoo12_addons_tour_travel/tt_agent_report_passport/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_passport.listing', {
#             'root': '/odoo12_addons_tour_travel/tt_agent_report_passport/odoo12_addons_tour_travel/tt_agent_report_passport',
#             'objects': http.request.env['odoo12_addons_tour_travel/tt_agent_report_passport.odoo12_addons_tour_travel/tt_agent_report_passport'].search([]),
#         })

#     @http.route('/odoo12_addons_tour_travel/tt_agent_report_passport/odoo12_addons_tour_travel/tt_agent_report_passport/objects/<model("odoo12_addons_tour_travel/tt_agent_report_passport.odoo12_addons_tour_travel/tt_agent_report_passport"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_agent_report_passport.object', {
#             'object': obj
#         })