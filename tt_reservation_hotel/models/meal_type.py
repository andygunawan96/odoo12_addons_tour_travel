from odoo import api, fields, models, _


class MealType(models.Model):
    _name = 'tt.meal.type'
    _description = 'Meal type(Room Only, Bed and Breakfast, America Breakfast)'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    # provider_id = fields.Integer('Provider')
    provider_id = fields.Many2one('res.partner', 'Provider')
