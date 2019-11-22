from odoo import api, fields, models, _
from ...tools.api import Response
import re

PASSPORT_TYPE = [
    ('passport', 'Passport'),
    ('e-passport', 'E-Passport')
]

APPLY_TYPE = [
    ('new', 'New'),
    ('renew', 'Renew'),
    ('umroh', 'Umroh'),
    ('add_name', 'Add Name')
]

PROCESS_TYPE = [
    ('regular', 'Regular'),
    ('kilat', 'Express'),
    ('super', 'Super Express')
]


class PassportPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.passport.pricelist'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    passport_type = fields.Selection(PASSPORT_TYPE, 'Passport Type')
    apply_type = fields.Selection(APPLY_TYPE, 'Apply Type')
    process_type = fields.Selection(PROCESS_TYPE, 'Process Type')

    country_id = fields.Many2one('res.country', 'Country')
    immigration_consulate = fields.Char('Immigration Consulate')
    notes = fields.Html('Notes')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    nta_price = fields.Monetary('NTA Price', default=0)
    cost_price = fields.Monetary('Cost Price', default=0)
    sale_price = fields.Monetary('Sale Price', default=0)
    commission_price = fields.Monetary('Commission Price', store=True, readonly=1, compute="_compute_commission_price")

    requirement_ids = fields.One2many('tt.reservation.passport.requirements', 'pricelist_id', 'Requirements')

    duration = fields.Integer('Duration (day(s))', help="in day(s)", required=True, default=1)
    commercial_duration = fields.Char('Duration', compute='_compute_duration', readonly=1)

    @api.multi
    @api.depends('cost_price', 'sale_price')
    @api.onchange('cost_price', 'sale_price')
    def _compute_commission_price(self):
        for rec in self:
            rec.commission_price = rec.sale_price - rec.cost_price

    @api.multi
    @api.onchange('duration')
    def _compute_duration(self):
        for rec in self:
            rec.commercial_duration = '%s day(s)' % str(rec.duration)
