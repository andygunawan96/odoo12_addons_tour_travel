from odoo import api, fields, models, _
from datetime import datetime, timedelta, date, time
from odoo import http
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.db_connector import GatewayConnector

try:
    from cStringIO import StringIO
except ImportError:
    pass

import pickle
import json
import base64
import logging
import traceback
import requests

# from Ap
_logger = logging.getLogger(__name__)

class EventResendVoucher(models.TransientModel):
    _name = "event.voucher.wizard"
    _description = 'Rodex Event Model'

    def get_default_email(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.contact_id.email or False

    def get_default_provider(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.provider_name

    def get_default_pnr(self):
        context = self.env.context
        new_obj = self.env[context['active_model']].browse(context['active_id'])
        return new_obj.pnr

    user_email_address = fields.Char(string="User Email", default=get_default_email)
    provider_name = fields.Char(string="Provider", default=get_default_provider, readonly=1)
    pnr = fields.Char(string="PNR", default=get_default_pnr)

    def resend_voucher_api(self):
        req = {
            'provider': self.provider_name,
            'order_id': self.pnr,
            'user_email_address': self.user_email_address
        }
        res = self.env['tt.event.api.con'].resend_voucher(req)
        if res['response'].get("success"):
            context = self.env.context
            new_obj = self.env[context['active_model']].browse(context['active_id'])
        else:
            raise UserError(_('Resend voucher failed!'))

class ReservationEvent(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.event'
    _order = 'id DESC'
    _description = 'Rodex Event Model'

    booking_uuid = fields.Char('Booking UUID')
    user_id = fields.Many2one('res.users', 'User')
    senior = fields.Integer('Senior')

    acceptance_date = fields.Datetime('Acceptance Date')
    rejected_date = fields.Datetime('Rejected Date')
    refund_date = fields.Datetime('Refund Date')

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    event_product_id = fields.Many2one('tt.master.event.lines', 'Event Product ID')
    event_name = fields.Char('Event Name')
    event_product = fields.Char('Product Type')
    event_product_uuid = fields.Char('Product Type UUID')
    visit_date = fields.Datetime('Visit Date')
    timeslot = fields.Char('Timeslot')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_event_id', string="Service Charge", readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.event', 'booking_id', string="Provider Booking", readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.event', 'booking_id', string="Passengers")

    information = fields.Text('Additional Information')
    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')
    voucher_url_ids = fields.One2many('tt.reservation.event.voucher', 'booking_id')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_event.tt_provider_type_event'))
    option_ids = fields.One2many('tt.reservation.event.option', 'booking_id', 'Options')
    extraQuestion_ids = fields.One2many('tt.reservation.event.extra.question', 'reservation_id', 'Extra Question')

    def _calc_grand_total(self):
        for i in self:
            i.total = 0
            i.total_fare = 0
            i.total_tax = 0
            i.total_discount = 0
            i.total_commission = 0

            for j in i.sale_service_charge_ids:
                if j.charge_code == 'fare':
                    i.total_fare += j.total
                if j.charge_code == 'tax':
                    i.total_tax += j.total
                if j.charge_code == 'disc':
                    i.total_discount += j.total
                if j.charge_code == 'r.oc':
                    i.total_commission += j.total

            i.total = i.total_fare + i.total_tax
            i.total_nta = i.total - i.total_commission

    def action_booked(self):
        self.write({
            'state': 'booked',
            'date': datetime.now(),
            'booked_uid': self.env.user.id
        })

    def get_datetime(self, utc=0):
        now_datetime = datetime.now() + timedelta(hours=utc)
        if utc >= 0:
            utc = '+{}'.format(utc)
        return '{} (GMT{})'.format(now_datetime.strftime('%d-%b-%Y %H:%M:%S'), utc)

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })

    def action_fail_refund(self, context):
        self.write({
            'state': 'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_partial_booked_api_event(self, context, pnr_list, hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_event(self):
        self.write({
            'state': 'partial_issued'
        })

    def action_expired(self):
        self.write({
            'state': 'cancel2',
            'expired_date': datetime.now()
        })

    def check_provider_state(self, context, pnr_list = [], hold_sate = False, req = {}):
        if all(i.state == 'booked' for i in self.provider_booking_ids):
            #booked
            pass
        elif all(i.state == 'issued' for i in self.provider_booking_ids):
            #issued
            pass
        elif all(i.state == 'refund' for i in self.provider_booking_ids):
            #refund
            self.action_refund()
        elif all(i.state == 'fail_refunded' for i in self.provider_booking_ids):
            #fail_refunded
            self.action_fail_refund(context)
        elif any(i.state == 'issued' for i in self.provider_booking_ids):
            #partially issued
            self.action_partial_issued_api_event()
        elif any(i.state == 'booked' for i in self.provider_booking_ids):
            #partially_booked
            self.action_partial_booked_api_event()
        elif all(i.state == 'fail_issued' for i in self.provider_booking_ids):
            #failed issued
            self.action_failed_issue()
        elif all(i.state == 'fail_booked' for i in self.provider_booking_ids):
            #fail booked
            self.action_failed_book()
        else:
            _logger.error("Status unknown")
            raise RequestException(1006)

    def action_calc_prices(self):
        self._calc_grand_total()

class TtReservationEventOption(models.Model):
    _name = 'tt.reservation.event.option'
    _description = 'Rodex Event Model'

    name = fields.Char('Information')
    value = fields.Char('Value')
    description = fields.Char('Description')
    booking_id = fields.Many2one('tt.reservation.event', 'Event Booking ID')

class TtReservationEventVoucher(models.Model):
    _name = 'tt.reservation.event.voucher'
    _description = 'Rodex Event Model'

    name = fields.Char('URL')
    booking_id = fields.Many2one('tt.reservation.event', 'Reservation')

class TtReservationExtraQuestion(models.Model):
    _name = 'tt.reservation.event.extra.question'
    _description = 'Rodex Event Model'

    reservation_id = fields.Many2one('tt.reservation.event', 'Reservation ID')
    extra_question_id = fields.Many2one('tt.event.extra.question', 'Extra Question')
    answer = fields.Char('answer')

class PrinoutEventInvoice(models.AbstractModel):
    _name = 'report.tt_reservation_event.printout_event_invoice'

    @api.model
    def render_html(self, docids, data=None):
        tt_event = self.env['tt.reservation.event'].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc': tt_event
        }
        return self.env['report'].with_context(landscape=False).render('tt_reservation_event.printout_event_invoice_template', docargs)
