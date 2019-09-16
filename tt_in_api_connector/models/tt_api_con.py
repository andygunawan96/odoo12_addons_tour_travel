from odoo import api,fields,models
from ...tools import ERR
from ...tools.ERR import RequestException
import logging,traceback

_logger = logging.getLogger(__name__)

class TtApiCon(models.Model):
    _name = 'tt.api.con'

    table_name = ''

    def api_webservice(self,action,data,context):
        try:
            try:
                table_obj = self.env[self.table_name]
            except:
                raise RequestException(1000)

            res = self.action_call(table_obj,action,data,context)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            res = e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error()
        return res

    def action_call(self,table_obj,action,data,context):
        pass