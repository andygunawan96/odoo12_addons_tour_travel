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
            no_check_state = ['issued', 'cancel', 'cancel2', 'cancel_pending', 'fail_cancel', 'fail_booked', 'fail_issued']
            inq_prov_obj = self.env['tt.provider.ppob'].sudo().search([('product_code', '=', data['product_code']), ('customer_number', '=', data['customer_number']), ('state', 'not in', no_check_state)], limit=1)
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

    def create_inquiry_api(self, data, context):
        try:
            res = {

            }
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1004)

    def update_inquiry_api(self, data, context):
        try:
            res = {

            }
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

    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.ppob'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        ppob_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_ppob')

        if not book_obj.printout_ticket_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = ppob_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = ppob_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'PPOB Bills %s.pdf' % book_obj.name,
                    'file_reference': 'PPOB Bills',
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
            'name': "ZZZ",
            'target': 'new',
            'url': book_obj.printout_ticket_id.url,
        }
        return url
