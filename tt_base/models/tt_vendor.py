from odoo import models, fields, api, _
import logging, traceback,pytz
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
from datetime import datetime
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)

class TtVendor(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.vendor'
    _rec_name = 'name'
    _description = 'Tour & Travel - Vendor'

    name = fields.Char('Name', required=True, default='')
    logo = fields.Binary('Vendor Logo')  # , attachment=True

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    npwp = fields.Char(string="NPWP", required=False, )
    est_date = fields.Datetime(string="Est. Date", required=False, )
    join_date = fields.Datetime(string="Join Date")
    website = fields.Char(string="Website", required=False, )
    email = fields.Char(string="Email", required=False, )
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    address_ids = fields.One2many('address.detail', 'agent_id', string='Addresses')
    phone_ids = fields.One2many('phone.detail', 'agent_id', string='Phones')
    social_media_ids = fields.One2many('social.media.detail', 'agent_id', 'Social Media')
    history_ids = fields.Char(string="History", required=False, )  # tt_history
    user_ids = fields.One2many('res.users', 'vendor_id', 'Users')
    payment_acquirer_ids = fields.One2many('payment.acquirer','agent_id',string="Payment Acquirer")  # payment_acquirer
    provider_id = fields.Many2one('tt.provider', string='Provider')
    active = fields.Boolean('Active', default='True')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)

    description = fields.Char('Description', default='')
