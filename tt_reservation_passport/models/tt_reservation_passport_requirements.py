from odoo import api, fields, models, _


class PassportRequirement(models.Model):
    _name = 'tt.reservation.passport.requirements'
    _description = 'Rodex Model'

    name = fields.Char('Name', related='type_id.name')
    type_id = fields.Many2one('tt.traveldoc.type', 'Document Type')
    pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Pricelist ID', readonly=True)
    required = fields.Boolean('Required', default=False)
