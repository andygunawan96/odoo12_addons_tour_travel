from odoo import api, fields, models, _
from datetime import datetime, timedelta, date, time
from odoo import http
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.db_connector import GatewayConnector
from .ApiConnector_Activity import ApiConnectorActivity

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
        res = ApiConnectorActivity().resend_voucher(req, '')
        if res['response'].get('success'):
            self.env['msg.wizard'].raise_msg("The Voucher has been Resent Successfully!")
            context = self.env.context
            new_obj = self.env[context['active_model']].browse(context['active_id'])
            new_obj.message_post(body='Resent Voucher Email.')
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
        ApiConnectorActivity().update_booking(req, '')

    def action_waiting(self):
        self.write({
            'state': 'in_progress',
            'issued_date': datetime.now(),
            'issued_uid': self.env.user.id,
        })

    def action_calc_prices(self):
        self._calc_grand_total()

    def force_update_booking(self):
        cookie = ''
        req = {
            'provider': self.provider_name,
            'uuid': self.booking_uuid,
            'pnr': self.pnr
        }
        if req['uuid'] or req['pnr']:
            if req['provider']:
                res = ApiConnectorActivity().get_booking(req, cookie)
                if res.get('response'):
                    values = res['response']
                    print(values)
                    search_request = {
                        'product_type_uuid': values['productTypeUuid'],
                        'date_start': datetime.strptime(self.visit_date[:10], "%Y-%m-%d").strftime('%Y-%m-%d'),
                        'date_end': (datetime.strptime(self.visit_date[:10], "%Y-%m-%d") + relativedelta(days=365)).strftime('%Y-%m-%d'),
                        'provider': self.provider_name,
                    }

                    res2 = ApiConnectorActivity().get_pricing(search_request, cookie)
                    if res2['error_code'] != 0:
                        error = {
                            'error_msg': res2['error_msg'],
                            'error_code': res2['error_code'],
                        }
                    else:
                        error = {
                            'error_msg': '',
                            'error_code': 0,
                        }
                        prices = res2['response']

                    temp_co_uid = self.booked_uid.id

                    sale_service_charge_summary = values['amountBreakdown']
                    service_chg_obj = self.env['tt.service.charge']
                    pax_lib = {
                        'senior': 'YCD',
                        'adult': 'ADT',
                        'child': 'CHD',
                        'infant': 'INF',
                    }

                    from_currency = self.env['res.currency'].search([('name', '=', values['currencyCode'])])
                    agent_type = self.env['res.users'].browse(temp_co_uid).agent_id.agent_type_id.id
                    if agent_type == self.env.ref('tt_base_rodex.agent_type_ho').id:
                        agent_type = self.agent_type_id.id

                    if agent_type in [self.env.ref('tt_base_rodex.agent_type_citra').id,
                                      self.env.ref('tt_base_rodex.agent_type_btbo').id]:
                        multiplier = 1
                        parent_multiplier = 0
                        ho_multiplier = 0
                    elif agent_type in [self.env.ref('tt_base_rodex.agent_type_japro').id,
                                        self.env.ref('tt_base_rodex.agent_type_btbr').id]:
                        multiplier = 0.8
                        parent_multiplier = 0.17
                        ho_multiplier = 0.03
                    elif agent_type in [self.env.ref('tt_base_rodex.agent_type_fipro').id]:
                        multiplier = 0.6
                        parent_multiplier = 0.35
                        ho_multiplier = 0.05
                    else:
                        multiplier = 0
                        parent_multiplier = 1
                        ho_multiplier = 0

                    commission_ho = 0
                    total_commission_price = 0
                    total_parent_commission_price = 0
                    total_ho_commission_price = 0

                    for service_charge in self.sale_service_charge_ids:
                        service_charge.sudo().unlink()

                    for val in sale_service_charge_summary:
                        pax_type_string = ''
                        if val.get('name'):
                            if val['name'] == 'senior':
                                pax_type_string = 'seniors'
                            elif val['name'] == 'adult':
                                pax_type_string = 'adults'
                            elif val['name'] == 'child':
                                pax_type_string = 'children'
                            else:
                                pax_type_string = 'adults'

                        if val.get('price'):
                            to_currency = self.env['res.currency']._compute(from_currency,
                                                                            self.env.user.company_id.currency_id,
                                                                            float(val['price']))

                            # break down coding ini kalo mau min price berdasarkan masing2 max type
                            pax = values['adults'] + values['children'] + values['seniors']
                            for price in prices:
                                for price_temp in price:
                                    if values.get('event_id') and price_temp.get('id'):
                                        if price_temp['id'] == values['event_id']:
                                            min_currency = price_temp['prices'][pax_type_string][str(pax)]
                                    else:
                                        if price_temp['date'] == values['arrivalDate']:
                                            min_currency = price_temp['prices'][pax_type_string][str(pax)]
                            ############################################################

                            if to_currency:
                                final_price = to_currency + 10000
                                commission_ho += 10000 * val['quantity']
                            else:
                                final_price = 0

                            sale_price = int(final_price * 1.03)
                            min_currency2 = self.env['res.currency']._compute(from_currency,
                                                                              self.env.user.company_id.currency_id,
                                                                              float(min_currency))

                            if sale_price < min_currency2:
                                sale_price = int(min_currency2)

                            commission_price = int((sale_price - final_price) * multiplier)

                            final_sale_price = 0
                            # pembulatan sale price keatas
                            for idx in range(10):
                                if (sale_price % 100) == 0:
                                    final_sale_price = sale_price
                                    break
                                if idx == 9 and ((sale_price % 1000) < int(str(idx + 1) + '00')) and sale_price > 0:
                                    final_sale_price = str(int(sale_price / 1000) + 1) + '000'
                                    break
                                elif (sale_price % 1000) < int(str(idx + 1) + '00') and sale_price > 0:
                                    if int(sale_price / 1000) == 0:
                                        final_sale_price = str(idx + 1) + '00'
                                    else:
                                        final_sale_price = str(int(sale_price / 1000)) + str(idx + 1) + '00'
                                    break

                            final_commission_price = 0
                            # pembulatan commission price kebawah
                            for idx in range(10):
                                if not commission_price > 0:
                                    break
                                if int(commission_price % 1000) < int(str(idx + 1) + '00'):
                                    if int(commission_price / 1000) == 0:
                                        final_commission_price = str(idx) + '00'
                                    else:
                                        final_commission_price = str(int(commission_price / 1000)) + str(idx) + '00'
                                    break

                            total_commission_price += int(final_commission_price) * val['quantity']
                            parent_commission_price = int((int(final_sale_price) - final_price) * parent_multiplier)
                            total_parent_commission_price += parent_commission_price * val['quantity']
                            ho_commission_price = int((int(final_sale_price) - final_price) * ho_multiplier)
                            total_ho_commission_price += ho_commission_price * val['quantity']

                            val.update({
                                'activity_id': self.id,
                                'charge_code': 'fare',
                                'charge_type': 'fare',
                                'pax_type': pax_lib[val['name']],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['quantity'],
                                'amount': int(final_sale_price),
                                'foreign_amount': val['price'],
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            })
                            val.pop('price')
                            val.pop('name')
                            val.pop('quantity')
                            service_chg_obj.create(val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.ac',
                                'charge_type': 'r.ac',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': int(final_commission_price) * -1,
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.ac1',
                                'charge_type': 'r.ac1',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': parent_commission_price * -1,
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.ac2',
                                'charge_type': 'r.ac2',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': ho_commission_price * -1,
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.oc',
                                'charge_type': 'r.oc',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': int(final_commission_price),
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.oc1',
                                'charge_type': 'r.oc1',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': parent_commission_price,
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            commission_val = {
                                'activity_id': self.id,
                                'charge_code': 'r.oc2',
                                'charge_type': 'r.oc2',
                                'pax_type': val['pax_type'],
                                'currency_id': self.env['res.currency'].browse(
                                    self.env.user.company_id.currency_id.id).id,
                                'pax_count': val['pax_count'],
                                'amount': ho_commission_price,
                                'foreign_amount': 0,
                                'foreign_currency_id': self.env['res.currency'].search(
                                    [('name', '=', values['currencyCode'])], limit=1).id,
                                'description': self.provider_name,
                            }
                            service_chg_obj.create(commission_val)
                            self.env.cr.commit()

                            self.action_calc_prices()

                    self.action_confirm(total_commission_price, total_parent_commission_price, total_ho_commission_price)
                    vals = self.env['tt.ledger'].prepare_vals('Commission & Profit : ' + self.name,
                                                              'HO: ' + self.name, str(fields.Datetime.now()),
                                                              'commission', self.currency_id.id, commission_ho,
                                                              0)
                    vals.update({
                        'agent_id': self.env['res.partner'].sudo().search(
                            [('is_HO', '=', True), ('parent_id', '=', False)], limit=1).id,
                        'booking_id': self.id,
                    })
                    commission_aml = self.env['tt.ledger'].create(vals)
                    commission_aml.action_done()

                    from_currency = self.env['res.currency'].search([('name', '=', values['currencyCode'])], limit=1)
                    temp1 = 0
                    for rec in self.sale_service_charge_ids:
                        if rec['charge_code'] == 'fare':
                            temp1 += rec['foreign_amount'] * rec['pax_count']
                    temp2 = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id,
                                                              temp1)

                    temp3 = self.env['tt.vendor.ledger'].search([('description', '=', self.name)])
                    for temp4 in temp3:
                        temp4.sudo().unlink()

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

    def action_done(self):
        self.write({
            'state': 'done',
        })
        self.message_post(body='Order DONE')

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

        ledger_objs = self.env['tt.ledger'].search([('res_id', '=', book_id)])
        for rec in ledger_objs:
            rec.sudo().write({
                'pnr': pnr
            })

    def update_booking(self, req, api_context, kwargs):
        try:
            booking_id = req['order_id'],
            prices = req['prices']
            book_info = req['book_info']

            booking_obj = self.browse(booking_id)
            booking_obj.write({
                'pnr': book_info.get('code') and book_info['code'] or '',
                'booking_uuid': book_info.get('uuid') and book_info['uuid'] or '',
                'sid_booked': api_context.get('sid') and api_context['sid'] or '',
                'state': book_info['status']
            })
            booking_obj.update_pnr_data(booking_id, book_info['code'])
            self.env.cr.commit()

            if not api_context or api_context['co_uid'] == 1:
                api_context['co_uid'] = booking_obj.booked_uid.id

            # sale_service_charge_summary = book_info['amountBreakdown']
            # service_chg_obj = self.env['tt.service.charge']
            # pax_lib = {
            #     'senior': 'YCD',
            #     'adult': 'ADT',
            #     'child': 'CHD',
            #     'infant': 'INF',
            # }
            # from_currency = self.env['res.currency'].search([('name', '=', book_info['currencyCode'])])
            # agent_type = self.env['res.users'].browse(api_context['co_uid']).agent_id.agent_type_id.id
            # if agent_type == self.env.ref('tt_base_rodex.agent_type_ho').id:
            #     agent_type = booking_obj.agent_type_id.id
            #
            # if agent_type in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_btbo').id]:
            #     multiplier = 1
            #     parent_multiplier = 0
            #     ho_multiplier = 0
            # elif agent_type in [self.env.ref('tt_base_rodex.agent_type_japro').id, self.env.ref('tt_base_rodex.agent_type_btbr').id]:
            #     multiplier = 0.8
            #     parent_multiplier = 0.17
            #     ho_multiplier = 0.03
            # elif agent_type in [self.env.ref('tt_base_rodex.agent_type_fipro').id]:
            #     multiplier = 0.6
            #     parent_multiplier = 0.35
            #     ho_multiplier = 0.05
            # else:
            #     multiplier = 0
            #     parent_multiplier = 1
            #     ho_multiplier = 0
            #
            # commission_ho = 0
            # total_commission_price = 0
            # total_parent_commission_price = 0
            # total_ho_commission_price = 0
            #
            # for service_charge in booking_obj.sale_service_charge_ids:
            #     service_charge.sudo().unlink()
            #
            # for val in sale_service_charge_summary:
            #     pax_type_string = ''
            #     if val.get('name'):
            #         if val['name'] == 'senior':
            #             pax_type_string = 'seniors'
            #             # pax = book_info['seniors']
            #         elif val['name'] == 'adult':
            #             pax_type_string = 'adults'
            #             # pax = book_info['adults']
            #         elif val['name'] == 'child':
            #             pax_type_string = 'children'
            #             # pax = book_info['children']
            #         else:
            #             pax_type_string = 'adults'
            #             # pax = book_info['adults']
            #
            #     if val.get('price'):
            #         to_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(val['price']))
            #
            #         # break down coding ini kalo mau min price berdasarkan masing2 max type
            #         pax = book_info['adults'] + book_info['children'] + book_info['seniors']
            #         for price in prices:
            #             for price_temp in price:
            #                 if book_info.get('event_id') and price_temp.get('id'):
            #                     if price_temp['id'] == book_info['event_id']:
            #                         min_currency = price_temp['prices'][pax_type_string][str(pax)]
            #                 else:
            #                     if price_temp['date'] == book_info['arrivalDate']:
            #                         min_currency = price_temp['prices'][pax_type_string][str(pax)]
            #         ############################################################
            #
            #         if to_currency:
            #             final_price = to_currency + 10000
            #             commission_ho += 10000 * val['quantity']
            #         else:
            #             final_price = 0
            #
            #         sale_price = int(final_price * 1.03)
            #
            #         if api_context['is_mobile']:
            #             min_currency2 = min_currency['sale_price']
            #         else:
            #             min_currency2 = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(min_currency))
            #
            #         if sale_price < min_currency2:
            #             sale_price = int(min_currency2)
            #
            #         commission_price = int((sale_price - final_price) * multiplier)
            #
            #         final_sale_price = 0
            #         # pembulatan sale price keatas
            #         for idx in range(10):
            #             if (sale_price % 100) == 0:
            #                 final_sale_price = sale_price
            #                 break
            #             if idx == 9 and ((sale_price % 1000) < int(str(idx + 1) + '00')) and sale_price > 0:
            #                 final_sale_price = str(int(sale_price / 1000) + 1) + '000'
            #                 break
            #             elif (sale_price % 1000) < int(str(idx + 1) + '00') and sale_price > 0:
            #                 if int(sale_price / 1000) == 0:
            #                     final_sale_price = str(idx + 1) + '00'
            #                 else:
            #                     final_sale_price = str(int(sale_price / 1000)) + str(idx + 1) + '00'
            #                 break
            #
            #         final_commission_price = 0
            #         # pembulatan commission price kebawah
            #         for idx in range(10):
            #             if not commission_price > 0:
            #                 break
            #             if int(commission_price % 1000) < int(str(idx + 1) + '00'):
            #                 if int(commission_price / 1000) == 0:
            #                     final_commission_price = str(idx) + '00'
            #                 else:
            #                     final_commission_price = str(int(commission_price / 1000)) + str(idx) + '00'
            #                 break
            #
            #         total_commission_price += int(final_commission_price) * val['quantity']
            #         parent_commission_price = int((int(final_sale_price) - final_price) * parent_multiplier)
            #         total_parent_commission_price += parent_commission_price * val['quantity']
            #         ho_commission_price = int((int(final_sale_price) - final_price) * ho_multiplier)
            #         total_ho_commission_price += ho_commission_price * val['quantity']
            #
            #         val.update({
            #             'activity_id': booking_id,
            #             'charge_code': 'fare',
            #             'charge_type': 'fare',
            #             'pax_type': pax_lib[val['name']],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['quantity'],
            #             'amount': int(final_sale_price),
            #             'foreign_amount': val['price'],
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         })
            #         val.pop('price')
            #         val.pop('name')
            #         val.pop('quantity')
            #         service_chg_obj.create(val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.ac',
            #             'charge_type': 'r.ac',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': int(final_commission_price) * -1,
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.ac1',
            #             'charge_type': 'r.ac1',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': parent_commission_price * -1,
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.ac2',
            #             'charge_type': 'r.ac2',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': ho_commission_price * -1,
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.oc',
            #             'charge_type': 'r.oc',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': int(final_commission_price),
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.oc1',
            #             'charge_type': 'r.oc1',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': parent_commission_price,
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         commission_val = {
            #             'activity_id': booking_id,
            #             'charge_code': 'r.oc2',
            #             'charge_type': 'r.oc2',
            #             'pax_type': val['pax_type'],
            #             'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
            #             'pax_count': val['pax_count'],
            #             'amount': ho_commission_price,
            #             'foreign_amount': 0,
            #             'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
            #             'description': booking_obj.provider_name,
            #         }
            #         service_chg_obj.create(commission_val)
            #         self.env.cr.commit()
            #
            #         booking_obj.action_calc_prices()

            response = {
                'order_number': booking_obj.name
            }

            res = ERR.get_no_error(response)
            return res

        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nUpdate PNR and prices failure'
            }

    def update_booking2(self, booking_id, book_info):
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
        else:
            desc = 'Activity Booking ' + self.name + ' From ' + self.agent_id.name

        data = {
            'code': 9901,
            'message': desc,
            'provider': self.provider_name,
        }
        GatewayConnector().telegram_notif_api(data, {})

    def create_booking(self, req, context, kwargs):
        try:
            booker_data = req.get('booker_data') and req['booker_data'] or False
            contacts_data = req.get('contacts_data') and req['contacts_data'] or False
            passengers = req.get('passengers_data') and req['passengers_data'] or False
            option = req.get('option') and req['option'] or False
            search_request = req.get('search_request') and req['search_request'] or False
            file_upload = req.get('file_upload') and req['file_upload'] or False
            provider = req.get('provider') and req['provider'] or ''
            try:
                agent_obj = self.env['tt.customer'].browse(int(booker_data['booker_id'])).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id

            if kwargs['force_issued']:
                is_enough = self.env['tt.agent'].check_balance_limit_api(agent_obj.id, kwargs['amount'])
                if not is_enough['error_code'] == 0:
                    raise Exception('BALANCE not enough')

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
            if option['perBooking']:
                for rec in option['perBooking']:
                    self.env['tt.reservation.activity.option'].sudo().create({
                        'name': rec['name'],
                        'value': str(rec['value']),
                        'booking_id': book_obj.id
                    })

            pax_ids = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id, ['title', 'pax_type', 'api_data', 'sku_real_id'])

            for psg in pax_ids:
                temp_obj = psg[0]
                extra_dict = psg[1]
                vals = temp_obj.copy_to_passenger()
                vals.update({
                    'booking_id': book_obj.id,
                    'title': extra_dict['title'],
                    'pax_type': extra_dict['pax_type'],
                    'activity_sku_id': extra_dict.get('sku_real_id', 0)
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

            book_obj.customer_parent_id = booker_obj.agent_id.id
            provider_activity_vals = {
                'booking_id': book_obj.id,
                'activity_id': activity_type_id.activity_id.id,
                'activity_product': activity_type_id.name,
                'activity_product_uuid': search_request['product_type_uuid'],
                'provider_id': provider_id.id,
                'visit_date': search_request['visit_date'],
                'balance_due': kwargs['amount'],
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

            book_obj.action_booked_activity(context)
            context['order_id'] = book_obj.id
            if kwargs['force_issued']:
                book_obj.action_issued_activity(context)

            self.env.cr.commit()

            response = {
                'order_id': book_obj.id,
                'order_number': book_obj.name,
                'status': book_obj.state,
            }

            return ERR.get_no_error(response)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return ERR.get_error(500)

    def _get_pricelist_ids(self, service_charge_summary):
        res = []
        for rec in service_charge_summary:
            res.append(rec['activity_id'])
        return res

    def get_vouchers_button_api(self, obj_id, co_uid):
        obj = self.env['tt.reservation.activity'].browse(obj_id)
        req = {
            'uuid': obj.booking_uuid,
            'pnr': obj.pnr,
            'provider': obj.provider_name
        }
        res2 = ApiConnectorActivity().get_vouchers_api(req, co_uid, '')

        try:
            ids = []
            for rec in res2['response']['ticket']:
                if res2['response']['provider'] == 'klook':
                    attachment_value = {
                        'name': 'Ticket.pdf',
                        'datas_fname': 'Ticket.pdf',
                        'res_model': 'tt.reservation.activity',
                        'res_id': obj.id,
                        'type': 'url',
                        'mimetype': res2['response']['format'],
                        'url': rec,
                    }

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
                    pdf_data = pickle.loads(rec)
                    if not pdf_data:
                        return False

                    attachment_value = {
                        'name': 'Ticket.pdf',
                        'datas': base64.encodestring(pdf_data),
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
        res2 = ApiConnectorActivity().get_vouchers(req, '')

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

    # def get_vouchers_by_api2(self, res2, req):
    #     temp = self.env['tt.reservation.activity'].search([('name', '=', req['order_number'])])
    #     if res2['response']['ticket'] and temp.state != 'done':
    #         temp.action_done()
    #
    #     result = {}
    #     for rec in res2['response']['ticket']:
    #         if res2['response']['provider'] == 'bemyguest':
    #             pdf_data = pickle.loads(rec)
    #             if not pdf_data:
    #                 return False
    #             result = {
    #                 'type': 'pdf',
    #                 'value': base64.encodestring(pdf_data)
    #             }
    #         if res2['response']['provider'] == 'globaltix':
    #             result = {
    #                 'type': 'url',
    #                 'value': rec
    #             }
    #     return result

    def prepare_summary_prices(self, values, infant):
        senior_amount = 0
        senior_price = 0
        adult_amount = 0
        adult_price = 0
        child_amount = 0
        child_price = 0
        additional_charge_amount = 0
        additional_charge_total = 0
        infant_amount = infant
        infant_price = 0
        commission_total = 0
        for rec in values:
            if rec['pax_type'] == 'YCD' and rec['charge_code'] == 'fare':
                senior_amount += rec['pax_count']
                senior_price += rec['amount'] * rec['pax_count']
            if rec['pax_type'] == 'ADT' and rec['charge_code'] == 'fare':
                adult_amount += rec['pax_count']
                adult_price += rec['amount'] * rec['pax_count']
            if rec['pax_type'] == 'CHD' and rec['charge_code'] == 'fare':
                child_amount += rec['pax_count']
                child_price += rec['amount'] * rec['pax_count']
            # if rec['pax_type'] == 'INF' and rec['charge_code'] == 'fare':
            #     infant_amount += rec['pax_count']
            if rec['charge_code'] == 'r.ac':
                commission_total += rec['amount'] * rec['pax_count'] * -1
            if rec['pax_type'] == 'ADT' and rec['charge_code'] == 'tax':
                additional_charge_amount += rec['pax_count']
                additional_charge_total += rec['amount']
        total_itinerary_price = senior_price + adult_price + child_price + additional_charge_total

        values = {
            'senior_amount': senior_amount,
            'senior_price': senior_price,
            'adult_amount': adult_amount,
            'adult_price': adult_price,
            'child_amount': child_amount,
            'child_price': child_price,
            'additional_charge_amount': additional_charge_amount,
            'additional_charge_total': additional_charge_total,
            'infant_amount': infant_amount,
            'infant_price': infant_price,
            'total_itinerary_price': total_itinerary_price,
            'commission_total': commission_total
        }
        return values

    def get_booking_for_vendor_by_api(self, data):
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
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            result = ERR.get_error(500)
        return result

    def get_booking_by_api(self, res, req):
        try:
            values = res['response']
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
            for rec in activity_booking.passenger_ids:
                passengers.append({
                    'name': str(rec.title) + '. ' + str(rec.first_name) + ' ' + str(rec.last_name),
                    'birth_date': rec.birth_date,
                    'pax_type': rec.pax_type,
                    'sku_name': rec.activity_sku_id.title
                })

            # prices = self.prepare_summary_prices(api_price_ids, activity_booking[0]['infant'])
            # prices.update({
            #     'total_itinerary_price': prices['total_itinerary_price'],
            # })

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

            attachments = self.env['ir.attachment'].search([('res_model', '=', 'tt.reservation.activity'), ('res_id', '=', activity_booking.id)]).ids
            booking_obj = self.env['tt.reservation.activity'].search([('name', '=', order_number)])

            if not attachments:
                res2 = self.get_vouchers_button_api(activity_booking.id, self.env.user.id)
                if res2:
                    attachments = res2

            if attachments:
                booking_obj.sudo().write({
                    'state': 'done',
                })
                self.env.cr.commit()
                values.update({
                    'status': 'done',
                })

            if booking_obj.state != 'done':
                booking_obj.sudo().write({
                    'state': values['status']
                })
                self.env.cr.commit()

            response = {
                'contacts': {
                    'email': activity_booking.contact_email,
                    'name': activity_booking.contact_name,
                    'phone': activity_booking.contact_phone,
                    'gender': contact.gender and contact.gender or '',
                    'marital_status': contact.marital_status and contact.marital_status or '',
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
                'currencyCode': values['currencyCode'],
                # 'price_itinerary': prices,
                'passengers': passengers,
                'name': order_number,
                'activity_details': activity_details,
                'voucher_detail': voucher_detail,
                'uuid': values.get('uuid') and values['uuid'] or '',
                'status': values['status'],
                'attachment_ids': attachments,
                'booking_options': book_option_ids,
            }
            result = ERR.get_no_error(response)
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            result = ERR.get_error(500)
        return result

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
        self.send_push_notif('booked')

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

    def get_booking(self, booking_number):
        row = self.env['tt.reservation.activity'].search([('name', '=', booking_number)])
        if not row:
            return ''
        temp = {
            'provider': row.provider,
            'uuid': row.booking_uuid,
            'pnr': row.pnr,
            'order_id': row.id,
            'upload_value': row.file_upload,
            'total_amount': row.total_fare,
        }
        return temp

    def get_booking_activity(self, booking_number=None, booking_id=None, api_context=None):
        if booking_number:
            booking_id = self.sudo().get_id(booking_number)

        if not booking_id:
            return {
                'error_code': 200,
                'error_msg': 'Invalid booking number %s or agent id' % booking_number
            }

        book_obj = self.sudo().browse(booking_id)

        # ENABLE IN PRODUCTION
        # user_obj = self.env['res.users'].sudo().browse(api_context['co_uid'])
        # if book_obj.agent_id.id != user_obj.agent_id.id:
        #     return {
        #         'error_code': 200,
        #         'error_msg': 'Invalid booking number %s or agent id' % booking_number,
        #         'response': {}
        #     }

        def get_pricelist_info(activity_id):
            values = {
                'id': activity_id.id,
                'name': activity_id.name,
                'description': activity_id.description,
                'pax_type': activity_id.pax_type,
                'transport_type': activity_id.transport_type,
                'duration': activity_id.duration,
                'entry_type': activity_id.entry_type,
                'visa_type': activity_id.visa_type,
                'passport_type': activity_id.passport_type,
                'apply_type': activity_id.apply_type,
                'process_type': activity_id.process_type,
                'notes': activity_id.notes,
                'country': {
                    'id': activity_id.country_id.id,
                    'name': activity_id.country_id.name,
                },
            }
            return values

        def get_itinerary_price(rec):
            res = []
            for price in rec:
                price_values = {
                    'charge_code': price.charge_code,
                    'pax_type': price.pax_type,
                    'currency': price.currency_id and {
                        'id': price.currency_id.id,
                        'name': price.currency_id.name,
                    } or {},
                    'pax_count': price.pax_count,
                    'amount': price.amount,
                    'total': price.total,
                    'foreign_amount': price.foreign_amount,
                    'foreign_currency': price.foreign_currency and {
                        'id': price.foreign_currency.id,
                        'name': price.foreign_currency.name,
                    } or {},
                    'description': price.description and price.description or '',
                }
                res.append(price_values)
            return res

        def get_contacts(rec):
            values = {
                'title': rec.title or '',
                'first_name': rec.first_name or '',
                'last_name': rec.last_name or '',
                'mobile': rec.mobile or '',
                'email': rec.email or '',
                'home_phone': rec.home_phone or '',
                'work_phone': rec.work_phone or '',
                'other_phone': rec.other_phone or '',
                'address': rec.address or '',
                'city': rec.city or '',
            }
            return values

        def get_passengers(to_passenger_ids):
            res = []
            for rec in to_passenger_ids:
                passenger = rec.passenger_id
                passenger_values = {
                    'title': passenger.title or '',
                    'first_name': passenger.first_name or '',
                    'last_name': passenger.last_name or '',
                    'pax_type': passenger.pax_type or '',
                    'birth_date': passenger.birth_date or '',
                    'nationality': {
                        'id': passenger.nationality_id.id or '',
                        'name': passenger.nationality_id.name or '',
                        'code': passenger.nationality_id.code or '',
                        'phone_code': passenger.nationality_id.phone_code or '',
                    },
                    'mobile': passenger.mobile or '',
                    'email': passenger.email or '',
                    'passport_number': passenger.passport_number or '',
                    'passport_expdate': passenger.passport_expdate or '',
                    'identity_number': passenger.identity_number or '',
                    'identity_type': passenger.identity_type or '',
                    'pricelist': get_pricelist_info(rec.activity_id) or '',
                }
                res.append(passenger_values)
            return res

        booking_row = {
            'id': book_obj.id or '',
            'name': book_obj.name or '',
            'date': book_obj.issued_date or '',
            'state': book_obj.state or '',
            'hold_date': book_obj.hold_date or ''
        }
        booking_row.update({
            'contacts': get_contacts(book_obj.contact_id) or {},
            # 'passengers': get_passengers(book_obj.to_passenger_ids) or [],
            'price_itinerary': get_itinerary_price(book_obj.sale_service_charge_ids) or [],
        })

        if not booking_row:
            return {
                'error_code': 200,
                'error_msg': 'Invalid booking number or agent id'
            }

        return {
            'response': booking_row,
            'error_code': 0,
            'error_msg': False
        }

    def confirm_booking_webhook(self, req):
        order_id = req.get('order_id')
        if order_id:
            book_obj = self.sudo().search([('pnr', '=', order_id)], limit=1)
            book_obj = book_obj[0]
            if book_obj.state not in ['done', 'cancel', 'cancel2', 'refund']:
                book_obj.sudo().write({
                    'state': req.get('status') == 'confirmed' and 'done' or 'rejected',
                    'voucher_url': req.get('voucher_url') and req['voucher_url'] or ''
                })

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

    def cron_update_status_booking(self):
        try:
            cookie = ''
            booking_objs = self.env['tt.reservation.activity'].search([('state', 'not in', ['rejected', 'cancel', 'done', 'cancel2', 'refund'])])
            for rec in booking_objs:
                req = {
                    'provider': rec['provider_name'],
                    'uuid': rec['booking_uuid'],
                    'pnr': rec['pnr']
                }
                if req['uuid'] or req['pnr']:
                    if req['provider']:
                        res = ApiConnectorActivity().get_booking(req, cookie)
                        if res['response']:
                            values = res['response']
                            method_name = 'action_%s' % values['status']
                            if hasattr(rec, method_name):
                                getattr(rec, method_name)()
                        else:
                            rec.action_failed_sync()
                            values = {
                                'status': 'failed',
                            }
                        if rec['state'] != values['status']:
                            self.send_notif_update_status_activity(rec, values['status'])
                    else:
                        pass
                else:
                    if rec['state'] != 'failed':
                        rec.action_failed_sync()
                        self.send_notif_update_status_activity(rec, 'failed')

        except Exception as e:
            _logger.error('Cron Error: Update Status Booking' + '\n' + traceback.format_exc())

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