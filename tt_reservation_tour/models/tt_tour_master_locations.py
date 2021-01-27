from odoo import api, fields, models, _
from ...tools import variables


class MasterLocations(models.Model):
    _name = 'tt.tour.master.locations'
    _description = 'Tour Master Locations'

    city_id = fields.Many2one('res.city', 'City')
    city_name = fields.Char('City Name', related='city_id.name', store=True)
    state_id = fields.Many2one('res.country.state', 'State')
    state_name = fields.Char('State Name', related='state_id.name', store=True)
    country_id = fields.Many2one('res.country', 'Country', required=True)
    country_name = fields.Char('Country Name', related='country_id.name', store=True)
