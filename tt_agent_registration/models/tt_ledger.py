from odoo import api, fields, models, _


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
