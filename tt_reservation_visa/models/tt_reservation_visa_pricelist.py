from odoo import api, fields, models, _

PAX_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Children'),
    ('INF', 'Infant')
]

ENTRY_TYPE = [
    ('single', 'Single'),
    ('double', 'Double'),
    ('multiple', 'Multiple')
]

VISA_TYPE = [
    ('tourist', 'Tourist'),
    ('business', 'Business'),
    ('student', 'Student')
]

PROCESS_TYPE = [
    ('regular', 'Regular'),
    ('kilat', 'Express'),
    ('super', 'Super Express')
]


class VisaPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.visa.pricelist'

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type', default='ADT', required=True)
    entry_type = fields.Selection(ENTRY_TYPE, 'Entry Type')
    visa_type = fields.Selection(VISA_TYPE, 'Visa Type')
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

    requirement_ids = fields.One2many('tt.reservation.visa.requirements', 'pricelist_id', 'Requirements')

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
