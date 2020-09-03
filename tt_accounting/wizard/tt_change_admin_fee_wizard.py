from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtChangeAdminFeeWizard(models.TransientModel):
    _name = "tt.change.admin.fee.wizard"
    _description = 'Change Admin Fee Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', readonly=True)
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',readonly=True)
    res_model = fields.Char('Related Reservation Name', index=True, readonly=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', domain=[('id', '=', -1)])

    @api.depends('agent_id', 'res_model')
    @api.onchange('agent_id', 'res_model')
    def _onchange_agent_id(self):
        agent_type_adm_ids = self.agent_id.agent_type_id.admin_fee_ids.ids
        agent_adm_ids = self.agent_id.admin_fee_ids.ids

        if self.res_model == 'tt.reschedule.line':
            after_sales_type = 'after_sales'
            target = ['ho_to_agent', 'agent_to_cust']
        elif self.res_model == 'tt.refund.line.customer':
            after_sales_type = 'refund'
            target = ['agent_to_cust']
        else:
            after_sales_type = 'refund'
            target = ['ho_to_agent']

        return {'domain': {
            'admin_fee_id': [('after_sales_type', '=', after_sales_type), ('target', 'in', target), '&', '|',
                ('agent_type_access_type', '=', 'all'), '|', '&', ('agent_type_access_type', '=', 'allow'),
                ('id', 'in', agent_type_adm_ids), '&', ('agent_type_access_type', '=', 'restrict'),
                ('id', 'not in', agent_type_adm_ids), '|', ('agent_access_type', '=', 'all'), '|', '&',
                ('agent_access_type', '=', 'allow'), ('id', 'in', agent_adm_ids), '&',
                ('agent_access_type', '=', 'restrict'), ('id', 'not in', agent_adm_ids)]
        }}

    def submit_change_admin_fee(self):
        try:
            target_obj = self.env[self.res_model].browse(int(self.res_id))
            target_obj.write({
                'admin_fee_id': self.admin_fee_id.id
            })
            _logger.info('Admin Fee Changed')
        except Exception as e:
            _logger.info('Warning: Error res_model di production')
            raise UserError('Failed to change admin fee!')
