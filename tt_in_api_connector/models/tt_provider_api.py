from odoo import api,models,fields
import json
import logging
from ...tools.ERR import RequestException
_logger = logging.getLogger(__name__)

class TtProviderApiCon(models.Model):
    _name = 'tt.provider.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.provider'

    def action_call(self, table_obj, action, data, context):
        if action == 'create_provider_ledger':
            res = table_obj.create_provider_ledger_api(data, context)
        else:
            raise RequestException(999)

        return res