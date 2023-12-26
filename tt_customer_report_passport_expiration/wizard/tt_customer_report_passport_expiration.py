from odoo import api, fields, models, _
import pytz
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class CustomerReportPassportExpiration(models.TransientModel):
    _name = 'tt.customer.report.passport.expiration.wizard'
    _description = 'Customer Report Passport Expiration Wizard'

    def _check_adm_user(self):
        return self.env.user.has_group('base.group_erp_manager')

    def _check_ho_user(self):
        return self.env.user.has_group('base.group_erp_manager') or (self.env.user.has_group('tt_base.group_tt_tour_travel') and self.env.user.agent_id.is_ho_agent)

    int_value = fields.Integer('Number Value')
    type_value = fields.Selection([('days','Day(s)'),
                                   ('months','Month(s)')],'Type')

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    all_ho = fields.Boolean('All Head Office', default=False)

    def get_agent_domain(self):
        if self.all_ho or not self.ho_id:
            dom = []
        else:
            dom = [('ho_id', '=', self.ho_id.id)]
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
        form_type_value = data['form'].pop('type_value')
        form_int_value = data['form'].pop('int_value')

        data['form']['date_before'] = (date_now + (form_type_value == 'days' and relativedelta(days=form_int_value) or relativedelta(months=form_int_value))).date()
        # ============= subtitle process ==========
        data['form']['subtitle'] = "Before {}".format(data['form']['date_before'])

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
            'form': self.read(['int_value', 'type_value', 'all_ho', 'ho_id', 'agent_id', 'all_agent'])[0]
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
            'form': self.read(['int_value', 'type_value', 'all_ho', 'ho_id', 'agent_id', 'all_agent'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)