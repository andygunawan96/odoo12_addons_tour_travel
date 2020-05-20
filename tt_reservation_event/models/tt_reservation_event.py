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
    event_name = fields.Char('Event Name')
    event_product_uuid = fields.Char('Product Type UUID')
    # visit_date = fields.Datetime('Visit Date')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_event_id', string="Service Charge", readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.event', 'booking_id', string="Provider Booking", readonly=True, states={'draft': [('readonly', False)]})
    # passenger_ids = fields.One2many('tt.reservation.passenger.event', 'booking_id', string="Passengers")

    information = fields.Text('Additional Information')
    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')
    voucher_url_ids = fields.One2many('tt.reservation.event.voucher', 'booking_id')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_event.tt_provider_type_event'))
    option_ids = fields.One2many('tt.reservation.event.option', 'booking_id', 'Options')
    # extra_question_ids = fields.One2many('tt.reservation.event.extra.question', 'reservation_id', 'Extra Question')

    @api.model
    def create(self, vals_list):
        try:
            vals_list['user_id'] = self.env.user.id
        except:
            pass
        return super(ReservationEvent, self).create(vals_list)

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
        # Create Order Number
        order_number = self.env['ir.sequence'].next_by_code(self._name)
        self.name = order_number
        self.write({
            'state': 'booked',
            'booked_uid': self.env.user.id,
            'booked_date': datetime.now(),
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

    def action_adding_new_answer(self, data, context):
        reservation_id = data['reservation_id']
        for i in data['question_answer']:
            temp_dict = {
                'reservation_id': reservation_id,
                'extra_question_id': i['extra_question_id'],
                'answer': i['answer']
            }
            self.env['tt.reservation.event.extra.question'].create(temp_dict)

    def create_booking_event_api(self, req, context):
        try:
            #recieve and handling data
            booker_data = req.get('booker') and req['booker'] or False
            contacts_data = req.get('contact') and req['contact'] or False
            event_code = req.get('event_code') and req['event_code'] or False
            event_option_codes = req.get('event_option_codes') and req['event_option_codes'] or False
            provider = req.get('provider') and req['provider'] or False

            #create all dependencies
            booker_obj = self.create_booker_api(booker_data, context)
            contact_obj = self.create_contact_api(contacts_data[0], booker_obj, context)

            #get all necessary data
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            event_id = self.env['tt.master.event'].sudo().search([('uuid', '=', event_code)], limit=1)
            event_options = []
            for i in event_option_codes:
                event_options.append( self.env['tt.event.option'].sudo().search([('option_code', '=', i['option_code'])]))

            #build temporary dict
            temp_main_dictionary = {
                'event_id': event_id.id,
                'event_name': event_id and event_id.name or req.get('event_name'),
                'provider_name': ','.join([provider_id.name,]),
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_title': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids[0].phone_number,
            }
            book_obj = self.create(temp_main_dictionary)

            # Create Provider Ids
            self.env['tt.provider.event'].create({
                'provider_id': provider_id.id,
                'booking_id': book_obj.id,
                'balance_due': book_obj.id, #di PNR
                'event_id': event_id and event_id.id or False,
                'event_product_id': event_id.id,
                'event_product': event_id and event_id.name or req.get('event_name'),
                'event_product_uuid': event_id and event_id.uuid or req.get('event_id'),
            })

            #fill child table of resrevation event
            for opt_obj in event_options:
                temp_option_dict = {
                    'booking_id': book_obj.id,
                    'event_option_id': opt_obj.id,
                }
                option_obj = self.env['tt.reservation.event.option'].create(temp_option_dict)

                # a = 0
                # for j in opt_obj:
                #     new_j = req['event_option_codes'][a]['extra_question']
                #     temp_extra_question_dict = {
                #         'reservation_event_option_id': book_obj.id,
                #         'extra_question_id': j['question_id'],
                #         'answer': j['answer']
                #     }
                #     self.env['tt.reservation.event.extra.question'].create(temp_extra_question_dict)
                #     a += 1

            #Create Service Charge
            for scs1 in req.get('service_charges') or []:
                for scs in scs1:
                    self.env['tt.service.charge'].create({
                        'booking_event_id': book_obj.id,
                        'charge_code': scs['charge_code'],
                        'charge_type': scs['charge_type'],
                        'pax_type': scs['pax_type'],
                        'pax_count': scs['pax_count'],
                        'amount': scs['amount'],
                        'foreign_amount': scs['foreign_amount'],
                        'total': scs['amount'] * scs['pax_count'],
                        'description': book_obj.pnr and book_obj.pnr or '',
                        'commission_agent_id': scs['commission_agent_id'],
                    })

            book_obj.action_booked()
            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_ids': provider_id.id,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def set_pnr_booking_event_api(self, req, context):
        booking_obj = self.search([('name', '=', req['order_number'])], limit=1)
        if booking_obj:
            booking_obj.update({'pnr': req['pnr'], 'hold_date': req['hold_date']})
            for rec in req['providers']:
                for prov in booking_obj.provider_booking_ids.filtered(lambda x: x.provider_id.name == rec):
                    prov.update({
                        'pnr': '',
                        'pnr2': '',
                        'status': 'booked',
                        'sid_booked': '',
                        'booked_uid': '',
                        'booked_date': '',
                    })
            return ERR.get_no_error({
                'book_id': booking_obj.id,
                'order_number': booking_obj.name,
                'status': booking_obj.state,
                'hold_date': booking_obj.hold_date,
                'PNR': booking_obj.pnr,
            })
        else:
            return ERR.get_error(1004)

    def to_dict(self):
        return {
            'order_number': self.name,
            'providers': [{'provider': rec.provider_id.code, 'pnr': self.pnr} for rec in self.provider_booking_ids],
            'event_name': self.event_name,
            'event_location': self.event_id and [{
                'name': rec.name,
                'address': rec.address,
                'city': rec.city_name,
                'country': rec.country_name,
                'lat': '',
                'long': '',
            } for rec in self.event_id.location_ids] or [],
            'description': self.event_id and self.event_id.description or '',
            'options': [self.option_ids and {
                'image_url': '',
                'name': rec.event_option_id.grade,
                'description': rec.event_option_id.description,
                'qty': 1,
                'currency': rec.event_option_id.currency_id.name,
                'price': rec.event_option_id.price,
            } for rec in self.option_ids] or [],
            'notes': '',
            'booker': self.booker_id.read(),
            'contact': self.contact_id.read(),
            'status': self.state,
        }

    def get_booking_from_backend(self, data, context):
        try:
            resv_obj = self.get_book_obj(data.get('order_id'), data.get('order_number'))
            if resv_obj:
                res = resv_obj.to_dict()
                return ERR.get_no_error(res)
            else:
                raise RequestException(1003)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()


class TtReservationEventOption(models.Model):
    _name = 'tt.reservation.event.option'
    _description = 'Rodex Event Model'

    booking_id = fields.Many2one('tt.reservation.event', "Reservation ID")
    event_option_id = fields.Many2one('tt.event.option', 'Event Option')
    description = fields.Char('Description')
    extra_question_ids = fields.One2many('tt.reservation.event.extra.question', 'reservation_event_option_id', 'Extra Question')
    ticket_number = fields.Char('Ticket Number')
    ticket_file_ids = fields.Many2many('tt.upload.center', 'reservation_event_ticket_rel', 'reservation_event_id', 'ticket_id', 'Tickets')

class TtReservationEventVoucher(models.Model):
    _name = 'tt.reservation.event.voucher'
    _description = 'Rodex Event Model'

    name = fields.Char('URL')
    booking_id = fields.Many2one('tt.reservation.event', 'Reservation')

class TtReservationExtraQuestion(models.Model):
    _name = 'tt.reservation.event.extra.question'
    _description = 'Rodex Event Model'

    reservation_event_option_id = fields.Many2one('tt.reservation.event', 'Reservation ID')
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
