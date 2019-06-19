from odoo import api, fields, models, _
from PIL import Image
from odoo.tools import image


class TtCompany(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.company'

    name = fields.Char('Name', required=True)
    logo = fields.Binary('Company Logo', attachment=True)
    logo_thumb = fields.Binary('Company Logo Thumb', compute="_get_logo_image", store=True, attachment=True)

    est_date = fields.Date('Established Date')
    email = fields.Char('Email')
    address_ids = fields.One2many('address.detail', 'company_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'company_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'company_id', string='Phones')
    agent_id = fields.Many2one('tt.agent', string='Agent')
    employee_ids = fields.One2many('res.employee', 'company_id', string='Employees')
    currency_id = fields.Many2one('res.currency', string='Currency')
    credit_limit = fields.Monetary('Credit Limit', required=True)
    # create_uid = fields.Many2one('res.users', 'Created by', readonly=True)
    # create_date = fields.Datetime('Create Date', readonly=True)
    # write_uid = fields.Many2one('res.users', 'Write by', readonly=True)
    # write_date = fields.Datetime('Write Date', readonly=True)
    company_bank_detail_ids = fields.One2many('company.bank.detail', 'company_id', string='Company Bank')
    active = fields.Boolean('Active', default=True)

    @api.depends('logo')
    def _get_logo_image(self):
        for record in self:
            if record.logo:
                record.logo_thumb = image.crop_image(record.logo, type='center', ratio=(4, 3), size=(200, 200))
            else:
                record.logo_thumb = False
