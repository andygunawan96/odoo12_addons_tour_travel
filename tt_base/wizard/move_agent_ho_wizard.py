from odoo import api, fields, models, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class MoveAgentHOWizard(models.TransientModel):
    _name = "move.agent.ho.wizard"
    _description = 'Move Agent HO Wizard'

    agent_id = fields.Many2one('tt.agent', 'Agent', domain=[('is_ho_agent', '!=', True)], required=True)
    old_ho_id = fields.Many2one('tt.agent', 'Old Head Office', domain=[('is_ho_agent', '=', True)], related='agent_id.ho_id', readonly=True)
    new_ho_id = fields.Many2one('tt.agent', 'New Head Office', domain=[('is_ho_agent', '=', True)], required=True)

    def submit_move_ho(self):
        old_ho_id = self.agent_id.ho_id.id
        old_ho_name = self.agent_id.ho_id.name
        if self.new_ho_id.id != old_ho_id:
            _logger.info('Moving %s from %s to %s...' % (self.agent_id.name, old_ho_name, self.new_ho_id.name))
            sql_query = """
            update tt_agent set parent_agent_id = %s where parent_agent_id = %s;
            """ % (self.agent_id.parent_agent_id.id, self.agent_id.id)
            self.env.cr.execute(sql_query)
            self.agent_id.write({
                'ho_id': self.new_ho_id.id,
                'parent_agent_id': self.new_ho_id.id
            })
            # model_list = self.env['ir.model'].search([('field_id.name', '=', 'ho_id'), ('field_id.name', 'in', ['agent_id', 'parent_agent_id'])])
            # for rec in model_list:
            #     _logger.info(rec.model)

            sql_query = """
                        update tt_customer_parent set ho_id = %s where parent_agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update tt_customer set ho_id = %s where (agent_id = %s or agent_as_staff_id = %s) and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update res_users set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update payment_acquirer set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update payment_acquirer_number set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update phone_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update address_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update social_media_detail set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)

            sql_query = """
                        update tt_agent_third_party_key set ho_id = %s where agent_id = %s and ho_id = %s;
                        """ % (self.new_ho_id.id, self.agent_id.id, old_ho_id)
            self.env.cr.execute(sql_query)
