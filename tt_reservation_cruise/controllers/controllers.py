# -*- coding: utf-8 -*-
from odoo import http

# class Odoo12AddonsTourTravel/ttReservationCruise(http.Controller):
#     @http.route('/odoo12_addons_tour_travel/tt_reservation_cruise/odoo12_addons_tour_travel/tt_reservation_cruise/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo12_addons_tour_travel/tt_reservation_cruise/odoo12_addons_tour_travel/tt_reservation_cruise/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_reservation_cruise.listing', {
#             'root': '/odoo12_addons_tour_travel/tt_reservation_cruise/odoo12_addons_tour_travel/tt_reservation_cruise',
#             'objects': http.request.env['odoo12_addons_tour_travel/tt_reservation_cruise.odoo12_addons_tour_travel/tt_reservation_cruise'].search([]),
#         })

#     @http.route('/odoo12_addons_tour_travel/tt_reservation_cruise/odoo12_addons_tour_travel/tt_reservation_cruise/objects/<model("odoo12_addons_tour_travel/tt_reservation_cruise.odoo12_addons_tour_travel/tt_reservation_cruise"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo12_addons_tour_travel/tt_reservation_cruise.object', {
#             'object': obj
#         })