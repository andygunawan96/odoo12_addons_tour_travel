from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAgentRegisApiCon(models.Model):
    _name = 'tt.agent.registration.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.agent.registration'

    def action_call(self, table_obj, action, data, context):
        if action == 'get_config_api':
            res = table_obj.get_config_api(context)
        elif action == 'get_all_registration_documents_api':
            res = table_obj.get_all_registration_documents_api(context)
        elif action == 'create_agent_registration_api':
            res = table_obj.create_agent_registration_api(data, context)
        elif action == 'get_promotions_api':
            res = table_obj.get_promotions_api(context)
        else:
            raise RequestException(999)

        return res