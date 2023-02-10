from odoo import api, fields, models, _


class MealTypeCategory(models.Model):
    _name = 'tt.meal.category'
    _description = 'Room Only or with breakfast'

    name = fields.Char('Name', required=True)

    def get_params_render_cache(self):
        return []

    def render_cache(self):
        params = self.get_params_render_cache()
        return [{
            'id': rec.id,
            'name': rec.name,
        } for rec in self.search(params)]


class MealType(models.Model):
    _name = 'tt.meal.type'
    _description = 'Meal type(Room Only, Bed and Breakfast, America Breakfast)'

    name = fields.Char('Name', required=True)
    category_id = fields.Many2one('tt.meal.category', 'Category')

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_code_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_params_render_cache(self):
        return []

    def render_cache(self):
        ### Hasil Return:
        ### {'A2':{
        ###     'ABF': ('American Breakfast', 'meal'),
        ###     'NYB': ('New Year Brunch', 'meal'),
        ###     'ROP': ('Room Only (Promo)', 'room only'),
        ###     'EXP': ('string dari meal type tsb', 'category name'),
        ### }}
        result = {}
        params = self.get_params_render_cache()
        for meal_type_obj in self.search(params):
            for provider_code_obj in meal_type_obj.provider_code_ids:
                if not result.get(provider_code_obj.provider_id.code):
                    result[provider_code_obj.provider_id.code] = {}
                if not result.get('rodextrip_hotel'):
                    result['rodextrip_hotel'] = {}
                result[provider_code_obj.provider_id.code][provider_code_obj.code] = [meal_type_obj.name, meal_type_obj.category_id.name]
                result['rodextrip_hotel'][provider_code_obj.code] = [meal_type_obj.name, meal_type_obj.category_id.name]
        return result