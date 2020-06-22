from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from odoo.exceptions import UserError

class VendorReportEvent(models.TransientModel):
    _name = "tt.report.vendor.event.wizard"

    event_name = fields.Selection(selection=lambda self: self._compute_event_list(), default='all')
    transaction_state = fields.Selection([('all', 'All'), ('request', 'Request'), ('confirm', 'Confirm'), ('done', 'Paid')], default='all')

    def _compute_event_list(self):
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
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        date_now = fields.datetime.now(tz=user_tz)
        data['form']['date_now'] = date_now

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
        # limitation = [('vendor_id', '=', self.env.user.id)]
        limitation = []
        if event_name['event_name'] != 'all':
            limitation.append(('event_id', '=', int(event_name['event_name'])))
        if transaction_state['transaction_state'] != 'all':
            limitation.append(('transaction_state', '=', transaction_state['transaction_state']))
        data = self.env['tt.event.reservation'].sudo().search(limitation)
        for i in data:
            temp_dict = {
                'event_reservation_ids': [(6,0,[i['id']])],
                'user_id': self.env.user.id
            }
            self.env['tt.event.reservation.temporary.payment'].sudo().create(temp_dict)
        # self.env['tt.event.reservation.temporary.payment'].sudo().create({
        #     'event_reservation_ids': [(6, 0, data.ids)],
        #     'user_id': self.env.user.id
        # })

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