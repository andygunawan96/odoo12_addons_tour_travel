from odoo import api, models, fields


class ServiceChargeVisa(models.Model):
    _inherit = "tt.service.charge"

    visa_id = fields.Many2one('tt.visa', 'Visa', ondelete='cascade', index=True, copy=False)
