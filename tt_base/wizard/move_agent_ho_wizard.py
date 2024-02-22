from odoo import api, fields, models, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class MoveAgentHOWizard(models.TransientModel):
    _name = "move.agent.ho.wizard"
    _description = 'Move Agent HO Wizard'

    agent_ids = fields.Many2many('tt.agent', 'move_agent_ho_agent_rel', 'move_agent_ho_id', 'agent_id', string='Agents')
    new_ho_id = fields.Many2one('tt.agent', 'New Head Office', domain=[('is_ho_agent', '=', True)], required=True)

    def get_agent_type_domain(self):
        return [('ho_id', '=', self.new_ho_id.id)]

    new_agent_type_id = fields.Many2one('tt.agent.type', 'New Agent Type', required=True, domain=get_agent_type_domain)

    @api.onchange('new_ho_id')
    def _onchange_domain_new_agent_type(self):
        self.new_agent_type_id = False
        return {'domain': {
            'new_agent_type_id': self.get_agent_type_domain()
        }}

    def submit_move_ho(self):
        for rec in self.agent_ids:
            old_ho_id = rec.ho_id.id
            old_ho_name = rec.ho_id.name
            if self.new_ho_id.id != old_ho_id:
                _logger.info('Moving %s from %s to %s...' % (rec.name, old_ho_name, self.new_ho_id.name))
                sql_query = """
                update tt_agent set parent_agent_id = %s where parent_agent_id = %s;
                """ % (rec.parent_agent_id.id, rec.id)
                self.env.cr.execute(sql_query)
                rec.write({
                    'ho_id': self.new_ho_id.id,
                    'parent_agent_id': self.new_ho_id.id,
                    'agent_type_id': self.new_agent_type_id.id
                })
                # model_list = self.env['ir.model'].search([('field_id.name', '=', 'ho_id'), ('field_id.name', 'in', ['agent_id', 'parent_agent_id'])])
                # for rec in model_list:
                #     _logger.info(rec.model)

                sql_query = """
                            update tt_customer_parent set ho_id = %s where parent_agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update tt_customer set ho_id = %s where (agent_id = %s or agent_as_staff_id = %s) and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update res_users set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update payment_acquirer set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update payment_acquirer_number set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update phone_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update address_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)

                sql_query = """
                            update social_media_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                            """ % (self.new_ho_id.id, rec.id, old_ho_id)
                self.env.cr.execute(sql_query)
