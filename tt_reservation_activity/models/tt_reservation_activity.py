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
    _description = 'Activity Voucher Wizard'

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
            'book_id': self.pnr,
            'user_email_address': self.user_email_add,
            'ho_id': self.agent_id.ho_id.id
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
    _description = 'Reservation Activity Option'

    name = fields.Char('Information')
    value = fields.Char('Value')
    description = fields.Text('Description')
    booking_id = fields.Many2one('tt.reservation.activity', 'Activity Booking')


class TtReservationActivityVouchers(models.Model):
    _name = 'tt.reservation.activity.vouchers'
    _description = 'Reservation Activity Vouchers'

    name = fields.Char('URL')
    booking_id = fields.Many2one('tt.reservation.activity', 'Reservation')
    upload_center_seq_id = fields.Char('Seq ID')


class ReservationActivity(models.Model):
    _inherit = ['tt.reservation']
    _name = 'tt.reservation.activity'
    _order = 'id DESC'
    _description = 'Reservation Activity'

    booking_uuid = fields.Char('Booking UUID')

    user_id = fields.Many2one('res.users', 'User')

    acceptance_date = fields.Datetime('Acceptance Date')
    rejected_date = fields.Datetime('Rejected Date')
    refund_date = fields.Datetime('Refund Date')

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_activity_id', string='Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    provider_booking_ids = fields.One2many('tt.provider.activity', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.activity', 'booking_id', string='Passengers')

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')
    voucher_url_ids = fields.One2many('tt.reservation.activity.vouchers', 'booking_id', 'Voucher URLs')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', default=lambda self: self.env.ref('tt_reservation_activity.tt_provider_type_activity'))
    option_ids = fields.One2many('tt.reservation.activity.option', 'booking_id', 'Options')
    activity_detail_ids = fields.One2many('tt.reservation.activity.details', 'booking_id', 'Reservation Details')

    def get_form_id(self):
        return self.env.ref("tt_reservation_activity.tt_reservation_activity_form_view")

    @api.depends('provider_booking_ids', 'provider_booking_ids.reconcile_line_id')
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

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            hold_date = datetime.now() + relativedelta(hours=6)
            self.action_booked_activity(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_activity(issued_req, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            # refund
            self.action_refund()
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_activity(context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            self.action_partial_issued_api_activity()
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.action_partial_booked_api_activity(context, pnr_list, hold_date)
        elif all(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif all(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_set_as_cancel()
        elif self.provider_booking_ids:
            provider_obj = self.provider_booking_ids[0]
            self.write({
                'state': provider_obj.state,
            })
        else:
            self.write({
                'state': 'draft',
            })
            # raise RequestException(1006)

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
        context = {
            "co_ho_id": self.agent_id.ho_id.id
        }
        GatewayConnector().telegram_notif_api(data, context)

    def action_issued_vendor(self):
        req = {
            'uuid': self.booking_uuid,
            'provider': self.activity_id.provider_id.code,
            'book_id': self.id,
            'pnr': self.pnr,
            'ho_id': self.agent_id.ho_id.id
        }
        res = self.env['tt.activity.api.con'].issued_booking_vendor(req)

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

    def action_rejected(self):
        self.write({
            'state': 'rejected',
            'rejected_date': datetime.now(),
        })

    def action_expired(self):
        self.write({
            'state': 'cancel2',
            'expired_date': datetime.now(),
        })

    def action_refund(self):
        self.write({
            'state': 'refund',
            'refund_date': datetime.now(),
            'refund_uid': self.env.user.id
        })

        # todo create refund ledger
        # self._create_refund_ledger_activity()

    def action_partial_booked_api_activity(self,context,pnr_list,hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_activity(self):
        self.write({
            'state': 'partial_issued'
        })

    @api.multi
    def action_set_as_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 112')
        super(ReservationActivity, self).action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def action_failed(self, data):
        booking_rec = self.browse(int(data['book_id']))
        booking_rec.write({
            'state': data['state'],
            'error_msg': data['error_msg']
        })
        return {
            'error_code': 0,
            'error_msg': False,
            'response': 'action_fail_booking'
        }

    def action_failed_sync(self):
        self.write({
            'state': 'fail_issued',
        })

    def action_issued(self):
        self.write({
            'state': 'issued',
        })

    def action_issued_api_activity(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_activity(data)

    def action_reverse_activity(self,context):
        self.write({
            'state': 'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def update_pnr_data(self, book_id, pnr):
        provider_objs = self.env['tt.provider.activity'].search([('booking_id', '=', book_id)])
        for rec in provider_objs:
            rec.write({
                'pnr': pnr
            })
            cost_service_charges = self.env['tt.service.charge'].search([('provider_activity_booking_id', '=', rec.id)])
            for rec2 in cost_service_charges:
                rec2.write({
                    'description': pnr
                })

        ledger_objs = self.env['tt.ledger'].search([('res_id', '=', book_id),('res_model','=',self._name)])
        for rec in ledger_objs:
            rec.write({
                'pnr': pnr
            })

    def update_booking_by_api(self, data, context, **kwargs):
        try:
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.activity'].browse(int(data['book_id']))
            else:
                book_objs = self.env['tt.reservation.activity'].search([('name', '=', data['order_number'])], limit=1)
                book_obj = book_objs[0]

            book_info = data.get('book_info') and data['book_info'] or {}

            if book_info['status'] == 'booked':
                write_vals = {
                    'sid_booked': context.get('sid') and context['sid'] or '',
                    'booking_uuid': book_info.get('uuid') and book_info['uuid'] or ''
                }

                pnr_list = []
                for rec in book_obj.provider_booking_ids:
                    rec.action_booked_api_activity(book_info, context)
                    pnr_list.append(book_info.get('code') or '')

                book_obj.check_provider_state(context, pnr_list)
                book_obj.write(write_vals)
            elif book_info['status'] == 'issued':
                for rec in book_obj.provider_booking_ids:
                    rec.action_issued_api_activity(context)

                book_obj.check_provider_state(context, req=data)
            self.env.cr.commit()

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
            response.update({
                'provider_booking': provider_booking_list,
            })
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
            return ERR.get_error(1005)

    def update_booking_by_api2(self, req_data):
        booking_obj = self.env['tt.reservation.activity'].search([('name', '=', req_data['order_number'])], limit=1)
        if booking_obj:
            booking_obj = booking_obj[0]
            booking_obj.write({
                'state': req_data['status']
            })
            self.env.cr.commit()
        return True

    def cancel_booking_by_api(self, data, context, **kwargs):
        try:
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.activity'].browse(int(data['book_id']))
            else:
                book_objs = self.env['tt.reservation.activity'].search([('name', '=', data['order_number'])], limit=1)
                book_obj = book_objs[0]

            book_obj.action_cancel()
            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
            response.update({
                'provider_booking': provider_booking_list,
            })
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
            return ERR.get_error(1005)

    # to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for idy, p_sc in enumerate(provider.cost_service_charge_ids):
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                c_type = ''
                c_code = ''
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                if p_charge_type != 'RAC':
                    if p_charge_code == 'csc':
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

            values = []
            for p_type, p_val in sc_value.items():
                for c_type, c_val in p_val.items():
                    curr_dict = {}
                    curr_dict['pax_type'] = p_type
                    curr_dict['booking_activity_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict['ho_id'] = self.ho_id.id if self.ho_id else ''
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
            carrier = req.get('carrier_code') and req['carrier_code'] or ''
            pricing = req.get('pricing') and req['pricing'] or []

            header_val = search_request
            booker_obj = self.create_booker_api(booker_data, context)
            contact_data = contacts_data[0]
            contact_objs = []
            for con in contacts_data:
                contact_objs.append(self.create_contact_api(con, booker_obj, context))

            contact_obj = contact_objs[0]
            provider_id = self.env['tt.provider'].search([('code', '=', provider)], limit=1)
            if not provider_id:
                raise RequestException(1002)
            carrier_id = self.env['tt.transport.carrier'].search([('code', '=', carrier)], limit=1)
            provider_id = provider_id[0]
            activity_product_id = self.env['tt.master.activity'].search([('uuid', '=', search_request['product_uuid']), ('provider_id', '=', provider_id.id)], limit=1)
            if not activity_product_id:
                raise RequestException(1004, additional_message='Activity not found. Please check your product_uuid.')
            activity_product_id = activity_product_id[0]
            activity_type_id = self.env['tt.master.activity.lines'].search([('uuid', '=', search_request['product_type_uuid']), ('activity_id', '=', activity_product_id.id)], limit=1)
            if not activity_type_id:
                raise RequestException(1004, additional_message='Activity type not found. Please check your product_type_uuid.')
            activity_type_id = activity_type_id[0]

            list_passenger_value = self.create_passenger_value_api(passengers)
            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)

            sku_ids_dict = {}
            adult = 0
            senior = 0
            child = 0
            infant = 0
            for idx, temp_pax in enumerate(passengers):
                pax_options = []
                if temp_pax.get('per_pax_data'):
                    for temp_psg_opt in temp_pax['per_pax_data']:
                        temp_opt_obj = self.env['tt.activity.booking.option'].search([('uuid', '=', temp_psg_opt['uuid']), ('type', '=', 'perPax')], limit=1)
                        temp_opt_obj = temp_opt_obj[0]
                        temp_desc = str(temp_psg_opt['value'])
                        for it_obj in temp_opt_obj.items:
                            if temp_psg_opt['value'] == it_obj.value:
                                temp_desc = it_obj.label
                        pax_opt_vals = {
                            'name': temp_opt_obj.name,
                            'value': str(temp_psg_opt['value']),
                            'description': temp_desc
                        }
                        pax_opt_obj = self.env['tt.reservation.passenger.activity.option'].create(pax_opt_vals)
                        pax_options.append(pax_opt_obj.id)

                if temp_pax.get('sku_id'):
                    temp_sku_id = self.env['tt.master.activity.sku'].search([('sku_id', '=', temp_pax['sku_id']), ('activity_line_id', '=', activity_type_id.id)], limit=1)
                    temp_sku_id = temp_sku_id and temp_sku_id[0].id or 0

                list_passenger_value[idx][2].update({
                    'customer_id': pax_ids[idx].id,
                    'title': temp_pax['title'],
                    'pax_type': temp_pax['pax_type'],
                    'activity_sku_id': temp_sku_id,
                    'option_ids': [(6, 0, pax_options)],
                })

                if not sku_ids_dict.get(str(temp_pax['sku_id'])):
                    sku_ids_dict.update({
                        str(temp_pax['sku_id']): 1,
                    })
                else:
                    temp_sku_val = sku_ids_dict[str(temp_pax['sku_id'])]
                    sku_ids_dict.update({
                        str(temp_pax['sku_id']): temp_sku_val + 1,
                    })

                if temp_pax['pax_type'] == 'ADT':
                    adult += 1
                elif temp_pax['pax_type'] == 'CHD':
                    child += 1
                elif temp_pax['pax_type'] == 'YCD':
                    senior += 1
                elif temp_pax['pax_type'] == 'INF':
                    infant += 1

            skus = []
            for temp_sku in activity_type_id.sku_ids:
                for key, val in sku_ids_dict.items():
                    if str(key) == str(temp_sku.sku_id) and val > 0:
                        skus.append({
                            'sku_id': str(key),
                            'amount': val,
                            'pax_type': temp_sku.pax_type,
                        })

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            currency_obj = None
            for svc in pricing:
                if not currency:
                    currency = svc['currency']
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                # if currency_obj:
                #     book_obj.currency_id = currency_obj.id

            header_val.update({
                'contact_id': contact_obj.id,
                'booker_id': booker_obj.id,
                'passenger_ids': list_passenger_value,
                'contact_title': contact_data['title'],
                'contact_name': contact_data['first_name'] + ' ' + contact_data['last_name'],
                'contact_email': contact_data.get('email') and contact_data['email'] or '',
                'contact_phone': contact_data.get('mobile') and str(contact_data['calling_code']) + " - "+ str(
                    contact_data['mobile']),
                'date': datetime.now(),
                'ho_id': context['co_ho_id'],
                'agent_id': context['co_agent_id'],
                'customer_parent_id': context.get('co_customer_parent_id', False),
                'user_id': context['co_uid'],
                'elder': senior,
                'adult': adult,
                'child': child,
                'infant': infant,
                'transport_type': 'activity',
                'provider_name': activity_type_id.activity_id.provider_id.code,
                'file_upload': file_upload,
                'currency_id': currency_obj.id if currency and currency_obj else self.env.user.company_id.currency_id.id
            })

            # create header & Update customer_parent_id
            book_obj = self.create(header_val)

            if option['perBooking']:
                for rec in option['perBooking']:
                    temp_opt_obj = self.env['tt.activity.booking.option'].search([('uuid', '=', rec['uuid']), ('type', '=', 'perBooking')], limit=1)
                    temp_opt_obj = temp_opt_obj[0]
                    temp_desc = str(rec['value'])
                    for it_obj in temp_opt_obj.items:
                        if rec['value'] == it_obj.value:
                            temp_desc = it_obj.label
                    self.env['tt.reservation.activity.option'].create({
                        'name': temp_opt_obj.name,
                        'value': str(rec['value']),
                        'description': temp_desc,
                        'booking_id': book_obj.id
                    })

            balance_due = 0
            for temp_sc in pricing:
                if temp_sc['charge_type'] not in ['ROC', 'RAC']:
                    balance_due += temp_sc['pax_count'] * temp_sc['amount']

            provider_activity_vals = {
                'booking_id': book_obj.id,
                'provider_id': provider_id.id,
                'carrier_id': carrier_id and carrier_id[0].id,
                'carrier_code': carrier_id and carrier_id[0].code,
                'carrier_name': carrier_id and carrier_id[0].name,
                'balance_due': balance_due,
                'total_price': balance_due,
                'sequence': 1
            }

            provider_activity_obj = self.env['tt.provider.activity'].create(provider_activity_vals)
            for psg in book_obj.passenger_ids:
                vals = {
                    'provider_id': provider_activity_obj.id,
                    'passenger_id': psg.id,
                    'pax_type': psg.pax_type,
                    'ticket_number': psg.activity_sku_id.sku_id
                }
                self.env['tt.ticket.activity'].create(vals)
            provider_activity_obj.delete_service_charge()
            provider_activity_obj.create_service_charge(pricing)

            reservation_details_vals = {
                'provider_booking_id': provider_activity_obj.id,
                'activity_id': activity_type_id.activity_id.id,
                'activity_product_id': activity_type_id.id,
                'visit_date': search_request['visit_date']
            }

            if search_request.get('timeslot'):
                timeslot_obj = self.env['tt.activity.master.timeslot'].search([('uuid', '=', search_request['timeslot']), ('product_type_id', '=', int(activity_type_id.id))], limit=1)
                timeslot_obj = timeslot_obj[0]
                reservation_details_vals.update({
                    'timeslot': str(timeslot_obj.startTime) + ' - ' + str(timeslot_obj.endTime),
                })

            if not activity_type_id.instantConfirmation:
                reservation_details_vals.update({
                    'information': 'On Request (max. 3 working days)',
                })

            self.env['tt.reservation.activity.details'].create(reservation_details_vals)

            prov_list = []
            for prov in book_obj.provider_booking_ids:
                prov_list.append(prov.to_dict())

            # channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)
                book_obj.create_svc_upsell()

            ## PAKAI VOUCHER
            if req.get('voucher'):
                book_obj.add_voucher(req['voucher']['voucher_reference'], context)

            response = book_obj.to_dict(context)
            response.update({
                'provider_booking': prov_list,
                'booking_uuid': book_obj.booking_uuid
            })

            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def payment_activity_api(self,req,context):
        return self.payment_reservation_api('activity',req,context)

    def issued_booking_by_api(self, req, context):
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.activity'].browse(int(req['book_id']))
            else:
                book_objs = self.env['tt.reservation.activity'].search([('name', '=', req['order_number'])], limit=1)
                book_obj = book_objs[0]

            provider_booking_list = []
            for prov in book_obj.provider_booking_ids:
                provider_booking_list.append(prov.to_dict())
            response = book_obj.to_dict(context)
            response.update({
                'provider_booking': provider_booking_list,
                'booking_uuid': book_obj.booking_uuid
            })
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def _get_pricelist_ids(self, service_charge_summary):
        res = []
        for rec in service_charge_summary:
            res.append(rec['activity_id'])
        return res

    def get_vouchers_button_api(self, obj_id, context):
        try:
            obj = self.env['tt.reservation.activity'].browse(obj_id)
            provider = ''
            visit_date = ''
            for rec in obj.provider_booking_ids:
                provider = rec.provider_id.code
                for rec2 in rec.activity_detail_ids:
                    visit_date = rec2.visit_date

            req = {
                'order_number': obj.name,
                'uuid': obj.booking_uuid,
                'pnr': obj.pnr,
                'provider': provider,
                'ho_id': obj.agent_id.ho_id.id
            }
            attachment_objs = []
            res2 = self.env['tt.activity.api.con'].get_vouchers(req)
            if res2['error_code'] == 0:
                for idx, rec in enumerate(res2['response']['ticket']):
                    attachment_value = {
                        'filename': 'Activity_Ticket.pdf',
                        'file_reference': str(obj.name) + ' ' + str(idx+1),
                        'file': rec,
                        'delete_date': visit_date + timedelta(days=7)
                    }
                    attachment_obj = self.env['tt.upload.center.wizard'].upload_file_api(attachment_value, context)
                    if attachment_obj['error_code'] == 0:
                        attachment_objs.append(attachment_obj['response'])

            new_vouch_objs = []
            for rec in attachment_objs:
                temp_vouch_obj = self.env['tt.reservation.activity.vouchers'].create({
                    'name': rec['url'],
                    'booking_id': obj.id,
                    'upload_center_seq_id': rec['seq_id']
                })
                new_vouch_objs.append({
                    'name': temp_vouch_obj.name,
                    'booking_id': temp_vouch_obj.booking_id.id,
                    'upload_center_seq_id': temp_vouch_obj.upload_center_seq_id
                })
            return ERR.get_no_error(new_vouch_objs)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def resend_voucher_button(self):
        view = self.env.ref('tt_reservation_activity.activity_voucher_wizard')
        context = dict(self._context or {})
        return {
            'name': 'Resend Voucher to Email',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'activity.voucher.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def get_vouchers_button(self):
        vouch_objs = self.env['tt.reservation.activity.vouchers'].search([('booking_id', '=', int(self.id))])

        if vouch_objs:
            vouch_arr = []
            for rec in vouch_objs:
                vouch_arr.append({
                    'name': rec.name,
                    'booking_id': rec.booking_id.id,
                    'upload_center_seq_id': rec.upload_center_seq_id
                })
            temp = ERR.get_no_error(vouch_arr)
        else:
            ctx = {
                'co_uid': self.booked_uid.id,
                'agent_id': self.booked_uid.agent_id.id,
                'co_agent_id': self.booked_uid.agent_id.id,
            }
            temp = self.get_vouchers_button_api(self[0]['id'], ctx)
        if temp:
            try:
                upload_center_obj = self.env['tt.upload.center'].search([('seq_id','=',temp['response'][0]['upload_center_seq_id'])],limit=1)
                return {
                    'name': 'Activity Voucher',
                    'res_model': 'ir.actions.act_url',
                    'type': 'ir.actions.act_url',
                    'target': 'current',
                    'url': temp['response'][0]['name'],
                    'path': upload_center_obj.path
                }
            except Exception as e:
                _logger.error(traceback.format_exc())
                raise UserError(_('Voucher is not available. Please contact HO!'))

    def get_vouchers_by_api2(self, req, ctx):
        try:
            booking_obj = self.env['tt.reservation.activity'].search([('name', '=', req['order_number'])], limit=1)
            if booking_obj:
                booking_obj = booking_obj[0]
                if not ctx or ctx['co_uid'] == 1:
                    ctx.update({
                        'co_uid': booking_obj.booked_uid.id,
                        'agent_id': booking_obj.booked_uid.agent_id.id,
                        'co_agent_id': booking_obj.booked_uid.agent_id.id,
                    })
                if booking_obj.agent_id.id != ctx.get('co_agent_id', -1):
                    raise RequestException(1001)
                vouch_objs = self.env['tt.reservation.activity.vouchers'].search([('booking_id', '=', int(booking_obj.id))])

                if vouch_objs:
                    vouch_arr = []
                    for rec in vouch_objs:
                        vouch_arr.append({
                            'name': rec.name,
                            'booking_id': rec.booking_id.id
                        })
                    temp = ERR.get_no_error(vouch_arr)
                else:
                    temp = self.get_vouchers_button_api(booking_obj[0]['id'], ctx)

                return temp['error_code'] == 0 and ERR.get_no_error(temp['response']) or temp
            else:
                raise RequestException(1001)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    @api.multi
    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.activity'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        activity_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_activity')
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = activity_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = activity_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Activity Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Activity Itinerary',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_itinerary_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_itinerary_id.url,
        }
        return url
        # return self.env.ref('tt_report_common.action_printout_itinerary_activity').report_action(self, data=datas)

    @api.multi
    def print_itinerary_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.activity'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        activity_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_activity')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = activity_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = activity_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Activity Itinerary %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Activity Itinerary',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.printout_itinerary_price_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.printout_itinerary_price_id.url,
        }
        return url
        # return self.env.ref('tt_report_common.action_printout_itinerary_activity').report_action(self, data=datas)

    # DEPRECATED
    @api.multi
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        activity_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_activity')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = activity_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = activity_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Activity HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Activity HO Invoice',
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
        # return activity_ho_invoice_id.report_action(self, data=datas)

    def get_booking_for_vendor_by_api(self, data, context):
        try:
            order_number = data['order_number']

            book_obj = self.env['tt.reservation.activity'].search([('name', '=', order_number)], limit=1)
            if book_obj:
                book_obj = book_obj[0]

                provider = ''
                for rec in book_obj.provider_booking_ids:
                    provider = rec.provider_id.code

                res = {
                    'provider': provider,
                    'uuid': book_obj.booking_uuid,
                    'pnr': book_obj.pnr,
                    'order_number': book_obj.name,
                    'book_id': book_obj.id,
                    'state': book_obj.state
                }
                result = ERR.get_no_error(res)
            else:
                raise RequestException(1001)
            return result
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def clean_string(self, txt):
        replace_list = {
            '<br>': '\n',
            '<p>': '',
            '</p>': '',
        }
        for key, val in replace_list.items():
            if txt:
                txt = txt.replace(key, val)
        return txt

    def get_booking_by_api(self, res, req, context):
        try:
            book_obj = self.get_book_obj(req.get('book_id'), req.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)

            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            # if book_obj.agent_id.id == context.get('co_agent_id',-1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
            #     if book_obj.agent_id.id != context.get('co_agent_id', -1):
            #         raise RequestException(1001)
            _co_user = self.env['res.users'].browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_system'):
                book_option_ids = []
                for rec in book_obj.option_ids:
                    book_option_ids.append({
                        'name': rec.name,
                        'value': rec.value,
                        'description': rec.description,
                    })

                # self.env.cr.execute("""SELECT * FROM tt_service_charge WHERE booking_activity_id=%s""", (book_obj[0]['id'],))
                # api_price_ids = self.env.cr.dictfetchall()
                psg_list = []
                for rec in book_obj.passenger_ids:
                    psg_list.append(rec.to_dict())

                voucher_url_parsed = []
                activity_voucher_urls = self.env['tt.reservation.activity.vouchers'].search([('booking_id', '=', int(book_obj.id))])
                if res.get('voucher_url') and not activity_voucher_urls:
                    new_vouch_obj = self.env['tt.reservation.activity.vouchers'].create({
                        'name': res['voucher_url'],
                        'booking_id': book_obj.id
                    })
                    voucher_url_parsed = [new_vouch_obj.name]
                elif activity_voucher_urls:
                    voucher_url_parsed = [url_voucher.name for url_voucher in activity_voucher_urls]

                if book_obj.state not in ['booked', 'issued', 'rejected', 'refund', 'cancel', 'cancel2', 'fail_booked', 'fail_issued', 'fail_refunded']:
                    book_obj.write({
                        'state': res['status']
                    })
                    self.env.cr.commit()

                prov_list = []
                for prov in book_obj.provider_booking_ids:
                    prov_list.append(prov.to_dict())
                response = book_obj.to_dict(context)
                response.update({
                    'passengers': psg_list,
                    'provider_booking': prov_list,
                    'booking_uuid': book_obj.booking_uuid,
                    'booking_options': book_option_ids,
                    'voucher_url': voucher_url_parsed and voucher_url_parsed or []
                })
                result = ERR.get_no_error(response)
                return result
            else:
                raise RequestException(1035)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def action_booked_activity(self,context,pnr_list,hold_date):
        if not context:  # Jika dari call from backend
            context = {
                'co_uid': self.env.user.id
            }
        if not context.get('co_uid'):
            context.update({
                'co_uid': self.env.user.id
            })

        if self.state != 'booked':
            write_values = {
                'state': 'booked',
                'pnr': ', '.join(pnr_list),
                'hold_date': hold_date,
                'booked_date': datetime.now(),
                'booked_uid': context['co_uid'] or self.env.user.id,
            }

            if write_values['pnr'] == '':
                write_values.pop('pnr')

            self.write(write_values)

            try:
                if self.agent_type_id.is_send_email_booked:
                    mail_created = self.env['tt.email.queue'].with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_activity')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'activity',
                            'order_number': self.name,
                            'type': 'booked',
                        }
                        temp_context = {
                            'co_agent_id': self.agent_id.id
                        }
                        self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
                    else:
                        _logger.info('Booking email for {} is already created!'.format(self.name))
                        raise Exception('Booking email for {} is already created!'.format(self.name))
            except Exception as e:
                _logger.info('Error Create Email Queue')

    def action_issued_activity(self,data):
        if self.state != 'issued':
            pnr_list = []
            provider_list = []
            carrier_list = []
            for rec in self.provider_booking_ids:
                pnr_list.append(rec.pnr or '')
                provider_list.append(rec.provider_id.name or '')
                carrier_list.append(rec.carrier_id.name or '')

            self.write({
                'state': 'issued',
                'issued_date': datetime.now(),
                'issued_uid': data.get('co_uid', self.env.user.id),
                'customer_parent_id': data['customer_parent_id'],
                'pnr': ', '.join(pnr_list),
                'provider_name': ','.join(provider_list),
                'carrier_name': ','.join(carrier_list),
            })

            try:
                if self.agent_type_id.is_send_email_issued:
                    mail_created = self.env['tt.email.queue'].with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_activity')], limit=1)
                    if not mail_created:
                        temp_data = {
                            'provider_type': 'activity',
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

    def get_id(self, booking_number):
        row = self.env['tt.reservation.activity'].search([('name', '=', booking_number)])
        if not row:
            return ''
        return row.id

    def confirm_booking_webhook(self, req):
        if req.get('book_id'):
            order_id = req['book_id']
            book_obj = self.sudo().search([('pnr', '=', order_id), ('provider_name', '=', req['provider'])], limit=1)
            book_obj = book_obj[0]
            if book_obj.state not in ['issued', 'cancel', 'cancel2', 'refund']:
                book_obj.sudo().write({
                    'state': req.get('status') and req['status'] or 'pending',
                })
            if req.get('voucher_url'):
                self.env['tt.reservation.activity.vouchers'].sudo().create({
                    'name': req['voucher_url'],
                    'booking_id': book_obj.id
                })
        elif req.get('booking_uuid'):
            booking_uuid = req['booking_uuid']
            book_obj = self.sudo().search([('booking_uuid', '=', booking_uuid), ('provider_name', '=', req['provider'])], limit=1)
            book_obj = book_obj[0]
            if book_obj.state not in ['issued', 'cancel', 'cancel2', 'refund']:
                book_obj.sudo().write({
                    'state': req.get('status') and req['status'] or 'pending',
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
        context = {
            "co_ho_id": activity_booking.agent_id.ho_id.id
        }
        GatewayConnector().telegram_notif_api(data, context)

    def action_activity_print_invoice(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'tt_reservation_activity.printout_activity_invoice')

    def file_upload_api(self, req, context):
        try:
            book_objs = self.env['tt.reservation.activity'].sudo().search([('name', '=', req['order_number'])], limit=1)
            book_obj = book_objs[0]
            req.update({
                'booking_uuid': book_obj.booking_uuid,
                'provider': book_obj.activity_id.provider_id.code
            })
            req.pop('order_number')
            return ERR.get_no_error(req)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def get_aftersales_desc(self):
        desc_txt = 'PNR: ' + self.pnr + '<br/>'
        for rec in self.provider_booking_ids:
            for rec2 in rec.activity_detail_ids:
                desc_txt += 'Activity: ' + rec2.activity_id.name + '<br/>'
                desc_txt += 'Product: ' + rec2.activity_product_id.name + '<br/>'
                desc_txt += 'Visit Date: ' + rec2.visit_date.strftime('%d %b %Y')
                if rec2.timeslot:
                    desc_txt += ' (' + rec2.timeslot + ')'
                desc_txt += '<br/><br/>'
        return desc_txt

    def get_passenger_pricing_breakdown(self):
        pax_list = []
        for rec in self.passenger_ids:
            pax_data = {
                'passenger_name': '%s %s' % (rec.title, rec.name),
                'pnr_list': []
            }
            for rec2 in self.provider_booking_ids:
                pax_ticketed = False
                ticket_num = ''
                for rec3 in rec2.ticket_ids.filtered(lambda x: x.passenger_id.id == rec.id):
                    pax_ticketed = True
                    if rec3.ticket_number:
                        ticket_num = rec3.ticket_number
                pax_pnr_data = {
                    'pnr': rec2.pnr,
                    'ticket_number': ticket_num,
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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_activity_ids.ids):
                    pax_pnr_data['ho_nta'] += rec3.amount
                    if rec3.charge_type == 'RAC' and rec3.charge_code == 'rac':
                        pax_pnr_data['agent_commission'] -= rec3.amount
                        pax_pnr_data['agent_nta'] += rec3.amount
                    if rec3.charge_type == 'RAC':
                        pax_pnr_data['total_commission'] -= rec3.amount
                        if rec3.commission_agent_id.is_ho_agent:
                            pax_pnr_data['ho_commission'] -= rec3.amount
                    if rec3.charge_type != 'RAC':
                        pax_pnr_data['grand_total'] += rec3.amount
                        pax_pnr_data['agent_nta'] += rec3.amount
                    if rec3.charge_type == 'FARE':
                        pax_pnr_data['fare'] += rec3.amount
                    if rec3.charge_type == 'TAX':
                        pax_pnr_data['tax'] += rec3.amount
                    if rec3.charge_type == 'ROC':
                        pax_pnr_data['upsell'] += rec3.amount
                    if rec3.charge_type == 'DISC':
                        pax_pnr_data['discount'] -= rec3.amount
                pax_pnr_data['parent_agent_commission'] = pax_pnr_data['total_commission'] - pax_pnr_data[
                    'agent_commission'] - pax_pnr_data['ho_commission']
                if pax_ticketed:
                    pax_data['pnr_list'].append(pax_pnr_data)
            pax_list.append(pax_data)
        return pax_list


class PrintoutActivityInvoice(models.AbstractModel):
    _name = 'report.tt_reservation_activity.printout_activity_invoice'
    _description = 'Report Reservation Activity Printout Invoice'

    @api.model
    def render_html(self, docids, data=None):
        tt_activity = self.env["tt.reservation.activity"].browse(docids)
        docargs = {
            'doc_ids': docids,
            'doc': tt_activity
        }
        return self.env['report'].with_context(landscape=False).render('tt_reservation_activity.printout_activity_invoice_template', docargs)
