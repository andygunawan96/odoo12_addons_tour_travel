from odoo import api, models, fields


class ServiceChargePassport(models.Model):
    _inherit = "tt.service.charge"

    passport_id = fields.Many2one('tt.reservation.passport', 'Passport', ondelete='cascade', index=True, copy=False)
