from odoo import api, fields, models

ADDRESS_TYPE = [
    ('work', 'Work'),
    ('home', 'Home'),
    ('custom', 'Custom')
]


class AddressDetail(models.Model):
    _name = 'address.detail'
    _order = 'sequence'
    _description = 'Tour & Travel - Address Detail'

    type = fields.Selection(ADDRESS_TYPE, 'Address Type', required=True)                         
    name = fields.Char('Type Name', store=True, readonly=False)
    sequence = fields.Integer('Sequence')
    address = fields.Char('Address', required=True)
    rt = fields.Char('RT')
    rw = fields.Char('RW')
    zip = fields.Char('Zip')
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='Country State')
    city_id = fields.Many2one('res.city', string='City')
    district_id = fields.Many2one('res.district', string='District')
    sub_district_id = fields.Many2one('res.sub.district', string='Sub District')
    customer_id = fields.Many2one('tt.customer', string='Customer')
    customer_parent_id = fields.Many2one('tt.customer.parent', string='Customer Parent')
    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain)
    agent_id = fields.Many2one('tt.agent', string='Agent')
    provider_id = fields.Many2one('tt.provider', string='Provider')
    active = fields.Boolean('Active', default=True)

    # @api.onchange('agent_id')
    # def _onchange_agent_id(self):
    #     self.agent_id = self.env.user.agent_id.id

    @api.onchange('type')
    def compute_address_name(self):
        for rec in self:
            if rec.type != 'custom':
                rec.name = rec.type
    
    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = vals_list['type']
        return super(AddressDetail, self).create(vals_list)
