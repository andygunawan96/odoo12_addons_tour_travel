from odoo import fields, models, api, _
import werkzeug
from odoo.exceptions import UserError
import logging, traceback
_logger = logging.getLogger(__name__)


class AgentInvoice(models.Model):
    _inherit = 'tt.agent.invoice'

    billing_statement_id = fields.Many2one('tt.billing.statement', 'Billing Statement', ondelete="set null")
    billing_date = fields.Date('Billing Date', related='billing_statement_id.date', store=True)
    billing_uid = fields.Many2one('res.users', 'Billed by')

    # CANDY: tambah booker type
    #fixme uncomment later
    # booker_type = fields.Selection(string='Booker Type', related='contact_id.booker_type')

    # Vin Registrasi]
    #fixme uncomment later
    # registration_id = fields.Many2one('res.partner.request', 'Registration')


    def _unlink_ledger(self):
        for rec in self:
            rec.ledger_id.sudo().unlink()

    def test_FPO_set_to_confirm(self):
        #FIXME. Fungsi ini harus di remove, krn hanya Temporary
        fpo_obj = self.env['tt.agent.invoice'].search([('booker_type', '=', 'FPO'),('billing_statement_id','!=','False')])
        for rec in fpo_obj:
            if rec.billing_statement_id.state == 'draft':
                rec.ledger_id.action_set_to_draft()
                rec.action_set_to_confirm()
                self._cr.commit()

    # MOVED TO ACTION_CANCEL ON TT_AGENT_SALES/MODELS/TT_AGENT_INVOICE.PY
    @api.one
    def action_set_to_confirm(self):
        #untuk keluarkan agent_invoice dari tt.billing.statemet-invoice.ids
        if self.billing_statement_id:
            if self.billing_statement_id.state == 'paid':
                raise UserError(_("You cannot change the state to 'Confirm' which Billing Statement's state is PAID"))
            add_notes = 'Ex- Agent Invoice : %s' % self.name
            self.billing_statement_id.notes = self.billing_statement_id.notes and self.billing_statement_id.notes + '\n' + add_notes or add_notes

        self.update({
            'billing_statement_id': False,
            'state': 'confirm',
        })
        # self._unlink_ledger()

    def action_set_to_confirm_api(self, obj_id, api_context=None):
        invoice_obj = self.browse(int(obj_id))
        if invoice_obj:
            invoice_obj.action_confirm()
            return {
                'error_code': 0,
                'error_msg': "Success",
                'response': {
                    'id': invoice_obj.id,
                    'name': invoice_obj.name,
                    'confirmed_uid': invoice_obj.confirmed_uid.name,
                    'state': invoice_obj.state,
                }
            }
        else:
            return {
                'error_code': 1,
                'error_msg': "No Agent Invoice Found",
                'response': {}
            }

    def action_bill_api(self, obj_id, api_context=None):
        invoice_obj = self.browse(int(obj_id))
        if invoice_obj:
            invoice_obj.action_bill()
            return {
                'error_code': 0,
                'error_msg': "Success",
                'response': {
                    'id': invoice_obj.id,
                    'name': invoice_obj.name,
                    'confirmed_uid': invoice_obj.confirmed_uid.name,
                    'state': invoice_obj.state,
                    'billing_statement_id': {
                        'id': invoice_obj.billing_statement_id.id,
                        'name': invoice_obj.billing_statement_id.name,
                    },
                }
            }
        else:
            return {
                'error_code': 1,
                'error_msg': "No Agent Invoice Found",
                'response': {}
            }

    def action_write_model_api(self, model, rec_id, vals):
        rec_obj = self.env[model].browse(int(rec_id))
        if rec_obj:
            rec_obj.write(vals)
        else:
            return {}

    def action_confirm(self):
        if self.state == 'draft':
            self.state = 'confirm'
            self.confirmed_date = fields.Datetime.now()
            self.confirmed_uid = self.env.user.id

    def create_billing_statement_new(self):
        inv_by_cor = {}
        for rec in self.search([('state', 'in', ['draft', 'confirm'])]):
            try:
                rec.action_confirm()
                sub_agent_id = rec.sub_agent_id.id
                if sub_agent_id not in inv_by_cor:
                    inv_by_cor[sub_agent_id] = {
                        # 'payment_term_id': rec.payment_term_id.id and rec.payment_term_id.id or False,
                        'due_date': fields.Date.context_today(rec) and fields.Date.context_today(rec) or False,
                        'agent_id': rec.agent_id.id and rec.agent_id.id or False,
                        'sub_agent_id': rec.sub_agent_id.id and rec.sub_agent_id.id or rec.agent_id.id,
                        'contact_id': rec.contact_id and rec.contact_id.id or False,
                        'invoice_ids': [(6, 0, rec.ids)],
                    }
                else:
                    inv_by_cor[sub_agent_id]['invoice_ids'][0][2].append(rec.id)

            except Exception as e:
                _logger.error('Cron Error: Create Billing Statement New' + '\n' + traceback.format_exc())

        for cor,value in inv_by_cor.items():
            bill_obj = rec.env['tt.billing.statement'].create(value)
            # bill_obj.onchange_sub_agent_id()  # Update payment_term, due_date
            for record in bill_obj.invoice_ids:
                # record.update({
                #     'billing_statement_id': bill_obj.id,
                # })
                # record._onchange_payment_term_date_invoice()
                record.action_bill()  # this call create_ledger for Agent Invoice
                bill_obj.action_confirm()
            rec.env.cr.commit()

    def create_billing_statement(self):
        if any(rec.state != 'confirm' for rec in self):
            raise UserError(_('You cannot create Billing Statement that an Invoice has been set to \'Confirm\'.'))


        values = {
            # 'payment_term_id': self.payment_term_id.id,
            'due_date': fields.Date.context_today(self),
            'agent_id': self.agent_id.id,
            'sub_agent_id': self.sub_agent_id.id,
            'contact_id': self.contact_id and self.contact_id.id or False,
            'invoice_ids': [(4, 0, self.ids)],
        }



        bill_obj = self.env['tt.billing.statement'].create(values)
        # bill_obj.onchange_sub_agent_id() #UPdate payment_term, due_date
        for rec in self:
            rec.update({
                'billing_statement_id': bill_obj.id,
            })
            # rec._onchange_payment_term_date_invoice()
            rec.action_bill()  #this call create_ledger for Agent Invoice
            rec.billing_statement_id.action_confirm()

    def get_agent_invoice(self, start_date=False, end_date=False, limit=10, offset=1, api_context=None):
        def compute_agent_inv(rec):
            def compute_agent_inv_line(rec):
                vals = {
                    'id': rec.id,
                    'name': rec.name,
                    'price_unit': rec.price_unit,
                    'discount': rec.discount,
                    'amount_discount': rec.amount_discount,
                    'quantity': rec.quantity,
                    'price_subtotal': rec.price_subtotal,
                }
                return vals

            new_vals = {
                'id': rec.id,
                'name': rec.name,
                'date': rec.date_invoice,
                'due_date': rec.date_due,
                'invoice_date': rec.date_invoice,
                'billing_date': rec.billing_date,
                'agent': rec.agent_id and {
                    'id': rec.agent_id.id,
                    'name': rec.agent_id.name,
                    'type': rec.agent_id.agent_type_id and rec.agent_id.agent_type_id.name or '',
                } or {},
                'sub_agent': rec.sub_agent_id and {
                    'id': rec.sub_agent_id.id,
                    'name': rec.sub_agent_id.name,
                    'type': rec.sub_agent_id.agent_type_id and rec.sub_agent_id.agent_type_id.name or '',
                } or {},
                'contact_id': rec.contact_id and {
                    'id': rec.contact_id.id,
                    'name': rec.contact_id and rec.contact_id.first_name + ' ' + rec.contact_id.last_name and rec.contact_id.last_name or '',
                } or {},
                'lines': rec.invoice_line_ids and [compute_agent_inv_line(rec1) for rec1 in rec.invoice_line_ids] or [],
                'booker_type': rec.booker_type,
                'origin': rec.origin,
                'payment_term_id': rec.payment_term_id and rec.payment_term_id.name or False,
                'amount_total': rec.amount_total,
                'pnr': rec.pnr,
                'transport_type': rec.transport_type,
                'confirmed_uid': rec.confirmed_uid.name,
                'issued_uid': rec.issued_uid.name,
                'state': rec.state,
            }
            return new_vals
        try:
            user_obj = self.env['res.users'].browse(api_context['co_uid'])
            domain = ['|', ('agent_id', 'in', user_obj.allowed_customer_ids.ids),
                      ('sub_agent_id', '=', user_obj.agent_id.id)]
            if start_date and end_date:
                domain += [('date_invoice', '>=', start_date), ('date_invoice', '<=', end_date)]
            if api_context.get('agent_id', False):
                domain += ['|', ('agent_id.name', 'ilike', api_context['agent_id']), ('sub_agent_id.name', 'ilike', api_context['agent_id'])]
            if api_context.get('amount', False):
                domain += [('amount_total', '=', api_context['amount'])]
            if api_context.get('pnr', False):
                domain += [('pnr', 'ilike', api_context['pnr']), ('pnr', '!=', False)]
            if api_context.get('state', False):
                if api_context['state'] != 'all':
                    if user_obj.agent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id]:
                        # If COR POR then show bill only
                        domain.append(('state', 'in', ['bill', 'bill2']))
                    else:
                        domain.append(('state', '=', api_context['state']))
                else:
                    domain.append(('state', 'in', ['draft', 'confirm', 'bill', 'bill2']))
            if api_context.get('name', False):
                domain += [('name', 'ilike', api_context['name'])]
            if api_context.get('ref_name', False):
                domain += [('origin', 'ilike', api_context['ref_name'])]
            if api_context.get('contact_name', False):
                domain += ['|',('contact_id.first_name', 'ilike', api_context['contact_name']),('contact_id.last_name', 'ilike', api_context['contact_name'])]

            order = api_context.get('order', 'id DESC')
            inv_ids = self.search(domain, limit=limit, offset=offset, order=order)

            response = {
                'error_code': 0,
                'error_msg': '',
                'response': {
                    'agent_invoice': [compute_agent_inv(rec) for rec in inv_ids],
                }
            }

        except Exception as e:
            response = {
                'error_code': 100,
                'error_msg': str(e),
            }

        return response

# class ResPartnerRequest(models.Model):
#     _inherit = 'res.partner.request'
#
#     agent_invoice_ids = fields.One2many('tt.agent.invoice', 'registration_id', 'Invoice(s)')
#
# class RequestPayment(models.Model):
#     _inherit = 'tt.request.payment'
#
#     agent_inv_id = fields.Many2one('tt.agent.invoice', string='Agent Inv.')
#
#     @api.one
#     def create_agent_invoice(self):
#         def prepare_agent_invoice(cust_obj):
#             return {
#                 'origin': 'Registration ' + self.request_id.name,
#                 'agent_id': self.request_id.reference_id.id,
#                 'sub_agent_id': self.request_id.reference_id.id,
#                 'contact_id': cust_obj.id,
#                 'payment_term_id': False,
#             }
#
#         Invoice = self.env['tt.agent.invoice']
#         InvoiceLine = self.env['tt.agent.invoice.line']
#         cust_obj = self.env['tt.customer.details'].create({
#             'first_name': self.request_id.partner_id.name.split(' ')[:-1],
#             'last_name': self.request_id.partner_id.name.split(' ')[-1:],
#             'mobile': self.request_id.partner_id.mobile,
#             'email': self.request_id.partner_id.email,
#         })
#         invoice = Invoice.create(prepare_agent_invoice(cust_obj))
#         doc_name = self.name and self.name or ''
#         values_line = {
#             'name': 'Registration ' + self.request_id.agent_type_id.name + ' ' + self.request_id.name + ':' + doc_name,
#             'price_unit': self.request_id.total_fee,
#             'quantity': 1,
#         }
#         values_line.update({'invoice_id': invoice.id})
#         InvoiceLine.sudo().create(values_line)
#         return invoice.id
#
#     def action_paid(self):
#         super(RequestPayment, self).action_paid()
#         self.agent_inv_id = self.create_agent_invoice()
#         self.agent_inv_id.registration_id = self.request_id.id
