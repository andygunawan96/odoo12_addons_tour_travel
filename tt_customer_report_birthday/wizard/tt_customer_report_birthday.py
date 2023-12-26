from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError

months_list = [
    ('01', 'January'),
    ('02', 'February'),
    ('03', 'March'),
    ('04', 'April'),
    ('05', 'May'),
    ('06', 'June'),
    ('07', 'July'),
    ('08', 'August'),
    ('09', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
]

class CustomerReportBirthday(models.TransientModel):
    _name = 'tt.customer.report.birthday.wizard'
    _description = 'Customer Report Birthday Wizard'

    def _check_adm_user(self):
        return self.env.user.has_group('base.group_erp_manager')

    def _check_ho_user(self):
        return self.env.user.has_group('base.group_erp_manager') or (self.env.user.has_group('tt_base.group_tt_tour_travel') and self.env.user.agent_id.is_ho_agent)

    month_from = fields.Selection(months_list, default='01')
    month_to = fields.Selection(months_list, default='01')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    all_ho = fields.Boolean('All Head Office', default=False)

    def get_agent_domain(self):
        if self.all_ho or not self.ho_id:
            dom = []
        else:
            dom = [('ho_id','=',self.ho_id.id)]
        return dom

    agent_id = fields.Many2one('tt.agent', string='Agent', domain=get_agent_domain, default=lambda self: self.env.user.agent_id)
    all_agent = fields.Boolean('All Agent', default=False)
    is_admin = fields.Boolean('Admin User', default=_check_adm_user)
    is_ho = fields.Boolean('Ho User', default=_check_ho_user)

    @api.onchange('all_ho', 'ho_id')
    def _onchange_domain_agent(self):
        return {'domain': {
            'agent_id': self.get_agent_domain()
        }}

    def _print_report_excel(self, data):
        raise UserError(_("Not implemented."))

    def _prepare_form(self, data):
        # ========== Timezone Process ==========
        user_tz = pytz.timezone('Asia/Jakarta')
        date_now = fields.datetime.now(tz=user_tz)
        data['form']['date_now'] = date_now

        data['form']['month_from'] = self.month_from
        data['form']['month_to'] = self.month_to

        # ============= subtitle process ==========
        data['form']['subtitle'] = "{} to {}".format(self.month_from, self.month_to)

        # ============= ho id and name ==========
        if self.all_ho == True:
            data['form']['ho_id'] = ''
            data['form']['ho_name'] = 'All Head Office'
        else:
            ho_id = data['form']['ho_id'][0] if 'ho_id' in data['form'].keys() else False
            if ho_id != self.env.user.ho_id.id and not self.env.user.has_group('base.group_erp_manager'):
                ho_id = self.env.user.ho_id.id
            ho_name = self.env['tt.agent'].sudo().browse(ho_id).name if ho_id else 'All Head Office'
            data['form']['ho_id'] = ho_id
            data['form']['ho_name'] = ho_name

        # ============= agent id and name ==========
        if self.all_agent == True:
            data['form']['agent_id'] = ''
            data['form']['agent_name'] = ''
        else:
            agent_id = data['form']['agent_id'][0] if 'agent_id' in data['form'].keys() else False
            if agent_id != self.env.user.agent_id.id and not self.env.user.agent_id.is_ho_agent:
                agent_id = self.env.user.agent_id.id
            agent_name = self.env['tt.agent'].sudo().browse(agent_id).name if agent_id else 'All Agent'
            data['form']['agent_id'] = agent_id
            data['form']['agent_name'] = agent_name

        if 'agent_type_id' in data['form']:
            agent_type = data['form']['agent_type_id']
            if not agent_type:
                data['form']['agent_type_id'] = False
                data['form']['agent_type'] = ''
            else:
                data['form']['agent_type_id'] = agent_type[0]
                data['form']['agent_type'] = agent_type[1]

    def _build_contexts(self, data):
        result = {}
        return result

    @api.multi
    def action_print(self):
        self.ensure_one()
        data = ({
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['month_from', 'month_to', 'all_ho', 'ho_id', 'all_agent', 'agent_id'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['date_now'] = str(data['form']['date_now'])[:19]
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report(data)

    def action_print_excel(self):
        self.ensure_one()
        data = ({
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['month_from', 'month_to', 'all_ho', 'ho_id', 'all_agent', 'agent_id'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)
