from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta
import base64

import json

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
    provider_booking_ids = fields.One2many('tt.provider.ppob', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'draft': [('readonly', False)]})
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_ppob.tt_provider_type_ppob'))

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
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    curr_dict = {}
                    curr_dict['pax_type'] = p_type
                    curr_dict['booking_ppob_id'] = self.id
                    curr_dict['description'] = provider.pnr
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

    def action_issued_ppob(self,co_uid,customer_parent_id,acquirer_id = False):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        })

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

    def action_issued_api_ppob(self,acquirer_id,customer_parent_id,context):
        self.action_issued_ppob(context['co_uid'],customer_parent_id,acquirer_id)

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            self.action_booked_api_ppob(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_issued_api_ppob(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
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
        elif all(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_set_as_cancel()
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def payment_ppob_api(self,req,context):
        payment_res = self.payment_reservation_api('ppob',req,context)
        return payment_res

    def get_inquiry_api(self, data, context):
        try:
            if data.get('order_number'):
                inq_obj = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                if inq_obj:
                    inq_prov_obj = []
                    for prov in inq_obj.provider_booking_ids:
                        inq_prov_obj.append(prov)
                else:
                    raise RequestException(1003)
            else:
                inq_prov_obj = self.env['tt.provider.ppob'].sudo().search([('product_code', '=', data['product_code']), ('customer_number', '=', data['customer_number']), ('state', 'in', ['booked', 'issued'])], limit=1)
            if inq_prov_obj:
                inq_prov_obj = inq_prov_obj[0]
                res = inq_prov_obj.booking_id.to_dict()
                res.update({
                    'provider_booking': [inq_prov_obj.to_dict()]
                })
            else:
                res = {
                    'order_number': False
                }
            return ERR.get_no_error(res)
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
        provider_vals = {
            'state': 'booked',
            'booked_uid': context['co_uid'],
            'booked_date': fields.Datetime.now(),
            'hold_date': fields.Datetime.now() + timedelta(days=1),
            'balance_due': data['total_amount'],
            'sequence': 1,
            'session_id': data.get('session_id') and data['session_id'] or '',
            'customer_number': data.get('customer_number') and data['customer_number'] or '',
            'customer_name': data.get('customer_name') and data['customer_name'] or '',
            'customer_id_number': data.get('customer_id_number') and data['customer_id_number'] or '',
            'unit_code': data.get('unit_code') and data['unit_code'] or '',
            'unit_name': data.get('unit_name') and data['unit_name'] or '',
            'unit_phone_number': data.get('unit_phone_number') and data['unit_phone_number'] or '',
            'unit_address': data.get('unit_address') and data['unit_address'] or '',
            'fare_type': data.get('fare_type') and data['fare_type'] or '',
            'power': data.get('power') and data['power'] or 0,
            'is_family': data.get('is_family') and data['is_family'] or False,
            'pnr': data.get('pnr') and data['pnr'] or '',
            'total': data.get('total') and data['total'] or 0,
            'registration_number': data.get('registration_number') and data['registration_number'] or '',
            'registration_date': data.get('registration_date') and datetime.strptime(data['registration_date'], '%Y%m%d') or False,
            'transaction_code': data.get('transaction_code') and data['transaction_code'] or '',
            'transaction_name': data.get('transaction_name') and data['transaction_name'] or '',
            'bill_expired_date': data.get('bill_expired_date') and datetime.strptime(data['bill_expired_date'], '%Y%m%d') or False,
            'meter_number': data.get('meter_number') and data['meter_number'] or '',
            'distribution_code': data.get('distribution_code') and data['distribution_code'] or '',
            'max_kwh': data.get('max_kwh') and data['max_kwh'] or 0,
            'unpaid_bill': data.get('unpaid_bill') and data['unpaid_bill'] or 0,
            'allowed_denomination_ids': [(6,0,nominal_id_list)],
        }
        prov_obj = self.env['tt.provider.ppob'].create(provider_vals)

        product_code = data['product_code']
        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', product_code), ('provider_type_id', '=', provider_type_id.id)])
        for rec in data['bill_data']:
            meter_history_list = []
            for rec2 in rec['meter_histories']:
                meter_history_list.append({
                    'before_meter': rec2.get('before_meter') and int(rec2['before_meter']) or 0,
                    'after_meter': rec2.get('after_meter') and int(rec2['after_meter']) or 0,
                })
            bill_vals = {
                'provider_booking_id': prov_obj and prov_obj.id or False,
                'carrier_id': carrier_obj and carrier_obj.id or False,
                'carrier_code': carrier_obj and carrier_obj.code or False,
                'carrier_name': carrier_obj and carrier_obj.name or False,
                'period': rec.get('period') and datetime.strptime(rec['period'], '%Y%m') or False,
                'total': rec.get('total') and rec['total'] or 0,
                'amount_of_month': rec.get('amount_of_month') and rec['amount_of_month'] or 0,
                'fare_amount': rec.get('fare_amount') and rec['fare_amount'] or 0,
                'admin_fee': rec.get('admin_fee') and rec['admin_fee'] or 0,
                'period_end_date': rec.get('period_end_date') and datetime.strptime(rec['period_end_date'], '%d%m%Y') or False,
                'meter_read_date': rec.get('meter_read_date') and datetime.strptime(rec['meter_read_date'], '%d%m%Y') or False,
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
                'customer_name': rec.get('customer_name', ''),
                'unit_code': rec.get('unit_code', ''),
                'unit_name': rec.get('unit_name', ''),
                'total': rec.get('total_amount', 0),
            }
            self.env['tt.bill.detail.ppob'].create(bill_detail_vals)
        prov_obj.create_service_charge(data['service_charges'])
        booking_tmp = {
            'provider_booking_ids': [(6,0,[prov_obj.id])],
            'provider_type_id': provider_type_id.id,
            'adult': 1,
            'child': 0,
            'infant': 0,
            'agent_id': context['co_agent_id'],
            'user_id': context['co_uid'],
        }

        return booking_tmp

    def create_inquiry_api(self, data, context):
        try:
            booker = {
                'first_name': "PPOB",
                'last_name': "Customer",
                'title': "MR",
                'nationality_name': "Indonesia",
                'nationality_code': "ID",
                'gender': "male",
                'email': "booking@rodextravel.tours",
                'calling_code': "62",
                'mobile': "315662000",
            }
            contacts = [{
                'first_name': "PPOB",
                'last_name': "Customer",
                'title': "MR",
                'nationality_name': "Indonesia",
                'nationality_code': "ID",
                'is_also_booker': True,
                'gender': "male",
                'email': "booking@rodextravel.tours",
                'calling_code': "62",
                'mobile': "315662000",
                'contact_id': "CTC_1",
                'sequence': 1
            }]
            nationality_id = self.env['res.country'].search([('code', '=ilike', 'ID')], limit=1).id
            psg_dict = {
                'pax_type': "ADT",
                'first_name': "PPOB",
                'last_name': "Customer",
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
            ppob_cust = self.env['tt.customer'].search([('first_name', '=', 'PPOB'), ('last_name', '=', 'Customer'), ('agent_id', '=', context['co_agent_id'])], limit=1)
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

                booker_obj = ppob_cust[0]
                contact_obj = ppob_cust[0]
                list_passenger_value = [(0,0,cust_dict)]
                list_customer_id = [ppob_cust[0]]
            else:
                booker_obj = self.create_booker_api(booker, context)
                contact_obj = self.create_contact_api(contacts[0], booker_obj, context)

                list_passenger_value = self.create_passenger_value_api_test(passengers)
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
            })

            resv_obj = self.env['tt.reservation.ppob'].create(values)
            resv_obj.check_provider_state(context)
            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                provider_list.append(rec.to_dict())
            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list
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
            if resv_obj.state != 'issued':
                for rec in resv_obj.provider_booking_ids:
                    rec.sudo().unlink()
                values = self._prepare_booking_api(data['data'], context)
                resv_obj.write(values)
                resv_obj.check_provider_state(context)

            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                provider_list.append(rec.to_dict())
            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)

    def issued_payment_api(self, data, context):
        try:
            if data.get('order_id'):
                resv_obj = self.env['tt.reservation.ppob'].sudo().browse(int(data['order_id']))
            else:
                resv_objs = self.env['tt.reservation.ppob'].sudo().search([('name', '=', data['order_number'])], limit=1)
                resv_obj = resv_objs and resv_objs[0] or False

            if not resv_obj:
                raise RequestException(1003)

            provider_list = []
            for rec in resv_obj.provider_booking_ids:
                bill_list = []
                for rec2 in rec.ppob_bill_ids:
                    temp_carrier_code = rec2.carrier_id and rec2.carrier_id.code or ''
                    if int(temp_carrier_code) == 522:
                        temp_total = data.get('total', 0)
                    else:
                        temp_total = rec2.total and rec2.total or 0
                    bill_list.append({
                        'carrier_code': temp_carrier_code,
                        'period': rec2.period and rec2.period.strftime('%Y%m') or '',
                        'total': temp_total
                    })

                provider_list.append({
                    'session_id': rec.session_id,
                    'customer_number': rec.customer_number,
                    'bill_data': bill_list,
                })

            res = {
                'order_number': resv_obj.name,
                'total_commission': resv_obj.total_commission,
                'provider_bookings': provider_list
            }
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
            for rec in resv_obj.provider_booking_ids:
                rec.update_status_api_ppob(data, context)
                provider_list.append(rec.to_dict())
            resv_obj.check_provider_state(context)

            res = resv_obj.to_dict()
            res.update({
                'provider_booking': provider_list
            })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)
