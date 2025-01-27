from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools.db_connector import GatewayConnector
from ...tools import variables
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class TtProviderEvent(models.Model):
    _name = 'tt.provider.event'
    _rec_name = 'pnr'
    _order = 'event_date'
    _description = 'Orbis Event Model'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    reference = fields.Char('Reference', default='')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.event', 'Order Number', ondelete='cascade')
    balance_due = fields.Float('Balance Due')
    sequence = fields.Integer('Sequence')
    event_id = fields.Many2one('tt.master.event', 'Event')
    event_product_id = fields.Many2one('tt.event.option', 'Event Product')
    event_product = fields.Char('Product Type')
    event_product_uuid = fields.Char('Product Type Uuid')
    event_date = fields.Datetime('Event Date')

    sid_booked = fields.Char('SID Booked')
    sid_issued = fields.Char('SID Issued')

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_event_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    promotion_code = fields.Char(string='Promotion Code')

    #booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Char('Hold Date')
    expired_date = fields.Datetime('Expired Date')

    # ticket_ids = fields.One2many('tt.ticket.event', 'provider_id', 'Ticket Number')
    passenger_ids = fields.One2many('tt.reservation.passenger.event', 'provider_id', 'Passenger(s)')

    error_history_ids = fields.One2many('tt.reservation.err.history', 'res_id', 'Error history')

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    total_price = fields.Float('Total Price', readonly=True, default=0)

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    def action_create_ledger(self, issued_uid, pay_method=None, use_point=False,payment_method_use_to_ho=False):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid, use_point=use_point, payment_method_use_to_ho=payment_method_use_to_ho)

    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']

        for scs in service_charge_vals:
            service_chg_obj.create({
                'charge_code': scs['charge_code'],
                'charge_type': scs['charge_type'],
                'pax_type': scs['pax_type'],
                'pax_count': scs['pax_count'],
                'amount': scs['amount'],
                'foreign_amount': scs['foreign_amount'],
                'total': scs['total'],
                'provider_hotel_booking_id': self.id,
                'description': self.pnr and self.pnr or '',
                'ho_id': self.booking_id.ho_id.id if self.booking_id and self.booking_id.ho_id else '',
                'commission_agent_id': not isinstance(scs, dict) and scs.commission_agent_id.id or False,
            })
            # scs_list.append(new_scs)
    # TODO END

    def action_set_to_book_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 125')
        if self.state == 'booked':
            raise UserError("Has been Booked.")

        self.write({
            'state': 'booked',
            'booked_uid': self.env.user.id,
            'booked_date': datetime.now()
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reverse_ledger_from_button(self):
        if not self.env.user.has_group('tt_base.group_reservation_provider_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 126')
        if self.state == 'fail_refunded':
            raise UserError("Cannot refund, this PNR has been refunded.")

        # if not self.is_ledger_created:
        #     raise UserError("This Provider Ledger is not Created.")

        ##fixme salahhh, ini ke reverse semua provider bukan provider ini saja
        for rec in self.booking_id.ledger_ids:
            if rec.pnr == self.pnr and not rec.is_reversed:
                rec.reverse_ledger()

        self.write({
            'state': 'fail_refunded',
            # 'is_ledger_created': False,
            'refund_uid': self.env.user.id,
            'refund_date': datetime.now()
        })

        self.booking_id.check_provider_state({'co_uid':self.env.user.id})

        try:
            data = {
                'code': 9901,
                'title': 'PROVIDER EVENT REVERSE LEDGER',
                'message': 'Provider Ledger reversed from button: %s (%s)\nUser: %s\n' % (
                self.booking_id.name, self.pnr, self.env.user.name)
            }
            context = {
                "co_ho_id": self.booking_id.ho_id.id
            }
            GatewayConnector().telegram_notif_api(data, context)
        except Exception as e:
            _logger.info('Failed to send "reverse provider ledger" telegram notification: ' + str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
