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
    code = fields.Char('code', readonly=True)
    html = fields.Html('Footer HTML')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', 'Agent', default=lambda self: self.env.user.agent_id)  # , default=lambda self: self.env.user.agent_id
    active = fields.Boolean('Active', default=True)

    def set_color_printout_api(self,data,context):
        try:
            ## printout o3
            if context.get('co_ho_seq_id'):
                agent_id = self.env['tt.agent'].search([('seq_id','=', context.get('co_ho_seq_id'))], limit=1)
                if agent_id:
                    agent_id.website_default_color = data['color'] if data['color'][0] == '#' else "#%s" % data['color']
                    res = ERR.get_no_error()
                else:
                    res = ERR.get_error(500)
            else:
                res = ERR.get_error(500)
            ## printout o2
            # self.env['ir.config_parameter'].set_param('tt_base.website_default_color', data['color'])
            # res = ERR.get_no_error()
        except Exception as e:
            res = ERR.get_error(500, additional_message="can't change data color")
            _logger.error(traceback.format_exc())
        return res

    def set_report_footer_api(self, data, context):
        try:
            report_obj = self.search([('code','=',data['code']),('agent_id','=',context['co_agent_id'])], limit=1)
            ho_id = None
            if context.get('co_ho_seq_id'):
                agent_ho_obj = self.env['tt.agent'].search([('seq_id','=',context['co_ho_seq_id'])], limit=1)
                if agent_ho_obj:
                    ho_id = agent_ho_obj.id
            if report_obj:
                report_obj.html = data['html']
            else:
                self.create({
                    'code': data['code'],
                    'name': data['name'],
                    'agent_id': context['co_agent_id'],
                    'html': data['html'],
                    'ho_id': ho_id
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
        data_agent_report_common_obj = self.search([('agent_id','=', context['co_agent_id'])])
        agent_obj = self.env['tt.agent'].search([('id','=',context['co_agent_id'])], limit=1)
        res = []
        if agent_obj:
            agent_ho_obj = agent_obj.ho_id
            data_ho_admin_report_common_obj = self.search([('agent_id','=', self.env.ref('tt_base.rodex_ho').id)])
            data_ho_report_common_ho_obj = self.search([('agent_id','=', agent_ho_obj.id)])
            for rec in data_ho_admin_report_common_obj:
                print = 0
                if agent_ho_obj.id == context['co_agent_id']:
                    print = 1
                elif rec['code'] not in exclude:
                    print = 1
                printout_check = 1
                if print:
                    for printout_agent in data_agent_report_common_obj: ## default agent
                        if rec['code'] == printout_agent['code']:
                            res.append({
                                'code': rec.code,
                                'name': rec.name,
                                'html': printout_agent.html or ''
                            })
                            printout_check = 0
                            break
                    if printout_check: ## default HO
                        for printout_ho in data_ho_report_common_ho_obj:
                            if rec['code'] == printout_ho['code']:
                                res.append({
                                    'code': rec.code,
                                    'name': rec.name,
                                    'html': printout_ho.html or ''
                                })
                    if printout_check: ## default kosong
                        res.append({
                            'code': rec.code,
                            'name': rec.name,
                            'html': ''
                        })
        return res

    def get_footer(self, code, agent_id):
        if agent_id != False:
            html = self.sudo().search([('code', '=', code), ('agent_id','=', agent_id.id)], limit=1)
            if html:
                return html
            else:
                ho_agent_obj = agent_id.ho_id
                html = self.sudo().search([('code', '=', code), ('agent_id', '=', ho_agent_obj.id)], limit=1)
                if html:
                    return html
                else:
                    return []
        ## tidak ada agent kembalikan kosong karena tidak ada HO
        return []