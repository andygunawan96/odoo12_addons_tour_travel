from odoo import api, fields, models, _
import time, copy, json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import base64
import logging
import traceback
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from decimal import Decimal

from .ApiConnector_Hotel import ApiConnectorHotels
API_CN_HOTEL = ApiConnectorHotels()
_logger = logging.getLogger(__name__)


class HotelReservation(models.Model):
    _name = 'tt.reservation.hotel'
    _description = 'Hotel Reservation'
    _inherit = "tt.reservation"
    _order = 'id DESC'

    # sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
    #                                help='COR / POR', related='contact_id.agent_id')

    checkin_date = fields.Date('Check In Date', readonly=True, states={'draft': [('readonly', False)]})
    checkout_date = fields.Date('Check Out Date', readonly=True, states={'draft': [('readonly', False)]})
    nights = fields.Integer('Total Nights', default=1, readonly=True, states={'draft': [('readonly', False)]})
    room_count = fields.Integer('Room Qty', default=1, readonly=True, states={'draft': [('readonly', False)]})

    # Booking Progress
    # state = fields.Selection([('draft', 'Draft'), ('confirm', 'Hold Booking'), ('issued', 'Issue'),
    #                           ('wait', 'Waiting Vendor Validation'), ('refund', 'Refund'), ('fail', 'Failed'),
    #                           ('cancel', 'Canceled'), ('done', 'Done')], default='draft', help='''
    #                               Draft: Draft Reservation;
    #                               Confirm: Hold Reservation;
    #                               Issued: Resv. already paid, Vendor Already confirm the booking;
    #                               Wait: Resv. already paid, Waiting vendor validate booking;
    #                               Refund: Refund Ledger (State: Issued= Cancellation Policy, Wait=No CP, Failed=No CP);
    #                               Failed: Resv. Failed to Vendor;
    #                               Canceled: Resv. Canceled by agent;
    #                               Done: Resv. Issued, Person already;
    #                           ''')
    provider_booking_ids = fields.One2many('tt.provider.hotel', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda
        x: x.env.ref('tt_reservation_hotel.tt_provider_type_hotel'))

    # Guests Information
    # passenger_ids = fields.Many2many('tt.customer', 'tt_reservation_hotel_guest_rel', 'booking_id',
    #                                  'passenger_id',
    #                                  string='List of Guest', readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.hotel', 'booking_id', string='Passengers')

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    # Hotel Information
    hotel_id = fields.Many2one('tt.hotel', 'Hotel Information', readonly=True, states={'draft': [('readonly', False)]})
    hotel_name = fields.Char('Hotel Name', readonly=True, states={'draft': [('readonly', False)]})
    hotel_address = fields.Char('Address', readonly=True, states={'draft': [('readonly', False)]})
    hotel_rating = fields.Selection([
        (0, 'No Star'), (1, 'One Star'), (2, 'Two Star'), (3, 'Three Star'),
        (4, 'Four Star'), (5, 'Five Star'), (6, 'Six Star'), (7, 'Seven Star'),
    ], 'Star', default=0, readonly=True, states={'draft': [('readonly', False)]})
    hotel_city = fields.Char('City', readonly=True, states={'draft': [('readonly', False)]})
    hotel_city_id = fields.Many2one('res.city', 'City', readonly=True, states={'draft': [('readonly', False)]})
    hotel_phone = fields.Char('Phone', readonly=True, states={'draft': [('readonly', False)]})

    # Provider Data & Booking Information
    provider_data = fields.Text('Provider Data', help='Catat Data penting dari provider')
    special_req = fields.Text('Special Request')
    description = fields.Text('Description')

    # Invoice & Payment
    sale_service_charge_ids = fields.One2many('tt.service.charge', 'resv_hotel_id', 'Service Charges', ondelete='cascade',
                                              readonly=True, states={'draft': [('readonly', False)]})
    total_supplementary_price = fields.Monetary('Supplementary', compute='_get_total_supplement')
    # Agent & Others

    # Booker Information
    # Todo: Email perlu disimpen?
    contact_email = fields.Char('Contact Email', states={'draft': [('readonly', False)]})
    norm_str = fields.Text('Hotel Norms + Booking Info')

    # Cancellation
    cancellation_policy_str = fields.Text('Cancellation Policy')
    sid_issued = fields.Char('SID Issued')
    sid_cancel = fields.Char('SID Cancel')

    # Voucher
    # voucher_name = fields.Char('Voucher', store=True)

    def get_form_id(self):
        return self.env.ref("tt_reservation_hotel.tt_reservation_hotel_form_views")

    @api.depends('room_detail_ids')
    def _compute_total_pax(self):
        for rec in self:
            total_pax = 0
            for room_detail_obj in rec.room_detail_ids:
                total_pax += len(room_detail_obj.room_date_ids)
            rec.total_pax = total_pax

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

    @api.depends('provider_booking_ids','provider_booking_ids.reconcile_line_id')
    def _compute_reconcile_state(self):
        for rec in self:
            if all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in
                    rec.provider_booking_ids]):
                rec.reconcile_state = 'reconciled'
            elif any([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in
                      rec.provider_booking_ids]):
                rec.reconcile_state = 'partial'
            elif all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'cancel' or False for rec1 in
                      rec.provider_booking_ids]):
                rec.reconcile_state = 'cancel'
            else:
                rec.reconcile_state = 'not_reconciled'

    def calc_voucher_name(self):
        for rec in self.search([('state', '=', 'issued')]):
            rec.voucher_name = ''
            for provider in rec.room_detail_ids:
                rec.voucher_name += provider.issued_name and provider.issued_name + '; ' or ''

    @api.multi
    @api.onchange('checkin_date', 'checkout_date')
    @api.depends('checkin_date', 'checkout_date')
    def count_days(self):
        for hotel in self:
            if hotel.checkout_date:
                hotel.nights = relativedelta(hotel.checkout_date, hotel.checkin_date).days

    @api.multi
    def get_hotel_name(self):
        for hotel in self:
            if hotel.hotel_id:
                hotel.hotel_name = hotel.hotel_id.name

    @api.onchange('hotel_id')
    @api.depends('hotel_id')
    def get_hotel_name(self):
        for rec in self:
            if rec.hotel_id:
                rec.hotel_name = rec.hotel_id.name
                rec.hotel_address = rec.hotel_id.street
                rec.hotel_city_id = rec.hotel_id.hotel_partner_city_id.id
                rec.hotel_phone = rec.hotel_id.phone

    @api.onchange('hotel_city_id')
    @api.depends('hotel_city_id')
    def get_city_name(self):
        for rec in self:
            if rec.hotel_city_id:
                rec.hotel_city = rec.hotel_city_id.name

    def compute_total_cost(self):
        self._compute_total_nta()
        self._compute_agent_nta()

    # This function similar to "print_itinerary" from other reservation
    def do_print_voucher(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        hotel_voucher_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_hotel')
        if not book_obj.printout_voucher_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = hotel_voucher_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = hotel_voucher_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel Voucher %s.pdf' % book_obj.name,
                    'file_reference': 'Hotel Voucher',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_voucher_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_voucher_id.url,
            'path': book_obj.printout_voucher_id.path
        }
        return url
        # return self.env.ref('tt_report_common.action_report_printout_reservation_hotel').report_action([], data=datas)

    # DEPRECATED
    @api.multi
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name,
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        hotel_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_hotel')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = hotel_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = hotel_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Hotel HO Invoice',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_ho_invoice_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_ho_invoice_id.url,
        }
        return url
        # return hotel_ho_invoice_id.report_action(self, data=datas)

    def print_itinerary(self, data, ctx=None):
        book_obj = False
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
            if 'provider_type' not in data:
                data['provider_type'] = self.provider_type_id.name

            book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
            datas = {'ids': book_obj.env.context.get('active_ids', [])}
            res = book_obj.read()
            res = res and res[0] or {}
            datas['form'] = res
            pdf_obj = book_obj.env.ref('tt_report_common.action_printout_itinerary_hotel')
            co_agent_id = book_obj.agent_id and book_obj.agent_id.id or self.env.user.agent_id.id
            co_uid = book_obj.user_id and book_obj.user_id.id or self.env.user.id

            book_name = book_obj.name
            if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
                pdf_report = pdf_obj.report_action(book_obj, data=datas)
                pdf_report['context'].update({
                    'active_model': book_obj._name,
                    'active_id': book_obj.id
                })
                pdf_report_bytes, _ = pdf_obj.render_qweb_pdf(data=pdf_report)
            else:
                pdf_report_bytes = False
        else:
            # Part ini untuk print ittin resv yg blum terbut di backend (tidk da model dkk) jadi data full dari json frontend
            pdf_obj = self.env.ref('tt_report_common.action_printout_itinerary_from_json')
            data = {'context': {'json_content': data['json_printout']}}
            pdf_report_bytes, _ = pdf_obj.sudo().render_qweb_pdf(False, data=data)
            book_name = 'Printout'
            co_agent_id = ctx['co_agent_id']
            co_uid = ctx['co_uid']
            # pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            # pdfhttpheaders.append(('Content-Disposition', 'attachment; filename="Itinerary.pdf"'))
            # self.make_response(pdf, headers=pdfhttpheaders)

        if pdf_report_bytes: #Value waktu ada render report baru
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel Itinerary %s.pdf' % book_name,
                    'file_reference': 'Hotel Itinerary',
                    'file': base64.b64encode(pdf_report_bytes),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            if book_obj:
                book_obj.printout_itinerary_id = upc_id.id
        else:
            upc_id = book_obj.printout_itinerary_id

        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': upc_id.url,
        }
        return url

    def print_itinerary_price(self, data, ctx=None):
        book_obj = False

        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        if data.get('order_number'):
            book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
            datas = {'ids': book_obj.env.context.get('active_ids', [])}
            res = book_obj.read()
            res = res and res[0] or {}
            datas['form'] = res
            datas['is_with_price'] = True
            pdf_obj = book_obj.env.ref('tt_report_common.action_printout_itinerary_hotel')
            co_agent_id = book_obj.agent_id and book_obj.agent_id.id or self.env.user.agent_id.id
            co_uid = book_obj.user_id and book_obj.user_id.id or self.env.user.id

            book_name = book_obj.name
            if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
                pdf_report = pdf_obj.report_action(book_obj, data=datas)
                pdf_report['context'].update({
                    'active_model': book_obj._name,
                    'active_id': book_obj.id
                })
                pdf_report_bytes, _ = pdf_obj.render_qweb_pdf(data=pdf_report)
            else:
                pdf_report_bytes = False
        else:
            # Part ini untuk print ittin resv yg blum terbut di backend (tidk da model dkk) jadi data full dari json frontend
            pdf_obj = self.env.ref('tt_report_common.action_printout_itinerary_from_json')
            data = {'context': {'json_content': data['json_printout']}}
            pdf_report_bytes, _ = pdf_obj.sudo().render_qweb_pdf(False, data=data)
            book_name = 'Printout'
            co_agent_id = ctx['co_agent_id']
            co_uid = ctx['co_uid']
            # pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            # pdfhttpheaders.append(('Content-Disposition', 'attachment; filename="Itinerary.pdf"'))
            # self.make_response(pdf, headers=pdfhttpheaders)

        # # jika panggil dari backend
        # if 'order_number' not in data:
        #     data['order_number'] = self.name
        #     if 'provider_type' not in data:
        #         data['provider_type'] = self.provider_type_id.name
        #
        #     book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
        #     datas = {'ids': book_obj.env.context.get('active_ids', [])}
        #     res = book_obj.read()
        #     res = res and res[0] or {}
        #     datas['form'] = res
        #     datas['is_with_price'] = True
        #     pdf_obj = book_obj.env.ref('tt_report_common.action_printout_itinerary_hotel')
        #     co_agent_id = book_obj.agent_id and book_obj.agent_id.id or self.env.user.agent_id.id
        #     co_uid = book_obj.user_id and book_obj.user_id.id or self.env.user.id
        #
        #     book_name = book_obj.name
        #     if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
        #         pdf_report = pdf_obj.report_action(book_obj, data=datas)
        #         pdf_report['context'].update({
        #             'active_model': book_obj._name,
        #             'active_id': book_obj.id
        #         })
        #         pdf_report_bytes, _ = pdf_obj.render_qweb_pdf(data=pdf_report)
        #     else:
        #         pdf_report_bytes = False
        # else:
        #     # Part ini untuk print ittin resv yg blum terbut di backend (tidk da model dkk) jadi data full dari json frontend
        #     pdf_obj = self.env.ref('tt_report_common.action_printout_itinerary_from_json')
        #     data = {'context': {'json_content': data['json_printout']}}
        #     pdf_report_bytes, _ = pdf_obj.sudo().render_qweb_pdf(False, data=data)
        #     book_name = 'Printout'
        #     co_agent_id = ctx['co_agent_id']
        #     co_uid = ctx['co_uid']
        #     # pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        #     # pdfhttpheaders.append(('Content-Disposition', 'attachment; filename="Itinerary.pdf"'))
        #     # self.make_response(pdf, headers=pdfhttpheaders)

        if pdf_report_bytes: #Value waktu ada render report baru
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel Itinerary %s (Price).pdf' % book_name,
                    'file_reference': 'Hotel Itinerary',
                    'file': base64.b64encode(pdf_report_bytes),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            if book_obj:
                book_obj.printout_itinerary_price_id = upc_id.id
        else:
            upc_id = book_obj.printout_itinerary_price_id

        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': upc_id.url,
        }
        return url

    @api.multi
    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_hotel')

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = airline_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = airline_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Hotel Ticket',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_ticket_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_ticket_id.url,
            'path': book_obj.printout_ticket_id.path
        }
        return url

    @api.multi
    def print_eticket_with_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_hotel')

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = airline_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = airline_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Hotel Ticket (Price) %s.pdf' % book_obj.name,
                    'file_reference': 'Hotel Ticket with Price',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_ticket_price_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_ticket_price_id.url,
            'path': book_obj.printout_ticket_price_id.path
        }
        return url

    # @api.depends('room_detail_ids.commission_amount', 'room_detail_ids.qty')
    # def _compute_total_commission_amount(self):
    #     total = 0
    #     for data in self:
    #         for line in data.room_detail_ids:
    #             total += line.commission_amount * line.qty
    #         data.total_commission_amount = total

    def _get_total_supplement(self):
        return 0

    def get_provider_list(self):
        self.ensure_one()
        provider_list = []
        for rec in self.room_detail_ids:
            if rec.provider_id.name not in provider_list:
                provider_list.append(rec.provider_id.name)
        return ','.join(provider_list)

    def get_pnr_list(self):
        self.ensure_one()
        provider_list = []
        for rec in self.room_detail_ids:
            # if rec.name and rec.name not in provider_list:
            #     provider_list.append(rec.name)
            if rec.issued_name and rec.issued_name not in provider_list:
                provider_list.append(rec.issued_name)
        return ','.join(provider_list)

    def create_agent_ledger(self, vals):
        new_aml = self.env['tt.ledger'].create(vals)
        return new_aml

    def create_vendor_ledger(self):
        for rec in self.room_detail_ids:
            desc = rec.reservation_id.name
            desc += rec.prov_sale_price and ': (' + str(rec.prov_sale_price) + ' ' or '('
            desc += rec.prov_currency_id and rec.prov_currency_id.name + ')' or ')'
            rate_obj = rec.provider_id.find_rate(str(fields.Date.today()), rec.prov_currency_id.id)
            desc += rate_obj and ' Rate: ' + str(rate_obj.buy_rate) or ''
            self.env['tt.provider.ledger'].sudo().create({
                'description': desc,
                'vendor_id': rec.provider_id.id,
                'rate_id': rate_obj and rate_obj.id or False,
                'debit': 0,
                'credit': rate_obj and rate_obj.buy_rate * rec.prov_sale_price or rec.prov_sale_price,
            })
        return True

    # def create_commission_ledger(self, uid):
    #     # Create Commission
    #     vals = self.env['tt.ledger'].prepare_vals(self._name,self.id,'Commission : ' + self.name, self.name, self.issued_date, 3,
    #                                               self.currency_id.id, uid.id, self.total_commission_amount, 0)
    #     vals = self.env['tt.ledger'].prepare_vals_for_resv(self, '', vals)
    #     self.create_agent_ledger(vals)

    # @api.multi
    # def create_ledger(self, uid):
    #     for rec in self:
    #         for prov in rec.provider_booking_ids:
        #             self.env['tt.ledger'].action_create_ledger(prov, uid)

    @api.multi
    def _refund_ledger(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            vals = ledger.prepare_vals('Resv : ' + rec.name, rec.name, rec.issued_date, 2, rec.currency_id.id, rec.total,
                                       0)
            vals['hotel_reservation_id'] = rec.id
            vals['agent_id'] = rec.agent_id.id
            new_aml = ledger.create(vals)
            new_aml.action_done()
            rec.ledger_id = new_aml

    @api.one
    def action_confirm(self, kwargs=False):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 141')
        self.state = 'confirm'
        self.booked_date = fields.Datetime.now()
        self.booked_uid = kwargs and kwargs.get('user_id', self.env.user.id) or self.env.user.id
        self.name = self.name == 'New' and self.env['ir.sequence'].next_by_code('tt.reservation.hotel') or self.name
        self.provider_name = self.get_provider_list()

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_hotel')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'hotel',
                        'order_number': self.name,
                        'type': 'booked',
                    }
                    temp_context = {
                        'co_agent_id': self.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                else:
                    _logger.info('Booked email for {} is already created!'.format(self.name))
                    raise Exception('Booked email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

    @api.one
    def action_booked(self, context):
        self.state = 'booked'
        self.booked_date = fields.Datetime.now()
        self.booked_uid = context.get('co_uid') or self.env.user.id,
        self.provider_name = self.get_provider_list()
        return True

    @api.multi
    def action_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 142')
        for rec in self:
            rec.state = 'draft'

    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 143')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 144')
        for rec in self:
            rec.state = 'issued'

    def action_issued_backend(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 145')
        if not self.ensure_one():
            raise UserError('Cannot Issued more than 1 Resv.')
        is_enough = self.action_issued()
        if not is_enough:
            raise UserError('Current Balance for Agent:' + self.agent_id.name + ' is ' + str(self.agent_id.actual_balance))

    def action_failed(self, msg=''):
        self.state = 'fail_issued'
        self.error_msg = msg
        return 'Resv:' + self.name + ' is set to Failed'

    @api.one
    def action_set_to_issued(self, kwargs=False):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 146')
        self.state = 'issued'

    @api.one
    def action_set_to_failed(self, kwargs=False):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 147')
        self.state = 'fail_issued'

    @api.one
    def action_issued(self, data, kwargs=False):
        if not self.ensure_one():
            return False
        # Jika cukup Potong Saldo
        # self.pnr = self.get_pnr_list()
        self.issued_date = fields.Datetime.now()
        self.issued_uid = data['co_uid']

        self.state = 'issued'
        self.calc_voucher_name()

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_hotel')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'hotel',
                        'order_number': self.name,
                        'type': 'issued',
                    }
                    temp_context = {
                        'co_agent_id': self.agent_id.id
                    }
                    self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                else:
                    _logger.info('Issued email for {} is already created!'.format(self.name))
                    raise Exception('Issued email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

        return True

    # def action_issued_backend(self, kwargs=False):
    #     a = self.action_issued()
    #     if not a:
    #         raise UserError('Balance in not enough to issued: ' + self.name + '(' + str(self.total) + ')' +
    #                         ' Current Balance for Agent:' + self.agent_id.name + ' is ' +
    #                         str(self.agent_id.balance))
    #     else:
    #         raise UserError('Order has been issued')

    # def action_force_issued(self):
    #     for rec in self:
    #         for prov in rec.provider_booking_ids:
    #             prov.action_force_issued(self.pnr)
    #             prov.action_create_ledger(self.issued_uid.id)
    #             prov.action_issued_api_hotel({'co_uid': self.env.user.id, 'signature': self.sid_issued or self.sid_booked})
    #
    #         if rec.invoice_line_ids:
    #             # Jika Error dan sdah buat invoice tidak kita create invoice lagi
    #             rec.state = 'issued'
    #         else:
    #             rec.action_issued()

    def action_in_progress_by_api(self):
        values = {
            'state': 'in_progress',
        }
        self.write(values)

    @api.one
    def action_done(self, issued_response={}):
        for room_detail in self.room_detail_ids:
            if issued_response.get(room_detail.provider_id.code):
                provider = issued_response[room_detail.provider_id.code]
                room_detail.name = provider.get('booking_code') or room_detail.name
                room_detail.issued_name = provider.get('issued_code') or room_detail.issued_name
        self.env.cr.commit()

        pnr_list = ','.join([rec.get('issued_code') or '' for rec in issued_response.values()])
        self.update_ledger_pnr(pnr_list)
        self.pnr = self.get_pnr_list()
        # if state == 'done':
        #     self.action_create_invoice()
        for prov in self.provider_booking_ids:
            if prov.state != 'issued' and issued_response.get(prov.provider_id.code) and issued_response[prov.provider_id.code]['status'].lower() == 'issued':
                prov.action_issued_api_hotel({
                    'pnr': self.get_pnr_list(),
                    'pnr2': prov.provider_id.id == self.env.ref('tt_reservation_hotel.tt_hotel_provider_rodextrip_hotel').id and issued_response[room_detail.provider_id.code]['booking_code'] or '', #isi PNR 2 untuk BTBO2
                    'co_uid': self.issued_uid.id,
                    'signature': self.sid_issued or self.sid_booked
                })
            elif issued_response[prov.provider_id.code]['status'] == 'in_process':
                prov.action_in_progress_api_hotel()
            self.create_svc_upsell()
        self.check_provider_state({'co_uid': self.issued_uid.id})
        return True

    def action_calc_passenger_data(self):
        for rec in self:
            for pax in rec.passenger_ids:
                if pax.title or pax.first_name or pax.gender or pax.identity_type:
                    continue
                pax.update({
                    # 'title': pax.customer_id.title,
                    'first_name': pax.customer_id.first_name,
                    'last_name': pax.customer_id.last_name,
                    'gender': pax.customer_id.gender,
                    'birth_date': pax.customer_id.birth_date,
                    'nationality_id': pax.customer_id.nationality_id,
                    # 'identity_type': pax.customer_id.identity_type,
                    # 'identity_number': pax.customer_id.identity_number,
                })

    def action_calc_pnr(self):
        # for rec in self.search([]):
        for rec in self:
            pnr = []
            vendor = []
            for rec1 in rec.room_detail_ids:
                if rec1.issued_name not in pnr:
                    if rec1.issued_name:
                        pnr.append(rec1.issued_name)
                if rec1.provider_id.code not in vendor:
                    if rec1.provider_id.code:
                        vendor.append(rec1.provider_id.code)
            rec.pnr = ','.join(pnr)
            rec.provider_name = ','.join(vendor)

    def _prepare_invoice(self):
        a = {
            'payment_term_id': 2,
            'partner_id': self.customer_id.id or self.agent_id.id,
            'resv_id': self.id,
            'name': self.name,
        }
        return a

    @api.multi
    def action_ticket_customer(self):
        vals = self._prepare_invoice()
        vals.update({
            'resv_type': 'cust',
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        hotel_name = self.hotel_id.name or ''
        for line in self.room_detail_ids:
            value_line = {
                'invoice_id': inv_id.id,
                'name': hotel_name + " " + line.room_info_id.name,
                'account_id': 17,
                'qty': 1,
                'price_unit': line.sale_price,
                'commission_amount': line.commission_amount,
                'no_ticket': line.id
            }
            self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        # value_line = {
        #     'invoice_id': inv_id.id,
        #     'name': self.hotel_id.name + " " + self.checkin_date + " " + self.checkout_date,
        #     'account_id': 17,
        #     'qty': 1,
        #     'price_unit': self.total,
        #     'commission_amount': self.total_commission_amount,
        #     'no_ticket': self.number
        # }
        # self.env['account.invoice.line'].create(value_line)

        # form_id = self.env.ref('tt_hotel.tt_hotel_reservation_detail_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            # 'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    @api.multi
    def action_ticket_agent(self):
        vals = self._prepare_invoice()
        vals.update({
            'resv_type': 'agent',
            'reference': self.name,
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        # for line in self.room_detail_ids:
        #     value_line = {
        #         'invoice_id': inv_id.id,
        #         'name': self.hotel_id.name + " " + line.room_info_id.name,
        #         'account_id': 17,
        #         'qty': 1,
        #         'price_unit': line.sale_price,
        #         'commission_amount': line.commission_amount,
        #         'no_ticket': line.id
        #     }
        #     self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        hotel_name = self.hotel_id.name or ''
        value_line = {
            'invoice_id': inv_id.id,
            'name': hotel_name + " " + self.checkin_date + " " + self.checkout_date,
            'account_id': 17,
            'qty': 1,
            'price_unit': self.total,
            'commission_amount': self.total_commission_amount,
            'no_ticket': self.number
        }
        self.env['account.invoice.line'].create(value_line)

        # form_id = self.env.ref('tt_hotel.tt_hotel_reservation_detail_form')
        self.action_issued()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            # 'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    @api.multi
    def action_ticket_vendor(self):
        vals = self._prepare_invoice()
        vals.update({
            'type': 'in_invoice',
            'resv_type': 'vendor',
            'reference': self.number,
            'journal_id': self.env['account.journal'].search([('type', '=', 'sale')])[0].id
        })
        inv_id = self.env['account.invoice'].create(vals)

        # Jika Dibuat per kamar per malam
        # for line in self.room_detail_ids:
        #     value_line = {
        #         'invoice_id': inv_id.id,
        #         'name': self.hotel_id.name + " " + line.room_info_id.name,
        #         'account_id': 17,
        #         'qty': 1,
        #         'price_unit': line.sale_price - line.commission_amount,
        #         'commission_amount': 0,
        #         'no_ticket': line.id
        #     }
        #     self.env['account.invoice.line'].create(value_line)

        # Jika Dibuat keseluruhan total
        price_unit = 0
        commission = 0
        for line in self.room_detail_ids.filtered(lambda x: x.payment_method == 'cash'):
            price_unit += line.sale_price - line.commission_amount
            commission += line.commission_amount
        hotel_name = self.hotel_id.name or ''
        value_line = {
            'invoice_id': inv_id.id,
            'name': hotel_name + " " + self.checkin_date + " " + self.checkout_date,
            'account_id': 17,
            'qty': 1,
            'price_unit': price_unit,
            'commission_amount': commission,
            'no_ticket': self.number
        }
        self.env['account.invoice.line'].create(value_line)
        self.action_done()
        form_id = self.env.ref('account.invoice_supplier_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.invoice',
            'res_id': inv_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    def get_agent_for_ledger(self, partner, booker_agent_id, user_agent_id):
        agent_id = False
        if partner:
            if partner.is_HO:
                agent_id = booker_agent_id.id
            elif partner.agent_type_id.id in self.env.user.allowed_customer_ids.ids:
                agent_id = user_agent_id
            else:
                agent_id = partner.id
        return agent_id

    def get_subagent_for_ledger(self, partner, booker_agent_id, user_agent_id):
        agent_id = False
        if partner:
            if partner.is_HO:
                agent_id = booker_agent_id
            else:
                agent_id = partner.id
        return agent_id

    @api.multi
    def action_send_email(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('tt_transport_printout', 'email_template_rodex')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        template_name = []
        template_name.append('kai')

        data = {
            'booking_id': self.id,
            'invoicing': 0,
            'carriers': template_name
        }
        ctx = dict()
        ctx.update({
            'default_model': 'tt.transport.booking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "tt_transport_printout.mail_template_data_notification_email_rodex",
            'data': data
        })

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def check_booking_status(self):
        # api_context = {
        #     'co_uid': self.env.user.id
        # }
        # res = API_CN_HOTEL.check_booking_status_by_api({'name': self.name, 'provider': self.room_detail_ids[0].provider_id.code,
        #                                                 'sid_booked': self.sid_booked, 'sid_issued': self.sid_issued,
        #                                                 'booking_id': self.id,
        #                                                 'booked_name': self.room_detail_ids[0].name,
        #                                                 'issued_name': self.room_detail_ids[0].issued_name,
        #                                                 }, api_context)
        ho_id = self.agent_id.ho_id
        res = self.env['tt.hotel.api.con'].check_booking_status({'name': self.name, 'provider': self.room_detail_ids[0].provider_id.code,
                                                                 'sid_booked': self.sid_booked, 'sid_issued': self.sid_issued,
                                                                 'booking_id': self.id,
                                                                 'booked_name': self.room_detail_ids[0].name,
                                                                 'issued_name': self.room_detail_ids[0].issued_name,
                                                                 }, ho_id=ho_id)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            return True

    def check_booking_policy(self):
        api_context = {
            'co_uid': self.env.user.agent_id.id
        }
        res = API_CN_HOTEL.check_booking_policy_by_api({'name': self.name, 'provider': self.room_detail_ids[0].provider_id.code,
                                                        'booked_name': self.room_detail_ids[0].name,
                                                        'issued_name': self.room_detail_ids[0].issued_name,
                                                        }, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            return True

    def cancel_booking(self):
        api_context = {
            'co_uid': self.env.user.agent_id.id
        }
        res = API_CN_HOTEL.cancel_booking_by_api({
            'name': self.name, 'provider': self.room_detail_ids[0].provider_id.code,
            'booked_name': self.room_detail_ids[0].name,
            'issued_name': self.room_detail_ids[0].issued_name,
        }, api_context)
        if res['error_code'] != 0:
            raise ('Error')
        else:
            if self.payment_acquirer_number_id:
                self.payment_acquirer_number_id.state = 'cancel'
            return True

    def check_provider_state(self, context, pnr_list=[], hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            self.action_booked(context)
        elif any(rec.state == 'in_progress' for rec in self.provider_booking_ids):
            self.action_in_progress_by_api()
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            # self.action_issued_api_ppob(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
            issued_req = {
                'co_uid': context['co_uid'],
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued(issued_req)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.write({
                'state':  'fail_refunded',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'cancel2' for rec in self.provider_booking_ids):
            self.write({
                'state': 'cancel2',
            })
        else:
            # entah status apa
            self.write({
                'state': 'cancel2',
            })

    def test_payment_hotel_b2c(self):
        book_obj = self
        #login gateway, payment
        req = {
            'order_number': book_obj.name,
            'user_id': book_obj.booked_uid.id,
            'provider_type': 'hotel',
            'ho_id': book_obj.agent_id.ho_id.id
        }
        res = self.env['tt.payment.api.con'].send_payment(req)
        #tutup payment acq number

    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        # April 30, 2020 - SAM
        this_service_charges = []
        # END
        for idx, provider in enumerate(self.provider_booking_ids):
            sc_value = {}
            for idy, p_sc in enumerate(provider.cost_service_charge_ids):
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                c_code = ''
                c_type = ''
                if p_charge_type != 'RAC':
                    if 'csc' in p_charge_code.split('.'):
                        c_type = "%s%s" % (p_charge_code, p_charge_type.lower())
                        sc_value[p_pax_type][c_type] = {
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        }
                        c_code = p_charge_code
                    elif not sc_value[p_pax_type].get(p_charge_type):
                        c_type = "%s%s" % (p_charge_type, idy) ## untuk service charge yg kembar contoh SSR
                        sc_value[p_pax_type][c_type] = {
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        }
                    if not c_code:
                        c_code = p_charge_type.lower()
                    if not c_type:
                        c_type = p_charge_type
                elif p_charge_type == 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_code):
                        sc_value[p_pax_type][p_charge_code] = {}
                        sc_value[p_pax_type][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code

                sc_value[p_pax_type][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_pax_type][c_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_pax_type][c_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_pax_type][c_type]['foreign_amount'] + p_sc.foreign_amount,
                    'commission_agent_id': p_sc.commission_agent_id.id
                })

            # values = []
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    # April 27, 2020 - SAM
                    curr_dict = {
                        'pax_type': p_type,
                        'booking_airline_id': self.id,
                        'description': provider.pnr,
                        'ho_id': self.ho_id.id if self.ho_id else ''
                    }
                    # curr_dict['pax_type'] = p_type
                    # curr_dict['booking_airline_id'] = self.id
                    # curr_dict['description'] = provider.pnr
                    # END
                    curr_dict.update(c_val)
                    # values.append((0,0,curr_dict))
                    # April 30, 2020 - SAM
                    this_service_charges.append((0,0,curr_dict))
                    # END
        # April 2020 - SAM
        #     self.write({
        #         'sale_service_charge_ids': values
        #     })
        self.write({
            'sale_service_charge_ids': this_service_charges
        })
        #END

    # Update Pake API in_connector

    # Pindahan dari test.search START
    ### TOOLS Start ###
    def prepare_nightly_price(self, nightly, meal_type='Room Only'):
        return [{
            'date': str(night.date),
            'currency': night.currency_id.name,
            'sale_price': night.sale_price,
            'meal_type': night.meal_type or meal_type,
        } for night in nightly]

    def prepare_booking_room(self, lines, customers):
        vals = []
        for room in lines:
            data = {
                # 'id': room.id,
                'prov_issued_code': room.issued_name,
                'prov_booking_code': room.name,
                'provider': room.provider_id.code,
                'dates': self.prepare_nightly_price(room.room_date_ids, room.room_info_id and room.room_info_id.meal_type or room.meal_type),
                'room_name': room.room_info_id and room.room_info_id.name or room.room_name,
                'room_vendor_code': room.room_vendor_code,
                'room_type': room.room_type,
                'room_rate': room.sale_price,
                'person': room.room_info_id and room.room_info_id.max_guest or 2,
                'currency': room.currency_id and room.currency_id.name,
                'meal_type': room.room_info_id and room.room_info_id.meal_type or room.meal_type,
            }
            vals.append(data)
        return vals

    def prepare_passengers(self, customers):
        return [cust.to_dict() for cust in customers]

    def prepare_bookers(self, bookers):
        return {
            'booker_seq_id': bookers['id'],
            'calling_code': bookers['nationality_id']['phone_code'],
            'country_code': bookers['nationality_id']['code'],
            'email': bookers['email'],
            'first_name': bookers['first_name'],
            'last_name': bookers['last_name'] or '',
            'mobile': bookers['phone_ids'] and bookers['phone_ids'][0]['calling_number'] or '',
            'nationality_code': bookers['nationality_id']['code'],
            'nationality_name': bookers['nationality_id']['name'],
            'title': bookers['gender'] == 'male' and 'MR' or bookers['marital_status'] in ['married','widowed'] and 'MRS' or 'MS',
            'work_phone': bookers['phone_ids'] and bookers['phone_ids'][0]['calling_number'] or '',
        }

    def prepare_service_charge(self, cost_sc, obj_pnr):
        sc_value = {}
        for p_sc in cost_sc:
            p_charge_type = p_sc.charge_type
            pnr = obj_pnr if not p_sc.description or p_sc.description == '0' else p_sc.description
            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = {}
                sc_value[pnr][p_charge_type].update({
                    'amount': 0,
                    'foreign_amount': 0,
                })

            if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
                if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
                    continue

            sc_value[pnr][p_charge_type].update({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': sc_value[pnr][p_charge_type]['amount'] + (p_sc.amount * p_sc.pax_count),
                # 'amount': p_sc.amount,
                'foreign_amount': sc_value[pnr][p_charge_type]['foreign_amount'] + (p_sc.foreign_amount * p_sc.pax_count),
                # 'foreign_amount': p_sc.foreign_amount,
            })

        return sc_value

    def get_service_charge_details_breakdown(self, cost_sc, obj_pnr):
        sc_value = {}
        for p_sc in cost_sc:
            p_charge_type = p_sc.charge_type
            pnr = obj_pnr if not p_sc.description or p_sc.description == '0' else p_sc.description
            commission_agent_id = p_sc.commission_agent_id

            # if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
            #     if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
            #         continue

            if p_charge_type == 'RAC' and commission_agent_id:
                continue

            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = []

            sc_value[pnr][p_charge_type].append({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': p_sc.amount,
                'pax_type': p_sc.pax_type,
                'foreign_amount': p_sc.foreign_amount,
            })

        result = []
        for pnr, pnr_data in sc_value.items():
            base_fare_ori = Decimal("0.0")
            base_tax_ori = Decimal("0.0")
            base_upsell_ori = Decimal("0.0")
            base_upsell_adj = Decimal("0.0")
            base_discount_ori = Decimal("0.0")
            base_agent_commission = Decimal("0.0")
            base_agent_commission_ori = Decimal("0.0")
            base_agent_commission_charge = Decimal("0.0")
            base_commission_vendor_real = Decimal("0.0")
            base_hidden_commission_ho = Decimal("0.0")
            base_hidden_fee_ho = Decimal("0.0")
            base_hidden_vat_ho = Decimal("0.0")
            base_vendor_vat = Decimal("0.0")
            base_fee_ho = Decimal("0.0")
            base_vat_ho = Decimal("0.0")
            base_no_hidden_commission_ho = Decimal("0.0")

            pax_type = ''

            for charge_type, service_charges in pnr_data.items():
                for sc in service_charges:
                    sc_amount = Decimal(str(sc['amount']))
                    '''
                        GENERAL     |   PROVIDER    |   AGENT   |   CUSTOMER    |   Pricing notes
                        FARE        |   ROC         |   ROC     |   ROC         |
                        TAX         |   RAC         |   RAC     |   RAC         |
                        ROC         |   RACHSP      |   RACHSA  |   -           |
                        DISC        |   ROCHSP      |   ROCHSA  |   -           |   HO service fee
                        RAC         |   RACHVP      |   RACHVA  |   -           |
                        RACCHG      |   ROCHVP      |   ROCHVA  |   -           |   HO tax of service fee
                        ROCCHG      |   RACAVP      |   RACAVA  |   RACAVC      |
                        RACUA       |   ROCAVP      |   ROCAVA  |   ROCAVC      |   HO tax of commission fee
                        ROCUA       |               |           |   
                    '''
                    charge_code = sc.get('charge_code', '')
                    if charge_type == 'FARE':
                        base_fare_ori += sc_amount
                    elif charge_type == 'TAX':
                        base_tax_ori += sc_amount
                    elif charge_type == 'RAC':
                        base_agent_commission += sc_amount
                        base_commission_vendor_real += sc_amount
                        base_agent_commission_ori += sc_amount
                    elif charge_type in ['RACUA', 'RACCHG']:
                        base_commission_vendor_real += sc_amount
                        base_agent_commission_ori += sc_amount
                        base_agent_commission_charge += sc_amount
                    elif charge_type in ['ROCUA', 'ROCCHG']:
                        pass
                    elif charge_type == 'DISC':
                        base_discount_ori += sc_amount
                    elif charge_type in ['RACHSP', 'RACHVP']:
                        base_commission_vendor_real += sc_amount
                        base_hidden_commission_ho += sc_amount
                    elif charge_type == 'ROCHSP':
                        base_hidden_fee_ho += sc_amount
                    elif charge_type == 'ROCHVP':
                        base_hidden_vat_ho += sc_amount
                    elif charge_type == 'RACAVP':
                        base_commission_vendor_real += sc_amount
                    elif charge_type == 'ROCAVP':
                        base_vendor_vat += sc_amount
                    elif charge_type in ['RACHSA', 'RACHVA', 'RACAVA']:
                        base_no_hidden_commission_ho += sc_amount
                    elif charge_type in ['ROCHVA', 'ROCAVA']:
                        base_vat_ho += sc_amount
                    elif charge_type == 'ROCHSA':
                        base_fee_ho += sc_amount
                    elif charge_type == 'RACAVC':
                        base_no_hidden_commission_ho += sc_amount
                    elif charge_type == 'ROCAVC':
                        base_vat_ho += sc_amount
                    elif charge_type == 'ROC' and charge_code[-3:] == 'adj':
                        base_upsell_adj += sc_amount
                    else:
                        base_upsell_ori += sc_amount

                    if not pax_type:
                        pax_type = sc['pax_type']

            base_price_ori = base_fare_ori + base_tax_ori
            base_price = base_price_ori + base_upsell_ori + base_discount_ori + base_upsell_adj
            base_nta_vendor_real = base_price + base_commission_vendor_real + base_vendor_vat - base_upsell_adj

            base_fare = base_fare_ori
            base_tax = base_tax_ori
            base_upsell_com = base_upsell_ori + base_upsell_adj
            base_discount = base_discount_ori
            if base_hidden_commission_ho != 0:
                base_upsell_com -= abs(base_hidden_commission_ho)
                if base_tax != 0:
                    base_tax += abs(base_hidden_commission_ho)
                else:
                    base_fare += abs(base_hidden_commission_ho)
            if base_no_hidden_commission_ho != 0:
                base_upsell_com -= abs(base_no_hidden_commission_ho)

            base_nta = base_price - abs(base_agent_commission)
            base_commission_ho = base_no_hidden_commission_ho + base_hidden_commission_ho

            base_commission_vendor = base_commission_vendor_real - base_hidden_commission_ho
            base_nta_vendor = base_nta_vendor_real - base_hidden_commission_ho
            base_price_ott = base_fare + base_tax
            base_upsell = base_upsell_ori + base_hidden_commission_ho
            if base_upsell < 0:
                base_upsell = 0

            pax_values = {
                'pnr': pnr,
                'service_charges': pnr_data,
                'pax_type': pax_type,
                'pax_count': 1,
                'base_fare_ori': float(base_fare_ori),
                'base_tax_ori': float(base_tax_ori),
                'base_price_ori': float(base_price_ori),
                'base_upsell_ori': float(base_upsell_ori),
                'base_upsell_adj': float(base_upsell_adj),
                'base_discount_ori': float(base_discount_ori),
                'base_price': float(base_price),
                'base_commission_vendor_real': float(base_commission_vendor_real),
                'base_vendor_vat': float(base_vendor_vat),
                'base_nta_vendor_real': float(base_nta_vendor_real),  #
                'base_commission_vendor': float(base_commission_vendor),
                'base_nta_vendor': float(base_nta_vendor),
                # 'base_price_ott': float(base_price_ott),
                'base_price_ott': 0, #HardCode 0 by bunga 5 feb 2024 (OTT ini harga ori tiket dri vendor, hotel cannot cos markup)
                'base_fare': float(base_fare),
                'base_tax': float(base_tax),
                'base_upsell_com': float(base_upsell_com),
                'base_upsell': float(base_upsell),
                'base_discount': float(base_discount),
                'base_fee_ho': float(base_fee_ho),
                'base_vat_ho': float(base_vat_ho),
                'base_commission': float(base_agent_commission),
                'base_commission_ori': float(base_agent_commission_ori),
                'base_commission_charge': float(base_agent_commission_charge),
                'base_nta': float(base_nta),
                'base_no_hidden_commission_ho': float(base_no_hidden_commission_ho),  #
                'base_hidden_fee_ho': float(base_hidden_fee_ho),
                'base_hidden_vat_ho': float(base_hidden_vat_ho),
                'base_hidden_commission_ho': float(base_hidden_commission_ho),
                'base_commission_ho': float(base_commission_ho),  #
            }
            result.append(pax_values)
        return result
    ### TOOLS END ###

    def get_booking(self, resv_id, context=False):
        try:
            if isinstance(resv_id, int):
                resv_obj = self.browse(resv_id)
            else:
                resv_obj = self.search([('name', '=ilike', resv_id)], limit=1)
            if not resv_obj:
                return 'Not Found'
            else:
                resv_obj = resv_obj[0]
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            try:
                _co_user.create_date
            except:
                raise RequestException(1008)
            # if resv_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or resv_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or resv_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            if resv_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_system'):
                rooms = self.sudo().prepare_booking_room(resv_obj.room_detail_ids, resv_obj.passenger_ids)
                passengers = self.sudo().prepare_passengers(resv_obj.passenger_ids)
                bookers = self.sudo().prepare_bookers(resv_obj.booker_id)

                passengers[0]['sale_service_charges'] = self.sudo().prepare_service_charge(resv_obj.sale_service_charge_ids, resv_obj.pnr or resv_obj.name)
                if len(resv_obj.passenger_ids[0].channel_service_charge_ids.ids) > 0: ##ASUMSI UPSELL HANYA 1 PER PASSENGER & HOTEL UPSELL PER RESERVASI (MASUK KE PAX 1)
                    svc_csc = self.sudo().prepare_service_charge(resv_obj.passenger_ids[0].channel_service_charge_ids, resv_obj.pnr or resv_obj.name)
                    for pnr in svc_csc:
                        passengers[0]['channel_service_charges'] = {
                            "amount": svc_csc[pnr]['CSC']['amount'],
                            "currency": svc_csc[pnr]['CSC']['currency']
                        }
                passengers[0]['service_charge_details'] = self.sudo().get_service_charge_details_breakdown(resv_obj.sale_service_charge_ids, resv_obj.pnr or resv_obj.name)
                provider_bookings = []
                for provider_booking in resv_obj.provider_booking_ids:
                    provider_bookings.append(provider_booking.to_dict())
                new_vals = resv_obj.to_dict(context)
                for a in ['arrival_date', 'departure_date']:
                    new_vals.pop(a)
                new_vals.update({
                    "state_description": dict(self.env['tt.reservation.hotel']._fields['state'].selection).get(resv_obj.state),
                    "room_count": resv_obj.room_count,
                    "checkin_date": str(resv_obj.checkin_date),
                    "checkout_date": str(resv_obj.checkout_date),
                    # "provider_type": "hotel",
                    'passengers': passengers,
                    'hotel_name': resv_obj.hotel_name,
                    'hotel_address': resv_obj.hotel_address,
                    'hotel_phone': resv_obj.hotel_phone,
                    'hotel_city_name': resv_obj.hotel_city,
                    'hotel_rating': 0,
                    'images': [],
                    'cancellation_policy': [],
                    'lat': '',
                    'long': '',
                    'hotel_rooms': rooms,
                    'sid_booked': resv_obj.sid_booked,
                    'uid_booked': self.sudo().env.ref('tt_base.agent_b2c_user').id,
                    'uname_booked': self.sudo().env.ref('tt_base.agent_b2c_user').name,
                    'cancellation_policy_str': resv_obj.cancellation_policy_str,
                    'special_request': resv_obj.special_req,
                    'currency': resv_obj.currency_id.name,
                    'provider_bookings': provider_bookings,
                    'total': resv_obj.total,
                })
            else:
                raise RequestException(1035)
            return ERR.get_no_error(new_vals)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    # def create_reservation(self, req, context={}):
    def create_booking_hotel_api(self, data, context):
        provider_data = data.get('provider_data', '')
        special_req = data.get('special_request', 'No Special Request')
        cancellation_policy = data.get('cancellation_policy', '')
        norm_str = data.get('norm_str', '')

        passengers_data = copy.deepcopy(data['passengers'])  # waktu create passenger fungsi odoo field kosong di hapus cth: work_place

        context['agent_id'] = self.sudo().env['res.users'].browse(context['co_uid']).agent_id.id
        context['ho_id'] = context.get('co_ho_id') and context['co_ho_id'] or self.sudo().env['res.users'].browse(
            context['co_uid']).ho_id.id

        for idx, pax in enumerate(data['passengers']):
            pax.update({
                'sequence': idx,
                'gender': 'male' if pax['title'] in ['MR', 'MSTR'] else 'female'
            })

        booker_obj = self.env['tt.reservation.hotel'].create_booker_api(data['booker'], context)
        contact_obj = self.env['tt.reservation.hotel'].create_contact_api(data['contact'][0], booker_obj, context)
        list_passenger_value = self.env['tt.reservation.hotel'].create_passenger_value_api(data['passengers'])
        list_customer_id = self.env['tt.reservation.hotel'].create_customer_api(data['passengers'], context,
                                                                                booker_obj.seq_id, contact_obj.seq_id)

        # fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
        for idx, rec in enumerate(list_passenger_value):
            rec[2].update({
                'customer_id': list_customer_id[idx].id
            })
            if passengers_data[idx].get('description'):
                rec[2].update({
                    'description': passengers_data[idx]['description']
                })

        for psg in list_passenger_value:
            util.pop_empty_key(psg[2])

        backend_hotel_obj = self.env['test.search'].get_backend_object(data['price_codes'][0]['provider'], data['hotel_obj']['id'])
        vals = self.env['test.search'].prepare_resv_value(backend_hotel_obj, data['hotel_obj'], data['checkin_date'], data['checkout_date'],
                                                          data['price_codes'],
                                                          booker_obj, contact_obj, provider_data, special_req, data['passengers'],
                                                          context['ho_id'], context['agent_id'], cancellation_policy,
                                                          context.get('hold_date', False))

        if data.get('member'):
            customer_parent_id = \
            self.env['tt.customer.parent'].search([('seq_id', '=', data['acquirer_seq_id'])], limit=1)[0]
        else:
            customer_parent_id = booker_obj.customer_parent_ids[0]

        customer_parent_type_id = customer_parent_id.customer_parent_type_id.id
        customer_parent_id = customer_parent_id.id

        vals.update({
            'user_id': context['co_uid'],
            'sid_booked': context['signature'],
            'booker_id': booker_obj.id,
            'contact_title': data['contact'][0]['title'],
            'contact_id': contact_obj.id,
            'contact_name': contact_obj.name,
            'contact_email': contact_obj.email,
            'contact_phone': contact_obj.phone_ids and "%s - %s" % (contact_obj.phone_ids[0].calling_code, contact_obj.phone_ids[0].calling_number) or '-',
            'passenger_ids': list_passenger_value,
            'customer_parent_id': context.get('co_customer_parent_id', False) or customer_parent_id,
            'customer_parent_type_id': context.get('co_customer_parent_type_id', False) or customer_parent_type_id,
        })

        resv_id = self.env['tt.reservation.hotel'].create(vals)
        resv_id.hold_date = context.get('hold_date', False)
        # resv_id.write({'passenger_ids': [(6, 0, [rec[0].id for rec in passenger_objs])]})

        ## CURRENCY 22 JUN - IVAN
        currency = ''
        for price_code in data['price_codes']:
            currency = price_code['currency']
        if currency:
            currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
            if currency_obj:
                resv_id.currency_id = currency_obj.id

        for price_obj in data['price_codes']:
            for room_rate in price_obj['rooms']:
                vendor_currency_id = self.env['res.currency'].sudo().search([('name', '=', room_rate['currency'])],
                                                                            limit=1).id
                provider_id = self.env['tt.provider'].search(
                    [('code', '=', self.env['test.search'].unmasking_provider(price_obj['provider']))], limit=1).id
                detail = self.env['tt.hotel.reservation.details'].sudo().create({
                    'provider_id': provider_id,
                    'reservation_id': resv_id.id,
                    'date': fields.Datetime.from_string(data['checkin_date']),
                    'date_end': fields.Datetime.from_string(data['checkout_date']),
                    'sale_price': float(room_rate['price_total']),
                    'prov_sale_price': float(room_rate['price_total_currency']),
                    'prov_currency_id': vendor_currency_id,
                    'room_name': room_rate['description'],
                    'room_vendor_code': price_obj['price_code'],
                    'room_type': room_rate['type'],
                    'meal_type': price_obj['meal_type'],
                    'commission_amount': float(room_rate.get('commission', 0)),
                    # 'supplements': ';; '.join([json.dumps(x) for x in room_rate['supplements']]),
                    'supplements': ';; '.join([x['name'] for x in room_rate['supplements']]),
                })
                self.env.cr.commit()
                total_price = 0
                for charge_id in room_rate['nightly_prices']:
                    charge_id_price = 0
                    for sc_per_night in charge_id['service_charges']:
                        charge_id_price += sc_per_night['total'] if sc_per_night['charge_type'] in ['FARE', 'TAX',
                                                                                                    'ROC'] else 0
                    total_price += charge_id_price
                    self.env['tt.room.date'].sudo().create({
                        'detail_id': detail.id,
                        'date': charge_id['date'],
                        'sale_price': charge_id_price,  # charge_id['price_currency'],
                        'commission_amount': charge_id['commission'],
                        'meal_type': '',
                    })
                    # Merge Jika Room type yg sama 2
                    for scs in charge_id['service_charges']:
                        scs.update({
                            'resv_hotel_id': resv_id.id,
                            'total': scs['amount'] * scs['pax_count'],
                            'currency_id': self.env['res.currency'].get_id(scs.get('currency'), default_param_idr=True),
                            'foreign_currency_id': self.env['res.currency'].get_id(scs.get('foreign_currency'),
                                                                                   default_param_idr=True),
                            'description': '0',
                            'ho_id': context.get('co_ho_id') and context['co_ho_id'] or (
                                resv_id.ho_id.id if resv_id.ho_id else '')
                        })
                        self.env['tt.service.charge'].create(scs)

                detail.sale_price = total_price
        # resv_id.total = total_rate

        # Create provider_booking_ids
        vend_hotel = self.env['tt.provider.hotel'].create({
            'provider_id': provider_id or '',
            'booking_id': resv_id.id,
            'pnr': '0',
            'pnr2': '',
            'balance_due': resv_id.total_nta,
            'total_price': resv_id.total_nta,
            'checkin_date': data['checkin_date'],
            'checkout_date': data['checkout_date'],
            'hotel_id': resv_id.hotel_id.id,
            'hotel_name': resv_id.hotel_name,
            'hotel_address': resv_id.hotel_address,
            'hotel_city': resv_id.hotel_city,
            'hotel_phone': resv_id.hotel_phone,
            'sid': context['sid'],
        })

        vend_hotel.create_service_charge(resv_id.sale_service_charge_ids)

        resv_id.action_booked(context)

        ## PAKAI VOUCHER
        if data.get('voucher'):
            resv_id.voucher_code = data['voucher']['voucher_reference']
        
        if context.get('co_job_position_rules'):
            if context['co_job_position_rules'].get('callback'):
                if context['co_job_position_rules']['callback'].get('source'):
                    if context['co_job_position_rules']['callback']['source'] == 'ptr':
                        third_party_data = copy.deepcopy(context['co_job_position_rules']['hotel'])
                        third_party_data.update({
                            "callback": context['co_job_position_rules']['callback'],
                            "source": context['co_job_position_rules']['callback']['source']
                        })
                        resv_id.update({
                            "third_party_webhook_data": json.dumps(third_party_data)
                        })
        
        return self.get_booking(resv_id.id, context)

    def action_done_hotel_api(self, data, context):
        book_id = data['book_id']
        acq_id = data['acq_id']
        issued_res = data['issued_result']

        resv_obj = self.search([('name', '=', book_id)], limit=1)[0]
        resv_obj.sid_issued = context['signature']
        resv_obj.issued_uid = context['co_uid']

        if acq_id:
            self.env['tt.reservation'].payment_reservation_api('hotel', {
                'book_id': resv_obj.id,
                'member': acq_id['member'],
                'acquirer_seq_id': acq_id['acquirer_seq_id'],
            }, context)

        # Matikan Part ini agar csc tidka tercatat di resv ny juga START
        # for pax in resv_obj.passenger_ids:
        #     for csc in pax.channel_service_charge_ids:
        #         csc.resv_hotel_id = resv_obj.id
        #         csc.total = csc.amount * csc.pax_count
        #         resv_obj.total += csc.total
        # Mtikan Part ini END
        # if resv_obj.state not in ['issued', 'fail_issued']:
        #     resv_obj.sudo().action_issued(acq_id, co_uid)
        return resv_obj.sudo().action_done(issued_res)

    def get_booking_hotel_api(self, data, context):
        return self.get_booking(data, context)

    def payment_hotel_api(self, data, context):
        return self.env['tt.reservation'].payment_reservation_api('hotel', data, context)
    # Pindahan dari test.search END

    def update_cost_service_charge_hotel_api(self, data, context):
        return data

    def get_passenger_pricing_breakdown(self):
        pax_list = []
        for rec in self.room_detail_ids:
            pax_data = {
                'passenger_name': rec.room_name,
                'pnr_list': []
            }
            for rec2 in self.provider_booking_ids.filtered(lambda x: x.pnr == rec.issued_name):
                pax_pnr_data = {
                    'pnr': rec2.pnr,
                    'ticket_number': '',
                    'currency_code': rec2.currency_id and rec2.currency_id.name or '',
                    'provider': rec2.provider_id and rec2.provider_id.name or '',
                    'carrier_name': self.carrier_name or '',
                    'agent_nta': 0,
                    'agent_commission': 0,
                    'parent_agent_commission': 0,
                    'ho_nta': 0,
                    'ho_commission': 0,
                    'total_commission': 0,
                    'upsell': 0,
                    'discount': 0,
                    'fare': 0,
                    'tax': 0,
                    'grand_total': 0
                }
                for rec3 in rec2.cost_service_charge_ids:
                    pax_pnr_data['ho_nta'] += rec3.amount
                    if rec3.charge_code != 'rac':
                        pax_pnr_data['agent_nta'] += rec3.amount
                    if rec3.charge_type == 'RAC' and rec3.charge_code == 'rac':
                        pax_pnr_data['agent_commission'] -= rec3.amount
                    if rec3.charge_type == 'RAC':
                        pax_pnr_data['total_commission'] -= rec3.amount
                    if rec3.charge_type != 'RAC':
                        pax_pnr_data['grand_total'] += rec3.amount
                    if rec3.charge_type == 'FARE':
                        pax_pnr_data['fare'] += rec3.amount
                    if rec3.charge_type == 'TAX':
                        pax_pnr_data['tax'] += rec3.amount
                    if rec3.charge_type == 'ROC':
                        pax_pnr_data['upsell'] += rec3.amount
                pax_data['pnr_list'].append(pax_pnr_data)
            pax_list.append(pax_data)
        return pax_list

    # Copycat dari create_refund_airline_api
    def create_refund_hotel_api(self, data, context):
        try:
            if data.get('book_id'):
                hotel_obj = self.env['tt.reservation.hotel'].browse(data['book_id'])
            elif data.get('order_number'):
                hotel_obj = self.env['tt.reservation.hotel'].search([('name', '=', data['order_number'])])
            else:
                raise Exception('Book ID or Order Number is not found')

            # VIN: 2021/03/02: admin fee tdak bisa di hardcode
            # TODO: refund type tdak boleh hardcode lagi, jika frontend sdah support pilih refund type regular / quick
            ref_type = data.get('refund_type', 'regular')
            admin_fee_obj = self.env['tt.refund'].get_refund_admin_fee_rule(hotel_obj.agent_id.id, ref_type)
            if ref_type == 'quick':
                refund_type = self.env.ref('tt_accounting.refund_type_quick_refund').id
            else:
                refund_type = self.env.ref('tt_accounting.refund_type_regular_refund').id
            # refund_type = 'regular'

            refund_line_ids = []
            # Untuk Hotel krena jmlah pax tidak valid?
            pax_price = hotel_obj.total
            total_charge_fee = hotel_obj.total - sum(x['received_amount'] for x in data['provider_bookings'])
            pax = hotel_obj.passenger_ids[0]
            line_obj = self.env['tt.refund.line'].create({
                'name': (pax.title or '') + ' ' + (pax.name or ''),
                'birth_date': pax.birth_date,
                'pax_price': pax_price,
                'charge_fee': total_charge_fee,
            })
            refund_line_ids.append(line_obj.id)

            res_vals = {
                'ho_id': hotel_obj.ho_id.id,
                'agent_id': hotel_obj.agent_id.id,
                'customer_parent_id': hotel_obj.customer_parent_id.id,
                'booker_id': hotel_obj.booker_id.id,
                'currency_id': hotel_obj.currency_id.id,
                'service_type': hotel_obj.provider_type_id.id,
                'refund_type_id': refund_type,
                'admin_fee_id': admin_fee_obj.id,
                'referenced_document': hotel_obj.name,
                'referenced_pnr': hotel_obj.pnr,
                'res_model': hotel_obj._name,
                'res_id': hotel_obj.id,
                # 'booking_desc': hotel_obj.get_aftersales_desc(), #Di Airline sperti ini
                'booking_desc': data.get('refund_code'),
                'notes': data.get('notes') and data['notes'] or '',
                'created_by_api': True,
            }
            res_obj = self.env['tt.refund'].create(res_vals)
            res_obj.confirm_refund_from_button()
            res_obj.update({
                'refund_line_ids': [(6, 0, refund_line_ids)],
            })
            res_obj.send_refund_from_button()
            res_obj.validate_refund_from_button()
            res_obj.finalize_refund_from_button()
            response = {
                'refund_id': res_obj.id,
                'refund_number': res_obj.name
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Create Refund Hotel API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Create Refund Hotel API, %s' % traceback.format_exc())
            return ERR.get_error(1030)


class ServiceCharge(models.Model):
    _inherit = "tt.service.charge"

    provider_hotel_booking_id = fields.Many2one('tt.provider.hotel', 'Resv. Detail')
    resv_hotel_id = fields.Many2one('tt.reservation.hotel', 'Hotel', ondelete='cascade', index=True, copy=False)
