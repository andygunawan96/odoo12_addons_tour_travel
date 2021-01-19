from odoo import api, fields, models, _
import logging, traceback
from ...tools import util,variables,ERR
_logger = logging.getLogger(__name__)

class TtReportCommonSetting(models.Model):
    _name = 'tt.report.common.setting'
    _description = 'Report Common Setting'
    _order = ''

    name = fields.Char('Name')
    code = fields.Char('code')
    html = fields.Html('Footer HTML')
    active = fields.Boolean('Active', default=True)

    def set_color_printout_api(self,data,context):
        try:
            self.env['ir.config_parameter'].set_param('tt_base.website_default_color', data['color'])
            res = ERR.get_no_error()
        except Exception as e:
            res = ERR.get_error(500, additional_message="can't change data color")
            _logger.error(traceback.format_exc())
        return res

    def set_report_footer_api(self, data, context):
        try:
            report_obj = self.search([('code','=',data['code'])], limit=1)
            report_obj.html = data['html']
            res = ERR.get_no_error(self.get_data_report_footer())
        except Exception as e:
            res = ERR.get_error(500)
            _logger.error(traceback.format_exc())
        return res

    def get_list_report_footer_api(self, data, context):
        try:
            res = ERR.get_no_error(self.get_data_report_footer())
        except Exception as e:
            res = ERR.get_error(500)
            _logger.error(traceback.format_exc())
        return res

    def get_data_report_footer(self):
        data = self.search([])
        res = []
        for rec in data:
            res.append({
                'code': rec.code,
                'name': rec.name,
                'html': rec.html or ''
            })
        return res