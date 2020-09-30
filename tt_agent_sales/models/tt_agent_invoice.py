from odoo import models, api, fields, _
from datetime import datetime, timedelta
from odoo import exceptions
from odoo.exceptions import UserError
from ...tools import ERR,util
import base64


class Ledger(models.Model):
    _inherit = 'tt.ledger'

    agent_invoice_id = fields.Many2one('tt.agent.invoice','Agent Invoice ID')


class AgentInvoice(models.Model):
    _name = 'tt.agent.invoice'
    _inherit = 'tt.history'
    _description = 'Rodex Model'
    _order = 'id desc'

    name = fields.Char('Name', default='New', readonly=True)
    total = fields.Monetary('Subtotal', compute="_compute_total",store=True)
    total_after_tax = fields.Monetary('Total (After Tax)', compute="_compute_total_tax",store=True)
    admin_fee = fields.Monetary('Admin Fee',compute="_compute_admin_fee",store=True)
    grand_total = fields.Monetary('Grand Total',compute="_compute_grand_total",store=True)

    paid_amount = fields.Monetary('Paid Amount', compute="_compute_paid_amount")
    invoice_line_ids = fields.One2many('tt.agent.invoice.line','invoice_id','Invoice Line', readonly=True,
                                       states={'draft': [('readonly', False)]})
    booker_id = fields.Many2one('tt.customer', 'Booker',readonly=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Vendor Refund'),
    ], index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('bill', 'Bill'),
        ('bill2', 'Bill (by system)'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Confirm' status is used when user creates invoice, an invoice number is generated.\n"
             " * The 'Bill' status is set when billing statement was created.\n"
             " * The 'Bill (by system)' status is set when billing statement was created automaticaly by system.\n"
             " * The 'Paid' status is set when the payment total .\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    agent_id = fields.Many2one('tt.agent', string='Agent', required=True, readonly=True, states={'draft': [('readonly', False)]})
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]}, help='COR/POR Name')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Parent Type',
                                              related='customer_parent_id.customer_parent_type_id')

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger',
                                 readonly=True, states={'draft': [('readonly', False)]}, domain=[('res_model', '=', 'tt.agent.invoice')])

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))

    # payment_ids = fields.One2many('tt.payment.invoice.rel', 'invoice_id', 'Payments',states={'paid': [('readonly', True)]})
    payment_ids = fields.One2many('tt.payment.invoice.rel', 'invoice_id', 'Payments',states={'paid': [('readonly', True)]})
    payment_acquirers = fields.Char('List of Acquirers',compute="_compute_acquirers",store=True)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    confirmed_date = fields.Datetime('Confirmed Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)

    date_invoice = fields.Date(string='Invoice Date', default=fields.Date.context_today,
                               index=True, copy=False, readonly=True)

    description = fields.Text('Description',readonly=True)

    printout_invoice_id = fields.Many2one('tt.upload.center', 'Printout Invoice')

    # Bill to
    bill_name = fields.Char('Billing to')
    bill_address = fields.Text('Billing Address')
    additional_information = fields.Text('Additional Information')
    bill_address_id = fields.Many2one('address.detail', 'Address')

    pnr = fields.Char("PNR",compute="_compute_invoice_pnr",store=True)
    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',readonly=True,domain=_get_res_model_domain)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('agent.invoice')
        new_invoice = super(AgentInvoice, self).create(vals_list)
        new_invoice.set_default_billing_to()
        return new_invoice

    # @api.multi
    # def write(self, vals):
    #     #pengecekan paid di sini dan tidak di compute paid supaya status berubah ketika tekan tombol save
    #     #jika tidak, saat pilih payment sebelum save bisa lgsg berubah jadi paid
    #     res = super(AgentInvoice, self).write(vals)
    #     # if 'payment_ids' in vals:
    #     self.check_paid_status()
    #     return res

    @api.depends("invoice_line_ids.pnr")
    def _compute_invoice_pnr(self):
        for rec in self:
            rec.pnr = ", ".join([rec1.pnr for rec1 in rec.invoice_line_ids if rec1.pnr])

    @api.depends("payment_ids.payment_acquirer")
    def _compute_acquirers(self):
        for rec in self:
            aqc_list = []
            for payment in rec.payment_ids:
                if payment.payment_acquirer and payment.state != 'cancel':
                    aqc_list.append(payment.payment_acquirer)
            rec.payment_acquirers = ",".join(aqc_list)

    def set_as_confirm(self):
        self.write({
            'state': "confirm",
            'confirmed_uid': self.env.user.id,
            'confirmed_date': datetime.now()
        })

    def action_cancel_invoice(self):
        if self.state not in ['cancel','paid']:
            legal = True
            for i in self.payment_ids:
                if i.state not in ['confirm','cancel']:
                    legal = False
            if legal:
                self.state = "cancel"
                for ledger in self.ledger_ids:
                    if not ledger.is_reversed:
                        ledger.reverse_ledger()
            else:
                raise UserError("Invoice payment state not [Confirm].")
        else:
            raise UserError("Invoice state not [Confirm].")

    def set_as_paid(self):
        self.state = "paid"

    def action_confirm_agent_invoice(self):
        if self.state == 'draft':
            self.state = 'confirm'
            self.confirmed_date = fields.Datetime.now()
            self.confirmed_uid = self.env.user.id

    def check_paid_status(self):
        paid_amount = 0
        for rec in self.payment_ids:
            if rec.state in ['approved']:
                paid_amount += rec.pay_amount
        if self.state != 'paid' and (paid_amount >= self.total and self.total != 0):
            self.state = 'paid'
        elif self.state not in ['confirm','bill','bill2'] and (paid_amount < self.total and self.total != 0):
            self.state = 'bill2'
        # return


    @api.multi
    @api.depends('invoice_line_ids.total', 'invoice_line_ids')
    def _compute_total(self):
        for inv in self:
            total = 0
            for rec in inv.invoice_line_ids:
                total += rec.total
            inv.total = total

    @api.multi
    @api.depends('invoice_line_ids.total_after_tax', 'invoice_line_ids')
    def _compute_total_tax(self):
        for inv in self:
            total = 0
            for rec in inv.invoice_line_ids:
                total += rec.total_after_tax
            inv.total_after_tax = total

    @api.multi
    @api.depends('invoice_line_ids.admin_fee', 'invoice_line_ids')
    def _compute_admin_fee(self):
        for inv in self:
            total = 0
            for rec in inv.invoice_line_ids:
                total += rec.admin_fee
            inv.admin_fee = total

    @api.multi
    @api.depends('total_after_tax','admin_fee')
    def _compute_grand_total(self):
        for inv in self:
            inv.grand_total = inv.total_after_tax + inv.admin_fee

    @api.multi
    def _compute_paid_amount(self):
        for inv in self:
            paid_amount = 0
            # paid_amount = sum(rec.pay_amount for rec in inv.payment_ids if (rec.create_date and rec.state in ['validate','validate2']))
            for rec in inv.payment_ids:
                if rec.state in ['approved']:
                    paid_amount += rec.pay_amount
            inv.paid_amount = paid_amount

    # def calculate_paid_amount(self):
    #     paid = 0
    #     for rec in self.payment_ids:
    #         paid += rec.pay_amount
    #     self.paid_amount = paid
    #     if self.paid_amount >= self.total:
    #         self.state = 'paid'
    #         self.billing_statement_id.check_status()

    def set_to_confirm(self):
        self.state = 'confirm'

    def set_to_bill(self):
        self.state = 'bill'

    def print_invoice_api(self, data, context):
        new_data = {}
        if data.get('bill_to_name'):
            new_data.update({
                'bill_to_name': data.get('bill_to_name')
            })
        if data.get('bill_address'):
            new_data.update({
                'bill_address': data.get('bill_address')
            })
        if data.get('additional_information'):
            new_data.update({
                'additional_information': data.get('additional_information')
            })
            
        url = []
        for rec in self.env['tt.reservation.%s' % data['provider_type']].search([('name', '=', data['order_number'])]):
            if new_data:
                for invoice in rec['invoice_line_ids']:
                    invoice.invoice_id.write(new_data)
                    invoice.invoice_id.printout_invoice_id.unlink()

            datas = {'ids': self.env.context.get('active_ids', [])}
            # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
            res = rec.read()
            res = res and res[0] or {}
            datas['form'] = res
            invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice')
            for invoice in rec['invoice_line_ids']:
                if not invoice.invoice_id.printout_invoice_id:
                    pdf_report = invoice_id.report_action(invoice.invoice_id, data=datas)
                    pdf_report['context'].update({
                        'active_model': invoice.invoice_id._name,
                        'active_id': invoice.invoice_id.id
                    })
                    pdf_report_bytes = invoice_id.render_qweb_pdf(data=pdf_report)
                    res = self.env['tt.upload.center.wizard'].upload_file_api(
                        {
                            'filename': 'Agent Invoice %s.pdf' % invoice.name,
                            'file_reference': 'Agent Invoice for %s' % invoice.name,
                            'file': base64.b64encode(pdf_report_bytes[0]),
                            'delete_date': datetime.today() + timedelta(minutes=10)
                        },
                        {
                            'co_agent_id': context['co_agent_id'],
                            'co_uid': context['co_uid'],
                        }
                    )
                    upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
                    invoice.invoice_id.printout_invoice_id = upc_id.id
                url.append({
                    'type': 'ir.actions.act_url',
                    'name': "Printout",
                    'target': 'new',
                    'url': invoice.invoice_id.printout_invoice_id.url,
                })
        return url
        # return self.env.ref('tt_report_common.action_report_printout_invoice').report_action(self, data=datas)


    def print_invoice(self):
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
                    'filename': 'Agent Invoice %s.pdf' % self.name,
                    'file_reference': 'Agent Invoice for %s' % self.name,
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
        }
        return url
        # return self.env.ref('tt_report_common.action_report_printout_invoice').report_action(self, data=datas)

    @api.onchange('customer_parent_id')
    def set_default_billing_to(self):
        for rec in self:
            if rec.customer_parent_id.customer_parent_type_id.name != 'FPO':
                # Klo  COR POR ambil alamat tagih dari COR/POR tsb
                rec.bill_name = rec.customer_parent_id.name
                rec.bill_address_id = rec.customer_parent_id.address_ids and rec.customer_parent_id.address_ids[0].id or False
                rec.bill_address = rec.bill_address_id.address
            else:
                # Klo FPO ambil alamat booker tsb
                rec.bill_name = rec.booker_id.name
                # TODO pertimbangkan ambil yg state = Work
                if rec.booker_id.address_ids:
                    rec.bill_address_id = rec.booker_id.address_ids[0].id
                    for rec2 in rec.booker_id.address_ids:
                        if rec2.type == 'work':
                            rec.bill_address_id = rec2.id
                            break
                    rec.bill_address = rec.bill_address_id.address
                else:
                    rec.bill_address = ''

