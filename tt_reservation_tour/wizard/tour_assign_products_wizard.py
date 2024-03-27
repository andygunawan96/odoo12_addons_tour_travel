from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TourAssignProductsWizard(models.TransientModel):
    _name = "tour.assign.products.wizard"
    _description = 'Tour Assign Products Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_tour.tt_provider_type_tour').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    ho_ids = fields.Many2many('tt.agent', 'tt_tour_assign_prod_ho_agent_rel', 'tour_assign_prod_id', 'ho_id',
                              string='Head Office(s)', domain=[('is_ho_agent', '=', True)])
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)

    def assign_to_selected_ho(self):
        if not self.ho_id:
            raise UserError('Please select Head Office!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError(
                'Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 362')

        all_tours = self.env['tt.master.tour'].search([('provider_id', '=', self.provider_id.id), ('ho_ids', '!=', self.ho_id.id)])
        for idx, rec in enumerate(all_tours):
            rec.write({
                'ho_ids': [(4, self.ho_id.id)]
            })
            _logger.info('Assigning Tour %s to HO %s' % (rec.name, self.ho_id.name))
            if (idx + 1) % 100 == 0:
                self.env.cr.commit()

    def assign_to_multiple_hos(self):
        if not self.ho_ids:
            raise UserError('Please select Head Office(s)!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 363')
        for rec in self.ho_ids:
            all_tours = self.env['tt.master.tour'].search([('provider_id', '=', self.provider_id.id),('ho_ids', '!=', rec.id)])
            for idx, rec2 in enumerate(all_tours):
                rec2.write({
                    'ho_ids': [(4, rec.id)]
                })
                _logger.info('Assigning Tour %s to HO %s' % (rec2.name, rec.name))
                if (idx + 1) % 100 == 0:
                    self.env.cr.commit()

    def delete_from_multiple_hos(self):
        if not self.ho_ids:
            raise UserError('Please select Head Office(s)!')
        if not self.env.user.has_group('base.group_erp_manager'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 364')
        for rec in self.ho_ids:
            all_tours = self.env['tt.master.tour'].search([('provider_id', '=', self.provider_id.id),('ho_ids', '=', rec.id)])
            for idx, rec2 in enumerate(all_tours):
                rec2.write({
                    'ho_ids': [(3, rec.id)]
                })
                _logger.info('Removing Tour %s from HO %s' % (rec2.name, rec.name))
                if (idx + 1) % 100 == 0:
                    self.env.cr.commit()
