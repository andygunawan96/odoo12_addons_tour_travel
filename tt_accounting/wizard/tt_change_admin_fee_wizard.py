from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtChangeAdminFeeWizard(models.TransientModel):
    _name = "tt.change.admin.fee.wizard"
    _description = 'Change Admin Fee Wizard'

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',readonly=True)
    res_model = fields.Char('Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', domain=[('id', '=', -1)])

    @api.depends('agent_id', 'res_model', 'res_id')
    @api.onchange('agent_id', 'res_model', 'res_id')
    def _onchange_agent_id(self):
        res_obj = self.env[self.res_model].browse(self.res_id)
        return {'domain': {
            'admin_fee_id': res_obj.get_admin_fee_domain()
        }}

    def submit_change_admin_fee(self):
        if not ({self.env.ref('tt_base.group_after_sales_master_level_3').id, self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 28')
        try:
            target_obj = self.env[self.res_model].browse(int(self.res_id))
            target_obj.write({
                'admin_fee_id': self.admin_fee_id.id
            })
            _logger.info('Admin Fee Changed')
        except Exception as e:
            _logger.info('Warning: Error res_model di production')
            raise UserError('Failed to change admin fee!')
