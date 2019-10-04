from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtAirlineApiCon(models.Model):
    _name = 'tt.upload.center.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.upload.center'

    def action_call(self, table_obj, action, data, context):

        if action == 'upload_file':
            res = table_obj.upload_file_api(data, context)
        else:
            raise RequestException(999)

        return res