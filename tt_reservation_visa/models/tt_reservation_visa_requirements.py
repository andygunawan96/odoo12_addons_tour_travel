from odoo import api, fields, models, _


class VisaRequirement(models.Model):
    _name = 'tt.reservation.visa.requirements'
    _description = 'Reservation Visa Requirements'

    name = fields.Char('Name', related='type_id.name')
    type_id = fields.Many2one('tt.traveldoc.type', 'Document Type')
    reference_code = fields.Char('Reference Code', required=False)
    pricelist_id = fields.Many2one('tt.reservation.visa.pricelist', 'Master Tour', readonly=False)
    required = fields.Boolean('Required', default=False)
