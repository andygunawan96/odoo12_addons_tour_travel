# -*- coding: utf-8 -*-
from odoo import http

# class TtAgentRegistration(http.Controller):
#     @http.route('/tt_agent_registration/tt_agent_registration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_agent_registration/tt_agent_registration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_agent_registration.listing', {
#             'root': '/tt_agent_registration/tt_agent_registration',
#             'objects': http.request.env['tt_agent_registration.tt_agent_registration'].search([]),
#         })

#     @http.route('/tt_agent_registration/tt_agent_registration/objects/<model("tt_agent_registration.tt_agent_registration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_agent_registration.object', {
#             'object': obj
#         })