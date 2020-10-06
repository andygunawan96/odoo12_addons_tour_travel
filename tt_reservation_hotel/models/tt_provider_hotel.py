from odoo import api, fields, models, _
from datetime import datetime
from ...tools import util,variables,ERR
from odoo.exceptions import UserError
import copy


class TransportBookingProvider(models.Model):
    _name = 'tt.provider.hotel'
    _description = 'Provider Hotel'
    _rec_name = 'pnr'
    _order = 'checkin_date'

    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider_id = fields.Many2one('tt.provider','Provider')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    booking_id = fields.Many2one('tt.reservation.hotel', 'Order Number', ondelete='cascade')
    balance_due = fields.Float('Balance Due')
    sequence = fields.Integer('Sequence')
    checkin_date = fields.Date('Check In Date', readonly=True, states={'draft': [('readonly', False)]})
    checkout_date = fields.Date('Check Out Date', readonly=True, states={'draft': [('readonly', False)]})
    hotel_id = fields.Many2one('tt.hotel', 'Hotel Information', readonly=True, states={'draft': [('readonly', False)]})
    hotel_name = fields.Char('Hotel Name', readonly=True, states={'draft': [('readonly', False)]})
    hotel_address = fields.Char('Address', readonly=True, states={'draft': [('readonly', False)]})
    hotel_city = fields.Char('City', readonly=True, states={'draft': [('readonly', False)]})
    hotel_phone = fields.Char('Phone', readonly=True, states={'draft': [('readonly', False)]})

    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_hotel_booking_id', 'Cost Service Charges')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    sid = fields.Char('Session ID', readonly=True)

    # Booking Progress
    booked_uid = fields.Many2one('res.users', 'Booked By')
    booked_date = fields.Datetime('Booking Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})
    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True, states={'draft': [('readonly', False)]})
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    # total = fields.Monetary(string='Total', readonly=True)
    # total_fare = fields.Monetary(string='Total Fare', compute=False, readonly=True)
    # total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    promotion_code = fields.Char(string='Promotion Code')

    total_price = fields.Float('Total Price', readonly=True, default=0)

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    def action_reverse_ledger_from_button(self):
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

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_booked_api_hotel(self, provider_data, api_context):
        for rec in self:
            rec.write({
                'pnr': provider_data['pnr'],
                'state': 'booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': fields.Datetime.now(),
            })
            for rec2 in rec.cost_service_charge_ids:
                rec2.sudo().write({
                    'description': provider_data['pnr']
                })

    def action_failed_booked_api_hotel(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked'
            })

    def action_issued_api_hotel(self, context):
        for rec in self:
            rec.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': context.get('co_uid'),
                'sid_issued': context.get('signature'),
                'balance_due': 0
            })

    def action_failed_issued_api_hotel(self):
        for rec in self:
            rec.write({
                'state': 'fail_issued'
            })

    def action_expired(self):
        self.state = 'cancel2'

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def action_force_issued(self, pnr=''):
        self.pnr =pnr
        self.pnr2 = pnr
        for rec in self.cost_service_charge_ids:
            rec.is_ledger_created = False

    def action_force_issued_from_button(self, payment_data={}):
        if self.state == 'issued':
            raise UserError("Has been Issued.")

        self.action_force_issued(self.pnr)
        self.action_create_ledger(self.issued_uid.id)
        self.action_issued_api_hotel({
            'co_uid': self.env.user.id,
            'signature': self.booking_id.sid_issued or self.booking_id.sid_booked
        })

        if self.booking_id.invoice_line_ids:
            # Jika Error dan sdah buat invoice tidak kita create invoice lagi
            self.booking_id.state = 'issued'
        else:
            self.booking_id.action_issued(payment_data, self.issued_uid.id)

    def action_set_to_issued_from_button(self, payment_data={}):
        if self.state == 'issued':
            raise UserError("Has been Issued.")

        if self.booking_id.invoice_line_ids:
            # Jika Error dan sdah buat invoice tidak kita create invoice lagi
            self.booking_id.state = 'issued'
        else:
            self.booking_id.action_issued(payment_data, self.issued_uid.id)

    # TODO START
    def create_service_charge(self, service_charge_vals):
        service_chg_obj = self.env['tt.service.charge']

        for scs in service_charge_vals:
            service_chg_obj.create({
                'charge_code': scs.charge_code,
                'charge_type': scs.charge_type,
                'pax_type': scs.pax_type,
                'pax_count': scs.pax_count,
                'amount': scs.amount,
                'foreign_amount': scs.foreign_amount,
                'total': scs.total,
                'provider_hotel_booking_id': self.id,
                'description': self.pnr and self.pnr or '',
                'commission_agent_id': scs.commission_agent_id.id,
            })
            # scs_list.append(new_scs)
    # TODO END

    def delete_service_charge(self):
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created

    def action_create_ledger(self, issued_uid, pay_method=None):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid)

    def to_dict(self):
        journey_list = []
        for rec in self.journey_ids:
            journey_list.append(rec.to_dict())
        ticket_list = []
        for rec in self.ticket_ids:
            ticket_list.append(rec.to_dict())
        res = {
            'pnr': self.pnr and self.pnr or '',
            'pnr2': self.pnr2 and self.pnr2 or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'balance_due': self.balance_due,
            'direction': self.direction,
            'origin': self.origin_id.code,
            'destination': self.destination_id.code,
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'journeys': journey_list,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            'tickets': ticket_list,
        }

        return res

    def get_carrier_name(self):
        return []