from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta
import base64
import json
from ...tools import util

_logger = logging.getLogger(__name__)


class ReservationPpob(models.Model):
    _name = "tt.reservation.ppob"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation PPOB"

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_ppob_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})
    passenger_ids = fields.One2many('tt.reservation.passenger.ppob', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    provider_booking_ids = fields.One2many('tt.provider.ppob', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_ppob.tt_provider_type_ppob'))
    prepaid_value = fields.Integer('Prepaid Value', default=0)
    is_ticket_printed = fields.Integer('Ticket Already Printed', default=0)
    ppob_bill_ids = fields.One2many('tt.bill.ppob', 'booking_id', string='Bills',
                                  readonly=True, states={'draft': [('readonly', False)]})
    ppob_bill_detail_ids = fields.One2many('tt.bill.detail.ppob', 'booking_id', string='Bill Details',
                                  readonly=True, states={'draft': [('readonly', False)]})

    def get_form_id(self):
        return self.env.ref("tt_reservation_ppob.tt_reservation_ppob_form_views")

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

    @api.depends('provider_booking_ids', 'provider_booking_ids.reconcile_line_id')
    def _compute_reconcile_state(self):
        for rec in self:
            if all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in rec.provider_booking_ids]):
                rec.reconcile_state = 'reconciled'
            elif any([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'match' or False for rec1 in rec.provider_booking_ids]):
                rec.reconcile_state = 'partial'
            elif all([rec1.reconcile_line_id and rec1.reconcile_line_id.state == 'cancel' or False for rec1 in rec.provider_booking_ids]):
                rec.reconcile_state = 'cancel'
            else:
                rec.reconcile_state = 'not_reconciled'

    def get_config_api(self, data, context):
        try:
            carrier_list = self.env['tt.transport.carrier'].search([('provider_type_id', '=', self.env.ref('tt_reservation_ppob.tt_provider_type_ppob').id)])
            multi_prov_carrier_list = self.env['tt.transport.carrier.search'].search([('carrier_id.provider_type_id', '=', self.env.ref('tt_reservation_ppob.tt_provider_type_ppob').id)])
            product_data = {}
            multi_prov_prod_data = {}
            for rec in multi_prov_carrier_list:
                carr_obj = rec.carrier_id
                for idx, prov in enumerate(rec.provider_ids):
                    prod_val = {
                        'name': idx > 0 and '%s %s' % (carr_obj.name, str(idx)) or carr_obj.name,
                        'code': '%s~%s' % (carr_obj.code, prov.code),
                        'category': carr_obj.icao,
                        'min_cust_number': carr_obj.adult_length_name,
                        'max_cust_number': carr_obj.child_length_name,
                        'provider_type': carr_obj.provider_type_id.name
                    }
                    if not multi_prov_prod_data.get(rec.ho_id.seq_id):
                        multi_prov_prod_data[rec.ho_id.seq_id] = {}
                    if not multi_prov_prod_data[rec.ho_id.seq_id].get(str(carr_obj.icao)):
                        multi_prov_prod_data[rec.ho_id.seq_id][str(carr_obj.icao)] = []
                    multi_prov_prod_data[rec.ho_id.seq_id][str(carr_obj.icao)].append(prod_val)
            for rec in carrier_list:
                prod_val = {
                    'name': rec.name,
                    'code': rec.code,
                    'category': rec.icao,
                    'min_cust_number': rec.adult_length_name,
                    'max_cust_number': rec.child_length_name,
                    'provider_type': rec.provider_type_id.name,
                }
                if not product_data.get(str(rec.icao)):
                    product_data[str(rec.icao)] = []
                product_data[str(rec.icao)].append(prod_val)
            allowed_denominations = [20000, 50000, 100000, 200000, 500000, 1000000, 5000000, 10000000, 50000000]
            voucher_data = {
                'prepaid_mobile': {},
                'game': {},
                'pdam': {},
                'pbb': {},
                'others': {}
            }
            for vouch_key in voucher_data.keys():
                # search_params = [('type', '=', vouch_key)]
                # if context.get('co_ho_id'):
                #     search_params.append(('ho_ids', '=', int(context['co_ho_id'])))
                # vouch_data = self.env['tt.master.voucher.ppob'].search(search_params)
                vouch_data = self.env['tt.master.voucher.ppob'].search([('type', '=', vouch_key)])
                similar_disp_names = {}
                for rec in vouch_data:
                    if not voucher_data[vouch_key].get(rec.provider_id.code):
                        voucher_data[vouch_key][rec.provider_id.code] = {}
                    if not similar_disp_names.get(rec.provider_id.code):
                        similar_disp_names[rec.provider_id.code] = {}
                    if vouch_key == 'prepaid_mobile':
                        temp_disp_name = rec.display_name
                    else:
                        temp_disp_name = rec.name
                    if vouch_key in ['pdam', 'pbb']:
                        if similar_disp_names[rec.provider_id.code].get(temp_disp_name.upper()):
                            og_disp_name = temp_disp_name
                            temp_disp_name += ' (Alternative %s)' % (chr(64 + int(similar_disp_names[rec.provider_id.code][temp_disp_name.upper()])))
                            similar_disp_names[rec.provider_id.code][og_disp_name.upper()] += 1
                        else:
                            similar_disp_names[rec.provider_id.code].update({
                                temp_disp_name.upper(): 1
                            })
                    voucher_data[vouch_key][rec.provider_id.code].update({
                        rec.code: temp_disp_name
                    })
            res = {
                'product_data': product_data,
                'search_config_data': multi_prov_prod_data,
                'allowed_denominations': allowed_denominations,
                'voucher_data': voucher_data
            }
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for idy, p_sc in enumerate(provider.cost_service_charge_ids):
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                c_code = ''
                c_type = ''
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
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

            values = []
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    curr_dict = {}
                    curr_dict['pax_type'] = p_type
                    curr_dict['booking_ppob_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict['ho_id'] = self.ho_id.id if self.ho_id else ''
                    curr_dict.update(c_val)
                    values.append((0,0,curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def action_reverse_ppob(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_partial_booked_api_ppob(self,context,pnr_list,hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_ppob(self,co_uid,customer_parent_id):
        self.write({
            'state': 'partial_issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        })

    @api.multi
    def action_set_as_cancel(self):
        for rec in self:
            rec.state = 'cancel'
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def action_issued_ppob(self,data):
        pnr_list = []
        provider_list = []
        carrier_list = []
        for rec in self.provider_booking_ids:
            pnr_list.append(rec.pnr or '')
            provider_list.append(rec.provider_id.code or '')
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
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_ppob')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'ppob',
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

    def action_booked_api_ppob(self,context,pnr_list,hold_date):
        if type(hold_date) != datetime:
            hold_date = False

        write_values = {
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }

        if write_values['pnr'] == '':
            write_values.pop('pnr')

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_ppob')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'ppob',
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

    def action_issued_api_ppob(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_ppob(data)

    def action_resync_api(self, data, context):
        try:
            if data.get('book_id'):
                resv_obj = self.env['tt.reservation.ppob'].sudo().browse(int(data['book_id']))
            else:
                resv_objs = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                resv_obj = resv_objs and resv_objs[0] or False

            if not resv_obj:
                raise RequestException(1003)

            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                if resv_obj.state in ['fail_issued', 'fail_refunded']:
                    rec.write({
                        'state': 'booked',
                        'booked_uid': context['co_uid'],
                        'booked_date': fields.Datetime.now(),
                        'hold_date': datetime.today() + timedelta(hours=1),
                    })
                provider_list.append(rec.to_dict())
            psg_list = []
            for rec in resv_obj.sudo().passenger_ids:
                psg_list.append(rec.to_dict())

            if resv_obj.state in ['fail_issued', 'fail_refunded']:
                resv_obj.write({
                    'state': 'booked',
                    'booked_uid': context['co_uid'],
                    'booked_date': datetime.now(),
                    'hold_date': datetime.today() + timedelta(hours=1)
                })

            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list,
                'passengers': psg_list
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            hold_date = datetime.today() + timedelta(hours=1)
            self.action_booked_api_ppob(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_ppob(issued_req, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_ppob(context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_partial_issued_api_ppob(context['co_uid'], customer_parent_id)
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.calculate_service_charge()
            self.action_partial_booked_api_ppob(context, pnr_list, hold_date)
        elif all(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif all(rec.state == 'fail_paid' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_paid()
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

    def payment_ppob_api(self,req,context):
        payment_res = self.payment_reservation_api('ppob',req,context)
        return payment_res

    def search_inquiry_api(self, data, context):
        try:
            search_req = data['search_RQ']
            search_cust_num = data['data'].get('customer_number') and str(data['data']['customer_number']) or str(search_req['customer_number'])
            search_query = [('carrier_code', '=', str(search_req['product_code'])),
                            ('customer_number', '=', search_cust_num),
                            ('provider_id.code', '=', data['data']['provider']),
                            ('state', '=', 'booked'), ('booking_id.agent_id.id', '=', context['co_agent_id'])]
            search_game_zone_id = ''
            if data['data'].get('game_zone_id'):
                search_game_zone_id = data['data']['game_zone_id']
            elif search_req.get('game_zone_id'):
                search_game_zone_id = search_req['game_zone_id']
            if search_game_zone_id:
                search_query.append(('game_zone_id', '=', str(search_game_zone_id)))
            inq_prov_obj = self.env['tt.provider.ppob'].sudo().search(search_query, limit=1)
            if inq_prov_obj:
                inq_prov_obj = inq_prov_obj[0]

                is_update_sc = False
                if data['data'].get('customer_name'):
                    temp_cust_name = data['data']['customer_name']
                else:
                    temp_cust_name = 'Customer PPOB'
                if (data['data'].get('total') and inq_prov_obj.total_price != data['data']['total']) or inq_prov_obj.customer_name != temp_cust_name:
                    is_update_sc = True

                vals = {
                    'order_number': inq_prov_obj.booking_id.name,
                    'data': data['data'],
                    'is_update_sc': is_update_sc
                }
                response = self.update_inquiry_api(vals, context)
            else:
                vals = {
                    'data': data['data'],
                }
                response = self.create_inquiry_api(vals, context)
            if response.get('error_code'):
                return response
            res = response['response']
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def get_inquiry_api(self, data, context):
        try:
            inq_obj = self.get_book_obj(data.get('book_id'), data.get('order_number'))
            try:
                inq_obj.create_date
            except:
                raise RequestException(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)

            # if inq_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if inq_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_system'):
                provider_code = ''
                provider_list = []
                total_price = 0
                for rec in inq_obj.provider_booking_ids:
                    provider_code = rec.provider_id and rec.provider_id.code or ''
                    total_price += rec.total
                    provider_list.append(rec.to_dict())
                psg_list = []
                for rec in inq_obj.sudo().passenger_ids:
                    psg_list.append(rec.to_dict())

                res = inq_obj.to_dict(context, data)
                res.update({
                    'provider_booking': provider_list,
                    'passengers': psg_list,
                    'state': inq_obj.state,
                    'prepaid_value': inq_obj.prepaid_value and inq_obj.prepaid_value or 0,
                    'total_price': total_price,
                    'provider': provider_code
                })
                return ERR.get_no_error(res)
            else:
                raise RequestException(1035)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def _prepare_booking_api(self, data, context):
        nominal_id_list = []
        for rec in data['nominal']:
            nominal_vals = {
                'nominal': int(rec)
            }
            new_nominal_obj = self.env['tt.master.nominal.ppob'].create(nominal_vals)
            nominal_id_list.append(new_nominal_obj.id)

        provider_type_id = self.env.ref('tt_reservation_ppob.tt_provider_type_ppob')
        provider_obj = self.env['tt.provider'].sudo().search([('code', '=', data['provider']), ('provider_type_id', '=', provider_type_id.id)])
        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', data['product_code'].split('~')[0]), ('provider_type_id', '=', provider_type_id.id)])
        # split product code in case of BTBO 2
        provider_vals = {
            'state': 'booked',
            'pnr': '1',
            'booked_uid': context['co_uid'],
            'booked_date': fields.Datetime.now(),
            'hold_date': fields.Datetime.now() + timedelta(hours=1),
            'balance_due': data['total'],
            'total_price': data['total'],
            'sequence': 1,
            'provider_id': provider_obj and provider_obj.id or False,
            'carrier_id': carrier_obj and carrier_obj.id or False,
            'carrier_code': data['product_code'],
            'carrier_name': carrier_obj and carrier_obj.name or False,
            'customer_number': data.get('customer_number') and data['customer_number'] or '',
            'customer_name': data.get('customer_name') and data['customer_name'] or 'Customer PPOB',
            'customer_id_number': data.get('customer_id_number') and data['customer_id_number'] or '',
            'game_zone_id': data.get('game_zone_id') and data['game_zone_id'] or '',
            'unit_code': data.get('unit_code') and data['unit_code'] or '',
            'unit_name': data.get('unit_name') and data['unit_name'] or '',
            'unit_phone_number': data.get('unit_phone_number') and data['unit_phone_number'] or '',
            'unit_address': data.get('unit_address') and data['unit_address'] or '',
            'fare_type': data.get('fare_type') and data['fare_type'] or '',
            'power': data.get('power') and data['power'] or 0,
            'is_family': data.get('is_family') and data['is_family'] or False,
            'original_pnr': data.get('pnr') and data['pnr'] or '',
            'total': data.get('total') and data['total'] or 0,
            'registration_number': data.get('registration_number') and data['registration_number'] or '',
            'registration_date': data.get('registration_date') and datetime.strptime(data['registration_date'], '%Y-%m-%d') or False,
            'is_send_transaction_code': data.get('is_send_transaction_code') and data['is_send_transaction_code'] or False,
            'transaction_code': data.get('transaction_code') and data['transaction_code'] or '',
            'transaction_name': data.get('transaction_name') and data['transaction_name'] or '',
            'bill_expired_date': data.get('bill_expired_date') and datetime.strptime(data['bill_expired_date'], '%Y-%m-%d') or False,
            'meter_number': data.get('meter_number') and data['meter_number'] or '',
            'distribution_code': data.get('distribution_code') and data['distribution_code'] or '',
            'max_kwh': data.get('max_kwh') and data['max_kwh'] or 0,
            'unpaid_bill': data.get('unpaid_bill') and data['unpaid_bill'] or 0,
            'unpaid_bill_display': data.get('unpaid_bill') and data['unpaid_bill'] - len(data['bill_data']) or 0,
            'allowed_denomination_ids': [(6,0,nominal_id_list)],
            'raw_additional_data': data.get('raw_additional_data') and data['raw_additional_data'] or ''
        }
        prov_obj = self.env['tt.provider.ppob'].create(provider_vals)

        for rec in data['bill_data']:
            meter_history_list = []
            for idx, rec2 in enumerate(rec['meter_histories']):
                meter_history_obj = self.env['tt.ppob.meter.history'].create({
                    'before_meter': rec2.get('before_meter') and int(rec2['before_meter']) or 0,
                    'after_meter': rec2.get('after_meter') and int(rec2['after_meter']) or 0,
                    'sequence': idx + 1
                })
                meter_history_list.append(meter_history_obj.id)
            bill_vals = {
                'provider_booking_id': prov_obj and prov_obj.id or False,
                'period': int(util.get_without_empty(rec, 'period')) and datetime.strptime(rec['period'], '%Y%m') or False,
                'description': rec.get('description') and rec['description'] or '',
                'total': rec.get('total') and rec['total'] or 0,
                'amount_of_month': rec.get('amount_of_month') and rec['amount_of_month'] or 1,
                'fare_amount': rec.get('fare_amount') and rec['fare_amount'] or 0,
                'admin_fee': rec.get('admin_fee') and rec['admin_fee'] or 0,
                'admin_fee_switcher': rec.get('admin_fee_switcher') and rec['admin_fee_switcher'] or 0,
                'period_end_date': rec.get('period_end_date') and datetime.strptime(rec['period_end_date'], '%Y-%m-%d') or False,
                'meter_read_date': rec.get('meter_read_date') and datetime.strptime(rec['meter_read_date'], '%Y-%m-%d') or False,
                'incentive': rec.get('incentive') and rec['incentive'] or 0,
                'ppn_tax_amount': rec.get('ppn_tax_amount') and rec['ppn_tax_amount'] or 0,
                'fine_amount': rec.get('fine_amount') and rec['fine_amount'] or 0,
                'meter_history_ids': [(6,0,meter_history_list)]
            }
            self.env['tt.bill.ppob'].create(bill_vals)

        for rec in data['bill_detail']:
            bill_detail_vals = {
                'provider_booking_id': prov_obj.id,
                'customer_number': rec.get('customer_number', ''),
                'customer_name': rec.get('customer_name', 'Customer PPOB'),
                'unit_code': rec.get('unit_code', ''),
                'unit_name': rec.get('unit_name', ''),
                'total': rec.get('total', 0),
            }
            self.env['tt.bill.detail.ppob'].create(bill_detail_vals)

        booking_tmp = {
            'provider_booking_ids': [(6,0,[prov_obj.id])],
            'provider_type_id': provider_type_id.id,
            'adult': 1,
            'child': 0,
            'infant': 0,
            'ho_id': context['co_ho_id'],
            'agent_id': context['co_agent_id'],
            'user_id': context['co_uid']
        }
        if data.get('prepaid_value'):
            booking_tmp.update({
                'prepaid_value': data['prepaid_value']
            })

        return booking_tmp

    def create_inquiry_api(self, data, context):
        try:
            ho_obj = self.env['tt.agent'].browse(context['co_ho_id'])
            placeholder_email = ho_obj.email and ho_obj.email or 'placeholder@email.com'
            cust_first_name = data['data'].get('customer_name') and data['data']['customer_name'] or 'Customer'
            cust_email = data['data'].get('customer_email') and data['data']['customer_email'] or placeholder_email
            nationality_id = self.env['res.country'].search([('code', '=ilike', 'ID')], limit=1).id
            booker = {
                'first_name': cust_first_name,
                'last_name': "PPOB",
                'title': "MR",
                'nationality_name': "Indonesia",
                'nationality_code': "ID",
                'gender': "male",
                'email': cust_email,
                'calling_code': "62",
                'mobile': "315662000",
                'is_search_allowed': False
            }
            contacts = [{
                'first_name': cust_first_name,
                'last_name': "PPOB",
                'title': "MR",
                'nationality_name': "Indonesia",
                'nationality_code': "ID",
                'is_also_booker': True,
                'gender': "male",
                'email': cust_email,
                'calling_code': "62",
                'mobile': "315662000",
                'contact_id': "CTC_1",
                'sequence': 1
            }]
            psg_dict = {
                'pax_type': "ADT",
                'first_name': cust_first_name,
                'last_name': "PPOB",
                'title': "MR",
                'gender': "male",
                'birth_date': "1990-01-01",
                'sequence': 1,
                'is_also_booker': True,
                'is_also_contact': True,
                'nationality_name': "Indonesia",
                'nationality_code': "ID",
                'passenger_id': "PSG_1",
            }
            passengers = [psg_dict]
            values = self._prepare_booking_api(data['data'], context)
            ppob_cust = self.env['tt.customer'].search([('first_name', '=', psg_dict['first_name']), ('last_name', '=', psg_dict['last_name']), ('agent_id', '=', context['co_agent_id'])], limit=1)
            if ppob_cust:
                cust_dict = {
                    'name': "%s %s" % (psg_dict['first_name'], psg_dict['last_name']),
                    'first_name': psg_dict['first_name'],
                    'last_name': psg_dict['last_name'],
                    'gender': psg_dict['gender'],
                    'title': psg_dict['title'],
                    'birth_date': psg_dict['birth_date'],
                    'nationality_id': nationality_id,
                    'identity_type': '',
                    'identity_number': '',
                    'identity_expdate': False,
                    'identity_country_of_issued_id': False,
                    'sequence': psg_dict['sequence']
                }

                if cust_email != placeholder_email and ppob_cust[0].email != cust_email:
                    ppob_cust[0].sudo().write({
                        'email': cust_email
                    })

                booker_obj = ppob_cust[0]
                contact_obj = ppob_cust[0]
                list_passenger_value = [(0,0,cust_dict)]
                list_customer_id = [ppob_cust[0]]
            else:
                booker_obj = self.create_booker_api(booker, context)
                contact_obj = self.create_contact_api(contacts[0], booker_obj, context)

                list_passenger_value = self.create_passenger_value_api(passengers)
                list_customer_id = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)

            # fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx, rec in enumerate(list_passenger_value):
                rec[2].update({
                    'customer_id': list_customer_id[idx].id
                })

            for psg in list_passenger_value:
                util.pop_empty_key(psg[2])

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_title': contacts[0]['title'],
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': "%s - %s" % (contact_obj.phone_ids[0].calling_code, contact_obj.phone_ids[0].calling_number),
                'passenger_ids': list_passenger_value,
                'customer_parent_id': context.get('co_customer_parent_id', False),
            })

            resv_obj = self.create(values)

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            for svc in data['data']['service_charges']:
                if not currency:
                    currency = svc['currency']
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                if currency_obj:
                    resv_obj.currency_id = currency_obj.id
            pnr_list = []
            total_price = 0
            for prov_obj in resv_obj.provider_booking_ids:
                prov_obj.create_ticket_api(passengers)
                prov_obj.create_service_charge(data['data']['service_charges'])
                total_price += prov_obj.total
                pnr_list.append(prov_obj.pnr)
            resv_obj.check_provider_state(context, pnr_list)
            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                provider_list.append(rec.to_dict())
            psg_list = []
            for rec in resv_obj.sudo().passenger_ids:
                psg_list.append(rec.to_dict())
            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list,
                'passengers': psg_list,
                'total_price': total_price
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004)

    def update_inquiry_api(self, data, context):
        try:
            resv_obj = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
            if not resv_obj:
                raise RequestException(1003)

            resv_obj = resv_obj[0]
            if resv_obj.state == 'booked' and data.get('is_update_sc'):
                for rec in resv_obj.provider_booking_ids:
                    ledger_created = rec.delete_service_charge()
                    if ledger_created:
                        rec.action_reverse_ledger()
                        rec.delete_service_charge()
                    rec.sudo().unlink()
                for rec in resv_obj.passenger_ids:
                    rec.update({
                        'cost_service_charge_ids': [(6, 0, [])]
                    })
                    rec.sudo().unlink()

                ho_obj = self.env['tt.agent'].browse(context['co_ho_id'])
                placeholder_email = ho_obj.email and ho_obj.email or 'placeholder@email.com'
                cust_first_name = data['data'].get('customer_name') and data['data']['customer_name'] or 'Customer'
                cust_email = data['data'].get('customer_email') and data['data']['customer_email'] or placeholder_email
                nationality_id = self.env['res.country'].search([('code', '=ilike', 'ID')], limit=1).id
                booker = {
                    'first_name': cust_first_name,
                    'last_name': "PPOB",
                    'title': "MR",
                    'nationality_name': "Indonesia",
                    'nationality_code': "ID",
                    'gender': "male",
                    'email': cust_email,
                    'calling_code': "62",
                    'mobile': "315662000",
                    'is_search_allowed': False
                }
                contacts = [{
                    'first_name': cust_first_name,
                    'last_name': "PPOB",
                    'title': "MR",
                    'nationality_name': "Indonesia",
                    'nationality_code': "ID",
                    'is_also_booker': True,
                    'gender': "male",
                    'email': cust_email,
                    'calling_code': "62",
                    'mobile': "315662000",
                    'contact_id': "CTC_1",
                    'sequence': 1
                }]
                psg_dict = {
                    'pax_type': "ADT",
                    'first_name': cust_first_name,
                    'last_name': "PPOB",
                    'title': "MR",
                    'gender': "male",
                    'birth_date': "1990-01-01",
                    'sequence': 1,
                    'is_also_booker': True,
                    'is_also_contact': True,
                    'nationality_name': "Indonesia",
                    'nationality_code': "ID",
                    'passenger_id': "PSG_1",
                }
                passengers = [psg_dict]

                values = self._prepare_booking_api(data['data'], context)
                ppob_cust = self.env['tt.customer'].search([('first_name', '=', psg_dict['first_name']), ('last_name', '=', psg_dict['last_name']), ('agent_id', '=', context['co_agent_id'])], limit=1)
                if ppob_cust:
                    cust_dict = {
                        'name': "%s %s" % (psg_dict['first_name'], psg_dict['last_name']),
                        'first_name': psg_dict['first_name'],
                        'last_name': psg_dict['last_name'],
                        'gender': psg_dict['gender'],
                        'title': psg_dict['title'],
                        'birth_date': psg_dict['birth_date'],
                        'nationality_id': nationality_id,
                        'identity_type': '',
                        'identity_number': '',
                        'identity_expdate': False,
                        'identity_country_of_issued_id': False,
                        'sequence': psg_dict['sequence']
                    }

                    if cust_email != placeholder_email and ppob_cust[0].email != cust_email:
                        ppob_cust[0].sudo().write({
                            'email': cust_email
                        })

                    booker_obj = ppob_cust[0]
                    contact_obj = ppob_cust[0]
                    list_passenger_value = [(0, 0, cust_dict)]
                    list_customer_id = [ppob_cust[0]]
                else:
                    booker_obj = self.create_booker_api(booker, context)
                    contact_obj = self.create_contact_api(contacts[0], booker_obj, context)

                    list_passenger_value = self.create_passenger_value_api(passengers)
                    list_customer_id = self.create_customer_api(passengers, context, booker_obj.seq_id, contact_obj.seq_id)

                # fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
                for idx, rec in enumerate(list_passenger_value):
                    rec[2].update({
                        'customer_id': list_customer_id[idx].id
                    })

                for psg in list_passenger_value:
                    util.pop_empty_key(psg[2])

                values.update({
                    'booker_id': booker_obj.id,
                    'contact_title': contacts[0]['title'],
                    'contact_id': contact_obj.id,
                    'contact_name': contact_obj.name,
                    'contact_email': contact_obj.email,
                    'contact_phone': "%s - %s" % (contact_obj.phone_ids[0].calling_code, contact_obj.phone_ids[0].calling_number),
                    'passenger_ids': list_passenger_value,
                })
                resv_obj.write(values)

                ## 22 JUN 2023 - IVAN
                ## GET CURRENCY CODE
                currency = ''
                for svc in data['data']['service_charges']:
                    if not currency:
                        currency = svc['currency']
                if currency:
                    currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                    if currency_obj:
                        resv_obj.currency_id = currency_obj.id
                provider_list = []
                pnr_list = []
                total_price = 0
                for rec in resv_obj.provider_booking_ids:
                    rec.create_ticket_api(passengers)
                    rec.create_service_charge(data['data']['service_charges'])
                    total_price += rec.total
                    pnr_list.append(rec.pnr)
                    provider_list.append(rec.to_dict())
                resv_obj.check_provider_state(context, pnr_list)
                psg_list = []
                for rec in resv_obj.sudo().passenger_ids:
                    psg_list.append(rec.to_dict())
            else:
                provider_list = []
                total_price = 0
                for rec in resv_obj.provider_booking_ids:
                    total_price += rec.total
                    provider_list.append(rec.to_dict())
                psg_list = []
                for rec in resv_obj.sudo().passenger_ids:
                    psg_list.append(rec.to_dict())

            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list,
                'passengers': psg_list,
                'total_price': total_price
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)

    def get_provider_api(self, data, context):
        try:
            if data.get('book_id'):
                resv_obj = self.env['tt.reservation.ppob'].sudo().browse(int(data['book_id']))
            else:
                resv_objs = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                resv_obj = resv_objs and resv_objs[0] or False

            if not resv_obj:
                raise RequestException(1003)

            provider_code = ''
            carrier_code = ''
            for rec in resv_obj.provider_booking_ids:
                provider_code = rec.provider_id and rec.provider_id.code or ''
                carrier_code = rec.carrier_id and str(rec.carrier_id.code) or ''

            res = {
                'provider': provider_code,
                'carrier': carrier_code
            }
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_pay_amount_api(self, data, context):
        try:
            if data.get('book_id'):
                resv_obj = self.env['tt.reservation.ppob'].sudo().browse(int(data['book_id']))
            else:
                resv_objs = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                resv_obj = resv_objs and resv_objs[0] or False

            if not resv_obj:
                raise RequestException(1003)

            new_total = data.get('total', 0)
            provider_list = []
            total_price = 0
            for rec in resv_obj.provider_booking_ids:
                temp_carrier_code = rec.carrier_id and rec.carrier_id.code or ''
                if int(temp_carrier_code) == 'pln_prepaid':
                    rec.write({
                        'total': new_total
                    })
                    for rec2 in rec.ppob_bill_ids:
                        rec2.write({
                            'total': new_total
                        })
                    if data.get('service_charges'):
                        temp_first_name = ''
                        temp_last_name = ''
                        for temp_psg in resv_obj.passenger_ids:
                            temp_first_name = temp_psg.first_name and temp_psg.first_name or ''
                            temp_last_name = temp_psg.last_name and temp_psg.last_name or ''
                        psg_dict = {
                            'pax_type': "ADT",
                            'first_name': temp_first_name,
                            'last_name': temp_last_name,
                            'title': "MR",
                            'gender': "male",
                            'birth_date': "1990-01-01",
                            'sequence': 1,
                            'is_also_booker': True,
                            'is_also_contact': True,
                            'nationality_name': "Indonesia",
                            'nationality_code': "ID",
                            'passenger_id': "PSG_1",
                        }
                        passengers = [psg_dict]
                        rec.prepaid_update_service_charge(passengers, data['service_charges'])
                total_price += rec.total
                provider_list.append(rec.to_dict())
            psg_list = []
            for rec in resv_obj.sudo().passenger_ids:
                psg_list.append(rec.to_dict())
            resv_obj.calculate_service_charge()
            resv_obj.write({
                'prepaid_value': new_total
            })
            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list,
                'passengers': psg_list,
                'total_price': total_price
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1006)

    def issued_payment_api(self, data, context):
        try:
            if data.get('book_id'):
                resv_obj = self.env['tt.reservation.ppob'].sudo().browse(int(data['book_id']))
            else:
                resv_objs = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                resv_obj = resv_objs and resv_objs[0] or False

            if not resv_obj:
                raise RequestException(1003)

            provider_code = ''
            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                if data.get('session_id'):
                    rec.write({
                        'session_id': data['session_id']
                    })
                provider_code = rec.provider_id and rec.provider_id.code or ''
                temp_carrier_code = rec.carrier_id and rec.carrier_id.code or ''
                bill_list = []
                for rec2 in rec.ppob_bill_ids:
                    bill_list.append({
                        'period': rec2.period and rec2.period.strftime('%Y%m') or '',
                        'total': rec2.total and rec2.total or 0
                    })

                provider_list.append({
                    'carrier_code': temp_carrier_code,
                    'session_id': rec.session_id and rec.session_id or '',
                    'customer_number': rec.customer_number,
                    'bill_data': bill_list,
                    'is_send_transaction_code': rec.is_send_transaction_code and rec.is_send_transaction_code or False,
                    'transaction_code': rec.transaction_code and rec.transaction_code or '',
                    'raw_additional_data': rec.raw_additional_data and rec.raw_additional_data or ''
                })

            total_admin = 0
            total_payment = 0
            for serv in resv_obj.sale_service_charge_ids:
                if serv.charge_type == 'ROC':
                    total_admin += serv.amount
                elif serv.charge_type == 'FARE':
                    total_payment += serv.amount

            res = {
                'order_number': resv_obj.name,
                'total_admin': total_admin,
                'total_payment': total_payment,
                'provider_booking': provider_list,
                'provider': provider_code
            }
            if resv_obj.prepaid_value:
                res.update({
                    'prepaid_value': resv_obj.prepaid_value
                })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1006)

    def update_inquiry_status_api(self, data, context):
        try:
            resv_obj = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
            if resv_obj:
                resv_obj = resv_obj[0]
            else:
                raise RequestException(1003)

            provider_list = []
            pnr_list = []
            for rec in resv_obj.provider_booking_ids:
                rec.update_status_api_ppob(data, context)
                pnr_list.append(rec.pnr)
                provider_list.append(rec.to_dict())
            resv_obj.check_provider_state(context, pnr_list)
            psg_list = []
            for rec in resv_obj.sudo().passenger_ids:
                psg_list.append(rec.to_dict())

            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list,
                'passengers': psg_list
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)

    def update_pnr_provider_ppob_api(self, req, context):
        _logger.info("Update\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.ppob'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.ppob'].search([('name', '=', req['order_number'])])
            else:
                raise Exception('Booking ID or Number not Found')
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            any_provider_changed = False

            for provider in req['provider_booking']:
                provider_obj = self.env['tt.provider.ppob'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)

                if provider['status'] == 'CANCEL':
                    provider_obj.action_cancel_api_ppob(context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID_FAILED':
                    provider_obj.action_failed_void_api_ppob(provider.get('error_code', -1), provider.get('error_msg', ''))
                    any_provider_changed = True

            if any_provider_changed:
                book_obj.check_provider_state(context, req=req)

            return ERR.get_no_error({
                'order_number': book_obj.name,
                'book_id': book_obj.id
            })
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
            return ERR.get_error(1005)

    def get_filename(self):
        provider = self.provider_booking_ids[0]
        if provider.carrier_id:
            return util.slugify_str(provider.carrier_id.name)
        return 'PPOB Bills'

    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.ppob'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        ppob_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_ppob')
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            filename = book_obj.get_filename()

            pdf_report = ppob_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = ppob_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': '%s Itinerary %s.pdf' % (filename, book_obj.name),
                    'file_reference': '%s Itinerary' % filename,
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
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

    def print_itinerary_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.ppob'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        ppob_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_ppob')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            filename = book_obj.get_filename()

            pdf_report = ppob_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = ppob_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': '%s Itinerary %s (Price).pdf' % (filename, book_obj.name),
                    'file_reference': '%s Itinerary' % filename,
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
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

    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.ppob'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        ppob_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_ppob')

        if not book_obj.printout_ticket_id or book_obj.is_ticket_printed < 2:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            filename = book_obj.get_filename()

            pdf_report = ppob_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = ppob_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': '%s %s.pdf' % (filename, book_obj.name),
                    'file_reference': filename,
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
        if book_obj.is_ticket_printed < 2:
            book_obj.is_ticket_printed += 1
        return url

    # DEPRECATED
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        ppob_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_ppob')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            filename = self.get_filename()

            pdf_report = ppob_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = ppob_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': '%s HO Invoice %s.pdf' % (filename, self.name),
                    'file_reference': '%s HO Invoice' % filename,
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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_ppob_ids.ids):
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
