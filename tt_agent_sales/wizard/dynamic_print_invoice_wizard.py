from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import base64, logging

_logger = logging.getLogger(__name__)


class DynamicPrintInvoiceLine(models.Model):
    _name = "tt.dynamic.print.invoice.line"
    _description = 'Rodex Dynamic Print Invoice Line Model'

    invoice_line_detail_id = fields.Many2one('tt.agent.invoice.line.detail', 'Invoice Line Detail', readonly=True)
    invoice_line_id = fields.Many2one('tt.agent.invoice.line', 'Invoice Line', readonly=True, related='invoice_line_detail_id.invoice_line_id')
    is_printed = fields.Boolean('Is Printed', default=True)
    print_wizard_id = fields.Many2one('tt.dynamic.print.invoice.wizard', 'Print Wizard', ondelete='cascade')


class DynamicPrintInvoice(models.Model):
    _name = "tt.dynamic.print.invoice.wizard"
    _description = 'Dynamic Print Invoice Wizard'

    invoice_id = fields.Many2one('tt.agent.invoice', 'Invoice')
    invoice_line_detail_ids = fields.One2many('tt.dynamic.print.invoice.line', 'print_wizard_id', 'Invoice Line(s)')

    def get_form_id(self):
        return self.env.ref("tt_agent_sales.tt_dynamic_print_invoice_wizard_form_view")

    def dynamic_print_invoice(self):
        datas = {'ids': self.invoice_id.env.context.get('active_ids', [])}
        res = self.invoice_id.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['included_detail_ids'] = []
        is_dynamic_print = False
        include_bool_list = []
        for rec in self.invoice_line_detail_ids:
            if rec.is_printed:
                datas['included_detail_ids'].append(rec.invoice_line_detail_id.id)
                include_bool_list.append(True)
            else:
                include_bool_list.append(False)
        if False in include_bool_list and True in include_bool_list:
            is_dynamic_print = True

        printout_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice')
        if self.invoice_id.agent_id:
            co_agent_id = self.invoice_id.agent_id.id
        else:
            co_agent_id = self.env.user.agent_id.id

        if self.invoice_id.confirmed_uid:
            co_uid = self.invoice_id.confirmed_uid.id
        else:
            co_uid = self.env.user.id

        print_count = self.invoice_id.dynamic_print_count
        if is_dynamic_print:
            datas['is_dynamic_print'] = True
            filename = print_count == 0 and 'Agent Invoice %s' % self.invoice_id.name or 'Agent Invoice %s - Reprint %s.pdf' % (self.invoice_id.name, print_count)
        else:
            datas['is_dynamic_print'] = False
            filename = 'Agent Invoice %s' % self.invoice_id.name
        pdf_report = printout_invoice_id.report_action(self.invoice_id, data=datas)
        pdf_report['context'].update({
            'active_model': self.invoice_id._name,
            'active_id': self.invoice_id.id
        })
        pdf_report_bytes = printout_invoice_id.render_qweb_pdf(data=pdf_report)
        res = self.env['tt.upload.center.wizard'].upload_file_api(
            {
                'filename': filename,
                'file_reference': 'Agent Invoice for %s' % self.invoice_id.name,
                'file': base64.b64encode(pdf_report_bytes[0]),
                'delete_date': datetime.today() + timedelta(minutes=10)
            },
            {
                'co_agent_id': co_agent_id,
                'co_uid': co_uid
            }
        )
        upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
        if is_dynamic_print:
            self.invoice_id.write({
                'dynamic_print_count': print_count + 1
            })
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': upc_id.url,
            'path': upc_id.path
        }
        return url
