from odoo import models, api, fields, _
import datetime
from odoo import exceptions
from odoo.exceptions import UserError


class Ledger(models.Model):
    _inherit = 'tt.ledger'

    agent_invoice_id = fields.Many2one('tt.agent.invoice','Agent Invoice ID')


class AgentInvoice(models.Model):
    _name = 'tt.agent.invoice'
    _description = 'Rodex Model'

    name = fields.Char('Name', default='New', readonly=True)
    total = fields.Monetary('Total', compute="_compute_total",store=True)
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

    ledger_ids = fields.One2many('tt.ledger', 'agent_invoice_id', 'Ledger',
                                              readonly=True, states={'draft': [('readonly', False)]})

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('account.invoice'))

    payment_ids = fields.One2many('tt.payment.invoice.rel', 'invoice_id', 'Payments',states={'paid': [('readonly', True)]})

    confirmed_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    confirmed_date = fields.Datetime('Confirmed Date', readonly=True)

    date_invoice = fields.Date(string='Invoice Date', default=fields.Date.context_today,
                               index=True, copy=False, readonly=True)
    description = fields.Text('Description',readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('agent.invoice')
        return super(AgentInvoice, self).create(vals_list)
    
    def write(self, vals):
        #pengecekan paid di sini dan tidak di compute paid supaya status berubah ketika tekan tombol save
        #jika tidak, saat pilih payment sebelum save bisa lgsg berubah jadi paid
        super(AgentInvoice, self).write(vals)
        # if 'payment_ids' in vals:
        if self.check_paid_status():
            self.state = 'paid'

    def set_as_confirm(self):
        self.write({
            'state': "confirm",
            'confirmed_uid': self.env.user.id,
            'confirmed_date': datetime.datetime.now()
        })

    def set_as_paid(self):
        self.state = "paid"

    def action_confirm_agent_invoice(self):
        if self.state == 'draft':
            self.state = 'confirm'
            self.confirmed_date = fields.Datetime.now()
            self.confirmed_uid = self.env.user.id

    def check_paid_status(self):
        return self.paid_amount >= self.total and self.total != 0

    @api.multi
    @api.depends('invoice_line_ids.total', 'invoice_line_ids')
    def _compute_total(self):
        for inv in self:
            total = 0
            for rec in inv.invoice_line_ids:
                total += rec.total
            inv.total = total

    @api.multi
    def _compute_paid_amount(self):
        for inv in self:
            paid_amount = 0
            # paid_amount = sum(rec.pay_amount for rec in inv.payment_ids if (rec.create_date and rec.state in ['validate','validate2']))
            for rec in inv.payment_ids:
                if rec.state in ['validated','validated2']:
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

    def print_invoice(self):
        if not self.agent_id.logo:
            raise UserError(_("Your agent have to set their logo."))

        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('tt_report_common.action_report_printout_invoice').report_action(self, data=datas)
