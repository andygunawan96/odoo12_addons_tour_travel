from odoo import api, fields, models


class RouteJourney(models.Model):
    _name = 'tt.route.journey'
    _rec_name = 'Journey'
    _description = 'Journey'

    name = fields.Char('Question')
    sequence = fields.Integer('Sequence')
