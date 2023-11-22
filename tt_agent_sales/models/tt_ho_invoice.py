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

    ho_invoice_id = fields.Integer('After Sales ID')
    ho_invoice_model = fields.Char('After Sales Model')

class AgentInvoiceInh(models.Model):
    _name = 'tt.ho.invoice'
    _inherit = 'tt.agent.invoice'
    _description = 'HO Invoice'
    _order = 'id desc'

    def _get_ho_invoice_model_domain(self):
        return [('ho_invoice_model', '=', self._name)]

    invoice_line_ids = fields.One2many('tt.ho.invoice.line', 'invoice_id', 'Invoice Line', readonly=True,
                                       states={'draft': [('readonly', False)]})
    payment_ids = fields.One2many('tt.payment.invoice.rel', 'ho_invoice_id', 'Payments',
                                  states={'paid': [('readonly', True)]})

    ledger_ids = fields.One2many('tt.ledger', 'ho_invoice_id', 'Ledger',
                                 readonly=True, states={'draft': [('readonly', False)]},
                                 domain=_get_ho_invoice_model_domain)
    is_use_credit_limit = fields.Boolean(default=False)

    total_after_tax = fields.Monetary('Total (After Fee)', compute="_compute_total_tax", store=True)

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
                    'filename': '%s.pdf' % self.name,
                    'file_reference': 'HO Invoice',
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

    def recompute_agent_nta(self):
        ## recompute for state bill & bill2
        ho_invoice_objs = self.search([('state','in',['bill', 'bill2'])])
        for ho_invoice_obj in ho_invoice_objs:
            temp_ho_obj = None
            for ho_invoice_line_obj in ho_invoice_obj.invoice_line_ids:
                ## hapus invoice line detail record
                ho_invoice_line_obj.invoice_line_detail_ids.unlink()
                ## create invoice line detail record
                book_obj = self.env[ho_invoice_line_obj.res_model_resv].browse(ho_invoice_line_obj.res_id_resv)
                total_price = 0
                commission_list = {}
                is_use_credit_limit = True  ## asumsi yang di recompute yang bayar pakai credit limit
                temp_ho_obj = book_obj.agent_id.ho_id
                if ho_invoice_line_obj.res_model_resv == 'tt.reservation.hotel':
                    for idx, room_obj in enumerate(book_obj.room_detail_ids):
                        meal = room_obj.meal_type or 'Room Only'
                        price_unit = room_obj.sale_price
                        for price_obj in book_obj.sale_service_charge_ids:
                            if price_obj.charge_type == 'RAC' and price_obj.charge_code != 'csc':
                                if is_use_credit_limit:
                                    if not price_obj.commission_agent_id:
                                        agent_id = book_obj.agent_id.id
                                    else:
                                        agent_id = price_obj.commission_agent_id.id
                                    if book_obj.agent_id.id != agent_id:
                                        if agent_id not in commission_list:
                                            commission_list[agent_id] = 0
                                        commission_list[agent_id] += price_obj.amount * -1
                                    else:
                                        price_unit += price_obj.amount
                                elif price_obj.commission_agent_id != (temp_ho_obj and temp_ho_obj or False):
                                    price_unit += price_obj.amount
                        ## FARE
                        self.env['tt.ho.invoice.line.detail'].create({
                            'desc': room_obj.room_name + ' (' + meal + ') ',
                            'invoice_line_id': ho_invoice_line_obj.id,
                            'price_unit': price_unit,
                            'quantity': 1,
                            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                            'commission_agent_id': self.agent_id.id
                        })
                        total_price += price_unit

                    ## RAC
                    for rec in commission_list:
                        self.env['tt.ho.invoice.line.detail'].create({
                            'desc': "Commission",
                            'price_unit': commission_list[rec],
                            'quantity': 1,
                            'invoice_line_id': ho_invoice_line_obj.id,
                            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                            'commission_agent_id': rec,
                            'is_commission': True
                        })
                else:
                    for psg in book_obj.passenger_ids:
                        desc_text = '%s, %s' % (' '.join((psg.first_name or '', psg.last_name or '')), psg.title or '')
                        price_unit = 0

                        for cost_charge in psg.cost_service_charge_ids:
                            if cost_charge.charge_type not in ['DISC', 'RAC'] and cost_charge.charge_code != 'csc':
                                price_unit += cost_charge.amount
                            elif cost_charge.charge_type == 'RAC' and cost_charge.charge_code != 'csc':
                                if is_use_credit_limit:
                                    if not cost_charge.commission_agent_id:
                                        agent_id = book_obj.agent_id.id
                                    else:
                                        agent_id = cost_charge.commission_agent_id.id
                                    if book_obj.agent_id.id != agent_id:
                                        if agent_id not in commission_list:
                                            commission_list[agent_id] = 0
                                        commission_list[agent_id] += cost_charge.amount * -1
                                    else:
                                        price_unit += cost_charge.amount
                                elif cost_charge.commission_agent_id != (temp_ho_obj and temp_ho_obj or False):
                                    price_unit += cost_charge.amount
                        ### FARE
                        self.env['tt.ho.invoice.line.detail'].create({
                            'desc': desc_text,
                            'price_unit': price_unit,
                            'quantity': 1,
                            'invoice_line_id': ho_invoice_line_obj.id,
                            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                            'commission_agent_id': self.agent_id.id
                        })
                        total_price += price_unit

                    ## RAC
                    for rec in commission_list:
                        self.env['tt.ho.invoice.line.detail'].create({
                            'desc': "Commission",
                            'price_unit': commission_list[rec],
                            'quantity': 1,
                            'invoice_line_id': ho_invoice_line_obj.id,
                            'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                            'commission_agent_id': rec,
                            'is_commission': True
                        })

            ## hapus payment record
            ho_invoice_obj.payment_ids.unlink()
            ## create payment record
            acq_obj = False
            ho_payment_vals = {
                'ho_id': temp_ho_obj and temp_ho_obj.id or False,
                'agent_id': self.agent_id.id,
                'acquirer_id': acq_obj,
                'real_total_amount': ho_invoice_obj.grand_total,
                # 'confirm_uid': data['co_uid'],
                'confirm_date': datetime.now(),
            }
            ho_payment_obj = self.env['tt.payment'].create(ho_payment_vals)
            self.env['tt.payment.invoice.rel'].create({
                'ho_invoice_id': ho_invoice_obj.id,
                'payment_id': ho_payment_obj.id,
                'pay_amount': ho_invoice_obj.grand_total
            })

