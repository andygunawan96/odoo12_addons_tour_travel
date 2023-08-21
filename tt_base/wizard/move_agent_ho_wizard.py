from odoo import api, fields, models, _
from datetime import datetime


class MoveAgentHOWizard(models.TransientModel):
    _name = "move.agent.ho.wizard"
    _description = 'Move Agent HO Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', domain=[('is_ho_agent', '!=', True)], required=True)
    old_ho_id = fields.Many2one('tt.agent', 'Old Head Office', domain=[('is_ho_agent', '=', True)], related='agent_id.ho_id', readonly=True)
    new_ho_id = fields.Many2one('tt.agent', 'New Head Office', domain=[('is_ho_agent', '=', True)], required=True)

    def submit_move_ho(self):
        if self.new_ho_id.id != self.old_ho_id.id:
            child_agent_list = self.env['tt.agent'].search([('parent_agent_id', '=', self.agent_id.id)])
            for rec in child_agent_list:
                rec.write({
                    'parent_agent_id': self.agent_id.parent_agent_id.id
                })
            self.agent_id.write({
                'ho_id': self.new_ho_id.id,
                'parent_agent_id': self.new_ho_id.id
            })
            # model_list = self.env['ir.model'].search([('field_id.name', '=', 'ho_id'), ('field_id.name', 'in', ['agent_id', 'parent_agent_id'])])
            # for rec in model_list:
            #     _logger.info(rec.model)
            cus_par_list = self.env['tt.customer.parent'].search([('parent_agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in cus_par_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            customer_list = self.env['tt.customer'].search([('ho_id', '=', self.old_ho_id.id), '|', ('agent_id', '=', self.agent_id.id), ('agent_as_staff_id', '=', self.agent_id.id)])
            for rec in customer_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            user_list = self.env['res.users'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in user_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            payment_acq_list = self.env['payment.acquirer'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in payment_acq_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            payment_acq_num_list = self.env['payment.acquirer.number'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in payment_acq_num_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            phone_list = self.env['phone.detail'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in phone_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            address_list = self.env['address.detail'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in address_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            socmed_list = self.env['social.media.detail'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in socmed_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
            third_party_list = self.env['tt.agent.third.party.key'].search([('agent_id', '=', self.agent_id.id), ('ho_id', '=', self.old_ho_id.id)])
            for rec in third_party_list:
                rec.write({
                    'ho_id': self.new_ho_id.id
                })
