# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class odoo12_addons_tour_travel/tt_reservation_cruise(models.Model):
#     _name = 'odoo12_addons_tour_travel/tt_reservation_cruise.odoo12_addons_tour_travel/tt_reservation_cruise'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100