from odoo import api, fields, models


class AddressDetail(models.Model):
    _name = 'address.detail'
    _order = 'sequence'
    _description = 'Tour & Travel - Address Detail'

    agent_id = fields.Many2one('tt.agent', string='Agent')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    company_id = fields.Many2one('tt.company', string='Company')
    type = fields.Selection([('work', 'Work'), ('home', 'Home'), ('custom', 'Custom')], 'Address Type', required=True)
    name = fields.Char('Type Name')
    sequence = fields.Integer('Sequence')
    address = fields.Char('Address', required=True)
    rt = fields.Char('RT')
    rw = fields.Char('RW')
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='Country State')
    city_id = fields.Many2one('res.city', string='City')
    district_id = fields.Many2one('res.district', string='District')
    sub_district_id = fields.Many2one('res.sub.district', string='Sub District')
    active = fields.Boolean('Active', default=True)

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'work':
            self.name = "Work"
        elif self.type == 'home':
            self.name = "Home"
        elif self.type == 'custom':
            self.name = ""
