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
            self.agent_id.write({
                'ho_id': self.new_ho_id.id
            })
