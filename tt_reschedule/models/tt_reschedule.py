from odoo import api,models,fields,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import base64
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback,pytz

_logger = logging.getLogger(__name__)


class Ledger(models.Model):
    _inherit = 'tt.ledger'

    reschedule_id = fields.Many2one('tt.reschedule', 'After Sales')


class TtRescheduleChanges(models.Model):
    _name = "tt.reschedule.changes"
    _description = "After Sales Model"

    name = fields.Char('Field Name', readonly=True)
    seg_sequence = fields.Integer('Segment Sequence', readonly=True)
    old_value = fields.Html('Old Value', readonly=True)
    new_value = fields.Html('New Value', readonly=True)
    reschedule_id = fields.Many2one('tt.reschedule', 'After Sales', readonly=True)


class TtRescheduleLine(models.Model):
    _name = "tt.reschedule.line"
    _description = "After Sales Model"
    _order = 'id DESC'

    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('reroute', 'Reroute'), ('revalidate', 'Revalidate'),
                                        ('reissue', 'Reissue'), ('upgrade', 'Upgrade Service'),
                                        ('addons', 'Addons (Meals, Baggage, Seat, etc)')], 'After Sales Type',
                                       default='reschedule',
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                       readonly=True)
    reschedule_amount = fields.Monetary('Expected After Sales Amount', default=0, required=True, readonly=True,
                                       related='reschedule_amount_ho')
    reschedule_amount_ho = fields.Monetary('Expected After Sales Amount', default=0, required=True, readonly=True,
                                          states={'confirm': [('readonly', False)]})
    real_reschedule_amount = fields.Monetary('Real After Sales Amount from Vendor', default=0, required=True,
                                            readonly=False, states={'draft': [('readonly', True)]})
    reschedule_id = fields.Many2one('tt.reschedule', 'After Sales', readonly=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', required=True)
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id, related='reschedule_id.currency_id')
    agent_id = fields.Many2one('tt.agent', 'Agent', related='reschedule_id.agent_id')
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True)
    admin_fee_id = fields.Many2one('tt.master.admin.fee', 'Admin Fee Type', domain=[('id', '=', -1)], readonly=True, states={'confirm': [('readonly', False)]})
    admin_fee = fields.Monetary('Admin Fee Amount', default=0, readonly=True, compute="_compute_admin_fee")
    admin_fee_ho = fields.Monetary('Admin Fee (HO)', default=0, readonly=True, compute="_compute_admin_fee")
    admin_fee_agent = fields.Monetary('Admin Fee (Agent)', default=0, readonly=True, compute="_compute_admin_fee")
    total_amount = fields.Monetary('Total Amount', default=0, readonly=True, compute="_compute_total_amount")
    sequence = fields.Integer('Sequence', default=50, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('final', 'Finalization'),
                              ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status',
                             default='confirm', related='reschedule_id.state', store=True)
    admin_fee_dummy = fields.Boolean('Generate Admin Fee Options')
    is_po_required = fields.Boolean('Is PO Required', readonly=True, compute='compute_is_po_required')
    letter_of_guarantee_ids = fields.One2many('tt.letter.guarantee', 'res_id', 'Purchase Order(s)', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('admin_fee_dummy'):
            vals.pop('admin_fee_dummy')
        return super(TtRescheduleLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('admin_fee_dummy'):
            vals.pop('admin_fee_dummy')
        return super(TtRescheduleLine, self).write(vals)

    @api.depends('admin_fee_id', 'reschedule_amount', 'reschedule_id')
    @api.onchange('admin_fee_id', 'reschedule_amount', 'reschedule_id')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.admin_fee_id:
                book_obj = self.env[rec.reschedule_id.res_model].browse(int(rec.reschedule_id.res_id))
                if book_obj:
                    pnr_amount = 0
                    for rec2 in book_obj.provider_booking_ids:
                        pnr_amount += 1

                    pax_amount = 0
                    for rec2 in book_obj.passenger_ids:
                        pax_amount += 1

                    admin_fee_ho = rec.admin_fee_id.get_final_adm_fee_ho(rec.reschedule_amount, pnr_amount, pax_amount)
                    admin_fee_agent = rec.admin_fee_id.get_final_adm_fee_agent(rec.reschedule_amount, pnr_amount, pax_amount)

                    rec.admin_fee_ho = admin_fee_ho
                    rec.admin_fee_agent = admin_fee_agent
                    rec.admin_fee = admin_fee_ho + admin_fee_agent
                else:
                    rec.admin_fee_ho = 0
                    rec.admin_fee_agent = 0
                    rec.admin_fee = 0
            else:
                rec.admin_fee_ho = 0
                rec.admin_fee_agent = 0
                rec.admin_fee = 0

    @api.depends('admin_fee', 'reschedule_amount')
    @api.onchange('admin_fee', 'reschedule_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.reschedule_amount + rec.admin_fee

    @api.onchange('admin_fee_dummy')
    def get_admin_fee_domain(self):
        agent_type_adm_ids = self.reschedule_id.agent_id.agent_type_id.admin_fee_ids.ids
        agent_adm_ids = self.reschedule_id.agent_id.admin_fee_ids.ids
        return {'domain': {
            'admin_fee_id': [('after_sales_type', '=', 'after_sales'), '&', '|',
                 ('agent_type_access_type', '=', 'all'), '|', '&', ('agent_type_access_type', '=', 'allow'),
                 ('id', 'in', agent_type_adm_ids), '&', ('agent_type_access_type', '=', 'restrict'),
                 ('id', 'not in', agent_type_adm_ids), '|', ('agent_access_type', '=', 'all'), '|', '&',
                 ('agent_access_type', '=', 'allow'), ('id', 'in', agent_adm_ids), '&',
                 ('agent_access_type', '=', 'restrict'), ('id', 'not in', agent_adm_ids)]
        }}

    @api.onchange('provider_id')
    def compute_is_po_required(self):
        for rec in self:
            if rec.provider_id.is_using_po:
                rec.is_po_required = True
            else:
                rec.is_po_required = False

    def generate_po(self):
        if self.reschedule_id.state == 'final':
            if not self.env.user.has_group('tt_base.group_tt_accounting_manager'):
                hour_passed = (datetime.now() - self.reschedule_id.final_date).seconds / 3600
                if hour_passed > 1:
                    raise UserError('Failed to generate Purchase Order. It has been more than 1 hour after this after sales was finalized, please contact Accounting Manager to generate Purchase Order.')

            if self.real_reschedule_amount <= 0:
                raise UserError('Please set Real After Sales Amount from Vendor.')

            po_exist = self.env['tt.letter.guarantee'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('type', '=', 'po')])
            if po_exist:
                raise UserError('Purchase Order for this reschedule line is already exist.')
            else:
                desc_str = str(dict(self._fields['reschedule_type'].selection).get(self.reschedule_type)) + '<br/>'
                pax_desc_str = ''
                pax_amount = 0
                for rec in self.reschedule_id.passenger_ids:
                    pax_amount += 1
                    pax_desc_str += '%s. %s<br/>' % (rec.title, rec.name)
                price_per_mul = self.real_reschedule_amount / pax_amount
                po_vals = {
                    'res_model': self._name,
                    'res_id': self.id,
                    'provider_id': self.provider_id.id,
                    'type': 'po',
                    'parent_ref': self.reschedule_id.name,
                    'pax_description': pax_desc_str,
                    'multiplier': 'Pax',
                    'multiplier_amount': pax_amount,
                    'quantity': 'Qty',
                    'quantity_amount': 1,
                    'currency_id': self.currency_id.id,
                    'price_per_mult': price_per_mul,
                    'price': self.real_reschedule_amount,
                }
                new_po_obj = self.env['tt.letter.guarantee'].create(po_vals)
                ref_num = ''
                if self.reschedule_id.pnr and self.reschedule_id.referenced_pnr:
                    if self.reschedule_id.pnr == self.reschedule_id.referenced_pnr:
                        ref_num = self.reschedule_id.pnr
                    else:
                        ref_num = self.reschedule_id.referenced_pnr + ' to ' + self.reschedule_id.pnr
                line_vals = {
                    'lg_id': new_po_obj.id,
                    'ref_number': ref_num,
                    'description': desc_str
                }
                self.env['tt.letter.guarantee.lines'].create(line_vals)
        else:
            raise UserError('You can only generate Purchase Order if this after sales state is "Finalized".')


class TtReschedule(models.Model):
    _name = "tt.reschedule"
    _inherit = "tt.refund"
    _description = "After Sales Model"
    _order = 'id DESC'

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('final', 'Finalization'),
                              ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status',
                             default='draft',
                             help=" * The 'Draft' status is used for Agent to make after sales request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set price.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request.\n"
                                  " * The 'Finalization' status is used for HO to finalize and process the request.\n"
                                  " * The 'Done' status means the agent's request has been done. Therefore the agent's balance has been cut.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n"
                                  " * The 'Expired' status means the request has been expired.\n")

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    ledger_ids = fields.One2many('tt.ledger', 'reschedule_id', 'Ledger(s)')
    adjustment_ids = fields.One2many('tt.adjustment', 'res_id', 'Adjustment', readonly=True, domain=_get_res_model_domain)
    pnr = fields.Char('New PNR', readonly=True, compute="_compute_new_pnr")
    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=','tt.reschedule')], readonly=True)
    state_invoice = fields.Selection([('wait', 'Waiting'), ('partial', 'Partial'), ('full', 'Full')],
                                     'Invoice Status', help="Agent Invoice status", default='wait',
                                     readonly=True, compute='set_agent_invoice_state')
    old_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_old_segment_rel', 'reschedule_id', 'segment_id', string='Old Segments',
                                       readonly=True)
    new_segment_ids = fields.Many2many('tt.segment.reschedule', 'tt_reschedule_new_segment_rel', 'reschedule_id', 'segment_id', string='New Segments',
                                       readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.Many2many('tt.reservation.passenger.airline', 'tt_reschedule_passenger_rel', 'reschedule_id', 'passenger_id',
                                     readonly=True)
    payment_acquirer_id = fields.Many2one('payment.acquirer', 'Payment Acquirer', domain="[('agent_id', '=', agent_id)]", readonly=False, states={'done': [('readonly', True)]})
    reschedule_amount = fields.Monetary('Expected After Sales Amount', default=0, required=True, readonly=True, compute='_compute_reschedule_amount')
    real_reschedule_amount = fields.Monetary('Real After Sales Amount from Vendor', default=0, readonly=True,
                                         compute='_compute_real_reschedule_amount')
    reschedule_line_ids = fields.One2many('tt.reschedule.line', 'reschedule_id', 'After Sales Line(s)', readonly=True, states={'confirm': [('readonly', False)]})
    reschedule_type_str = fields.Char('After Sales Type', readonly=True, compute='_compute_reschedule_type_str', store=True)
    change_ids = fields.One2many('tt.reschedule.changes', 'reschedule_id', 'Changes', readonly=True)

    printout_reschedule_id = fields.Many2one('tt.upload.center', 'Printout Reschedule', readonly=True)
    created_by_api = fields.Boolean('Created By API', default=False, readonly=True)
    refund_type_id = fields.Many2one('tt.refund.type', 'Refund Type', required=False, readonly=True)

    def get_reschedule_admin_fee_rule(self, agent_id):
        current_refund_env = self.env.ref('tt_accounting.admin_fee_reschedule')
        refund_admin_fee_list = self.env['tt.master.admin.fee'].search([('after_sales_type', '=', 'after_sales')])
        for admin_fee in refund_admin_fee_list:
            if agent_id in admin_fee.agent_ids.ids:
                current_refund_env = admin_fee
                # TODO perlu di break disini atau ambil yg paling trakhir?
        return current_refund_env

    def get_reschedule_fee_amount(self, agent_id, order_number='', order_type='', refund_amount=0, passenger_count=0):
        admin_fee_obj = self.get_reschedule_admin_fee_rule(agent_id)

        pnr_amount = 1
        pax_amount = 1
        if order_number and order_type:
            book_obj = self.env['tt.reservation.'+order_type].search([('name', '=', order_number)], limit=1)

            pnr_amount = len(book_obj.provider_booking_ids.ids)
            pax_amount = len(book_obj.passenger_ids.ids)

        admin_fee_ho = admin_fee_obj.get_final_adm_fee_ho(refund_amount, pnr_amount, pax_amount)
        admin_fee_agent = admin_fee_obj.get_final_adm_fee_agent(refund_amount, pnr_amount, pax_amount)
        admin_fee = admin_fee_ho + admin_fee_agent
        return {
            'admin_fee_ho': admin_fee_ho,
            'admin_fee_agent': admin_fee_agent,
            'admin_fee': admin_fee,
        }

    def compute_admin_fee_api(self, req):
        reschedule_fee = self.get_reschedule_fee_amount(req['agent_id'], req['order_number'], req['order_type'], req['refund_amount'], req.get('passenger_count'))
        return reschedule_fee['admin_fee']

    @api.depends('invoice_line_ids')
    def set_agent_invoice_state(self):

        states = []

        for rec in self.invoice_line_ids:
            states.append(rec.state)

        if all(state == 'draft' for state in states) or not states:
            self.state_invoice = 'wait'
        elif all(state != 'draft' for state in states):
            self.state_invoice = 'full'
        elif any(state != 'draft' for state in states):
            self.state_invoice = 'partial'

    @api.depends('new_segment_ids')
    @api.onchange('new_segment_ids')
    def _compute_new_pnr(self):
        for rec in self:
            pnr = ''
            for rec2 in rec.new_segment_ids:
                pnr += rec2.pnr and rec2.pnr + ',' or ''
            rec.pnr = pnr and pnr[:-1] or ''

    @api.depends('reschedule_line_ids')
    @api.onchange('reschedule_line_ids')
    def _compute_admin_fee(self):
        for rec in self:
            adm_fee = 0
            adm_fee_ho = 0
            adm_fee_agent = 0
            for rec2 in rec.reschedule_line_ids:
                adm_fee += rec2.admin_fee
                adm_fee_ho += rec2.admin_fee_ho
                adm_fee_agent += rec2.admin_fee_agent
            rec.admin_fee = adm_fee
            rec.admin_fee_ho = adm_fee_ho
            rec.admin_fee_agent = adm_fee_agent

    @api.depends('reschedule_line_ids')
    @api.onchange('reschedule_line_ids')
    def _compute_reschedule_amount(self):
        for rec in self:
            resch_amount = 0
            for rec2 in rec.reschedule_line_ids:
                resch_amount += rec2.reschedule_amount
            rec.reschedule_amount = resch_amount

    @api.depends('reschedule_line_ids')
    @api.onchange('reschedule_line_ids')
    def _compute_real_reschedule_amount(self):
        for rec in self:
            resch_amount = 0
            for rec2 in rec.reschedule_line_ids:
                resch_amount += rec2.real_reschedule_amount
            rec.real_reschedule_amount = resch_amount

    @api.depends('admin_fee', 'reschedule_amount')
    @api.onchange('admin_fee', 'reschedule_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.reschedule_amount + rec.admin_fee

    @api.depends('reschedule_line_ids')
    @api.onchange('reschedule_line_ids')
    def _compute_reschedule_type_str(self):
        for rec in self:
            temp_str = ''
            for rec2 in rec.reschedule_line_ids:
                temp_str += str(dict(rec2._fields['reschedule_type'].selection).get(rec2.reschedule_type)) + ', '
            rec.reschedule_type_str = temp_str and temp_str[:-2] or ''

    def set_to_confirm(self):
        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
            'hold_date': False
        })

    def confirm_reschedule_from_button(self):
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        self.write({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })

    def send_reschedule_from_button(self):
        if self.state != 'confirm':
            raise UserError("Cannot Send because state is not 'confirm'.")

        self.write({
            'state': 'sent',
            'sent_uid': self.env.user.id,
            'sent_date': datetime.now(),
        })

    def validate_reschedule_from_button(self):
        if self.state != 'sent':
            raise UserError("Cannot Validate because state is not 'Sent'.")

        for rec in self.reschedule_line_ids:
            credit = rec.reschedule_amount + rec.admin_fee_ho + rec.admin_fee_agent
            debit = 0
            ledger_type = rec.reschedule_type == 'addons' and 8 or 7
            temp_desc = str(dict(rec._fields['reschedule_type'].selection).get(rec.reschedule_type)) + '\n'
            self.env['tt.ledger'].create_ledger_vanilla(
                self._name,
                self.id,
                'After Sales : %s' % (self.name),
                self.name,
                datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                ledger_type,
                self.currency_id.id,
                self.env.user.id,
                self.agent_id.id,
                False,
                debit,
                credit,
                temp_desc + ' for %s (PNR: from %s to %s)' % (self.referenced_document, self.referenced_pnr, self.pnr),
                **{'reschedule_id': self.id}
            )

            if rec.admin_fee_ho:
                ho_agent = self.env.ref('tt_base.rodex_ho')
                credit = 0
                debit = rec.admin_fee_ho
                ledger_type = 6
                self.env['tt.ledger'].sudo().create_ledger_vanilla(
                    self._name,
                    self.id,
                    'After Sales Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    ho_agent and ho_agent.id or False,
                    False,
                    debit,
                    credit,
                    temp_desc + ' Admin Fee for %s (PNR: from %s to %s)' % (self.referenced_document, self.referenced_pnr, self.pnr),
                    **{'reschedule_id': self.id}
                )

            if rec.admin_fee_agent:
                credit = 0
                debit = rec.admin_fee_agent
                ledger_type = 3
                self.env['tt.ledger'].sudo().create_ledger_vanilla(
                    self._name,
                    self.id,
                    'After Sales Agent Admin Fee: %s' % (self.name),
                    self.name,
                    datetime.now(pytz.timezone('Asia/Jakarta')).date(),
                    ledger_type,
                    self.currency_id.id,
                    self.env.user.id,
                    self.agent_id.id,
                    False,
                    debit,
                    credit,
                    temp_desc + ' Agent Admin Fee for %s (PNR: from %s to %s)' % (self.referenced_document, self.referenced_pnr, self.pnr),
                    **{'reschedule_id': self.id}
                )

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'final_admin_fee': self.admin_fee,
        })

    def finalize_reschedule_from_button(self):
        if self.state != 'validate':
            raise UserError("Cannot Finalize because state is not 'Validated'.")

        for rec in self.new_segment_ids:
            if not rec.pnr:
                raise UserError("PNR in New Segments must be filled!")

        self.write({
            'state': 'final',
            'final_uid': self.env.user.id,
            'final_date': datetime.now()
        })

    def check_po_required(self):
        required = False
        for rec in self.reschedule_line_ids:
            if rec.provider_id.is_using_po:
                if not rec.letter_of_guarantee_ids:
                    required = True
        return required

    def action_done(self):
        if self.state != 'final':
            raise UserError("Cannot Approve because state is not 'Finalized'.")
        if self.check_po_required():
            raise UserError(_('Purchase Order is required in one Line or more. Please check all Line(s)!'))

        self.action_create_invoice()
        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now()
        })

    def cancel_reschedule_from_button(self):
        if self.state in ['validate', 'final']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
            for rec in self.ledger_ids:
                rec.reverse_ledger()

        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

    def action_create_invoice(self):
        invoice_id = False

        if not invoice_id:
            invoice_id = self.env['tt.agent.invoice'].create({
                'booker_id': self.booker_id.id,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'customer_parent_type_id': self.customer_parent_type_id.id,
                'state': 'confirm',
                'confirmed_uid': self.env.user.id,
                'confirmed_date': datetime.now()
            })

        desc_str = self.name + ' ('
        if self.referenced_document:
            desc_str += 'After Sales for ' + self.referenced_document + '); '
        else:
            desc_str += '); '

        if self.passenger_ids:
            desc_str += 'Passengers: '
            for rec in self.passenger_ids:
                desc_str += rec.title + ' ' + rec.name + ', '
            desc_str = desc_str[:-2]
            desc_str += ';'

        inv_line_obj = self.env['tt.agent.invoice.line'].create({
            'res_model_resv': self._name,
            'res_id_resv': self.id,
            'invoice_id': invoice_id.id,
            'desc': desc_str
        })

        invoice_line_id = inv_line_obj.id

        for rec in self.reschedule_line_ids:
            inv_line_obj.write({
                'invoice_line_detail_ids': [(0, 0, {
                    'desc': str(dict(rec._fields['reschedule_type'].selection).get(rec.reschedule_type)),
                    'price_unit': rec.total_amount,
                    'quantity': 1,
                    'invoice_line_id': invoice_line_id,
                })]
            })

        ##membuat payment dalam draft
        payment_obj = self.env['tt.payment'].create({
            'agent_id': self.agent_id.id,
            'acquirer_id': self.payment_acquirer_id and self.payment_acquirer_id.id or False,
            'real_total_amount': inv_line_obj.total,
            'customer_parent_id': self.customer_parent_id.id,
            'state': 'confirm',
            'payment_date': datetime.now(),
            'reference': self.name,
            'confirm_uid': self.confirm_uid.id
        })

        self.env['tt.payment.invoice.rel'].create({
            'invoice_id': invoice_id.id,
            'payment_id': payment_obj.id,
            'pay_amount': inv_line_obj.total,
        })

    def generate_changes(self):
        for rec in self.change_ids:
            rec.sudo().unlink()
        unchecked_fields = ['pnr', 'create_uid', 'create_date', 'write_uid', 'write_date', 'old_id', 'sequence', 'seat_ids', 'segment_addons_ids', 'passenger_ids',
                            'id', 'journey_id', 'booking_id', 'leg_ids', '__last_update']
        for idx, rec in enumerate(self.new_segment_ids):
            new_seg_dict = rec.read()
            old_seg_dict = self.old_segment_ids[idx].read()
            for key, val in new_seg_dict[0].items():
                if key not in unchecked_fields:
                    if val != old_seg_dict[0][key]:
                        change_vals = {
                            'reschedule_id': self.id,
                            'seg_sequence': rec.old_id,
                            'name': rec._fields[str(key)].string,
                            'old_value': old_seg_dict[0][key],
                            'new_value': val
                        }
                        self.env['tt.reschedule.changes'].sudo().create(change_vals)
            if rec.seat_ids:
                if self.old_segment_ids[idx].seat_ids:
                    old_seat_str = ''
                    for rec2 in self.old_segment_ids[idx].seat_ids:
                        if rec2.passenger_id:
                            old_seat_str += 'Passenger: ' + (rec2.passenger_id.title and rec2.passenger_id.title + ' ' or '') + (rec2.passenger_id.name and rec2.passenger_id.name or '-') + '<br/>'
                            old_seat_str += 'Seat: ' + (rec2.seat and rec2.seat or 'No Seat') + '<br/><br/>'
                    new_seat_str = ''
                    for rec2 in rec.seat_ids:
                        if rec2.passenger_id:
                            new_seat_str += 'Passenger: ' + (rec2.passenger_id.title and rec2.passenger_id.title + ' ' or '') + (rec2.passenger_id.name and rec2.passenger_id.name or '-') + '<br/>'
                            new_seat_str += 'Seat: ' + (rec2.seat and rec2.seat or 'No Seat') + '<br/><br/>'

                    if old_seat_str != new_seat_str:
                        change_vals = {
                            'reschedule_id': self.id,
                            'seg_sequence': rec.old_id,
                            'name': 'Seats',
                            'old_value': old_seat_str,
                            'new_value': new_seat_str
                        }
                        self.env['tt.reschedule.changes'].sudo().create(change_vals)
                else:
                    new_seat_str = ''
                    for rec2 in rec.seat_ids:
                        if rec2.passenger_id:
                            new_seat_str += 'Passenger: ' + (rec2.passenger_id.title and rec2.passenger_id.title + ' ' or '') + (rec2.passenger_id.name and rec2.passenger_id.name or '-') + '<br/>'
                            new_seat_str += 'Seat: ' + (rec2.seat and rec2.seat or 'No Seat') + '<br/><br/>'
                    change_vals = {
                        'reschedule_id': self.id,
                        'seg_sequence': rec.old_id,
                        'name': 'Seats',
                        'old_value': 'Standard Seat',
                        'new_value': new_seat_str
                    }
                    self.env['tt.reschedule.changes'].sudo().create(change_vals)
            else:
                if self.old_segment_ids[idx].seat_ids:
                    old_seat_str = ''
                    for rec2 in self.old_segment_ids[idx].seat_ids:
                        if rec2.passenger_id:
                            old_seat_str += 'Passenger: ' + (rec2.passenger_id.title and rec2.passenger_id.title + ' ' or '') + (rec2.passenger_id.name and rec2.passenger_id.name or '-') + '<br/>'
                            old_seat_str += 'Seat: ' + (rec2.seat and rec2.seat or 'No Seat') + '<br/><br/>'
                    change_vals = {
                        'reschedule_id': self.id,
                        'seg_sequence': rec.old_id,
                        'name': 'Seats',
                        'old_value': old_seat_str,
                        'new_value': 'Standard Seat'
                    }
                    self.env['tt.reschedule.changes'].sudo().create(change_vals)

            if rec.segment_addons_ids:
                if self.old_segment_ids[idx].segment_addons_ids:
                    old_addons_str = ''
                    for rec2 in self.old_segment_ids[idx].segment_addons_ids:
                        old_addons_str += 'Detail Code: ' + (rec2.detail_code and rec2.detail_code or '-') + '<br/>'
                        old_addons_str += 'Detail Type: ' + (rec2.detail_type and rec2.detail_type or '-') + '<br/>'
                        old_addons_str += 'Detail Name: ' + (rec2.detail_name and rec2.detail_name or '-') + '<br/>'
                        old_addons_str += 'Amount: ' + (rec2.amount and str(rec2.amount) or '-') + '<br/>'
                        old_addons_str += 'Unit: ' + (rec2.unit and rec2.unit or '-') + '<br/>'
                        old_addons_str += 'Description: ' + (rec2.description and rec2.description or '-') + '<br/><br/>'
                    new_addons_str = ''
                    for rec2 in rec.segment_addons_ids:
                        new_addons_str += 'Detail Code: ' + (rec2.detail_code and rec2.detail_code or '-') + '<br/>'
                        new_addons_str += 'Detail Type: ' + (rec2.detail_type and rec2.detail_type or '-') + '<br/>'
                        new_addons_str += 'Detail Name: ' + (rec2.detail_name and rec2.detail_name or '-') + '<br/>'
                        new_addons_str += 'Amount: ' + (rec2.amount and str(rec2.amount) or '-') + '<br/>'
                        new_addons_str += 'Unit: ' + (rec2.unit and rec2.unit or '-') + '<br/>'
                        new_addons_str += 'Description: ' + (rec2.description and rec2.description or '-') + '<br/><br/>'

                    if old_addons_str != new_addons_str:
                        change_vals = {
                            'reschedule_id': self.id,
                            'seg_sequence': rec.old_id,
                            'name': 'Addons',
                            'old_value': old_addons_str,
                            'new_value': new_addons_str
                        }
                        self.env['tt.reschedule.changes'].sudo().create(change_vals)
                else:
                    new_addons_str = ''
                    for rec2 in rec.segment_addons_ids:
                        new_addons_str += 'Detail Code: ' + (rec2.detail_code and rec2.detail_code or '-') + '<br/>'
                        new_addons_str += 'Detail Type: ' + (rec2.detail_type and rec2.detail_type or '-') + '<br/>'
                        new_addons_str += 'Detail Name: ' + (rec2.detail_name and rec2.detail_name or '-') + '<br/>'
                        new_addons_str += 'Amount: ' + (rec2.amount and str(rec2.amount) or '-') + '<br/>'
                        new_addons_str += 'Unit: ' + (rec2.unit and rec2.unit or '-') + '<br/>'
                        new_addons_str += 'Description: ' + (rec2.description and rec2.description or '-') + '<br/><br/>'
                    change_vals = {
                        'reschedule_id': self.id,
                        'seg_sequence': rec.old_id,
                        'name': 'Addons',
                        'old_value': 'No Addons',
                        'new_value': new_addons_str
                    }
                    self.env['tt.reschedule.changes'].sudo().create(change_vals)
            else:
                if self.old_segment_ids[idx].segment_addons_ids:
                    old_addons_str = ''
                    for rec2 in self.old_segment_ids[idx].segment_addons_ids:
                        old_addons_str += 'Detail Code: ' + (rec2.detail_code and rec2.detail_code or '-') + '<br/>'
                        old_addons_str += 'Detail Type: ' + (rec2.detail_type and rec2.detail_type or '-') + '<br/>'
                        old_addons_str += 'Detail Name: ' + (rec2.detail_name and rec2.detail_name or '-') + '<br/>'
                        old_addons_str += 'Amount: ' + (rec2.amount and str(rec2.amount) or '-') + '<br/>'
                        old_addons_str += 'Unit: ' + (rec2.unit and rec2.unit or '-') + '<br/>'
                        old_addons_str += 'Description: ' + (rec2.description and rec2.description or '-') + '<br/><br/>'
                    change_vals = {
                        'reschedule_id': self.id,
                        'seg_sequence': rec.old_id,
                        'name': 'Addons',
                        'old_value': old_addons_str,
                        'new_value': 'No Addons'
                    }
                    self.env['tt.reschedule.changes'].sudo().create(change_vals)

    def print_reschedule_changes(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        reschedule_printout_action = self.env.ref('tt_report_common.action_report_printout_reschedule')
        if not self.printout_reschedule_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            # if self.user_id:
            #     co_uid = self.user_id.id
            # else:
            co_uid = self.env.user.id

            pdf_report = reschedule_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = reschedule_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Reschedule %s.pdf' % self.name,
                    'file_reference': 'Reschedule Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_reschedule_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_reschedule_id.url,
        }
        return url
        # return reschedule_printout_id.report_action(self, data=datas)

    def get_reschedule_data(self):
        resv_obj = self.env[self.res_model].browse(self.res_id)
        passenger_list = []
        for rec in self.passenger_ids:
            passenger_list.append(rec.to_dict())
        prov_list = []
        for rec in resv_obj.provider_booking_ids:
            prov_list.append(rec.to_dict())
        old_segments = []
        for rec in self.old_segment_ids:
            temp_seg = rec.to_dict()
            seat_list = []
            for rec2 in rec.seat_ids:
                seat_list.append({
                    'passenger': rec2.passenger_id.title + ' ' + rec2.passenger_id.name,
                    'seat': rec2.seat
                })
            addons_list = []
            for rec2 in rec.segment_addons_ids:
                addons_list.append({
                    'detail_code': rec2.detail_code,
                    'detail_type': rec2.detail_type,
                    'detail_name': rec2.detail_name,
                    'description': rec2.description,
                    'amount': rec2.amount,
                    'sequence': rec2.sequence,
                })
            temp_seg.update({
                'ref_sequence': rec.id,
                'origin_port': rec.origin_id.name,
                'destination_port': rec.destination_id.name,
                'seats': seat_list,
                'addons': addons_list,
            })
            old_segments.append(temp_seg)
        new_segments = []
        for rec in self.new_segment_ids:
            temp_seg = rec.to_dict()
            seat_list = []
            for rec2 in rec.seat_ids:
                seat_list.append({
                    'passenger': rec2.passenger_id.title + ' ' + rec2.passenger_id.name,
                    'seat': rec2.seat
                })
            addons_list = []
            for rec2 in rec.segment_addons_ids:
                addons_list.append({
                    'detail_code': rec2.detail_code,
                    'detail_type': rec2.detail_type,
                    'detail_name': rec2.detail_name,
                    'description': rec2.description,
                    'amount': rec2.amount,
                    'sequence': rec2.sequence,
                })
            temp_seg.update({
                'ref_sequence': rec.old_id,
                'origin_port': rec.origin_id.name,
                'destination_port': rec.destination_id.name,
                'seats': seat_list,
                'addons': addons_list,
            })
            new_segments.append(temp_seg)
        changes = []
        for rec in self.change_ids:
            changes.append({
                'ref_sequence': rec.seg_sequence,
                'name': rec.name,
                'old_value': rec.old_value,
                'new_value': rec.new_value,
            })
        lines = []
        for rec in self.reschedule_line_ids:
            lines.append({
                'after_sales_type': rec.reschedule_type,
                'expected_amount': rec.reschedule_amount_ho,
                'admin_fee': rec.admin_fee,
                'total_amount': rec.total_amount,
            })
        new_vals = {
            'reschedule_number': self.name,
            'agent': self.agent_id.name,
            'agent_type': self.agent_type_id.name,
            'customer_parent': self.customer_parent_id.name,
            'customer_parent_type': self.customer_parent_type_id.name,
            'booker': self.booker_id.name,
            'currency': self.currency_id.name,
            'service_type': self.service_type,
            'direction': resv_obj.direction,
            'sector_type': resv_obj.sector_type,
            'resv_order_number': self.referenced_document,
            'old_pnr': self.referenced_pnr and self.referenced_pnr or '',
            'new_pnr': self.pnr and self.pnr or '',
            'expected_amount': self.reschedule_amount,
            'admin_fee': self.admin_fee,
            'total_amount': self.total_amount,
            'passengers': passenger_list,
            'old_segments': old_segments,
            'new_segments': new_segments,
            'changes': changes,
            'reschedule_lines': lines,
            'provider_bookings': prov_list,
            'created_by_api': self.created_by_api,
            'state': self.state
        }

        return new_vals



