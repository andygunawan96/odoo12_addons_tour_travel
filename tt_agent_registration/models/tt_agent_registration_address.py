from odoo import api, fields, models
from ...tt_base.models.address_detail import ADDRESS_TYPE


class AgentRegistrationAddress(models.Model):
    _name = 'tt.agent.registration.address'
    _description = 'Agent Registration Address'

    agent_registration_id = fields.Many2one('tt.agent.registration', string='Agent Registration ID')
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
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    agent_id = fields.Many2one('tt.agent', string='Agent')
    active = fields.Boolean('Active', default=True)

    @api.onchange('type')
    def compute_address_name(self):
        for rec in self:
            if rec.type != 'custom':
                rec.name = rec.type

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = vals_list['type']
        return super(AgentRegistrationAddress, self).create(vals_list)
