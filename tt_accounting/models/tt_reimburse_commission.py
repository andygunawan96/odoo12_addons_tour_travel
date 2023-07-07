from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging,traceback
from ...tools import variables

_logger = logging.getLogger(__name__)


class ReimburseCommissionTier(models.Model):
    _name = 'tt.reimburse.commission.tier'

    lower_limit = fields.Float('Lower Limit', default=0)
    rac_amount = fields.Float('Commission Multiplier', default=0.0)
    denominator = fields.Integer('Denominator', default=100)
    rac_preview = fields.Char('Commission Preview', readonly=True, compute='_onchange_rac_denominator')
    active = fields.Boolean('Active', default=True)

    @api.onchange('rac_amount', 'denominator')
    @api.depends('rac_amount', 'denominator')
    def _onchange_rac_denominator(self):
        self.rac_preview = str(self.rac_amount / (self.denominator / 100)) + '%'


class TtReimburseCommission(models.Model):
    _name = 'tt.reimburse.commission'
    _inherit = 'tt.history'
    _order = 'id DESC'
    _description = 'Reimburse Commission Data'

    name = fields.Char('Name', compute='_compute_name_reimburse')
    res_model = fields.Char('Reservation Provider Name', index=True)
    res_id = fields.Integer('Reservation Provider ID', index=True, help='ID of the followed resource')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', compute='compute_agent_id', store=True)
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', readonly=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True)
    reservation_ref = fields.Char('Reservation Ref')
    provider_pnr = fields.Char('PNR Ref')
    provider_issued_date = fields.Datetime('Provider Issued Date')
    rac_mode = fields.Selection([('fare', 'Fare'), ('tax', 'Tax'), ('fare_tax', 'Fare + Tax')], 'Commission Mode', default='fare_tax')
    base_price = fields.Monetary('Reservation Base Price', default=0)
    rac_amount = fields.Float('Commission Multiplier', default=0.0)
    denominator = fields.Integer('Denominator', default=100)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    rac_amount_num = fields.Monetary('Commission Amount (Exact Number)', default=0)
    tier_rac_mode = fields.Selection([('fare', 'Fare'), ('tax', 'Tax'), ('fare_tax', 'Fare + Tax')],
                                     'Tier Commission Mode', default='fare')
    commission_tier_ids = fields.Many2many('tt.reimburse.commission.tier', 'reimburse_data_tier_rel',
                                           'reimburse_commission_id', 'commission_tier_id', 'Commission Tier')
    service_charge_ids = fields.One2many('tt.reimburse.commission.service.charge', 'reimburse_id', string='Service Charges', readonly=1)
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('cancel', 'Cancelled')], 'State', default='draft')
    approved_date = fields.Datetime('Approved Date', readonly=1)
    approved_uid = fields.Many2one('res.users', 'Approved By', readonly=1)
    cancel_date = fields.Datetime('Cancelled Date', readonly=1)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=1)

    @api.onchange('provider_type_id', 'provider_id', 'provider_pnr')
    @api.depends('provider_type_id', 'provider_id', 'provider_pnr')
    def _compute_name_reimburse(self):
        for rec in self:
            final_name = ''
            if rec.provider_type_id:
                final_name += rec.provider_type_id.name + ' - '
            if rec.provider_id:
                final_name += rec.provider_id.name + ' - '
            if rec.provider_pnr:
                final_name += rec.provider_pnr
            rec.name = final_name

    @api.onchange('res_model', 'res_id')
    @api.depends('res_model', 'res_id')
    def compute_agent_id(self):
        for rec in self:
            obj = self.env[rec.res_model].browse(rec.res_id)
            if obj:
                if obj.booking_id:
                    rec.agent_id = obj.booking_id.agent_id and obj.booking_id.agent_id.id or False
                else:
                    rec.agent_id = False
            else:
                rec.agent_id = False

    def action_approve(self):
        if not self.env.user.has_group('tt_base.group_pricing_agent_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 19')
        if self.state == 'draft':
            commission_list = [rec.to_dict() for rec in self.service_charge_ids]
            provider_obj = self.env[self.res_model].browse(self.res_id)
            if provider_obj:
                provider_obj.create_service_charge(commission_list)
                self.approved_date = fields.Datetime.now()
                self.approved_uid = self.env.user.id
                self.state = 'approved'
            else:
                raise UserError(_('Provider Object not found.'))

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_pricing_agent_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 20')
        if self.state == 'draft':
            self.cancel_date = fields.Datetime.now()
            self.cancel_uid = self.env.user.id
            self.state = 'cancel'

    def action_set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_pricing_agent_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 21')
        if self.state == 'cancel':
            self.state = 'draft'

    def multi_action_approve(self):
        for rec in self:
            rec.action_approve()

    def multi_action_cancel(self):
        for rec in self:
            rec.action_cancel()

    def multi_action_set_to_draft(self):
        for rec in self:
            rec.action_set_to_draft()

    def open_reference(self):
        form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
        form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class TtReimburseCommissionServiceCharge(models.Model):
    _name = 'tt.reimburse.commission.service.charge'
    _description = 'Reimburse Commission Service Charge'

    reimburse_id = fields.Many2one('tt.reimburse.commission', 'Reimburse Data')
    charge_code = fields.Char('Charge Code', default='fare', required=True)
    charge_type = fields.Char('Charge Type')  # FARE, INF, TAX, SSR, CHR
    pax_type = fields.Selection(variables.PAX_TYPE, string='Pax Type')
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pax_count = fields.Integer('Pax Count', default=1)
    amount = fields.Monetary('Amount', currency_field='currency_id')
    total = fields.Monetary('Total', currency_field='currency_id')
    foreign_currency_id = fields.Many2one('res.currency', 'Foreign Currency',
                                          default=lambda self: self.env.user.company_id.currency_id)
    foreign_amount = fields.Monetary('Foreign Amount', currency_field='foreign_currency_id')

    sequence = fields.Integer('Sequence')
    description = fields.Text('Description')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])
    commission_agent_id = fields.Many2one('tt.agent', 'Agent ( Commission )', help='''Agent who get commission''')

    def to_dict(self):
        res = {
            'charge_code': self.charge_code,
            'charge_type': self.charge_type,
            'currency': self.currency_id.name,
            'amount': self.amount,
            'foreign_currency': self.foreign_currency_id.name,
            'foreign_amount': self.foreign_amount,
            'pax_count': self.pax_count,
            'pax_type': self.pax_type,
            'total': self.total,
        }
        if self.commission_agent_id:
            res.update({
                'commission_agent_id': self.commission_agent_id.id
            })
        return res
