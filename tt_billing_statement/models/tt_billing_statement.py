from odoo import api,models,fields
from odoo.exceptions import UserError
from datetime import date,timedelta,datetime
import pytz
import base64
import logging

try:
    from BytesIO import BytesIO
except ImportError:
    from io import BytesIO
import zipfile

_logger = logging.getLogger(__name__)

class TtBillingStatement(models.Model):
    _name = 'tt.billing.statement'
    _inherit = 'tt.history'
    _description = 'Billing Statement'
    _order = 'id desc'

    name = fields.Char('Number', required=True, readonly=True, default='New')
    date_billing = fields.Date('Date', default=fields.Date.context_today, readonly=True, states={'draft': [('readonly', False)]})

    due_date = fields.Date('Due Date', readonly=True,
                             states={'draft': [('readonly', False)]})

    transaction_start_date = fields.Date('Start Date', readonly=True,
                           states={'draft': [('readonly', False)]})

    transaction_end_date = fields.Date('End Date', readonly=True,
                             states={'draft': [('readonly', False)]})

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, readonly=True,
                               states={'draft': [('readonly', False)]},
                               default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True,
                               states={'draft': [('readonly', False)]},
                               default=lambda self: self.env.user.agent_id.id)
    agent_type_id = fields.Many2one('tt.agent.type', string='Agent Type', related='agent_id.agent_type_id', store=True)
    # customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', required=True, readonly=True,
    #                                states={'draft': [('readonly', False)]})
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True,
                                   states={'draft': [('readonly', False)]}) ## TESTING REQUIRED FALSE UNTUK AGENT
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', string='Customer Type', related='customer_parent_id.customer_parent_type_id',
                                        store=True)

    # contact_id = fields.Many2one('tt.customer', 'Booker / Contact', readonly=True,
    #                              states={'draft': [('readonly', False)]})

    contact_id_backup = fields.Integer('Backup ID')
    # booker_type = fields.Selection(string='Booker Type', related='contact_id.booker_type')

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('partial', 'Partial Paid')
                                 , ('paid', 'Paid'), ('cancel', 'Cancelled')], 'Status', default='draft', readonly=True,
                             states={'draft': [('readonly', False)]})
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    amount_total = fields.Monetary('Total', compute='_compute_amount_total', store=False)

    invoice_ids = fields.One2many('tt.agent.invoice', 'billing_statement_id', string='Agent Invoices')
    ho_invoice_ids = fields.One2many('tt.ho.invoice', 'billing_statement_id', string='HO Invoices')

    # payment_transaction_ids = fields.One2many('payment.transaction', 'billing_statement_id', string='Payments',
    #                                           required=True)

    paid_amount = fields.Monetary('Paid Amount', store=False, compute='_compute_amount_total')
    unpaid_amount = fields.Monetary('Unpaid Amount', store=False, compute='_compute_amount_total')

    # collectibility_status = fields.Selection([('current', 'Current'), ('special_mention', 'Special Mention'),
    #                                           ('substandard', 'Substandard'), ('doubtful', 'Doubtful'),
    #                                           ('bad', 'Bad')], 'Collectibility Status',
    #                                          help="Collectibility status information (late categories):\n"
    #                                               " * Current (payment is on time and did not exceed the due date).\n"
    #                                               " * Special mention (payment is yet to be done between 1 - 10 calendar days after the due date).\n"
    #                                               " * Substandard (payment is still yet to be done between 11 - 20 calendar days after the due date).\n"
    #                                               " * Doubtful (payment is still yet to be done between 21 - 30 calendar days after the due date).\n"
    #                                               " * Bad (payment is not been done more than calendar days after the due date).\n")
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

    def unlink_all_printout(self, type='All'):
        for rec in self:
            rec.printout_billing_statement_id.sudo().unlink()

    def compute_date_billing_all(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 69')
        for rec in self.search([]):
            rec.date_billing = rec.create_date.date()

    @api.model
    def create(self, vals_list):
        # if 'invoice_ids' in vals_list:
        #     amount_total = 0
        #     for inv in vals_list['invoice_ids']:
        #         amount_total+= self.env['tt.agent.invoice'].browse(inv[2][0]).total
        #     vals_list['amount_total'] = amount_total
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.billing.statement')
        new_billing = super(TtBillingStatement, self).create(vals_list)
        new_billing.fill_start_end_date()
        return new_billing

    # def find_transaction_date(self,today_date,cycle_list,increment_plus=True):
    #     while(today_date.strftime('%A') not in cycle_list and
    #           'Date %s' % (today_date.strftime('%d')) not in cycle_list and
    #           'No billing' not in cycle_list and
    #           cycle_list):
    #         today_date += timedelta(days=increment_plus and 1 or -1)
    #     return today_date

    def fill_start_end_date(self):
        ## untuk billing agent invoice corporate
        if self.customer_parent_id:
            last_billing_obj = self.search([('id','!=',self.id or -1),
                                            ('customer_parent_id','=',self.customer_parent_id.id),
                                            ('transaction_end_date','!=',False)],
                                           order='transaction_end_date desc', limit=1)
        ## untuk billing ho invoice agent, yg customer parentny kosong
        elif self.agent_id:
            last_billing_obj = self.search([('id', '!=', self.id or -1),
                                            ('agent_id','=',self.agent_id.id),
                                            ('customer_parent_id', '=', False),
                                            ('transaction_end_date', '!=', False)],
                                           order='transaction_end_date desc', limit=1)

        # cycle_list = [str(rec1.name) for rec1 in self.customer_parent_id.billing_cycle_ids]

        if last_billing_obj.transaction_end_date:
            start_date = last_billing_obj.transaction_end_date + timedelta(days=1)
            # start_date = self.find_transaction_date(cycle_list,increment_plus=False)
        elif self.customer_parent_id:
            start_date = self.customer_parent_id.create_date.date()
        else:
            start_date = self.create_date.date()

        tz_utc7 = pytz.timezone('Asia/Jakarta')
        # today_date = date.today() + timedelta(days=1)
        today_date = datetime.now(tz_utc7).date()
        # end_date = self.find_transaction_date(today_date,cycle_list,increment_plus=True)
        end_date = today_date - timedelta(days=1)

        if end_date < start_date:
            end_date = start_date

        self.transaction_start_date = date(start_date.year,start_date.month,start_date.day)
        self.transaction_end_date = date(end_date.year,end_date.month,end_date.day)

    @api.multi
    @api.depends('invoice_ids.total', 'invoice_ids.paid_amount','invoice_ids', 'ho_invoice_ids.total', 'ho_invoice_ids.paid_amount','ho_invoice_ids')
    def _compute_amount_total(self):
        for rec in self:
            amount_total = 0
            paid_amount = 0
            for inv in rec.invoice_ids:
                if inv.state != 'cancel':
                    amount_total += inv.total_after_tax
                    paid_amount += inv.paid_amount

            for inv in rec.ho_invoice_ids:
                if inv.state != 'cancel':
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

    def check_status_bs(self):
        if all([rec.state == 'paid' for rec in self.invoice_ids]) or self.paid_amount == self.amount_total:
            self.state = 'paid'
        elif any([rec.state == 'paid' for rec in self.invoice_ids]):
            self.state = 'partial'
        elif all([rec.state == 'confirm' for rec in self.invoice_ids]):
            self.state = 'confirm'
        elif all([rec.state == 'cancel' for rec in self.invoice_ids]):
            self.state = 'cancel'

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
                    'delete_date': datetime.today() + timedelta(days=1)
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
            'name': "Printout",
            'target': 'new',
            'url': self.printout_billing_statement_id.url,
        }
        return url
        # return printout_billing_statement_action.report_action(self, data=datas)

    def print_all_agent_invoice(self):
        zip_filename = "inv_%s.zip" % self.name
        bitIO = BytesIO()
        zip_file = zipfile.ZipFile(bitIO, "w", zipfile.ZIP_DEFLATED)

        for inv_obj in self.ho_invoice_ids:
            # if not inv_obj.printout_invoice_id:
            #     inv_obj.print_invoice()
            if inv_obj.printout_invoice_id:
                zip_file.write(inv_obj.printout_invoice_id.path, inv_obj.printout_invoice_id.filename)
            # zip_file.writestr('qq' + str(inv_obj.name) + '.json', 'data_json')
        for inv_obj in self.invoice_ids:
            if inv_obj.printout_invoice_id:
                zip_file.write(inv_obj.printout_invoice_id.path, inv_obj.printout_invoice_id.filename)
        zip_file.close()

        res = self.env['tt.upload.center.wizard'].upload_file_api(
            {
                'filename': '%s' % zip_filename,
                'file_reference': 'ZipFile',
                'file': base64.b64encode(bitIO.getvalue()),
                'delete_date': datetime.today() + timedelta(minutes=10)
            },
            {
                'co_agent_id': self.agent_id.id,
                'co_uid': self.env.user.id,
            }
        )
        upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)

        url = {
            'type': 'ir.actions.act_url',
            'name': "Zip " + str(datetime.now()),
            'target': 'new',
            'url': upc_id.url,
        }
        return url

    def get_email_reply_to(self):
        try:
            final_email = ''
            if self.agent_id:
                ho_agent_obj = self.agent_id.ho_id
                final_email = ho_agent_obj.email_server_id.smtp_user
        except Exception as e:
            _logger.error(str(e))
            final_email = ''
        return final_email

    def get_company_name(self):
        company_obj = self.env['res.company'].search([],limit=1)
        return company_obj.name
