from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
import math

_logger = logging.getLogger(__name__)


class TtMasterAdminFee(models.Model):
    _inherit = 'tt.history'
    _name = "tt.master.admin.fee"
    _description = 'Master Admin Fee'

    name = fields.Char('Name')
    after_sales_type = fields.Selection([('after_sales', 'After Sales'), ('refund', 'Refund')], 'After Sales Type', default='after_sales')
    min_amount = fields.Float('Minimum Amount', default=0)
    type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type (For Amount per PNR)', default='amount')
    amount = fields.Float('Amount per PNR', default=0)
    per_pax_type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type (For Amount per Passenger)', default='amount')
    per_pax_amount = fields.Float('Amount per Passenger', default=0)
    target = fields.Selection([("ho_to_agent", "HO To Agent"), ("agent_to_cust", "Agent To Customer")], 'Target', default='ho_to_agent')
    agent_type_ids = fields.Many2many('tt.agent.type', 'master_admin_fee_agent_type_rel', 'admin_fee_id', 'agent_type_id', string='Agent Types')
    agent_type_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Type Access Type', default='all')
    agent_ids = fields.Many2many('tt.agent', 'master_admin_fee_agent_rel', 'admin_fee_id', 'agent_id', string='Agents')
    agent_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Access Type', default='all')

    def get_final_adm_fee(self, total=0, pnr_multiplier=1, pax_multiplier=1):
        final_amt = 0
        if self.type == 'amount':
            final_amt += self.amount * pnr_multiplier
        else:
            result = ((self.amount / 100.0) * total) * pnr_multiplier
            final_amt += math.ceil(result)

        if self.per_pax_amount:
            if self.per_pax_type == 'amount':
                final_amt += self.per_pax_amount * pax_multiplier
            else:
                result = ((self.per_pax_amount / 100.0) * total) * pax_multiplier
                final_amt += math.ceil(result)

        if final_amt < self.min_amount:
            final_amt = self.min_amount

        return final_amt


class TtAgent(models.Model):
    _inherit = 'tt.agent'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_rel', 'agent_id', 'admin_fee_id', string='Admin Fee')


class TtAgentType(models.Model):
    _inherit = 'tt.agent.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_type_rel', 'agent_type_id', 'admin_fee_id', string='Admin Fee')
