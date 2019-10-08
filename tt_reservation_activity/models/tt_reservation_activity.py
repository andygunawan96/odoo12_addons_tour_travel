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


class ActivityResendVoucher(models.TransientModel):
    _name = "activity.voucher.wizard"
    _description = 'Rodex Model'

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

    user_email_add = fields.Char(string="User Email", default=get_default_email)
    provider_name = fields.Char(string="Provider", default=get_default_provider, readonly="1")
    pnr = fields.Char(string="PNR", default=get_default_pnr, readonly="1")

    def resend_voucher_api(self):
        req = {
            'provider': self.provider_name,
            'order_id': self.pnr,
            'user_email_address': self.user_email_add
        }
        res = self.env['tt.activity.api.con'].resend_voucher(req)
        if res['response'].get('success'):
            # self.env['msg.wizard'].raise_msg("The Voucher has been Resent Successfully!")
            context = self.env.context
            new_obj = self.env[context['active_model']].browse(context['active_id'])
            # new_obj.message_post(body='Resent Voucher Email.')
        else:
            raise UserError(_('Resend Voucher Failed!'))


class TtReservationActivityOption(models.Model):
    _name = 'tt.reservation.activity.option'
    _description = 'Rodex Model'

    name = fields.Char('Information')
    value = fields.Char('Value')
    booking_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')


class ReservationActivity(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.activity'
    _order = 'id DESC'
    _description = 'Rodex Model'

    booking_uuid = fields.Char('Booking UUID')

    user_id = fields.Many2one('res.users', 'User')
    senior = fields.Integer('Senior')

    acceptance_date = fields.Datetime('Acceptance Date')
    rejected_date = fields.Datetime('Rejected Date')
    refund_date = fields.Datetime('Refund Date')

    activity_id = fields.Many2one('tt.master.activity', 'Activity')
    activity_product_id = fields.Many2one('tt.master.activity.lines', 'Activity Product')
    activity_name = fields.Char('Activity Name')
    activity_product = fields.Char('Product Type')
    activity_product_uuid = fields.Char('Product Type Uuid')
    visit_date = fields.Datetime('Visit Date')
    timeslot = fields.Char('Timeslot')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_activity_id', string='Prices')
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', domain=[('res_model','=','tt.reservation.activity')])
    provider_booking_ids = fields.One2many('tt.provider.activity', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.activity', 'booking_id', string='Passengers')

    information = fields.Text('Additional Information')
    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_activity.tt_provider_type_activity'))
    option_ids = fields.One2many('tt.reservation.activity.option', 'booking_id', 'Options')

    def _calc_grand_total(self):
        for rec in self:
            rec.total = 0
            rec.total_fare = 0
            rec.total_tax = 0
            rec.total_discount = 0
            rec.total_commission = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_code == 'fare':
                    rec.total_fare += line.total
                if line.charge_code == 'tax':
                    rec.total_tax += line.total
                if line.charge_code == 'disc':
                    rec.total_discount += line.total
                if line.charge_code == 'r.oc':
                    rec.total_commission += line.total

            rec.total = rec.total_fare + rec.total_tax + rec.total_discount
            rec.total_nta = rec.total - rec.total_commission

    def action_booked(self):
        self.write({
            'state': 'booked',
            'date': datetime.now(),
            'booked_uid': self.env.user.id,
            # 'hold_date': datetime.now() + relativedelta(days=1),
        })

    def get_datetime(self, utc=0):
        now_datetime = datetime.now() + timedelta(hours=utc)
        # adjustment server time
        # now_datetime = adjustment_datetime(now_datetime, 0, 7, 6)
        if utc >= 0:
            utc = '+{}'.format(utc)
        return '{} (GMT{})'.format(now_datetime.strftime('%d-%b-%Y %H:%M:%S'), utc)

    def send_notif_current_balance(self, balance, state, pnr):
        data = {
            'code': 9901,
            'message': 'PNR %s is now %s, current balance: %s' % (pnr, state, balance),
            'provider': self.provider_name,
        }
        GatewayConnector().telegram_notif_api(data, {})

    def action_issued(self):
        req = {
            'uuid': self.booking_uuid,
            'provider': self.provider_name,
            'order_id': self.id,
            'pnr': self.pnr,
        }
        res = self.env['tt.activity.api.con'].update_booking(req)

    def action_waiting(self):
        self.write({
            'state': 'in_progress',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id,
        })

    def action_calc_prices(self):
        self._calc_grand_total()

    def action_approved(self):
        self.write({
            'state': 'approved',
            'acceptance_date': datetime.now(),
        })
        self.message_post(body='Order APPROVED')

    def action_rejected(self):
        self.write({
            'state': 'rejected',
            'rejected_date': datetime.now(),
        })
        self.message_post(body='Order REJECTED')

    def action_expired(self):
        self.write({
            'state': 'cancel2',
            'expired_date': datetime.now(),
        })
        self.message_post(body='Order EXPIRED')

    def action_refunded(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
        })

        # todo create refund ledger
        # self._create_refund_ledger_activity()

        self.message_post(body='Order REFUNDED')

    def action_cancelled(self):
        for rec in self.invoice_id:
            rec.action_cancel()
        self._create_anti_ledger_activity()
        self._create_anti_commission_ledger_activity()
        self.write({
            'state': 'cancel',
            'cancelled_date': datetime.now(),
            'cancelled_uid': self.env.user.id
        })
        self.message_post(body='Order CANCELLED')

    def action_failed(self, booking_id, error_msg):
        booking_rec = self.browse(booking_id)
        booking_rec.write({
            'state': 'fail_issued',
            'error_msg': error_msg
        })
        self.send_push_notif('failed')
        return {
            'error_code': 0,
            'error_msg': False,
            'response': 'action_fail_booking'
        }

    def action_failed_sync(self):
        self.write({
            'state': 'fail_issued',
        })
        self.message_post(body='Order FAILED')
        self.send_push_notif('failed')

    def action_done(self):
        self.write({
            'state': 'done',
        })
        self.message_post(body='Order DONE')
        self.send_push_notif('done')

    def call_create_invoice(self, acquirer_id):
        _logger.info('Creating Invoice for ' + self.name)

    def update_pnr_data(self, book_id, pnr):
        provider_objs = self.env['tt.provider.activity'].search([('booking_id', '=', book_id)])
        for rec in provider_objs:
            rec.sudo().write({
                'pnr': pnr
            })
            cost_service_charges = self.env['tt.service.charge'].search([('provider_activity_booking_id', '=', rec.id)])
            for rec2 in cost_service_charges:
                rec2.sudo().write({
                    'description': pnr
                })

        ledger_objs = self.env['tt.ledger'].search([('res_id', '=', book_id),('res_model','=',self._name)])
        for rec in ledger_objs:
            rec.sudo().write({
                'pnr': pnr
            })

    def update_booking_by_api(self, req, api_context):
        try:
            booking_id = req['order_id'],
            prices = req['prices']
            book_info = req['book_info']
            if req.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', req['seq_id'])])
                if not acquirer_id:
                    raise RequestException(1017)
            else:
                raise RequestException(1017)

            booking_obj = self.browse(booking_id)
            booking_obj.write({
                'pnr': book_info.get('code') and book_info['code'] or '',
                'booking_uuid': book_info.get('uuid') and book_info['uuid'] or '',
                'sid_booked': api_context.get('sid') and api_context['sid'] or '',
                'state': book_info['status']
            })
            booking_obj.update_pnr_data(booking_id, book_info['code'])
            booking_obj.calculate_service_charge()
            self.env.cr.commit()
            booking_obj.call_create_invoice(acquirer_id)

            if not api_context or api_context['co_uid'] == 1:
                api_context['co_uid'] = booking_obj.booked_uid.id

            response = {
                'order_number': booking_obj.name
            }

            res = ERR.get_no_error(response)
            return res

        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                booking_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                booking_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1005)

    def update_booking_by_api2(self, booking_id, book_info):
        booking_obj = self.browse(booking_id)
        booking_obj.write({
            'state': book_info['status']
        })
        self.env.cr.commit()
        return True

    def send_push_notif(self, type):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        obj_id = str(self.id)
        model = 'tt.reservation.activity'
        url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model
        if type == 'issued':
            desc = 'Activity Issued ' + self.name + ' From ' + self.agent_id.name
        elif type == 'failed':
            desc = 'FAILED Activity Issued ' + self.name + ' From ' + self.agent_id.name
        elif type == 'done':
            desc = 'Activity CONFIRMED BY VENDOR ' + self.name + ' From ' + self.agent_id.name
        else:
            desc = 'Activity Booking ' + self.name + ' From ' + self.agent_id.name

        data = {
            'code': 9901,
            'message': desc,
            'provider': self.provider_name,
        }
        GatewayConnector().telegram_notif_api(data, {})

    # to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for p_sc in provider.cost_service_charge_ids:
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                if p_charge_type != 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_type):
                        sc_value[p_pax_type][p_charge_type] = {}
                        sc_value[p_pax_type][p_charge_type].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_type
                    c_code = p_charge_type.lower()
                elif p_charge_type == 'RAC':
                    if not sc_value[p_pax_type].get(p_charge_code):
                        sc_value[p_pax_type][p_charge_code] = {}
                        sc_value[p_pax_type][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pax_type][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
                    'pax_count': p_sc.pax_count,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_pax_type][c_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_pax_type][c_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_pax_type][c_type]['foreign_amount'] + p_sc.foreign_amount,
                })

            values = []
            for p_type, p_val in sc_value.items():
                for c_type, c_val in p_val.items():
                    curr_dict = {}
                    curr_dict['pax_type'] = p_type
                    curr_dict['booking_activity_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict.update(c_val)
                    values.append((0, 0, curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def create_booking_activity_api(self, req, context):
        try:
            booker_data = req.get('booker_data') and req['booker_data'] or False
            contacts_data = req.get('contacts_data') and req['contacts_data'] or False
            passengers = req.get('passengers_data') and req['passengers_data'] or False
            option = req.get('option') and req['option'] or False
            search_request = req.get('search_request') and req['search_request'] or False
            file_upload = req.get('file_upload') and req['file_upload'] or False
            provider = req.get('provider') and req['provider'] or ''
            pricing = req.get('pricing') and req['pricing'] or []
            try:
                agent_obj = self.env['tt.customer'].browse(int(booker_data['booker_id'])).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            if req['force_issued']:
                is_enough = self.env['tt.agent'].check_balance_limit_api(agent_obj.id, req['amount'])
                if is_enough['error_code'] != 0:
                    _logger.error('Balance not enough')
                    raise RequestException(1007)

            header_val = search_request
            booker_obj = self.create_booker_api(booker_data, context)
            contact_data = contacts_data[0]
            contact_objs = []
            for con in contacts_data:
                contact_objs.append(self.create_contact_api(con, booker_obj, context))

            contact_obj = contact_objs[0]

            activity_type_id = self.env['tt.master.activity.lines'].sudo().search([('uuid', '=', search_request['product_type_uuid'])])
            if activity_type_id:
                activity_type_id = activity_type_id[0]
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', search_request['provider'])])
            if provider_id:
                provider_id = provider_id[0]

            header_val.update({
                'contact_id': contact_obj.id,
                'booker_id': booker_obj.id,
                'contact_name': contact_data['first_name'] + ' ' + contact_data['last_name'],
                'contact_email': contact_data.get('email') and contact_data['email'] or '',
                'contact_phone': contact_data.get('mobile') and str(contact_data['calling_code']) + str(contact_data['mobile']),
                'state': 'booked',
                'date': datetime.now(),
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
                'activity_id': activity_type_id.activity_id.id,
                'activity_product_id': activity_type_id.id,
                'visit_date': datetime.strptime(search_request['visit_date'], '%Y-%m-%d').strftime('%d %b %Y'),
                'activity_name': activity_type_id.activity_id.name,
                'activity_product': activity_type_id.name,
                'activity_product_uuid': search_request['product_type_uuid'],
                'senior': search_request['senior'],
                'adult': search_request['adult'],
                'child': search_request['child'],
                'infant': search_request['infant'],
                'transport_type': 'activity',
                'provider_name': activity_type_id.activity_id.provider_id.code,
                'file_upload': file_upload,
            })

            if search_request.get('timeslot'):
                header_val.update({
                    'timeslot': str(search_request['timeslot']['startTime']) + ' - ' + str(search_request['timeslot']['endTime']),
                })

            if not activity_type_id.instantConfirmation:
                header_val.update({
                    'information': 'On Request (max. 3 working days)',
                })

            # create header & Update customer_parent_id
            book_obj = self.sudo().create(header_val)

            if req.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', req['seq_id'])])
            else:
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id

            book_obj.sudo().write({
                'customer_parent_id': customer_parent_id,
            })

            if option['perBooking']:
                for rec in option['perBooking']:
                    self.env['tt.reservation.activity.option'].sudo().create({
                        'name': rec['name'],
                        'value': str(rec['value']),
                        'booking_id': book_obj.id
                    })

            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id, ['title', 'pax_type', 'api_data', 'sku_real_id'])

            for idx, psg in enumerate(pax_ids):
                temp_obj = psg[0]
                extra_dict = psg[1]
                vals = temp_obj.copy_to_passenger()
                vals.update({
                    'booking_id': book_obj.id,
                    'title': extra_dict['title'],
                    'pax_type': extra_dict['pax_type'],
                    'activity_sku_id': extra_dict.get('sku_real_id', 0),
                    'sequence': idx + 1,
                })
                psg_obj = self.env['tt.reservation.passenger.activity'].sudo().create(vals)
                if extra_dict.get('api_data'):
                    for temp_psg_opt in extra_dict['api_data']:
                        pax_opt_vals = {
                            'name': temp_psg_opt['name'],
                            'value': temp_psg_opt['value'],
                            'activity_passenger_id': psg_obj.id
                        }
                        self.env['tt.reservation.passenger.activity.option'].sudo().create(pax_opt_vals)

            # book_obj.customer_parent_id = booker_obj.customer_parent_id.id
            provider_activity_vals = {
                'booking_id': book_obj.id,
                'activity_id': activity_type_id.activity_id.id,
                'activity_product_id': activity_type_id.id,
                'activity_product': activity_type_id.name,
                'activity_product_uuid': search_request['product_type_uuid'],
                'provider_id': provider_id.id,
                'visit_date': search_request['visit_date'],
                'balance_due': req['amount'],
            }

            provider_activity_obj = self.env['tt.provider.activity'].sudo().create(provider_activity_vals)
            for psg in book_obj.passenger_ids:
                vals = {
                    'provider_id': provider_activity_obj.id,
                    'passenger_id': psg.id,
                    'pax_type': psg.pax_type,
                    'ticket_number': psg.activity_sku_id.sku_id
                }
                self.env['tt.ticket.activity'].sudo().create(vals)
            provider_activity_obj.delete_service_charge()
            for rec in pricing:
                provider_activity_obj.create_service_charge(rec)

            book_obj.action_booked_activity(context)
            context['order_id'] = book_obj.id
            if req['force_issued']:
                book_obj.action_issued_activity(context)

            self.env.cr.commit()

            response = {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'status': book_obj.state,
            }

            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def _get_pricelist_ids(self, service_charge_summary):
        res = []
        for rec in service_charge_summary:
            res.append(rec['activity_id'])
        return res

    def get_vouchers_button_api(self, obj_id, co_uid):
        obj = self.env['tt.reservation.activity'].browse(obj_id)
        req = {
            'order_number': obj.name,
            'uuid': obj.booking_uuid,
            'pnr': obj.pnr,
            'provider': obj.provider_name
        }
        res2 = self.env['tt.activity.api.con'].get_vouchers(req)

        try:
            ids = []
            for rec in res2['response']['ticket']:
                if res2['response']['provider'] == 'globaltix':
                    attachment_value = {
                        'name': 'Ticket.pdf',
                        'datas_fname': 'Ticket.pdf',
                        'res_model': 'tt.reservation.activity',
                        'res_id': obj.id,
                        'type': 'url',
                        'mimetype': res2['response']['format'],
                        'url': rec,
                    }

                if res2['response']['provider'] == 'bemyguest':
                    pdf_data = pickle.loads(rec.encode())
                    if not pdf_data:
                        return False

                    attachment_value = {
                        'name': 'Ticket.pdf',
                        'datas': base64.encodebytes(pdf_data),
                        'datas_fname': 'Ticket.pdf',
                        'res_model': 'tt.reservation.activity',
                        'res_id': obj.id,
                        'type': 'binary',
                        'mimetype': 'application/x-pdf',
                    }

                attachment_obj = self.env['ir.attachment'].sudo().create(attachment_value)
                self.env.cr.commit()
                ids.append(attachment_obj.id)
            return ids
        except Exception:
            return False

    def resend_voucher_button(self):
        view = self.env.ref('tt_reservation_activity.activity_voucher_wizard')
        view_id = view and view.id or False
        context = dict(self._context or {})
        return {
            'name': 'Resend Voucher to Email',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'activity.voucher.wizard',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def get_vouchers_button(self):
        req = {
            'uuid': self.booking_uuid,
            'pnr': self.pnr,
            'provider': self.provider_name
        }
        res2 = self.env['tt.activity.api.con'].get_vouchers(req)

        for rec in res2['response']['ticket']:
            if res2['response']['provider'] == 'klook':
                attachment_value = {
                    'name': 'Ticket.pdf',
                    'datas_fname': 'Ticket.pdf',
                    'res_model': 'tt.reservation.activity',
                    'res_id': self.id,
                    'type': 'url',
                    'mimetype': res2['response']['format'],
                    'url': rec,
                }

            if res2['response']['provider'] == 'globaltix':
                attachment_value = {
                    'name': 'Ticket.pdf',
                    'datas_fname': 'Ticket.pdf',
                    'res_model': 'tt.reservation.activity',
                    'res_id': self.id,
                    'type': 'url',
                    'mimetype': res2['response']['format'],
                    'url': rec,
                }

            if res2['response']['provider'] == 'bemyguest':
                pdf_data = pickle.loads(rec)
                if not pdf_data:
                    return False

                attachment_value = {
                    'name': 'Ticket.pdf',
                    'datas': base64.encodestring(pdf_data),
                    'datas_fname': 'Ticket.pdf',
                    'res_model': 'tt.reservation.activity',
                    'res_id': self.id,
                    'type': 'binary',
                    'mimetype': 'application/x-pdf',
                }

            self.env['ir.attachment'].sudo().create(attachment_value)
            self.env.cr.commit()
        self.action_done()

    def get_vouchers_by_api2(self, req, ctx):
        booking_obj = self.env['tt.reservation.activity'].search([('name', '=', req['order_number'])])
        temp = self.env['ir.attachment'].search([('res_model', '=', 'tt.reservation.activity'), ('res_id', '=', booking_obj[0]['id'])]).ids

        if not ctx or ctx['co_uid'] == 1:
            ctx['co_uid'] = booking_obj.booked_uid.id

        if not temp:
            temp = self.get_vouchers_button_api(booking_obj[0]['id'], ctx['co_uid'])

        result = []
        for tmp in temp:
            attachment = self.env['ir.attachment'].browse(tmp)
            if booking_obj.provider_name == 'globaltix':
                url = attachment.url
                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    pdf_data = r.content.encode('base64')
                    result.append(pdf_data.replace('\n', ''))
            elif booking_obj.provider_name == 'bemyguest':
                pdf_data = attachment.datas
                result.append(pdf_data.replace('\n', ''))

        return result

    def get_booking_for_vendor_by_api(self, data, context):
        try:
            order_number = data['order_number']

            self.env.cr.execute("""SELECT * FROM tt_reservation_activity WHERE name=%s""", (order_number,))
            activity_booking = self.env.cr.dictfetchall()

            if activity_booking:
                self.env.cr.execute("""SELECT * FROM tt_provider_activity WHERE booking_id=%s""", (activity_booking[0]['id'],))
                act_provider_ids = self.env.cr.dictfetchall()

                provider_obj = self.env['tt.provider'].browse(act_provider_ids[0]['provider_id'])
                req = {
                    'provider': provider_obj.code,
                    'uuid': activity_booking[0]['booking_uuid'],
                    'pnr': activity_booking[0]['pnr'],
                    'order_number': order_number,
                    'order_id': activity_booking[0]['id'],
                }
            else:
                req = {
                    'no_order_number': True
                }
            result = ERR.get_no_error(req)
            return result
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def get_booking_by_api(self, res, req, context):
        try:
            order_number = req['order_number']

            activity_booking = self.env['tt.reservation.activity'].search([('name', '=', order_number)])
            if activity_booking:
                activity_booking = activity_booking[0]

            book_option_ids = []
            for rec in activity_booking.option_ids:
                book_option_ids.append({
                    'name': rec.name,
                    'value': rec.value,
                })

            # self.env.cr.execute("""SELECT * FROM tt_service_charge WHERE booking_activity_id=%s""", (activity_booking[0]['id'],))
            # api_price_ids = self.env.cr.dictfetchall()
            passengers = []
            for rec in activity_booking.sudo().passenger_ids:
                passengers.append(rec.to_dict())
            contact = self.env['tt.customer'].browse(activity_booking.contact_id.id)

            master = self.env['tt.master.activity'].browse(activity_booking.activity_id.id)
            activity_details = {
                'name': master.name,
                'description': master.description,
                'highlights': master.highlights,
                'additionalInfo': master.additionalInfo,
                'safety': master.safety,
                'warnings': master.warnings,
                'priceIncludes': master.priceIncludes,
                'priceExcludes': master.priceExcludes,
            }
            master_line = self.env['tt.master.activity.lines'].search([('activity_id', '=', master.id), ('uuid', '=', activity_booking.activity_product_uuid)])
            if master_line:
                master_line = master_line[0]
            voucher_detail = {
                'voucher_validity': {
                    'voucher_validity_date': master_line.voucher_validity_date,
                    'voucher_validity_days': master_line.voucher_validity_days,
                    'voucher_validity_type': master_line.voucher_validity_type,
                },
                'voucherUse': master_line.voucherUse,
                'voucherRedemptionAddress': master_line.voucherRedemptionAddress,
                'cancellationPolicies': master_line.cancellationPolicies,
            }
            attachments = False
            if activity_booking.provider_name in ['bemyguest', 'globaltix']:
                attachments = self.env['ir.attachment'].search([('res_model', '=', 'tt.reservation.activity'), ('res_id', '=', activity_booking.id)]).ids

                # if not attachments:
                #     res2 = self.get_vouchers_button_api(activity_booking.id, self.env.user.id)
                #     if res2:
                #         attachments = res2

            if res.get('voucher_url') and not activity_booking.voucher_url:
                activity_booking.sudo().write({
                    'voucher_url': res['voucher_url']
                })

            if activity_booking.state not in ['done', 'rejected', 'cancel', 'cancel2']:
                activity_booking.sudo().write({
                    'state': res['status']
                })
                self.env.cr.commit()
                if attachments:
                    res.update({
                        'status': 'done',
                    })

            response = {
                'contacts': {
                    'email': activity_booking.contact_email,
                    'name': activity_booking.contact_name,
                    'phone': activity_booking.contact_phone,
                    'gender': contact.gender and contact.gender or '',
                    'marital_status': contact.marital_status and contact.marital_status or False,
                },
                'activity': {
                    'name': master.name,
                    'type': master_line.name,
                },
                'adults': activity_booking.adult,
                'children': activity_booking.child,
                'seniors': activity_booking.senior,
                'pnr': activity_booking.pnr,
                'visit_date': str(activity_booking.visit_date)[:10],
                'timeslot': activity_booking.timeslot and activity_booking.timeslot or False,
                'currencyCode': res['currencyCode'],
                'passengers': passengers,
                'name': order_number,
                'activity_details': activity_details,
                'voucher_detail': voucher_detail,
                'uuid': res.get('uuid') and res['uuid'] or '',
                'status': activity_booking.state,
                'attachment_ids': attachments,
                'booking_options': book_option_ids,
                'voucher_url': res.get('voucher_url') and res['voucher_url'] or False
            }
            result = ERR.get_no_error(response)
            return result
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def action_booked_activity(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }

        vals = {
            'state': 'booked',
            'booked_uid': api_context and api_context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': datetime.now() + relativedelta(days=1),
        }
        self.write(vals)

    def action_issued_activity(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        vals = {
            'state': 'issued',
            'issued_uid': api_context['co_uid'] or self.env.user.id,
            'issued_date': datetime.now(),
        }
        self.sudo().write(vals)
        for rec in self.provider_booking_ids:
            rec.action_create_ledger()
        self.send_push_notif('issued')

    def get_id(self, booking_number):
        row = self.env['tt.reservation.activity'].search([('name', '=', booking_number)])
        if not row:
            return ''
        return row.id

    def confirm_booking_webhook(self, req):
        order_id = req.get('order_id')
        if order_id:
            book_obj = self.sudo().search([('pnr', '=', order_id)], limit=1)
            book_obj = book_obj[0]
            if book_obj.state not in ['done', 'cancel', 'cancel2', 'refund']:
                book_obj.sudo().write({
                    'state': req.get('status') and req['status'] or 'pending',
                    'voucher_url': req.get('voucher_url') and req['voucher_url'] or ''
                })
        response = {
            'success': True
        }
        return ERR.get_no_error(response)

    def send_notif_update_status_activity(self, activity_booking, state):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        obj_id = str(activity_booking.id)
        model = 'tt.reservation.activity'
        url = base_url + '/web#id=' + obj_id + '&view_type=form&model=' + model

        desc = '<a href="{}">{}</a>'.format(url, activity_booking.name)

        if activity_booking.activity_name:
            try:
                desc += '\nName : ' + str(activity_booking.activity_name.decode('utf-8'))
            except:
                desc += '\nName : ' + str(activity_booking.activity_name.encode('utf-8'))
        else:
            desc += '\nName : ' + str(activity_booking.activity_name)

        if state:
            try:
                desc += '\nStatus : ' + str(state.title().decode('utf-8')) + '\n'
            except:
                desc += '\nStatus : ' + str(state.title().encode('utf-8')) + '\n'
        else:
            desc += '\nStatus : ' + str(state) + '\n'

        data = {
            'code': 9901,
            'message': 'Activity Booking Status Updated: ' + desc,
            'provider': self.provider_name,
        }
        GatewayConnector().telegram_notif_api(data, {})

    def action_activity_print_invoice(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'tt_reservation_activity.printout_activity_invoice')


class PrintoutActivityInvoice(models.AbstractModel):
    _name = 'report.tt_reservation_activity.printout_activity_invoice'

    @api.model
    def render_html(self, docids, data=None):
        tt_activity = self.env["tt.reservation.activity"].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc': tt_activity
        }
        return self.env['report'].with_context(landscape=False).render('tt_reservation_activity.printout_activity_invoice_template', docargs)
