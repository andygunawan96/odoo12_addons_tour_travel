from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PPOBAssignVouchersWizard(models.TransientModel):
    _name = "ppob.assign.vouchers.wizard"
    _description = 'PPOB Assign Vouchers Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_ppob.tt_provider_type_ppob').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    ho_ids = fields.Many2many('tt.agent', 'tt_ppob_assign_voucher_ho_agent_rel', 'ppob_assign_voucher_id', 'ho_id',
                              string='Head Office(s)', domain=[('is_ho_agent', '=', True)])

    def assign_to_multiple_hos(self):
        if not self.ho_ids:
            raise UserError('Please select Head Office(s)!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 364')
        all_ppob_vouchers = self.env['tt.master.voucher.ppob'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in all_ppob_vouchers:
            for rec2 in self.ho_ids:
                if rec2.id not in rec.ho_ids.ids:
                    rec.write({
                        'ho_ids': [(4, rec2.id)]
                    })
                    _logger.info('Assigning PPOB Vouchers %s to HO %s' % (rec.name, rec2.name))

    def assign_to_all_hos(self):
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 365')
        all_ppob_vouchers = self.env['tt.master.voucher.ppob'].sudo().search([('provider_id', '=', self.provider_id.id)])
        all_hos = self.env['tt.agent'].search([('is_ho_agent', '=', True)])
        for rec in all_ppob_vouchers:
            for rec2 in all_hos:
                if rec2.id not in rec.ho_ids.ids:
                    rec.write({
                        'ho_ids': [(4, rec2.id)]
                    })
                    _logger.info('Assigning PPOB Vouchers %s to HO %s' % (rec.name, rec2.name))
