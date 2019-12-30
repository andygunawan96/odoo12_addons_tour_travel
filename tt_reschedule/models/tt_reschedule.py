from odoo import api,models,fields
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from ...tools import variables


class TtReschedule(models.Model):
    _name = "tt.reschedule"
    _inherit = "tt.refund"
    _description = "Reschedule Model"
    _order = 'id DESC'

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('sent', 'Sent'), ('validate', 'Validated'), ('approve', 'Approved'),
                              ('done', 'Done'), ('cancel', 'Canceled'), ('expired', 'Expired')], 'Status',
                             default='draft',
                             help=" * The 'Draft' status is used for Agent to make reschedule request.\n"
                                  " * The 'Confirmed' status is used for HO to confirm and process the request.\n"
                                  " * The 'Sent' status is used for HO to send the request back to Agent with a set price.\n"
                                  " * The 'Validated' status is used for Agent to final check and validate the request.\n"
                                  " * The 'Approved' status is used for HO to approve and process the request.\n"
                                  " * The 'Done' status means the agent's request has been rescheduled.\n"
                                  " * The 'Canceled' status is used for Agent or HO to cancel the request.\n"
                                  " * The 'Expired' status means the request has been expired.\n")
    reschedule_amount = fields.Integer('Estimated Amount', default=0, required=True, readonly=True)
    new_pnr = fields.Char('New PNR', readonly=True, compute="_compute_new_pnr")
    invoice_line_ids = fields.One2many('tt.agent.invoice.line', 'res_id_resv', 'Invoice', domain=[('res_model_resv','=', 'tt.reschedule')])
    old_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_old_segment_rel', 'reschedule_id', 'segment_id', string='Old Segments',
                                      readonly=True)
    new_segment_ids = fields.Many2many('tt.segment.airline', 'tt_reschedule_new_segment_rel', 'reschedule_id', 'segment_id', string='New Segments',
                                  readonly=True, states={'draft': [('readonly', False)]})
    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('revalidate', 'Upgrade Service'),
                                        ('reissued', 'Reroute'), ('upgrade', 'Upgrade')], 'Reschedule Type', default='reschedule',
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                       readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.reschedule')
        if 'service_type' in vals_list:
            vals_list['service_type'] = self.parse_service_type(vals_list['service_type'])

        return super(TtReschedule, self).create(vals_list)

    @api.depends('new_segment_ids')
    @api.onchange('new_segment_ids')
    def _compute_admin_fee_id(self):
        for rec in self:
            new_pnr = ''
            for rec2 in rec.new_segment_ids:
                new_pnr += rec2.pnr + ','
            rec.new_pnr = new_pnr and new_pnr[:-1] or ''

    @api.depends('reschedule_type')
    @api.onchange('reschedule_type')
    def _compute_admin_fee_id(self):
        for rec in self:
            rec.admin_fee_id = self.env.ref('tt_accounting.admin_fee_reschedule').id

    @api.depends('admin_fee_id', 'reschedule_amount')
    @api.onchange('admin_fee_id', 'reschedule_amount')
    def _compute_admin_fee(self):
        for rec in self:
            if rec.admin_fee_id:
                if rec.admin_fee_id.type == 'amount':
                    pnr_amount = 0
                    book_obj = self.env[rec.res_model].browse(int(rec.res_id))
                    for rec2 in book_obj.provider_booking_ids:
                        pnr_amount += 1
                else:
                    pnr_amount = 1
                rec.admin_fee = rec.admin_fee_id.get_final_adm_fee(rec.reschedule_amount, pnr_amount)
            else:
                rec.admin_fee = 0

    @api.depends('admin_fee', 'reschedule_amount')
    @api.onchange('admin_fee', 'reschedule_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.reschedule_amount - rec.admin_fee

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

        self.write({
            'state': 'validate',
            'validate_uid': self.env.user.id,
            'validate_date': datetime.now(),
            'final_admin_fee': self.admin_fee,
        })

    def approve_reschedule_from_button(self):
        if self.state != 'validate':
            raise UserError("Cannot Approve because state is not 'Validated'.")

        self.write({
            'state': 'approve',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now()
        })

    def action_done(self):
        pass

    def cancel_reschedule_from_button(self):
        if self.state in ['validate', 'approve']:
            if not self.cancel_message:
                raise UserError("Please fill the cancellation message!")
        self.write({
            'state': 'cancel',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now()
        })

