from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

PAYMENT_METHOD = [
    ('cash', 'Cash'),
    ('installment', 'Installment')
]


class TourBooking(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.tour.booking'

    tour_id = fields.Many2one('tt.tour.pricelist', 'Tour ID')
    # tour_id = fields.Char('Tour ID')

    line_ids = fields.One2many('tt.tour.booking.line', 'tour_booking_id', 'Line')  # Perlu tidak?

    arrival_date = fields.Date('Arrival Date', readonly=True, states={'draft': [('readonly', False)]})
    next_installment_date = fields.Date('Next Due Date', compute='_next_installment_date', store=True)

    passenger_ids = fields.One2many('tt.reservation.customer', 'customer_id', 'Passenger')
    # sale_service_charge_ids = fields.One2many('tt.service.charge', 'tb_provider_id', 'Sale Service Charge IDs')
    # agent_invoice_ids = fields.One2many('tt.agent.invoice', 'resv_id', 'Agent Invoice')  # One2Many -> tt.agent.invoice

    provider_booking_ids = fields.One2many('tt.tb.provider', 'booking_id', 'Provider Booking IDs')

    payment_method = fields.Selection(PAYMENT_METHOD, 'Payment Method')

    # *STATE*
    def action_booked(self):
        self.write({
            'state': 'book',
            'booked_date': datetime.now(),
            'booked_uid': self.env.user.id,
            'hold_date': datetime.now() + relativedelta(days=1),
        })
        # self.message_post(body='Order BOOKED')

    def action_issued(self):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id
        })
        # self.message_post(body='Order ISSUED')

    def action_reissued(self):
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        if (self.tour_id.seat - pax_amount) >= 0:
            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': self.env.user.id
            })
            # self.message_post(body='Order REISSUED')
        else:
            raise UserError(
                _('Cannot reissued because there is not enough seat quota.'))

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })
        # self.message_post(body='Order REFUNDED')

        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
        self.tour_id.seat += pax_amount
        if self.tour_id.seat > self.tour_id.quota:
            self.tour_id.seat = self.tour_id.quota
        self.tour_id.state_tour = 'open'

        print('state : ' + self.state)

    def action_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_date': datetime.now(),
            'cancel_uid': self.env.user.id
        })
        # self.message_post(body='Order CANCELED')

        if self.state != 'refund':
            pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')
            self.tour_id.seat += pax_amount
            if self.tour_id.seat > self.tour_id.quota:
                self.tour_id.seat = self.tour_id.quota
            self.tour_id.state_tour = 'open'

        for rec in self.tour_id.passengers_ids:
            if rec.tour_booking_id.id == self.id:
                rec.sudo().tour_pricelist_id = False
    # *END STATE*

    def action_booked_tour(self, api_context=None):
        # if not api_context:
        #     api_context = {
        #         'co_uid': self.env.user.id
        #     }
        # vals = {}
        # if self.name == 'New':
        #     vals.update({
        #         'name': self.env['ir.sequence'].next_by_code('transport.booking.tour'),
        #         'state': 'partial_booked',
        #     })
        self.action_booked()

        # Kurangi seat sejumlah pax_amount, lalu cek sisa kuota tour
        pax_amount = sum(1 for temp in self.line_ids if temp.pax_type != 'INF')  # jumlah orang yang di book
        self.tour_id.seat -= pax_amount  # seat tersisa dikurangi jumlah orang yang di book
        if self.tour_id.seat <= int(0.2 * self.tour_id.quota):
            self.tour_id.state_tour = 'definite'  # pasti berangkat jika kuota >=80%
        if self.tour_id.seat == 0:
            self.tour_id.state_tour = 'sold'  # kuota habis

    def action_cancel_by_manager(self):
        self.action_refund()
        self.action_cancel()
        # refund

    #############################################################################################################
    #############################################################################################################

    def get_id(self, booking_number):
        row = self.env['tt.tour.booking'].search([('name', '=', booking_number)])
        if not row:
            return ''
        return row.id


