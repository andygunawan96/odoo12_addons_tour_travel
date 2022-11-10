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

    ho_invoice_id = fields.Many2one('tt.ho.invoice','HO Invoice ID')

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

    # Fungsi Asli dri tt.agent.invoice ==> set_default_billing_to
    def set_default_ho_billing_to(self):
        for rec in self:
            rec.bill_name = rec.agent_id.name
            rec.bill_address_id = rec.agent_id.address_ids and rec.agent_id.address_ids[0].id or False
            rec.bill_address = rec.bill_address_id.address if rec.bill_address_id else ''

    @api.model
    def create(self, vals_list):
        if type(vals_list) == dict:
            vals_list = [vals_list]
        for rec in vals_list:
            if 'name' not in rec:
                rec['name'] = self.env['ir.sequence'].next_by_code('ho.invoice')
        new_invoice = super(AgentInvoiceInh, self).create(vals_list)
        new_invoice.set_default_ho_billing_to()
        return new_invoice

    def print_invoice(self): ## NEED UPDATE KO VINCENT
        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res

        invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho')
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
                    'filename': 'HO Invoice %s.pdf' % self.name,
                    'file_reference': 'HO Invoice for %s' % self.name,
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

    def check_paid_status(self):
        paid_amount = 0
        for rec in self.payment_ids:
            if rec.state in ['approved']:
                paid_amount += rec.pay_amount
        self.prev_state = self.state
        if self.state != 'paid' and (paid_amount >= self.grand_total and self.grand_total != 0):
            if self.state not in ['bill', 'bill2']: ## BELUM BILL LANGSUNG PAYMENT
                ## CREATE LEDGER BILL
                self.create_ledger_invoice(debit=False)
            self.state = 'paid'
        elif self.state not in ['confirm','bill','bill2'] and (paid_amount < self.grand_total and self.grand_total != 0):
            self.state = 'confirm'

            ## KEMBALIKAN LEDGER COMMISSION
            for ledger_obj in self.ledger_ids:
                if ledger_obj.source_of_funds_type == 'balance' and not ledger_obj.is_reversed:
                    ledger_obj.reverse_ledger()
