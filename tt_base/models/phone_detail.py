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
    phone_number = fields.Char('Phone Number', required=True)
    agent_id = fields.Many2one('tt.agent', string='Agent')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'type': self.type,
            'phone_number': self.phone_number
        }