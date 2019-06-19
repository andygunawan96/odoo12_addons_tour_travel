from odoo import api, fields, models, _

TYPE = [
    ('work', 'Work'),
    ('home', 'Home'),
    ('custom', 'Custom')
]


class PhoneDetail(models.Model):
    _name = 'phone.detail'
    _description = 'Tour & Travel - Phone Detail'

    type = fields.Selection(TYPE, 'Address Type', required=True)
    name = fields.Char('Type Name')
    country_id = fields.Many2one('res.country', string='Country')
    phone_number = fields.Char('Phone Number', required=True)
    agent_id = fields.Many2one('tt.agent', string='Agent')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    company_id = fields.Many2one('tt.company', string='Company')
    active = fields.Boolean('Active', default=True)

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'work':
            self.name = "Work"
        elif self.type == 'home':
            self.name = "Home"
        elif self.type == 'custom':
            self.name = ""
