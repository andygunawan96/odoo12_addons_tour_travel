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
    _order = 'sequence, id desc'

    name = fields.Char('Name')
    after_sales_type = fields.Selection([('after_sales', 'After Sales'), ('refund', 'Refund'), ('offline', 'Issued Offline')], 'Transaction Type', default='after_sales')
    refund_type_id = fields.Many2one('tt.refund.type', 'Refund Type', required=False)
    min_amount_ho = fields.Float('Minimum Amount (HO)', default=0)
    min_amount_agent = fields.Float('Minimum Amount (Agent)', default=0)
    agent_type_ids = fields.Many2many('tt.agent.type', 'master_admin_fee_agent_type_rel', 'admin_fee_id', 'agent_type_id', string='Agent Types')
    agent_type_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Type Access Type', default='all')
    agent_ids = fields.Many2many('tt.agent', 'master_admin_fee_agent_rel', 'admin_fee_id', 'agent_id', string='Agents')
    agent_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Agent Access Type', default='all')
    provider_type_ids = fields.Many2many('tt.provider.type', 'master_admin_fee_provider_type_rel', 'master_admin_fee_id', 'provider_type_id', string='Provider Types')
    provider_type_access_type = fields.Selection([("all", "ALL"),("allow", "Allowed"),("restrict", "Restricted")], 'Provider Type Access Type', default='all', required=True)
    admin_fee_line_ids = fields.One2many('tt.master.admin.fee.line', 'master_admin_fee_id', 'Admin Fee Line(s)')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    sequence = fields.Integer('Sequence', default=50)
    active = fields.Boolean('Active', default=True)

    def get_final_adm_fee_ho(self, total=0, pnr_multiplier=1, pax_multiplier=1, journey_multiplier=1):
        final_amt = 0
        for rec in self.admin_fee_line_ids:
            if rec.balance_for == 'ho':
                if rec.is_per_pnr and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pnr:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey:
                    if rec.type == 'amount':
                        final_amt += rec.amount * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier
                        final_amt += math.ceil(result)

                else:
                    if rec.type == 'amount':
                        final_amt += rec.amount
                    else:
                        result = (rec.amount / 100.0) * total
                        final_amt += math.ceil(result)

        if final_amt < self.min_amount_ho:
            final_amt = self.min_amount_ho

        return final_amt

    def get_final_adm_fee_agent(self, total=0, pnr_multiplier=1, pax_multiplier=1, journey_multiplier=1):
        final_amt = 0
        for rec in self.admin_fee_line_ids:
            if rec.balance_for == 'agent':
                if rec.is_per_pnr and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey and rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pnr:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pnr_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pnr_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_journey:
                    if rec.type == 'amount':
                        final_amt += rec.amount * journey_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * journey_multiplier
                        final_amt += math.ceil(result)

                elif rec.is_per_pax:
                    if rec.type == 'amount':
                        final_amt += rec.amount * pax_multiplier
                    else:
                        result = ((rec.amount / 100.0) * total) * pax_multiplier
                        final_amt += math.ceil(result)

                else:
                    if rec.type == 'amount':
                        final_amt += rec.amount
                    else:
                        result = (rec.amount / 100.0) * total
                        final_amt += math.ceil(result)

        if final_amt < self.min_amount_agent:
            final_amt = self.min_amount_agent

        return final_amt


class TtAgent(models.Model):
    _inherit = 'tt.agent'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_rel', 'agent_id', 'admin_fee_id', string='Admin Fee')


class TtAgentType(models.Model):
    _inherit = 'tt.agent.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_agent_type_rel', 'agent_type_id', 'admin_fee_id', string='Admin Fee')


class TtProviderType(models.Model):
    _inherit = 'tt.provider.type'

    admin_fee_ids = fields.Many2many('tt.master.admin.fee', 'master_admin_fee_provider_type_rel', 'provider_type_id', 'admin_fee_id', string='Admin Fee')


class TtMasterAdminFeeLine(models.Model):
    _name = "tt.master.admin.fee.line"
    _description = 'Master Admin Fee Line'
    _rec_name = 'amount'

    type = fields.Selection([('amount', 'Amount'), ('percentage', 'Percentage')], 'Type', default='amount')
    amount = fields.Integer('Amount', default=0)
    is_per_pnr = fields.Boolean('Is Per PNR', default=True)
    is_per_pax = fields.Boolean('Is Per Pax', default=True)
    is_per_journey = fields.Boolean('Is Per Journey', default=False)
    balance_for = fields.Selection([('ho', 'Head Office'), ('agent', 'Agent')], 'Balance For', default='ho')
    master_admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Master Admin Fee')

    @api.onchange("is_per_pnr")
    def _compute_per_pnr(self):
        if self.is_per_pnr:
            self.is_per_journey = False

    @api.onchange("is_per_journey")
    def _compute_per_journey(self):
        if self.is_per_journey:
            self.is_per_pnr = False
