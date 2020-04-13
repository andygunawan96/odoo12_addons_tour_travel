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

    month_from = fields.Selection(months_list, default='01')
    month_to = fields.Selection(months_list, default='01')

    def _print_report_excel(self, data):
        raise UserError(_("Not implemented."))

    def _prepare_form(self, data):
        # ========== Timezone Process ==========
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_now = fields.datetime.now(tz=user_tz)
        data['form']['date_now'] = date_now

        data['form']['month_from'] = self.month_from
        data['form']['month_to'] = self.month_to

        # ============= subtitle process ==========
        data['form']['subtitle'] = "{} to {}".format(self.month_from, self.month_to)

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
            'form': self.read(['month_from', 'month_to'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)