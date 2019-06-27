# -*- coding: utf-8 -*-
from odoo import http

# class TtTour(http.Controller):
#     @http.route('/tt_reservation_tour/tt_tour/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tt_tour/tt_tour/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tt_tour.listing', {
#             'root': '/tt_tour/tt_tour',
#             'objects': http.request.env['tt_tour.tt_tour'].search([]),
#         })

#     @http.route('/tt_tour/tt_tour/objects/<model("tt_tour.tt_tour"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tt_tour.object', {
#             'object': obj
#         })