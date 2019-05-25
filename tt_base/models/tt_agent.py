from odoo import models, fields, api
from PIL import Image
from odoo.tools import image


class TtAgent(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Agent'

    name = fields.Char('Name', required=True, default='')
    logo = fields.Binary('Agent Logo', attachment=True)
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True)

    reference = fields.Many2one('tt.agent', 'Reference')
    balance = fields.Monetary(string="Balance",  required=False, )
    actual_balance = fields.Monetary(string="Actual Balance",  required=False, )
    annual_revenue_target = fields.Monetary(string="Annual Revenue Target",  required=False, )
    annual_profit_target = fields.Monetary(string="Annual Profit Target",  required=False, )
    credit_limit = fields.Monetary(string="Credit Limit",  required=False, )
    npwp = fields.Char(string="NPWP", required=False, )
    est_date = fields.Datetime(string="Est. Date", required=False, )
    mou_start = fields.Datetime(string="Mou. Start", required=False, )
    mou_end = fields.Datetime(string="Mou. End", required=False, )
    website = fields.Char(string="Website", required=False, )
    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency', string='Currency')
    va_mandiri = fields.Char(string="VA Mandiri", required=False, )
    va_bca = fields.Char(string="VA BCA", required=False, )
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    # reservation_id = fields.Char(string="Reservation Detail", required=False, )
    ledger_id = fields.Char(string="Ledger ID", required=False, )  # tt_ledger
    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent")
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type ID')
    history_ids = fields.Char(string="History", required=False, )  # tt_history
    company_ids = fields.One2many('tt.company', 'agent_id', string='Company')
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    active = fields.Boolean('Active', default='True')

    @api.depends('logo')
    def _get_logo_image(self):
        for record in self:
            if record.logo:
                record.logo_thumb = image.crop_image(record.logo, type='center', ratio=(4, 3), size=(200, 200))
            else:
                record.logo_thumb = False

    # @api.multi
    # def write(self, value):
    #     self_dict = self.read()
    #     key_list = [key for key in value.keys()]
    #     for key in key_list:
    #         print(self.fields_get().get(key)['string'])
    #         self.message_post(body=_("%s has been changed from %s to %s by %s.") %
    #                                (self.fields_get().get(key)['string'],  # Model String / Label
    #                                 self_dict[0].get(key),  # Old Value
    #                                 value[key],  # New Value
    #                                 self.env.user.name))  # User that Changed the Value
    #     return super(TtAgent, self).write(value)
