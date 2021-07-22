from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError


class AgentReportCommon(models.TransientModel):
    _name = "tt.agent.report.common.wizard"
    _description = "Agent Report Common"

    def _check_ho_user(self):
        return self.env.user.agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)

    period = fields.Selection([('today', 'Today'), ('yesterday', 'Yesterday'),
                               ('1', 'This month'), ('2', 'A month ago'), ('3', 'Two month ago'),
                               ('custom', 'Custom')], 'Period', default='today')

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    agent_id = fields.Many2one('tt.agent', string='Agent', default=lambda self: self.env.user.agent_id)
    all_agent = fields.Boolean('All Agent', default=False)
    is_ho = fields.Boolean('Ho User', default=_check_ho_user)

    subtitle_report = fields.Char('Subtitle', help='This field use for report subtitle')

    @api.onchange('period')
    def _onchage_period(self):
        if self.period in ('today', 'custom'):
            self.date_from = fields.Date.context_today(self)
            self.date_to = fields.Date.context_today(self)
            self.subtitle_report = ''
        elif self.period == 'yesterday':
            self.date_from = (fields.Date.from_string(fields.Date.context_today(self)) - timedelta(days=1)).strftime('%Y-%m-%d')
            self.date_to = self.date_from
            self.subtitle_report = 'Yesterday ( %s - %s )' % (self.date_from, self.date_to)
        elif self.period == '1':
            self.date_from = datetime.now().strftime('%Y-%m-01')
            self.date_to = fields.Date.context_today(self)
            self.subtitle_report = '%s - %s' % (self.date_from, self.date_to)
        elif self.period == '2':
            self.date_from = (datetime.today() - relativedelta(months=+1)).strftime('%Y-%m-01')
            self.date_to = (self.date_from + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')
            self.subtitle_report = '%s - %s' % (self.date_from, self.date_to)
        elif self.period == '3':
            self.date_from = (datetime.today() - relativedelta(months=+2)).strftime('%Y-%m-01')
            self.date_to = (self.date_from + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')
            self.subtitle_report = '%s - %s' % (self.date_from, self.date_to)

    # to be override by other module
    def _print_report(self, data):
        raise UserError(_('Not implemented.'))

    # to be override by other module
    def _print_report_excel(self, data):
        raise UserError(_('Not implemented.'))

    def _prepare_form(self, data):
        # ========== Timezone Process ==========
        # user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        user_tz = pytz.timezone('Asia/Jakarta')
        date_now = fields.datetime.now(tz=user_tz)
        data['form']['date_now'] = date_now

        date_from_utc = data['form'].get('date_from', fields.Date.context_today(self))
        date_from_utc = user_tz.localize(fields.Datetime.from_string(date_from_utc))
        date_from = date_from_utc.astimezone(pytz.timezone('UTC'))
        date_to_utc = '%s %s' % (data['form'].get('date_to', fields.Date.context_today(self)), '23:59:59')
        date_to_utc = user_tz.localize(fields.Datetime.from_string(date_to_utc))
        date_to = date_to_utc.astimezone(pytz.timezone('UTC'))

        data['form']['date_from'] = date_from.strftime("%Y-%m-%d %H:%M:%S")
        data['form']['date_to'] = date_to.strftime("%Y-%m-%d %H:%M:%S")
        data['form']['date_from_utc'] = date_from_utc.strftime("%Y-%m-%d %H:%M:%S")
        data['form']['date_to_utc'] = date_to_utc.strftime("%Y-%m-%d %H:%M:%S")

        # ============= subtitle process ==========
        if not self.subtitle_report:
            self.subtitle_report = self.date_from.strftime("%d-%b-%Y") + ' to ' + self.date_to.strftime("%d-%b-%Y")
        data['form']['subtitle'] = self.subtitle_report

        # ============= agent id and name ==========
        if self.all_agent == True:
            data['form']['agent_id'] = ''
            data['form']['agent_name'] = 'All Agent'
        else:
            agent_id = data['form']['agent_id'][0] if data['form']['agent_id'] else False
            if agent_id != self.env.user.agent_id.id and self.env.user.agent_id.agent_type_id.id != self.env.ref('tt_base.agent_type_ho').id:
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
            'form': self.read(['date_from', 'date_to', 'period', 'all_agent', 'agent_id', 'state', 'provider_type', 'chart_frequency', 'agent_type_id'])[0]
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
            'form': self.read(['date_from', 'date_to', 'period', 'agent_id', 'state', 'provider_type', 'chart_frequency', 'agent_type_id', 'agent_type', 'logging_daily', 'period_mode', 'state_vendor'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)
