from odoo import api,models,fields
from ...tools.ERR import RequestException

class TtFrontendBannerApiCon(models.Model):
    _name = 'tt.frontend.banner.api.con'
    _inherit = 'tt.api.con'

    table_name = 'tt.frontend.banner'

    def action_call(self, table_obj, action, data, context):

        if action == 'add_banner':
            res = table_obj.add_banner_api(data, context)
        elif action == 'update_banner':
            res = table_obj.set_inactive_delete_banner_api(data, context)
        elif action == 'get_banner':
            res = table_obj.get_banner_api(data, context)
        else:
            raise RequestException(999)
        return res