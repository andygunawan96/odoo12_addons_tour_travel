from odoo import api,models,fields
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64

class TtBillingStatement(models.Model):
    _name = 'tt.billing.statement'
    _inherit = 'tt.history'
    _description = 'Rodex Model'
    _order = 'id desc'

    name = fields.Char('Number', required=True, readonly=True, default='New')
    date = fields.Date('Date', index=True, default=fields.Date.context_today, required=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    due_date = fields.Date('Due Date')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True,
                               states={'draft': [('readonly', False)]},
                               default=lambda self: self.env.user.agent_id.id)
    agent_type_id = fields.Many2one('tt.agent.type', string='Agent Type', related='agent_id.agent_type_id', store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', string='Customer Type', related='customer_parent_id.customer_parent_type_id',
                                        store=True)

    contact_id = fields.Many2one('tt.customer', 'Booker / Contact', readonly=True,
                                 states={'draft': [('readonly', False)]})

    contact_id_backup = fields.Integer('Backup ID')
    # booker_type = fields.Selection(string='Booker Type', related='contact_id.booker_type')

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('partial', 'Partial')
                                 , ('paid', 'Paid'), ('cancel', 'Cancelled')], 'Status', default='draft', readonly=True,
                             states={'draft': [('readonly', False)]})
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    amount_total = fields.Monetary('Total', compute='_compute_amount_total', store=False)

    invoice_ids = fields.One2many('tt.agent.invoice', 'billing_statement_id', string='Agent Invoices')

    # payment_transaction_ids = fields.One2many('payment.transaction', 'billing_statement_id', string='Payments',
    #                                           required=True)

    paid_amount = fields.Monetary('Paid Amount', store=False, compute='_compute_amount_total')
    unpaid_amount = fields.Monetary('Unpaid Amount', store=False, compute='_compute_amount_total')

    collectibility_status = fields.Selection([('current', 'Current'), ('special_mention', 'Special Mention'),
                                              ('substandard', 'Substandard'), ('doubtful', 'Doubtful'),
                                              ('bad', 'Bad')], 'Collectibility Status',
                                             help="Collectibility status information (late categories):\n"
                                                  " * Current (payment is on time and did not exceed the due date).\n"
                                                  " * Special mention (payment is yet to be done between 1 - 10 calendar days after the due date).\n"
                                                  " * Substandard (payment is still yet to be done between 11 - 20 calendar days after the due date).\n"
                                                  " * Doubtful (payment is still yet to be done between 21 - 30 calendar days after the due date).\n"
                                                  " * Bad (payment is not been done more than calendar days after the due date).\n")
    #compute='_compute_collectibility_status',

    # email_to_id = fields.Many2one('res.partner', string='Temp. fields')

    confirm_uid = fields.Many2one('res.users', 'Set to Confirm by', readonly=True)
    confirm_date = fields.Datetime('Set to Confirm Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Done by', readonly=True)
    done_date = fields.Datetime('Done Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Canceled by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)

    printout_billing_statement_id = fields.Many2one('tt.upload.center', 'Printout Billing Statement', readonly=True)

    # double_payment = fields.Boolean('Double Payment')

    @api.model
    def create(self, vals_list):
        # if 'invoice_ids' in vals_list:
        #     amount_total = 0
        #     for inv in vals_list['invoice_ids']:
        #         amount_total+= self.env['tt.agent.invoice'].browse(inv[2][0]).total
        #     vals_list['amount_total'] = amount_total
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.billing.statement')
        return super(TtBillingStatement, self).create(vals_list)

    @api.multi
    @api.depends('invoice_ids.total', 'invoice_ids.paid_amount','invoice_ids')
    def _compute_amount_total(self):
        for rec in self:
            amount_total = 0
            paid_amount = 0
            for inv in rec.invoice_ids:
                amount_total += inv.total_after_tax
                paid_amount += inv.paid_amount
            rec.amount_total = amount_total
            rec.paid_amount = paid_amount
            rec.unpaid_amount = rec.amount_total - rec.paid_amount

    @api.one
    def action_confirm(self):
        # self.paid_amount = 0
        # self.amount_total = 200000
        # if self.paid_amount != self.amount_total:
        if True:

            self.confirm_uid = self.env.user.id
            self.confirm_date = fields.Datetime.now()
            self.state = 'confirm'
        else:
            raise UserError('You can not set to confirm this billing. Please cancel the "Payment" first')

    def check_status(self):
        if all([rec.state == 'paid' for rec in self.invoice_ids]):
            self.state = 'paid'

    def print_report_billing_statement(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        printout_billing_statement_action = self.env.ref('tt_report_common.action_report_printout_billing')
        if not self.printout_billing_statement_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = printout_billing_statement_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = printout_billing_statement_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Billing Statement %s.pdf' % self.name,
                    'file_reference': 'Billing Statement Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_billing_statement_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_billing_statement_id.url,
        }
        return url
        # return printout_billing_statement_action.report_action(self, data=datas)
