from odoo import api, fields, models, _


class RoomType(models.Model):
    _name = 'tt.room.type'
    _description = 'Room Type (Superrior, Double, Twin, Loft etc)'

    name = fields.Char('Name')
    guest_count = fields.Integer('Person Capacity')

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_code_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)