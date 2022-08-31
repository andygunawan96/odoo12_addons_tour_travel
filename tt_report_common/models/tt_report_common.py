from odoo import api, fields, models, _
import logging, traceback
from ...tools import util,variables,ERR
_logger = logging.getLogger(__name__)

class TtReportCommonSetting(models.Model):
    _name = 'tt.report.common.setting'
    _description = 'Report Common Setting'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name')
    code = fields.Char('code')
    html = fields.Html('Footer HTML')
    agent_id = fields.Many2one('tt.agent', 'Agent', default=lambda self: self.env.user.agent_id)  # , default=lambda self: self.env.user.agent_id
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
            report_obj = self.search([('code','=',data['code']),('agent_id','=',context['co_agent_id'])], limit=1)
            if report_obj:
                report_obj.html = data['html']
            else:
                self.create({
                    'code': data['code'],
                    'name': data['name'],
                    'agent_id': context['co_agent_id'],
                    'html': data['html']
                })
            res = ERR.get_no_error(self.get_data_report_footer(context))
        except Exception as e:
            res = ERR.get_error(500)
            _logger.error(traceback.format_exc())
        return res

    def get_list_report_footer_api(self, data, context):
        try:
            res = ERR.get_no_error(self.get_data_report_footer(context))
        except Exception as e:
            res = ERR.get_error(500)
            _logger.error(traceback.format_exc())
        return res

    def get_data_report_footer(self, context):
        exclude = [
            'refund_to_agent',
            'letter_guarantee_po',
            'letter_guarantee',
            'visa_ticket_ho',
            'reschedule_ticket'
        ]
        data = self.search([('agent_id','=', context['co_agent_id'])])
        data_code = self.search([('agent_id','=', self.env.ref('tt_base.rodex_ho').id)])
        res = []
        for rec in data_code:
            print = 0
            if self.env.ref('tt_base.rodex_ho').id == context['co_agent_id']:
                print = 1
            elif rec['code'] not in exclude:
                print = 1
            printout_check = 1
            if print:
                for printout_agent in data:
                    if rec['code'] == printout_agent['code']:
                        res.append({
                            'code': rec.code,
                            'name': rec.name,
                            'html': printout_agent.html or ''
                        })
                        printout_check = 0
                        break
                if printout_check:
                    res.append({
                        'code': rec.code,
                        'name': rec.name,
                        'html': rec.html or ''
                    })
        return res

    def get_footer(self, code, agent_id):
        if agent_id != False:
            html = self.search([('code', '=', code), ('agent_id','=', agent_id.id)], limit=1)
            if html:
                return html
        return self.search([('code', '=', code), ('agent_id','=', self.env.ref('tt_base.rodex_ho').id)], limit=1)