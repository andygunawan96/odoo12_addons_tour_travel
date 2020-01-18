from odoo import api, fields, models, _

TYPE = [
    ('work', 'Work'),
    ('home', 'Home'),
    ('other', 'Other')
]


class PhoneDetail(models.Model):
    _name = 'phone.detail'
    _description = 'Tour & Travel - Phone Detail'

    type = fields.Selection(TYPE, 'Phone Type', required=True, default='work')
    country_id = fields.Many2one('res.country', string='Country')
    calling_code = fields.Char('Calling Code', required=True)
    calling_number = fields.Char('Calling Number', required=True)
    phone_number = fields.Char('Phone Number', readonly=True, compute='_compute_phone_number')
    agent_id = fields.Many2one('tt.agent', string='Agent')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'type': self.type,
            'calling_code': self.calling_code,
            'calling_number': self.calling_number,
        }

    @api.depends('calling_code', 'calling_number')
    @api.onchange('calling_code', 'calling_number')
    def _compute_phone_number(self):
        for rec in self:
            rec.phone_number = (rec.calling_code and rec.calling_code or '') + (rec.calling_number and rec.calling_number or '')
