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
    new_pnr = fields.Char('New PNR')
    reschedule_type = fields.Selection([('reschedule', 'Reschedule'), ('upgrade', 'Upgrade Service'),
                                        ('reroute', 'Reroute'), ('seat', 'Request Seat'),
                                        ('corename', 'Core Name'), ('ssr', 'SSR')
                                        ], 'Reissue Type', default='reschedule',
                                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                       readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.reschedule')
        if 'service_type' in vals_list:
            vals_list['service_type'] = self.parse_service_type(vals_list['service_type'])

        return super(TtReschedule, self).create(vals_list)

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

