from odoo import api, fields, models, _
from ...tools import variables
from odoo.exceptions import UserError
import logging
import traceback

_logger = logging.getLogger(__name__)

STATE_INVOICE = [
    ('open', 'Open'),
    ('trouble', 'Trouble'),
    ('done', 'Done'),
    ('cancel', 'Cancel')
]


class InstallmentInvoice(models.Model):
    _name = 'tt.installment.invoice.groupbooking'
    _description = 'Installment Invoice Group Booking'

    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    amount = fields.Monetary('Amount', default=0, readonly=True)

    due_date = fields.Date('Due Date', required=True)

    booking_id = fields.Many2one('tt.reservation.groupbooking', 'Group Booking Reservation ID', readonly=True)
    groupboooking_booking_state = fields.Selection(variables.BOOKING_STATE, related="booking_id.state", store=True, readonly=True)

    state_invoice = fields.Selection(STATE_INVOICE, 'State Invoice', default='open', readonly=True)

    # ledger_ids = fields.One2many('tt.ledger', 'resv_id', 'Ledger')
    agent_invoice_id = fields.Many2one('tt.agent.invoice', 'Agent Invoice', readonly=True)

    description = fields.Text('Description')
    payment_rules_id = fields.Many2one('tt.payment.rules.groupbooking', 'Payment Rules ID', readonly=True)

    def get_formatted_due_date(self):
        return self.due_date.strftime('%d %B %Y')

    def action_open(self):
        self.sudo().write({
            'state_invoice': 'open'
        })

    def action_trouble(self):
        self.sudo().write({
            'state_invoice': 'trouble'
        })
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_num = self.env.ref('tt_reservation_tour.tt_reservation_tour_view_action_all').id
            menu_num = self.env.ref('tt_reservation_tour.submenu_reservation_tour_all').id

            data = {
                'url': base_url + "/web#id=" + str(self.booking_id.id) + "&action=" + str(action_num) + "&model=tt.reservation.tour&view_type=form&menu_id=" + str(menu_num),
                'order_number': self.booking_id.name,
                'tour_name': self.booking_id.tour_id.name,
                'due_date': self.due_date
            }

            context = {
                'co_uid': self.env.user.id,
                'co_user_name': self.env.user.name,
            }
            self.env['tt.tour.api.con'].send_tour_payment_expired_notification(data, context)
        except Exception as e:
            _logger.error("Send Tour Payment Expired Notification Telegram Error\n" + traceback.format_exc())

    def action_done(self):
        if self.agent_invoice_id.state == 'paid':
            self.sudo().write({
                'state_invoice': 'done'
            })
        else:
            raise UserError(
                _('Invoice has not been paid.'))

    def action_set_to_done(self):
        self.sudo().write({
            'state_invoice': 'done'
        })

    def action_cancel(self):
        if self.agent_invoice_id.state == 'cancel':
            self.sudo().write({
                'state_invoice': 'cancel'
            })
        else:
            raise UserError(
                _('Please cancel the invoice first.'))

    def action_pay_now(self):
        if self.state_invoice in ['open', 'trouble']:
            commission_ledger = False
            not_paid_installments = self.env['tt.installment.invoice.groupbooking'].sudo().search([('state_invoice', 'in', ['open', 'trouble']), ('booking_id', '=', int(self.booking_id.id)), ('id', '!=', int(self.id))])
            if not not_paid_installments:
                commission_ledger = True
            else:
                for rec in not_paid_installments:
                    if rec.due_date < self.due_date:
                        raise UserError(_('Please pay the previous installment first!'))
            for rec in self.booking_id.provider_booking_ids:
                rec.action_create_installment_ledger(self.booking_id.issued_uid.id, self.payment_rules_id.id, commission_ledger)
            self.sudo().write({
                'state_invoice': 'done'
            })
        else:
            raise UserError(
                _('This installment cannot be paid.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
