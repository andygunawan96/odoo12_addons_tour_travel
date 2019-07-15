from odoo import fields,api,models

class TtCustomerParent(models.Model):
    _inherit = 'tt.history'
    _name = 'tt.customer.parent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Customer Parent'

    name = fields.Char('Name', required=True,default="CusPar")
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True) #fixme later

    customer_parent_type_id = fields.Many2one('tt.customer.parent.type','Customer Parent Type', required=True)
    parent_agent_id = fields.Many2one('tt.agent', 'Parent')

    balance = fields.Monetary(string="Balance",  required=False, )
    actual_balance = fields.Monetary(string="Actual Balance",  required=False, )
    credit_limit = fields.Monetary(string="Credit Limit",  required=False, )

    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency',default=lambda self: self.env.user.company_id,string='Currency')
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    customer_ids = fields.Many2many('tt.customer', 'tt_customer_customer_parent_rel','customer_id','customer_parent_id', 'Customer')
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True)
    active = fields.Boolean('Active', default='True')


    #ledger history
    #booking History