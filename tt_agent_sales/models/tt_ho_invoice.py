import traceback

from odoo import models, api, fields, _
from datetime import datetime, timedelta
from odoo import exceptions
from odoo.exceptions import UserError
from ...tools import ERR,util
import base64,logging

_logger = logging.getLogger(__name__)

class Ledger(models.Model):
    _inherit = 'tt.ledger'

    ho_invoice_id = fields.Many2one('tt.ho.invoice','Agent Invoice ID')

class AgentInvoiceInh(models.Model):
    _name = 'tt.ho.invoice'
    _inherit = 'tt.agent.invoice'
    _description = 'HO Invoice'
    _order = 'id desc'

    invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'invoice_id', 'Invoice Line', readonly=True,
                                       states={'draft': [('readonly', False)]})
    payment_ids = fields.One2many('tt.payment.invoice.rel', 'ho_invoice_id', 'Payments',
                                  states={'paid': [('readonly', True)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 readonly=True, states={'draft': [('readonly', False)]},
                                 domain=[('res_model', '=', 'tt.ho.invoice')])
    is_use_credit_limit = fields.Boolean(default=False)

    @api.model
    def create(self, vals_list):
        if type(vals_list) == dict:
            vals_list = [vals_list]
        for rec in vals_list:
            if 'name' not in rec:
                rec['name'] = self.env['ir.sequence'].next_by_code('ho.invoice')
        new_invoice = super(AgentInvoiceInh, self).create(vals_list)
        new_invoice.set_default_billing_to()
        return new_invoice

    def print_invoice(self): ## NEED UPDATE KO VINCENT
        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res

        invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice')
        if not self.printout_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.confirmed_uid:
                co_uid = self.confirmed_uid.id
            else:
                co_uid = self.env.user.id

            pdf_report = invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'HO Agent Invoice %s.pdf' % self.name,
                    'file_reference': 'HO Agent Invoice for %s' % self.name,
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_invoice_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_invoice_id.url,
            'path': self.printout_invoice_id.path
        }
        return url
        # return self.env.ref('tt_report_common.action_report_printout_invoice').report_action(self, data=datas)

