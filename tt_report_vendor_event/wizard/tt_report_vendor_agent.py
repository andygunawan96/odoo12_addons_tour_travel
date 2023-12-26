from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError

class VendorReportEvent(models.TransientModel):
    _name = "tt.report.vendor.event.wizard"

    def _check_ho_user(self):
        return self.env.user.has_group('base.group_erp_manager') or (self.env.user.has_group('tt_base.group_tt_tour_travel') and self.env.user.agent_id.is_ho_agent)

    is_ho = fields.Boolean('Ho User', compute=_check_ho_user)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    event_name = fields.Selection(selection=lambda self: self._compute_event_list(), default='all')
    transaction_state = fields.Selection([('all', 'All'), ('request', 'Request'), ('confirm', 'Confirm'), ('done', 'Paid')], default='all')

    def _compute_event_list(self):
        if self.is_ho:
        # Temp VIN: jngan di SYNC cman test local ku nyantol
        # if self.env.user.agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
            event_list = self.env['tt.master.event'].sudo().search([])
        else:
            event_list = self.env['tt.master.event'].sudo().search([('event_vendor_id', '=', self.env.user.vendor_id.id)])
        value = [('all', 'All')]
        for i in event_list:
            temp_tuple = (str(i.id), str(i.name))
            if temp_tuple not in value:
                value.append(temp_tuple)
        return value

    def _print_report_excel(self, data):
        raise UserError(_("Not Implemented"))

    def _prepare_form(self, data):
        # ========== Timezone Process ==========
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

        data['form']['event_name'] = self.event_name
        data['form']['transaction_state'] = self.transaction_state
        data['form']['vendor_id'] = self.env.user.vendor_id.id

    def _build_contexts(self, data):
        result = {}
        return result

    @api.multi
    def action_print(self):
        self.ensure_one()
        event_name = self.read(['event_name'])[0]
        transaction_state = self.read(['transaction_state'])[0]
        date_from_raw = self.read(['date_from'])[0]
        date_to_raw = self.read(['date_to'])[0]

        date_from = date_from_raw['date_from'].strftime("%Y-%m-%d %H:%M:%S")
        date_to = date_to_raw['date_to'].strftime("%Y-%m-%d %H:%M:%S")
        # limitation = [('vendor_id', '=', self.env.user.id)]
        limitation = []
        if event_name['event_name'] != 'all':
            limitation.append(('event_id', '=', int(event_name['event_name'])))
        if transaction_state['transaction_state'] != 'all':
            limitation.append(('state', '=', transaction_state['transaction_state']))
        if date_from:
            limitation.append(('sales_date', '>=', date_from))
        if date_to:
            limitation.append(('sales_date', '<=', date_to))
        data = self.env['tt.event.reservation'].sudo().search(limitation)
        title = "{} - {}, {}".format(date_from, date_to, event_name)
        # Opsi 1 Print 1 Data as 1 Record
        # for i in data:
        #     temp_dict = {
        #         'event_reservation_ids': [(6,0,[i['id']])],
        #         'user_id': self.env.user.id
        #     }
        #     self.env['tt.event.reservation.temporary.payment'].sudo().create(temp_dict)

        # Opsi 2 Print 1 Data as multi Record bisa dipakai untuk rekapan dan tag bukti bayar
        self.env['tt.event.reservation.temporary.payment'].sudo().create({
            'event_reservation_ids': [(6, 0, data.ids)],
            'user_id': self.env.user.id,
            'title': title
        })

    @api.multi
    def action_print_excel(self):
        self.ensure_one()
        data = ({
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(['event_name', 'transaction_state'])[0]
        })
        self._prepare_form(data)
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self._print_report_excel(data)