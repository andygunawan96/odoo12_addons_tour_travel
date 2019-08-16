from odoo import api, fields, models, _
from datetime import datetime, timedelta, date, time
from odoo import http
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
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


class ActivityTtLedger(models.Model):
    _inherit = 'tt.ledger'

    reservation_activity_id = fields.Many2one('tt.reservation.activity', 'Activity Booking', readonly=True)


class ActivityInvoiceInh(models.Model):
    _inherit = 'tt.agent.invoice'

    activity_transaction_id = fields.Many2one('tt.reservation.activity', 'Activity Booking', readonly=True)


class ActivityPricesInh(models.Model):
    _inherit = 'tt.service.charge'

    activity_id = fields.Many2one('tt.reservation.activity', 'Activity Booking', readonly=True)


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


class ActivityBooking(models.Model):
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
    passenger_ids = fields.Many2many('tt.customer', 'tt_reservation_activity_passengers_rel', 'booking_id',
                                     'passenger_id',
                                     string='List of Passenger', readonly=True, states={'draft': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'activity_id', string='Prices')
    invoice_ids = fields.One2many('tt.agent.invoice', 'activity_transaction_id', string='Invoices')
    ledger_id = fields.One2many('tt.ledger', 'reservation_activity_id', string='Ledgers')
    line_ids = fields.One2many('tt.reservation.activity.line', 'reservation_activity_id', string='Line')

    booking_option = fields.Text('Booking Option')

    information = fields.Text('Additional Information')
    file_upload = fields.Text('File Upload')
    voucher_url = fields.Text('Voucher URL')

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

    def action_confirm(self, commission, parent_commission, ho_commission):
        self.create_agent_invoice_activity()
        self._create_ledger_activity()
        self._create_commission_ledger_activity(commission, parent_commission, ho_commission)

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
                        'reservation_activity_id': self.id,
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

                    self.vendor_ledger_id = self.env['tt.vendor.ledger'].sudo().create({
                        'debit': 0,
                        'credit': temp2,
                        'vendor_id': self.env['res.partner'].search([('provider_code', '=', self.provider_name)],
                                                                    limit=1).id,
                        'description': self.name,
                        'name': self.env['res.partner'].search([('provider_code', '=', self.provider_name)],
                                                               limit=1).name,
                    })
                    self.send_notif_current_balance(self.sudo().vendor_ledger_id.curr_balance, self.state,
                                                    self.pnr)

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
            'state': 'expired',
            'expired_date': datetime.now(),
        })
        self.message_post(body='Order EXPIRED')

    def action_refunded(self):
        self.write({
            'state': 'refunded',
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
            'state': 'cancelled',
            'cancelled_date': datetime.now(),
            'cancelled_uid': self.env.user.id
        })
        self.message_post(body='Order CANCELLED')

    def action_failed(self, booking_id, error_msg):
        booking_rec = self.browse(booking_id)
        booking_rec.write({
            'state': 'failed',
            'error_msg': error_msg
        })
        return {
            'error_code': 0,
            'error_msg': False,
            'response': 'action_fail_booking'
        }

    def action_failed_sync(self):
        self.write({
            'state': 'failed',
        })
        self.message_post(body='Order FAILED')

    def action_done(self):
        self.write({
            'state': 'done',
        })
        self.message_post(body='Order DONE')

    #######################################################################################################
    #######################################################################################################

    def _create_ledger_activity(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            vals = ledger.prepare_vals('Activity Payment : ' + rec.name, rec.name,
                                       str(fields.Datetime.now()), 'activity', rec.currency_id.id, 0, rec.total)
            vals.update({
                'reservation_activity_id': rec.id,
                'agent_id': rec.agent_id.id,
                'pnr': rec.pnr,
                'display_provider_name': rec.activity_id.name,
            })
            # vals['description'] = rec.description

            new_aml = ledger.sudo().create(vals)
            new_aml.action_done()

    def _create_anti_ledger_activity(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            vals = ledger.prepare_vals('Reversal Activity Payment : ' + rec.name, rec.name,
                                       str(fields.Datetime.now()), 'activity', rec.currency_id.id, rec.total, 0)
            vals['reservation_activity_id'] = rec.id
            vals['agent_id'] = rec.agent_id.id
            vals['display_provider_name'] = rec.activity_id.name

            new_aml = ledger.sudo().create(vals)
            new_aml.action_done()
            # rec.cancel_ledger_id = new_aml

    def _create_commission_ledger_activity(self, agent_commission, parent_commission, ho_commission):
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            # total_commission = rec.total_commission
            #
            # if rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_btbo').id]:
            #     agent_commission = total_commission
            #     parent_commission = 0
            #     ho_commission = 0
            # elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_japro').id, self.env.ref('tt_base_rodex.agent_type_btbr').id]:
            #     agent_commission = total_commission * 0.8
            #     parent_commission = total_commission * 0.17
            #     ho_commission = total_commission * 0.03
            # elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_fipro').id]:
            #     agent_commission = total_commission * 0.6
            #     parent_commission = total_commission * 0.35
            #     ho_commission = total_commission * 0.05
            # elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id]:
            #     agent_commission = 0
            #     parent_commission = total_commission
            #     ho_commission = 0
            # else:
            #     agent_commission = 0
            #     parent_commission = 0
            #     ho_commission = 0

            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name,
                                               str(fields.Datetime.now()), 'commission', rec.currency_id.id, agent_commission, 0)
                vals.update({
                    'agent_id': rec.agent_id.id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml.id

            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, str(fields.Datetime.now()), 'commission',
                                               rec.currency_id.id, parent_commission, 0)
                vals.update({
                    'agent_id': rec.customer_parent_id.parent_agent_id.id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

            if ho_commission > 0:
                vals = ledger_obj.prepare_vals('Commission & Profit : ' + rec.name, 'HO: ' + rec.name, str(fields.Datetime.now()),
                                               'commission',
                                               rec.currency_id.id, ho_commission, 0)
                vals.update({
                    'agent_id': rec.env['res.partner'].sudo().search(
                        [('is_HO', '=', True), ('parent_id', '=', False)], limit=1).id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

    def _create_anti_commission_ledger_activity(self):
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            sum_comisi = rec.sum_comisi

            if rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_btbo').id]:
                agent_commission = sum_comisi
                parent_commission = 0
                ho_commission = 0
            elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_japro').id, self.env.ref('tt_base_rodex.agent_type_btbr').id]:
                agent_commission = sum_comisi * 0.8
                parent_commission = sum_comisi * 0.17
                ho_commission = sum_comisi * 0.03
            elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_fipro').id]:
                agent_commission = sum_comisi * 0.6
                parent_commission = sum_comisi * 0.35
                ho_commission = sum_comisi * 0.05
            elif rec.customer_parent_id.agent_type_id.id in [self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id]:
                agent_commission = 0
                parent_commission = sum_comisi
                ho_commission = 0
            else:
                agent_commission = 0
                parent_commission = 0
                ho_commission = 0

            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Reversal Commission : ' + rec.name, rec.name,
                                               str(fields.Datetime.now()), 'commission', rec.currency_id.id, 0, agent_commission)
                vals.update({
                    'agent_id': rec.agent_id.id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml.id

            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Reversal Commission : ' + rec.name, 'PA: ' + rec.name, str(fields.Datetime.now()), 'commission',
                                               rec.currency_id.id, 0, parent_commission)
                vals.update({
                    'agent_id': rec.customer_parent_id.parent_agent_id.id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

            if ho_commission > 0:
                vals = ledger_obj.prepare_vals('Reversal Commission & Profit : ' + rec.name, 'HO: ' + rec.name, str(fields.Datetime.now()),
                                               'commission',
                                               rec.currency_id.id, 0, ho_commission)
                vals.update({
                    'agent_id': rec.env['res.partner'].sudo().search(
                        [('is_HO', '=', True), ('parent_id', '=', False)], limit=1).id,
                    'reservation_activity_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

    def create_agent_invoice_activity(self):
        def prepare_agent_invoice(self):
            return {
                'origin': self.name,
                'agent_id': self.agent_id.id,
                'customer_parent_id': self.customer_parent_id.id,
                'contact_id': self.contact_id.id,
                'activity_transaction_id': self.id,
                'pnr': self.pnr
            }

        Invoice = self.env['tt.agent.invoice']
        InvoiceLine = self.env['tt.agent.invoice.line']
        invoice = Invoice.create(prepare_agent_invoice(self))

        if self.activity_id.name and self.activity_product:
            try:
                description = str(self.activity_id.name.decode('utf-8')) + '\n' + str(self.activity_product.decode('utf-8')) + '\n' + str(self.visit_date) + '\nAn. '
            except:
                description = str(self.activity_id.name.encode('utf-8')) + '\n' + str(self.activity_product.encode('utf-8')) + '\n' + str(self.visit_date) + '\nAn. '
        else:
            description = str(self.activity_id.name) + '\n' + str(self.activity_product) + '\n' + str(self.visit_date) + '\nAn. '

        for pax in self.line_ids:
            description += str(pax['passenger_id']['title'] + ' ' + pax['passenger_id']['first_name'] + ' ' + pax['passenger_id']['last_name']) + '\n'
        for price in self.sale_service_charge_ids:
            if price['charge_code'] not in ['r.ac', 'r.oc', 'r.ac1', 'r.oc1', 'r.ac2', 'r.oc2']:
                values_line = {
                    'name': description,
                    'price_unit': price['amount'],
                    'quantity': price['pax_count'],
                }
                values_line.update({'invoice_id': invoice.id})
                InvoiceLine.sudo().create(values_line)

    #######################################################################################################
    #######################################################################################################

    def delete_prices(self, booking_id):
        try:
            booking_obj = self.browse(booking_id)
            for rec in booking_obj.ledger_id:
                if rec.transaction_type == 3:
                    ledger_type = 'commission'
                if rec.transaction_type == 23:
                    ledger_type = 'activity'
                vals = self.env['tt.ledger'].prepare_vals(rec.name, rec.ref, str(fields.Datetime.now()),
                                                          ledger_type, rec.currency_id.id, rec.credit, rec.debit)
                vals.update({
                    'agent_id': rec.agent_id.id,
                    'reservation_activity_id': booking_obj.id,
                })
                ledger_obj = self.env['tt.ledger'].create(vals)
                ledger_obj.action_done()
            for rec in booking_obj.invoice_id:
                rec.sudo().action_cancel()
            return {
                'error_code': 0,
                'error_msg': 'Success',
            }
        except Exception as e:
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nDelete prices failure'
            }

    def update_booking(self, booking_id, prices, book_info, api_context, kwargs):
        try:
            booking_obj = self.browse(booking_id)
            booking_obj.write({
                'pnr': book_info['code'],
                'booking_uuid': book_info['uuid'],
                'sid': api_context['sid'],
                'state': book_info['status']
            })
            self.env.cr.commit()

            if not api_context or api_context['co_uid'] == 1:
                api_context['co_uid'] = booking_obj.booked_uid.id

            sale_service_charge_summary = book_info['amountBreakdown']
            service_chg_obj = self.env['tt.service.charge']
            pax_lib = {
                'senior': 'YCD',
                'adult': 'ADT',
                'child': 'CHD',
                'infant': 'INF',
            }
            from_currency = self.env['res.currency'].search([('name', '=', book_info['currencyCode'])])
            agent_type = self.env['res.users'].browse(api_context['co_uid']).agent_id.agent_type_id.id
            if agent_type == self.env.ref('tt_base_rodex.agent_type_ho').id:
                agent_type = booking_obj.agent_type_id.id

            if agent_type in [self.env.ref('tt_base_rodex.agent_type_citra').id, self.env.ref('tt_base_rodex.agent_type_btbo').id]:
                multiplier = 1
                parent_multiplier = 0
                ho_multiplier = 0
            elif agent_type in [self.env.ref('tt_base_rodex.agent_type_japro').id, self.env.ref('tt_base_rodex.agent_type_btbr').id]:
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

            for service_charge in booking_obj.sale_service_charge_ids:
                service_charge.sudo().unlink()

            for val in sale_service_charge_summary:
                pax_type_string = ''
                if val.get('name'):
                    if val['name'] == 'senior':
                        pax_type_string = 'seniors'
                        # pax = book_info['seniors']
                    elif val['name'] == 'adult':
                        pax_type_string = 'adults'
                        # pax = book_info['adults']
                    elif val['name'] == 'child':
                        pax_type_string = 'children'
                        # pax = book_info['children']
                    else:
                        pax_type_string = 'adults'
                        # pax = book_info['adults']

                if val.get('price'):
                    to_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(val['price']))

                    # break down coding ini kalo mau min price berdasarkan masing2 max type
                    pax = book_info['adults'] + book_info['children'] + book_info['seniors']
                    for price in prices:
                        for price_temp in price:
                            if book_info.get('event_id') and price_temp.get('id'):
                                if price_temp['id'] == book_info['event_id']:
                                    min_currency = price_temp['prices'][pax_type_string][str(pax)]
                            else:
                                if price_temp['date'] == book_info['arrivalDate']:
                                    min_currency = price_temp['prices'][pax_type_string][str(pax)]
                    ############################################################

                    # if val['name'] == 'senior':
                    #     if book_info['productTypeUuid'] == 'efedb1fc-f150-5eaa-bf6e-fc202f6114bd': #uss
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(38))
                    #     elif book_info['productTypeUuid'] == '7c101353-085e-5a3c-935e-35ac89761f39': #sea
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(26))
                    #     elif book_info['productTypeUuid'] == '2d22548e-365b-4ca7-bc5c-7bcfac7d44b4': #combo
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(62))
                    # if val['name'] == 'adult':
                    #     if book_info['productTypeUuid'] == 'efedb1fc-f150-5eaa-bf6e-fc202f6114bd': #uss
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(72))
                    #     elif book_info['productTypeUuid'] == '7c101353-085e-5a3c-935e-35ac89761f39': #sea
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(35))
                    #     elif book_info['productTypeUuid'] == '2d22548e-365b-4ca7-bc5c-7bcfac7d44b4': #combo
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(107))
                    # if val['name'] == 'child':
                    #     if book_info['productTypeUuid'] == 'efedb1fc-f150-5eaa-bf6e-fc202f6114bd': #uss
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(53))
                    #     elif book_info['productTypeUuid'] == '7c101353-085e-5a3c-935e-35ac89761f39': #sea
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(26))
                    #     elif book_info['productTypeUuid'] == '2d22548e-365b-4ca7-bc5c-7bcfac7d44b4': #combo
                    #         min_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(79))

                    if to_currency:
                        final_price = to_currency + 10000
                        commission_ho += 10000 * val['quantity']
                        # if to_currency <= 150000:
                        #     final_price = to_currency + 2000
                        #     commission_ho += 2000 * val['quantity']
                        # elif to_currency <= 300000:
                        #     final_price = to_currency + 4000
                        #     commission_ho += 4000 * val['quantity']
                        # elif to_currency <= 450000:
                        #     final_price = to_currency + 6000
                        #     commission_ho += 6000 * val['quantity']
                        # elif to_currency <= 600000:
                        #     final_price = to_currency + 8000
                        #     commission_ho += 8000 * val['quantity']
                        # else:
                        #     final_price = to_currency + 10000
                        #     commission_ho += 10000 * val['quantity']
                    else:
                        final_price = 0

                    sale_price = int(final_price * 1.03)

                    if api_context['is_mobile']:
                        min_currency2 = min_currency['sale_price']
                    else:
                        min_currency2 = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, float(min_currency))

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
                        'activity_id': booking_id,
                        'charge_code': 'fare',
                        'charge_type': 'fare',
                        'pax_type': pax_lib[val['name']],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['quantity'],
                        'amount': int(final_sale_price),
                        'foreign_amount': val['price'],
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    })
                    val.pop('price')
                    val.pop('name')
                    val.pop('quantity')
                    service_chg_obj.create(val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.ac',
                        'charge_type': 'r.ac',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': int(final_commission_price) * -1,
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.ac1',
                        'charge_type': 'r.ac1',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': parent_commission_price * -1,
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.ac2',
                        'charge_type': 'r.ac2',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': ho_commission_price * -1,
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.oc',
                        'charge_type': 'r.oc',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': int(final_commission_price),
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.oc1',
                        'charge_type': 'r.oc1',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': parent_commission_price,
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    commission_val = {
                        'activity_id': booking_id,
                        'charge_code': 'r.oc2',
                        'charge_type': 'r.oc2',
                        'pax_type': val['pax_type'],
                        'currency_id': self.env['res.currency'].browse(self.env.user.company_id.currency_id.id).id,
                        'pax_count': val['pax_count'],
                        'amount': ho_commission_price,
                        'foreign_amount': 0,
                        'foreign_currency_id': self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1).id,
                        'description': booking_obj.provider_name,
                    }
                    service_chg_obj.create(commission_val)
                    self.env.cr.commit()

                    booking_obj.action_calc_prices()

            if kwargs['force_issued']:
                booking_obj.action_confirm(total_commission_price, total_parent_commission_price, total_ho_commission_price)

                vals = self.env['tt.ledger'].prepare_vals('Commission & Profit : ' + booking_obj.name, 'HO: ' + booking_obj.name, str(fields.Datetime.now()), 'commission', booking_obj.currency_id.id, commission_ho, 0)
                vals.update({
                    'agent_id': self.env['res.partner'].sudo().search([('is_HO', '=', True), ('parent_id', '=', False)], limit=1).id,
                    'reservation_activity_id': booking_obj.id,
                })
                commission_aml = self.env['tt.ledger'].create(vals)
                commission_aml.action_done()

                from_currency = self.env['res.currency'].search([('name', '=', book_info['currencyCode'])], limit=1)
                temp1 = 0
                for rec in booking_obj.sale_service_charge_ids:
                    if rec['charge_code'] == 'fare':
                        temp1 += rec['foreign_amount'] * rec['pax_count']
                temp2 = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, temp1)

                temp3 = self.env['tt.vendor.ledger'].search([('description', '=', booking_obj.name)])
                for temp4 in temp3:
                    temp4.sudo().unlink()

                booking_obj.vendor_ledger_id = self.env['tt.vendor.ledger'].sudo().create({
                    'debit': 0,
                    'credit': temp2,
                    'vendor_id': self.env['res.partner'].search([('provider_code', '=', booking_obj.provider_name)], limit=1).id,
                    'description': booking_obj.name,
                    'name': self.env['res.partner'].search([('provider_code', '=', booking_obj.provider_name)], limit=1).name,
                })
                self.send_notif_current_balance(booking_obj.sudo().vendor_ledger_id.curr_balance, booking_obj.state, booking_obj.pnr)

            return {
                'error_code': 0,
                'error_msg': 'Success',
                'order_number': booking_obj.name,
            }


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

    def _validate_activity(self, data, type):
        list_data = []
        if type == 'context':
            list_data = ['co_uid', 'is_company_website']
        elif type == 'header':
            list_data = ['senior', 'adult', 'child', 'infant']

        keys_data = []
        for rec in data.iterkeys():
            keys_data.append(str(rec))

        for ls in list_data:
            if not ls in keys_data:
                raise Exception('ERROR Validate %s, key : %s' % (type, ls))
        return True

    def _activity_header_normalization(self, data):
        res = {}
        int_key_att = ['senior', 'adult', 'child', 'infant']

        for rec in int_key_att:
            res.update({
                rec: int(data[rec])
            })

        return res

    def update_api_context(self, customer_parent_id, context):
        context['co_uid'] = int(context['co_uid'])
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        if context['is_company_website']:
            #============================================
            #====== Context dari WEBSITE/FRONTEND =======
            #============================================
            if user_obj.agent_id.agent_type_id.id in \
                    (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                # ===== COR/POR User =====
                context.update({
                    'agent_id': user_obj.agent_id.parent_agent_id.id,
                    'customer_parent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif customer_parent_id:
                # ===== COR/POR in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'customer_parent_id': customer_parent_id,
                    'booker_type': 'COR/POR',
                })
            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'customer_parent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })
        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'customer_parent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context

    def _create_contact(self, vals, context):
        country_obj = self.env['res.country'].sudo()
        contact_obj = self.env['tt.customer.details'].sudo()
        if vals.get('contact_id'):
            vals['contact_id'] = int(vals['contact_id'])
            contact_rec = contact_obj.browse(vals['contact_id'])
            if contact_rec:
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    'mobile': vals.get('mobile', contact_rec.mobile),
                })
            return contact_rec

        country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
        vals['nationality_id'] = country and country[0].id or False

        if context['booker_type'] == 'COR/POR':
            vals['passenger_on_partner_ids'] = [(4, context['customer_parent_id'])]

        country = country_obj.search([('code', '=', vals.pop('country_code'))])
        vals.update({
            'commercial_agent_id': context['agent_id'],
            'agent_id': context['agent_id'],
            'country_id': country and country[0].id or False,
            'pax_type': 'ADT',
            'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
            'mobile_orig': vals.get('mobile', ''),
            'email': vals.get('email', vals['email']),
            'mobile': vals.get('mobile', vals['mobile']),
        })
        return contact_obj.sudo().create(vals)

    # def issued_booking(self, service_charge_summary, activity_data, context, kwargs):
    #     book_obj = self.browse(context['order_id'])
    #     book_obj.action_issued_activity(service_charge_summary, activity_data, kwargs, context)
    #     self.env.cr.commit()
    #     return {
    #         'error_code': 0,
    #         'error_msg': 'Success',
    #         'response': {
    #             'order_id': book_obj.id,
    #             'order_number': book_obj.name,
    #             'status': book_obj.state,
    #         }
    #     }

    def _create_passengers(self, passengers, contact_obj, context):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer.details'].sudo()
        res_ids = []
        for psg in passengers:
            if psg.get('nationality_code'):
                country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False

            vals_for_update = {
                # 'passport_number': psg.get('passport_number'),
                # 'passport_expdate': psg.get('passport_expdate'),
                'nationality_id': psg['nationality_id'],
                # 'country_of_issued_id': psg.get('country_of_issued_id'),
                # 'passport_issued_date': psg.get('passport_issued_date'),
                # 'identity_type': psg.get('identity_type'),
                # 'identity_number': psg.get('identity_number'),
                'birth_date': psg.get('birth_date'),
                'email': psg.get('email'),
                'commercial_agent_id': contact_obj.commercial_agent_id.id,
                'agent_id': contact_obj.agent_id.id,
                'mobile': psg.get('mobile'),
            }

            psg_exist = False
            if psg['passenger_id']:
                psg['passenger_id'] = int(psg['passenger_id'])
                passenger_obj = self.env['tt.customer.details'].sudo().browse(psg['passenger_id'])
                if passenger_obj:
                    psg_exist = True
                    if context['booker_type'] == 'COR/POR':
                        vals_for_update['passenger_on_partner_ids'] = [(4, context['customer_parent_id'])]
                    passenger_obj.write(vals_for_update)
                    res_ids.append(passenger_obj.id)
            if not psg_exist:
                # Cek Booker sama dengan Passenger
                if [psg['title'], psg['first_name'], psg['last_name']] == [contact_obj.title, contact_obj.first_name, contact_obj.last_name]:
                    contact_obj.write(vals_for_update)
                    psg_exist = True
                    res_ids.append(contact_obj.id)

            if not psg_exist:
                if context['booker_type'] == 'COR/POR':
                    psg['passenger_on_partner_ids'] = [(4, context['customer_parent_id'])]
                    psg['agent_id'] = context['customer_parent_id']
                else:
                    psg['agent_id'] = context['agent_id']

                psg.update({
                    'commercial_agent_id': context['agent_id'],
                    'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone:</span>'.format(**psg),
                })
                psg_obj = passenger_obj.create(psg)
                res_ids.append(psg_obj.id)
        return res_ids

    def create_booking(self, contact_data, passengers, option, search_request, file_upload, context, kwargs):
        try:
            self._validate_activity(context, 'context')
            self._validate_activity(search_request, 'header')
            try:
                agent_obj = self.env['tt.customer.details'].browse(int(contact_data['contact_id'])).agent_id
                if not agent_obj:
                    agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            except Exception:
                agent_obj = self.env['res.users'].browse(int(context['co_uid'])).agent_id
            context = self.update_api_context(agent_obj.id, context)

            if kwargs['force_issued']:
                is_enough = self.env['res.partner'].check_balance_limit(agent_obj.id, kwargs['amount'])
                if not is_enough['error_code'] == 0:
                    raise Exception('BALANCE not enough')

            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            # PRODUCTION
            # self.validate_booking(api_context=context)
            user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
            contact_data.update({
                'agent_id': user_obj.agent_id.id,
                'commercial_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
                'display_mobile': user_obj.mobile,
            })
            if user_obj.agent_id.agent_type_id.id in (self.env.ref('tt_base_rodex.agent_type_cor').id, self.env.ref('tt_base_rodex.agent_type_por').id):
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'COR/POR',
                        'display_mobile': user_obj.mobile,
                    })

            header_val = self._activity_header_normalization(search_request)
            contact_obj = self._create_contact(contact_data, context)

            psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
            activity_id = self.env['tt.master.activity.lines'].sudo().search([('uuid', '=', search_request['product_type_uuid'])])

            booking_option = ''
            if option['perBooking']:
                for rec in option['perBooking']:
                    booking_option += rec['name'] + ': ' + str(rec['value']) + '\n'

            header_val.update({
                'contact_id': contact_obj.id,
                'display_mobile': contact_obj.mobile,
                'state': 'reserved',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
                'activity_id': activity_id.activity_id.id,
                'visit_date': datetime.strptime(search_request['visit_date'], '%Y-%m-%d').strftime('%d %b %Y'),
                'activity_name': activity_id.activity_id.name,
                'activity_product': activity_id.name,
                'activity_product_uuid': search_request['product_type_uuid'],
                'booking_option': booking_option,
                'senior': search_request['senior'],
                'adult': search_request['adult'],
                'child': search_request['child'],
                'infant': search_request['infant'],
                'transport_type': 'activity',
                'provider': activity_id.activity_id.provider,
                'file_upload': file_upload,
            })

            if not activity_id.instantConfirmation:
                header_val.update({
                    'information': 'On Request (max. 3 working days)',
                })

            # create header & Update customer_parent_id
            book_obj = self.sudo().create(header_val)

            # kwargs.update({
            #     'visit_date': search_request['visit_date'],
            # })

            for psg in passengers:
                vals = {
                    'reservation_activity_id': book_obj.id,
                    'passenger_id': psg['passenger_id'],
                    'pax_type': psg['pax_type'],
                    'pax_mobile': psg.get('mobile'),
                    'api_data': psg.get('api_data'),
                    # 'pricelist_id': book_obj.activity_id.id
                }
                self.env['tt.reservation.activity.line'].sudo().create(vals)

            # for rec in service_charge_summary:
            #     rec.update({
            #         'reservation_activity_id': book_obj.id,
            #         'activity_id': rec['pricelist_id'],
            #         'currency_id': self.env['res.currency'].search([('name', '=', rec['currency'])]).id
            #     })
            #     rec.pop('pricelist_id')
            #     rec.pop('currency')
            #     self.env['tt.reservation.activity.price'].sudo().create(rec)

            book_obj.customer_parent_id = contact_data['agent_id']

            book_obj.action_booked_activity(context)
            context['order_id'] = book_obj.id
            if kwargs['force_issued']:
                book_obj.action_issued_activity(context)

            self._create_passengers(passengers, contact_obj, context)

            self.env.cr.commit()
            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': {
                    'order_id': book_obj.id,
                    'order_number': book_obj.name,
                    'status': book_obj.state,
                }
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def _evaluate_passenger_info(self, passengers, contact_id, agent_id):
        res = []
        country_obj = self.env['res.country'].sudo()
        psg_obj = self.env['tt.customer.details'].sudo()
        for psg in passengers:
            p_id = psg.get('passenger_id')
            if p_id:
                p_object = psg_obj.browse(int(p_id))
                if p_object:
                    res.append(int(p_id))
                    if psg.get('passport_number'):
                        p_object['passport_number'] = psg['passport_number']
                    if psg.get('passport_expdate'):
                        p_object['passport_expdate'] = psg['passport_expdate']
                    if psg.get('country_of_issued_id'):
                        p_object['country_of_issued_id'] = psg['country_of_issued_id']
                    p_object.write({
                        'domicile': psg.get('domicile'),
                        'mobile': psg.get('mobile')
                    })
            else:
                country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
                if psg.get('country_of_issued_code'):
                    country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                    psg['country_of_issued_id'] = country and country[0].id or False
                if not psg.get('passport_expdate'):
                    try:
                        psg.pop('passport_expdate')
                    except Exception:
                        pass

                psg.update({
                    'contact_id': contact_id,
                    'passenger_id': False,
                    'agent_id': agent_id,
                })
                psg_res = psg_obj.sudo().create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                res.append(psg_res.id)
        return res

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

    def get_booking_by_api(self, data):
        order_number = data['order_number']

        self.env.cr.execute("""SELECT * FROM tt_reservation_activity WHERE name=%s""", (order_number,))
        activity_booking = self.env.cr.dictfetchall()

        self.env.cr.execute("""SELECT * FROM tt_tb_service_charge WHERE activity_id=%s""", (activity_booking[0]['id'],))
        api_price_ids = self.env.cr.dictfetchall()

        req = {
            'provider': api_price_ids[0]['description'],
            'uuid': activity_booking[0]['booking_uuid'],
            'pnr': activity_booking[0]['pnr'],
            'order_number': order_number,
            'order_id': activity_booking[0]['id'],
        }
        return req

    def get_booking_by_api2(self, res, req):
        values = res['response']
        order_number = req['order_number']

        self.env.cr.execute("""SELECT * FROM tt_reservation_activity WHERE name=%s""", (order_number,))
        activity_booking = self.env.cr.dictfetchall()

        self.env.cr.execute("""SELECT * FROM tt_service_charge WHERE activity_id=%s""", (activity_booking[0]['id'],))
        api_price_ids = self.env.cr.dictfetchall()

        self.env.cr.execute("""SELECT * FROM tt_reservation_activity_line WHERE reservation_activity_id=%s""", (activity_booking[0]['id'],))
        line_ids = self.env.cr.dictfetchall()

        pax_ids = ()
        for rec in line_ids:
            pax_ids += (rec['passenger_id'],)

        self.env.cr.execute("""SELECT birth_date, first_name, id, last_name, pax_type, title FROM tt_customer_details WHERE id in %s""", (pax_ids,))
        passenger_ids = self.env.cr.dictfetchall()

        prices = self.prepare_summary_prices(api_price_ids, activity_booking[0]['infant'])
        prices.update({
            'total_itinerary_price': prices['total_itinerary_price'],
        })

        temp = self.env['tt.master.activity'].browse(activity_booking[0]['activity_id'])
        activity_details = {
            'name': temp.name,
            'description': temp.description,
            'highlights': temp.highlights,
            'additionalInfo': temp.additionalInfo,
            'safety': temp.safety,
            'warnings': temp.warnings,
            'priceIncludes': temp.priceIncludes,
            'priceExcludes': temp.priceExcludes,
        }
        temp2 = self.env['tt.master.activity.lines'].search([('activity_id', '=', temp.id), ('uuid', '=', activity_booking[0]['activity_product_uuid'])])
        voucher_detail = {
            'voucher_validity': {
                'voucher_validity_date': temp2.voucher_validity_date,
                'voucher_validity_days': temp2.voucher_validity_days,
                'voucher_validity_type': temp2.voucher_validity_type,
            },
            'voucherUse': temp2.voucherUse,
            'voucherRedemptionAddress': temp2.voucherRedemptionAddress,
            'cancellationPolicies': temp2.cancellationPolicies,
        }

        attachments = self.env['ir.attachment'].search([('res_model', '=', 'tt.reservation.activity'), ('res_id', '=', activity_booking[0]['id'])]).ids
        booking_obj = self.env['tt.reservation.activity'].search([('name', '=', order_number)])

        if not attachments:
            res2 = self.get_vouchers_button_api(activity_booking[0]['id'], self.env.user.id)
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

        master = self.env['tt.master.activity'].browse(int(activity_booking[0]['activity_id']))

        result = {
            'contacts': {
                'email': values['email'],
                'first_name': values['firstName'],
                'last_name': values['lastName'],
                'phone': values['phone'],
                'title': values['salutation'],
            },
            'activity': {
                'name': activity_booking[0]['activity_name'],
                'type': values['productTypeTitle'],
            },
            'adults': values['adults'],
            'children': values['children'],
            'seniors': values['seniors'],
            'pnr': values['code'],
            'visit_date': values['arrivalDate'],
            'currencyCode': values['currencyCode'],
            # 'productTypeUuid': values['productTypeUuid'],
            'price_itinerary': prices,
            'passengers': passenger_ids,
            'name': order_number,
            'activity_details': activity_details,
            'voucher_detail': voucher_detail,
            'uuid': values['uuid'],
            'status': values['status'],
            'attachment_ids': attachments,
            'photo_url': master.image_ids[0].photos_url + master.image_ids[0].photos_path
        }
        return result

    def action_booked_activity(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        vals = {}
        if self.name == 'New':
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('activity.booking'),
            })

        vals.update({
            'state': 'reserved',
            'booked_uid': api_context and api_context['co_uid'],
            'date': datetime.now(),
            'hold_date': datetime.now() + relativedelta(days=1),
        })
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
            if book_obj.state not in ['approved', 'done', 'cancelled', 'expired', 'refunded']:
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
            booking_objs = self.env['tt.reservation.activity'].search([('state', 'not in', ['approved', 'rejected', 'cancelled', 'done', 'expired', 'refunded'])])
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