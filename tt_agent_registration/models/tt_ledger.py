from odoo import api, fields, models, _
from datetime import datetime


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')

    def prepare_vals_for_agent_regis(self, agent_regis_obj, vals):
        vals.update({
            'description': 'Ledger for ' + agent_regis_obj.name,
            'res_id': agent_regis_obj.id,
            'res_model': agent_regis_obj._name,
            'validate_uid': agent_regis_obj.sudo().issued_uid.id,
            'agent_id': agent_regis_obj.parent_agent_id.id,
            'agent_type_id': agent_regis_obj.parent_agent_id.agent_type_id.id
        })
        return vals

    def create_agent_comm_ledger(self):
        ledger = self.env['tt.ledger']

        agent_comm_vals = ledger.prepare_vals('Recruit Comm. : ' + self.name, 'Recruit Comm. : ' + self.name,
                                              datetime.now(), 3, self.currency_id.id, line.amount, 0)
        agent_comm_vals = ledger.prepare_vals_for_agent_regis(self, agent_comm_vals)
        agent_comm_vals.update({
            'agent_id': self.parent_agent_id.id
        })
        self.env['tt.ledger'].create(agent_comm_vals)
