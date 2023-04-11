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

    def _check_ho_user(self):
        return self.env.user.agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id

    month_from = fields.Selection(months_list, default='01')
    month_to = fields.Selection(months_list, default='01')

    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain, default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent', string='Agent', default=lambda self: self.env.user.agent_id)
    all_agent = fields.Boolean('All Agent', default=False)
    is_ho = fields.Boolean('Ho User', default=_check_ho_user)

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

        # ============= agent id and name ==========
        if self.all_agent == True:
            data['form']['agent_id'] = ''
            data['form']['agent_name'] = ''
        else:
            agent_id = data['form']['agent_id'][0] if 'agent_id' in data['form'].keys() else False
            if agent_id != self.env.user.agent_id.id and self.env.user.agent_id.agent_type_id.id != self.env.ref(
                    'tt_base.agent_type_ho').id:
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
            'form': self.read(['month_from', 'month_to'])[0]
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
            'form': self.read(['month_from', 'month_to', 'agent_id', 'all_agent'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)