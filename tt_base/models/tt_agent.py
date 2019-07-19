from odoo import models, fields, api
from PIL import Image
from odoo.tools import image
import logging, traceback
from ...tools.api import Response


_logger = logging.getLogger(__name__)


class TtAgent(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.agent'
    _rec_name = 'name'
    _description = 'Tour & Travel - Agent'

    name = fields.Char('Name', required=True, default='')
    logo = fields.Binary('Agent Logo', attachment=True)
    logo_thumb = fields.Binary('Agent Logo Thumb', compute="_get_logo_image", store=True, attachment=True)

    reference = fields.Many2one('tt.agent', 'Reference', help="Agent who Refers This Agent")
    balance = fields.Monetary(string="Balance",  required=False, )
    actual_balance = fields.Monetary(string="Actual Balance",  required=False, )
    annual_revenue_target = fields.Monetary(string="Annual Revenue Target", required=False, )
    annual_profit_target = fields.Monetary(string="Annual Profit Target", required=False, )
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
    customer_parent_ids = fields.One2many('tt.customer.parent', 'parent_agent_id', 'Customer Parent')
    customer_parent_walkin_id = fields.Many2one('tt.customer.parent','Walk In Parent')
    customer_ids = fields.One2many('tt.customer', 'agent_id', 'Customer')
    # ledger_id = fields.One2many('tt.ledger', 'agent_id', 'Ledger', required=False, )  # tt_ledger
    ledger_id = fields.Char('Ledger', required=False, )  # tt_ledger
    parent_agent_id = fields.Many2one('tt.agent', string="Parent Agent", Help="Agent who became Parent of This Agent")
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type')
    history_ids = fields.Char(string="History", required=False, )  # tt_history
    user_ids = fields.One2many('res.users', 'agent_id', 'User')
    payment_acquirer_ids = fields.Char(string="Payment Acquirer", required=False, )  # payment_acquirer
    agent_bank_detail_ids = fields.One2many('agent.bank.detail', 'agent_id', 'Agent Bank')  # agent_bank_detail
    tac = fields.Text('Terms and Conditions', readonly=True, states={'draft': [('readonly', False)],
                                                                     'confirm': [('readonly', False)]})
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

    @api.model
    def create(self, vals_list):
        new_agent = super(TtAgent, self).create(vals_list)
        agent_name = str(new_agent.name)
        walkin_obj = self.env['tt.customer.parent'].create(
            {
                'parent_agent_id': new_agent.id,
                'customer_parent_type_id': self.env.ref('tt_base.agent_type_fpo').id,
                'name': agent_name + ' FPO'
            }
        )
        new_agent.write({
            'customer_parent_walkin_id': walkin_obj.id
        })
        return new_agent

    def get_balance(self, agent_id):
        agent_obj = self.env['tt.agent'].browse([agent_id])
        if not agent_obj:
            return 'Agent/Sub Agent not Found'
        return agent_obj.balance

    def get_data(self):
        res = {
            'id': self.id,
            'name': self.name,
            'agent_type_id': self.agent_type_id and self.agent_type_id.get_data() or {},
        }
        return res

    def get_agent_level_api(self, agent_id):
        try:
            _obj = self.sudo().browse(int(agent_id))
            response = []

            level = 0
            temp_agent_ids = []
            temp = _obj
            while True:
                values = temp.get_data()
                values.update({'agent_level': level})
                response.append(values)
                temp_agent_ids.append(temp.id)
                if not temp.parent_agent_id or temp.parent_agent_id.id in temp_agent_ids:
                    break
                temp = temp.parent_agent_id
                level += 1
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error('%s, %s' % (str(e), traceback.format_exc()))
            res = Response().get_error(str(e), 500)
        return res
