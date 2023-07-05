from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VisaAssignProductsWizard(models.TransientModel):
    _name = "visa.assign.products.wizard"
    _description = 'Visa Assign Products Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    ho_ids = fields.Many2many('tt.agent', 'tt_visa_assign_prod_ho_agent_rel', 'visa_assign_prod_id', 'ho_id',
                              string='Head Office(s)', domain=[('is_ho_agent', '=', True)])
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)

    def assign_to_selected_ho(self):
        if not self.ho_id:
            raise UserError('Please select Head Office!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 365')
        all_visa = self.env['tt.reservation.visa.pricelist'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in all_visa:
            if self.ho_id.id not in rec.ho_ids.ids:
                rec.write({
                    'ho_ids': [(4, self.ho_id.id)]
                })
                _logger.info('Assigning Visa %s to HO %s' % (rec.name, self.ho_id.name))

    def assign_to_multiple_hos(self):
        if not self.ho_ids:
            raise UserError('Please select Head Office(s)!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 366')
        all_visa = self.env['tt.reservation.visa.pricelist'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in all_visa:
            for rec2 in self.ho_ids:
                if rec2.id not in rec.ho_ids.ids:
                    rec.write({
                        'ho_ids': [(4, rec2.id)]
                    })
                    _logger.info('Assigning Visa %s to HO %s' % (rec.name, rec2.name))

    def delete_from_multiple_hos(self):
        if not self.ho_ids:
            raise UserError('Please select Head Office(s)!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 367')
        all_visa = self.env['tt.reservation.visa.pricelist'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in all_visa:
            for rec2 in self.ho_ids:
                if rec2.id in rec.ho_ids.ids:
                    rec.write({
                        'ho_ids': [(3, rec2.id)]
                    })
                    _logger.info('Removing Visa %s from HO %s' % (rec.name, rec2.name))
