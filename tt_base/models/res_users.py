from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    # allowed_customer_ids = fields.Many2many('res.partner', 'Allowed Partners', compute='_compute_allowed_customer_ids')
    language = fields.Selection([('ID', 'Bahasa Indonesia'), ('US', 'English (United States)'),
                                 ('GB', 'English (United Kingdom)'), ('DE', 'Germany'), ('ES', 'Espanol'),
                                 ('CHN', 'Chinese')], 'Language')
    transaction_limit = fields.Monetary('Transaction Limit')
    currency_id = fields.Many2one('res.currency', 'Currency')
    customer_id = fields.Many2one('tt.customer', 'Customer')
    date_format = fields.Selection([('format1', 'Tuesday, 12 February 2019'),
                   ('format2', 'Tuesday, 12 February 19'),
                   ('format3', 'Tuesday, 12 Feb 2019'),
                   ('format4', 'Tuesday, 12 Feb 19'),
                   ('format5', 'Tuesday, 12-02-2019'),
                   ('format6', 'Tuesday, 12-02-19'),
                   ('format7', 'Tue, 12 February 2019'),
                   ('format8', 'Tue, 12 February 19'),
                   ('format9', 'Tue, 12 Feb 2019'),
                   ('format10', 'Tue, 12 Feb 19'),
                   ('format11', 'Tue, 12-02-2019'),
                   ('format12', 'Tue, 12-02-19')], 'Date Format')
    time_format = fields.Selection([('format1', '23:59:59'),
                   ('format2', '23:59'),
                   ('format3', '11:59:59 PM'),
                   ('format4', '11:59 PM')], 'Time Format')
    user_type = fields.Selection([('b2b', 'Business to Business (B2B)'),
                                  ('b2c', 'Business to Customer (B2C)')], 'User Type')
    device_type = fields.Selection([('web', 'Web'),
                   ('android', 'Mobile Android'),
                   ('ios', 'Mobile iOS')], 'Device Type')

    #Fungsi ini perlu di lengkapi/disempurnakan
    #Tujuan : kalau res_pertner.parent_agent_id berubah maka user.agent_id ikut berubah
    @api.onchange('partner_id.parent_agent_id')
    @api.depends('partner_id.parent_agent_id')
    def _onchange_partner_id(self):
        self.agent_id = self.parent_id.parent_agent_id

    # @api.multi
    # def _compute_allowed_customer_ids(self):
    #     for rec in self:
    #         rec.allowed_customer_ids = [rec.partner_id.id, rec.agent_id.id] \
    #                                    + rec.agent_id.sub_agent_ids.ids

    @api.model
    def create(self, vals):
        new_user = super(ResUsers, self).create(vals)
        new_user.partner_id.parent_id = new_user.agent_id.id
        new_user.partner_id.parent_agent_id = False
        return new_user
