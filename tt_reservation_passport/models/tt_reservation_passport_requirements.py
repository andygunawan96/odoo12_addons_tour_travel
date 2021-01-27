from odoo import api, fields, models, _


class PassportRequirement(models.Model):
    _name = 'tt.reservation.passport.requirements'
    _description = 'Reservation Passport Requirements'

    name = fields.Char('Name', related='type_id.name')
    type_id = fields.Many2one('tt.traveldoc.type', 'Document Type')
    reference_code = fields.Char('Reference Code', required=False)
    pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Pricelist ID', readonly=True)
    required = fields.Boolean('Required', default=False)
