from odoo import api, fields, models, _


class ReservationCruise(models.Model):
    _name = 'tt.reservation.cruise'
    _inherit = 'tt.reservation'
    _order = 'name desc'
    _description = 'Rodex Model'

    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type',
                                       default=lambda self: self.env['tt.provider.type'].search(
                                           [('code', '=', 'cruse')],
                                           limit=1))

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_cruise_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
