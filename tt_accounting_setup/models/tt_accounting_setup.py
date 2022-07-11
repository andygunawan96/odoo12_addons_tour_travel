from odoo import models, fields, api, _
import logging, traceback,pytz
from ...tools import ERR,variables,util
from odoo.exceptions import UserError
from datetime import datetime,timedelta
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)


class TtAccountingSetup(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.accounting.setup'
    _description = 'Tour & Travel - Accounting Setup'

    accounting_provider = fields.Selection(variables.ACCOUNTING_VENDOR, 'Accounting Provider', required=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    cycle = fields.Selection([('real_time', 'Real Time'), ('per_batch', 'Per Batch')], 'Send Cycle', default='real_time', required=True)
    is_recon_only = fields.Boolean('Only Send Reconciled Records', default=False)
    sequence = fields.Integer('Sequence', default=20)
    active = fields.Boolean('Active', default='True')
    is_send_topup = fields.Boolean('Send Top Up Transaction', default=False)
    is_send_refund = fields.Boolean('Send Refund Transaction', default=False)
    variable_ids = fields.One2many('tt.accounting.setup.variables', 'accounting_setup_id', 'Variables')

    @api.depends('accounting_provider')
    @api.onchange('accounting_provider')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = dict(self._fields['accounting_provider'].selection).get(self.accounting_provider)

    def copy_setup(self):
        new_setup_obj = self.copy()

        for rec in self.variable_ids:
            self.env['tt.accounting.setup.variables'].create({
                'accounting_setup_id': new_setup_obj.id,
                'variable_name': rec.variable_name or '',
                'variable_value': rec.variable_value or ''
            })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_num = self.env.ref('tt_accounting_setup.tt_accounting_setup_action_view').id
        menu_num = self.env.ref('tt_accounting_setup.menu_administration_accounting_setup').id
        return {
            'type': 'ir.actions.act_url',
            'name': new_setup_obj.display_name,
            'target': 'self',
            'url': base_url + "/web#id=" + str(new_setup_obj.id) + "&action=" + str(
                action_num) + "&model=tt.master.tour&view_type=form&menu_id=" + str(menu_num),
        }


class TtAccountingSetupVariables(models.Model):
    _name = 'tt.accounting.setup.variables'
    _description = 'Tour & Travel - Accounting Setup Variables'

    accounting_setup_id = fields.Many2one('tt.accounting.setup', 'Accounting Setup')
    variable_name = fields.Char('Variable Name')
    variable_value = fields.Char('Variable Value')
