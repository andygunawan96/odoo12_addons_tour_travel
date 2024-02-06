from odoo import api,models,fields, _
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta
import base64
import json
import copy
import pytz

_logger = logging.getLogger(__name__)


class ReservationInsurance(models.Model):

    _name = "tt.reservation.insurance"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation Insurance"

    origin = fields.Char('Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination = fields.Char('Destination', readonly=True, states={'draft': [('readonly', False)]})
    sector_type = fields.Char('Sector', readonly=True, compute='', store=True)
    start_date = fields.Char('Start Date', readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Char('End Date', readonly=True, states={'draft': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_insurance_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.insurance', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    provider_booking_ids = fields.One2many('tt.provider.insurance', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})
    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default= lambda self: self.env.ref('tt_reservation_insurance.tt_provider_type_insurance'))

    is_get_booking_from_vendor = fields.Boolean('Get Booking From Vendor')
    printout_ticket_original_ids = fields.Many2many('tt.upload.center', 'reservation_insurance_attachment_rel', 'ori_ticket_id',
                                       'attachment_id', string='Attachments')

    def compute_journey_code(self):
        objs = self.env['tt.reservation.insurance'].sudo().search([])
        for rec in objs:
            for journey in rec.journey_ids:
                journey._compute_journey_code()

    def get_form_id(self):
        return self.env.ref("tt_reservation_insurance.tt_reservation_insurance_form_views")

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

    @api.multi
    def action_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 154')
        for rec in self:
            rec.state = 'draft'


    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 155')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 156')
        for rec in self:
            rec.state = 'issued'

    def action_booked_api_insurance(self,context,pnr_list=[],hold_date=False):
        if type(hold_date) != datetime:
            hold_date = False

        write_values = {
            'state': 'booked',
            # 'pnr': ', '.join(pnr_list),
            # 'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }
        # May 11, 20202 - SAM
        # Bisa di comment, karena fungsi mengisi hold dan pnr telah dipisahkan
        if hold_date:
            write_values['hold_date'] = hold_date and hold_date.strftime('%Y-%m-%d %H:%M:%S') or False
        if pnr_list:
            write_values['pnr'] = ', '.join(pnr_list)
        # END

        # if write_values['pnr'] == '':
        #     write_values.pop('pnr')

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_insurance')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'insurance',
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

    def action_issued_api_insurance(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_insurance(data)

    def action_reverse_insurance(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_refund_failed_insurance(self,context):
        self.write({
            'state':  'refund_failed',
        })

    def action_issued_insurance(self,data):
        values = {
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': data.get('co_uid', self.env.user.id),
            'customer_parent_id': data['customer_parent_id']
        }
        if not self.booked_date:
            values.update({
                'booked_date': values['issued_date'],
                'booked_uid': values['issued_uid'],
            })
        self.write(values)

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_insurance')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'insurance',
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

    def action_partial_booked_api_insurance(self,context,pnr_list=[],hold_date=False):
        if type(hold_date) != datetime:
            hold_date = False

        values = {
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            # 'hold_date': hold_date,
            # 'pnr': ','.join(pnr_list)
        }

        # May 11, 2020 - SAM
        # Bisa di comment karena fungsi mengisi pnr list dan hold date dipindahkan ke fungsi lain
        if pnr_list:
            values['pnr'] = ', '.join(pnr_list)
        if hold_date:
            values['hold_date'] = hold_date
        # END

        self.write(values)

    def action_partial_issued_api_insurance(self,co_uid,customer_parent_id):
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

    @api.multi
    def action_set_as_refund_pending(self):
        for rec in self:
            rec.state = 'refund_pending'

    @api.multi
    def action_set_as_cancel_pending(self):
        for rec in self:
            rec.state = 'cancel_pending'

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 157')
        super(ReservationInsurance, self).action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    def action_issued_from_button(self):
        api_context = {
            'co_uid': self.env.user.id
        }
        if api_context['co_uid'] == 1:#odoo bot
            api_context['co_uid'] = 2 #administrator
        self.validate_issue(api_context=api_context)
        res = self.action_issued_api(self.name, api_context)
        if res['error_code']:
            raise UserWarning(res['error_msg'])

    def create_booking_insurance_api(self, req, context):
        _logger.info("Create\n" + json.dumps(req))
        book_data = req['data']
        booker = req['booker']
        contacts = req['contacts']
        passengers_data = copy.deepcopy(req['passengers'])  # waktu create passenger fungsi odoo field kosong di hapus cth: work_place
        passengers = req['passengers']
        is_force_issued = req.get('force_issued', False)
        # END

        try:
            values = self._prepare_booking_api(book_data, context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            list_passenger_value = self.create_passenger_value_api(passengers)
            for pax in passengers:
                ## CREATE PAX AGAR BISA TEROPONG UNTUK NEXT BOOKING, BELUM COBA LINK TAKUT ADA BUG
                ## TODO LINK PAX TANPA PRICE
                if pax.get('data_insurance'):
                    if pax['data_insurance'].get('relation'):
                        try:
                            self.create_customer_api(pax['data_insurance']['relation'], context, booker_obj.seq_id, contact_obj.seq_id)
                        except Exception as e:
                            _logger.error("%s, %s" % (str(e), traceback.format_exc()))
                    if pax['data_insurance'].get('beneficiary'):
                        try:
                            self.create_customer_api([pax['data_insurance']['beneficiary']], context, booker_obj.seq_id,contact_obj.seq_id)
                        except Exception as e:
                            _logger.error("%s, %s" % (str(e), traceback.format_exc()))

            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
                rec[2].update({
                    'customer_id': list_customer_id[idx].id,
                    'email': passengers_data[idx]['email'],
                    'phone_number': passengers_data[idx]['phone_number'],
                    'insurance_data': passengers_data[idx].get('data_insurance') and json.dumps(passengers_data[idx]['data_insurance']) or ''
                })
                if passengers_data[idx].get('description'):
                    rec[2].update({
                        'description': passengers_data[idx]['description']
                    })

            for psg in list_passenger_value:
                util.pop_empty_key(psg[2])

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            currency_obj = None
            for svc_summary in book_data['service_charge_summary']:
                for svc in svc_summary['service_charges']:
                    currency = svc['currency']
                    break
                break

            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                # if currency_obj:
                    # book_obj.currency_id = currency_obj.id

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_title': contacts[0]['title'],
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids and "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number) or '-',
                'passenger_ids': list_passenger_value,
                'is_force_issued': is_force_issued,
                'currency_id': currency_obj.id if currency and currency_obj else self.env.user.company_id.currency_id.id
                # END
            })

            book_obj = self.create(values)
            provider_ids, name_ids = book_obj._create_provider_api(book_data, context)
            hold_date = False
            for provider_obj in provider_ids:
                provider_obj.create_ticket_api(passengers)
                service_charges_val = []
                for svc_summary in book_data['service_charge_summary']:
                    for svc in svc_summary['service_charges']:
                        ## currency di skip default ke company
                        service_charges_val.append({
                            "pax_type": svc['pax_type'],
                            "pax_count": svc['pax_count'],
                            "currency": svc['currency'],
                            "amount": svc['amount'],
                            "total_amount": svc['total'],
                            "foreign_currency": svc['foreign_currency'],
                            "foreign_amount": svc['amount'],
                            "charge_code": svc['charge_code'],
                            "charge_type": svc['charge_type'],
                            "commission_agent_id": svc.get('commission_agent_id', False)
                        })

                provider_obj.create_service_charge(service_charges_val)

            book_obj.calculate_service_charge()
            book_obj.check_provider_state(context)

            response_provider_ids = []
            for provider in provider_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })

            book_obj.write({
                'provider_name': ','.join(name_ids['provider']),
                'carrier_name': ','.join(name_ids['carrier']),
            })

            # channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)
                book_obj.create_svc_upsell()

            ## PAKAI VOUCHER
            if req.get('voucher'):
                book_obj.add_voucher(req['voucher']['voucher_reference'], context)

            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_ids': response_provider_ids
            }
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

    def update_pnr_provider_insurance_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        _logger.info("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.insurance'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.insurance'].search([('name', '=', req['order_number'])])
            else:
                raise Exception('Booking ID or Number not Found')
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            # book_status = []
            # pnr_list = []
            # hold_date = datetime.max.replace(year=2020)
            any_provider_changed = False
            any_pnr_changed = False

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.insurance'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                # book_status.append(provider['status'])

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    # self.update_pnr_booked(provider_obj,provider,context)
                    provider_obj.action_booked_api_insurance(provider, context)
                    provider_obj.update_ticket_api(provider['tickets'])
                    provider_obj.update({
                        "hold_date": provider['hold_date']
                    })
                    provider_obj.update_pnr(provider['pnr'])
                    any_provider_changed = True
                elif provider['status'] == 'ISSUED' and not provider.get('error_code'):
                    if 'tickets' in provider:
                        provider_obj.update_ticket_api(provider['tickets'])
                    provider_obj.update_pnr(provider['pnr'])
                    if provider_obj.state == 'issued':
                        continue
                    provider_obj.action_issued_api_insurance(provider, context)
                    any_provider_changed = True
                elif provider['status'] == 'FAIL_BOOKED':
                    provider_obj.action_failed_booked_api_insurance(provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_insurance(provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'CANCELLED':
                    provider_obj.action_cancel_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'REFUND_PENDING':
                    provider_obj.action_refund_pending_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'CANCEL_PENDING':
                    provider_obj.action_cancel_pending_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID':
                    provider_obj.action_void_api_insurance(provider, context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID_PENDING':
                    provider_obj.action_void_pending_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'REFUND':
                    provider_obj.action_refund_api_insurance(provider, context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID_FAILED':
                    provider_obj.action_failed_void_api_insurance(provider.get('error_code', -1), provider_obj['error_msg'])
                    any_provider_changed = True
                elif provider['status'] == 'REFUND_FAILED':
                    provider_obj.action_refund_failed_api_insurance(provider.get('error_code', -1), provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED':
                    provider_obj.action_rescheduled_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED_PENDING':
                    provider_obj.action_rescheduled_pending_api_insurance(context)
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED_FAILED':
                    provider_obj.action_failed_rescheduled_api_insurance(provider.get('error_code', -1), provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'REISSUE':
                    provider_obj.action_reissue_api_insurance(context)
                    any_provider_changed = True

            # for rec in book_obj.provider_booking_ids:
            #     if rec.pnr:
            #         pnr_list.append(rec.pnr)

            if any_provider_changed:
                book_obj.calculate_service_charge()
                book_obj.check_provider_state(context, req=req)

            # if any_pnr_changed:
            #     book_obj.write({'pnr': ','.join(pnr_list)})

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

    def to_dict_reschedule(self):
        return []

    def get_booking_insurance_api(self,req, context):
        try:
            # _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
                res = book_obj.to_dict(context, req)
                psg_list = []
                for rec_idx, rec in enumerate(book_obj.sudo().passenger_ids):
                    rec_data = rec.to_dict()
                    rec_data.update({
                        'passenger_number': rec.sequence
                    })
                    psg_list.append(rec_data)
                prov_list = []
                for rec in book_obj.provider_booking_ids:
                    prov_list.append(rec.to_dict())

                res.update({
                    'origin': book_obj.origin,
                    'destination': book_obj.destination,
                    'sector_type': book_obj.sector_type,
                    'start_date': book_obj.start_date,
                    'end_date': book_obj.end_date,
                    'passengers': psg_list,
                    'provider_bookings': prov_list,
                })
                return Response().get_no_error(res)
            else:
                raise RequestException(1035)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def payment_insurance_api(self,req,context):
        payment_res = self.payment_reservation_api('insurance',req,context)
        return payment_res

    def _prepare_booking_api(self, book_data, context_gateway):
        provider_type_id = self.env.ref('tt_reservation_insurance.tt_provider_type_insurance')

        booking_tmp = {
            'start_date': book_data['date_start'],
            'end_date': book_data['date_end'],
            'origin': book_data['origin'],
            'destination': book_data['destination'],
            'sector_type': book_data.get('international') and 'international' or 'domestic',
            'provider_type_id': provider_type_id.id,
            'adult': book_data['pax_count'],
            'ho_id': context_gateway['co_ho_id'],
            'agent_id': context_gateway['co_agent_id'],
            'customer_parent_id': context_gateway.get('co_customer_parent_id',False),
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    # April 24, 2020 - SAM
    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_insurance(issued_req, context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            # self.calculate_service_charge()
            self.action_partial_issued_api_insurance(context['co_uid'],customer_parent_id)
        elif all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.action_booked_api_insurance(context, pnr_list, hold_date)
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            # self.calculate_service_charge()
            # self.action_partial_booked_api_insurance(context, pnr_list, hold_date)
            self.action_partial_booked_api_insurance(context)
        elif all(rec.state == 'rescheduled' for rec in self.provider_booking_ids):
            self.write({
                'state': 'rescheduled',
                'reschedule_uid': context['co_uid'],
                'reschedule_date': datetime.now()
            })
        elif any(rec.state == 'rescheduled' for rec in self.provider_booking_ids):
            self.write({
                'state': 'partial_rescheduled',
                'reschedule_uid': context['co_uid'],
                'reschedule_date': datetime.now()
            })
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif any(rec.state == 'partial_refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'partial_refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'void' for rec in self.provider_booking_ids):
            self.write({
                'state': 'void',
                'cancel_uid': context['co_uid'],
                'cancel_date': datetime.now()
            })
        elif any(rec.state == 'partial_void' for rec in self.provider_booking_ids):
            self.write({
                'state': 'partial_void',
                'cancel_uid': context['co_uid'],
                'cancel_date': datetime.now()
            })
        elif any(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif any(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_insurance(context)
        elif any(rec.state == 'refund_failed' for rec in self.provider_booking_ids):
            self.action_refund_failed_insurance(context)
        elif any(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_set_as_cancel()
        # elif all(rec.state == 'refund_pending' for rec in self.provider_booking_ids):
        #     # refund pending
        #     self.action_set_as_refund_pending()
        # elif all(rec.state == 'cancel_pending' for rec in self.provider_booking_ids):
        #     # cancel pending
        #     self.action_set_as_cancel_pending()
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

        self.set_provider_detail_info()

        # FIXME Error provider_sequence sudah di remove
        # if self.ledger_ids:
        #     for rec in self.ledger_ids:
        #         if not rec.pnr and rec.provider_sequence >= 0:
        #             rec.write({
        #                 'pnr': self.provider_booking_ids[rec.provider_sequence].pnr
        #             })
    # END

    def check_provider_state_backup(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            self.action_booked_api_insurance(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            if req.get('force_issued'):
                self.calculate_service_charge()
                self.action_booked_api_insurance(context, pnr_list, hold_date)
                payment_res = self.payment_insurance_api({'book_id': req['book_id'],
                                                        'member': req.get('member', False),
                                                        'acquirer_seq_id': req.get('acquirer_seq_id', False)}, context)
                if payment_res['error_code'] != 0:
                    try:
                        ho_id = self.agent_id.ho_id.id
                        self.env['tt.insurance.api.con'].send_force_issued_not_enough_balance_notification(self.name, context, ho_id)
                    except Exception as e:
                        _logger.error("Send TOP UP Approve Notification Telegram Error\n" + traceback.format_exc())
                    raise RequestException(payment_res['error_code'],additional_message=payment_res['error_msg'])

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_insurance(issued_req, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_insurance(context)
        elif all(rec.state == 'refund_failed' for rec in self.provider_booking_ids):
            self.action_refund_failed_insurance(context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_partial_issued_api_insurance(context['co_uid'],customer_parent_id)
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.calculate_service_charge()
            self.action_partial_booked_api_insurance(context, pnr_list, hold_date)
        elif all(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif all(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_set_as_cancel()
        elif all(rec.state == 'refund_pending' for rec in self.provider_booking_ids):
            # refund pending
            self.action_set_as_refund_pending()
        elif all(rec.state == 'cancel_pending' for rec in self.provider_booking_ids):
            # cancel pending
            self.action_set_as_cancel_pending()
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def _create_provider_api(self, book_data, api_context):
        _destination_type = self.provider_type_id
        provider_insurance_obj = self.env['tt.provider.insurance']
        provider_id = self.env['tt.provider'].get_provider_id(book_data['provider'], _destination_type)
        carrier_id = self.env['tt.transport.carrier'].get_id(book_data['provider'],_destination_type) ## TODO LIST KALAU DARI RT INSURANCE
        def_service_charges = {
            'default': book_data.get('service_charges_default') and book_data['service_charges_default'] or [],
            'idr': book_data.get('service_charges_idr') and book_data['service_charges_idr'] or []
        }
        # lis of providers ID
        res = []
        name = {'provider': [], 'carrier': []}
        name['provider'].append(book_data['provider'])
        if carrier_id:
            name['carrier'].append(carrier_id.name)
        sequence = 0
        values = {
            'pnr': self.name,
            'provider_id': provider_id,
            'carrier_id': carrier_id.id if carrier_id else False,
            'booking_id': self.id,
            'sequence': sequence,
            'additional_information': book_data['info'],
            'origin': book_data['origin'],
            'destination': book_data['destination'],
            'start_date': book_data['date_start'],
            'end_date': book_data['date_end'],
            'master_area': book_data['master_area_id'],
            'plan_trip': book_data['plan_trip_id'],
            'master_trip': book_data['master_trip_id'],
            'product_type': book_data.get('product_type_code', ''),
            'balance_due': book_data['total'],
            'total_price': book_data['total'],
            'hold_date': (datetime.strptime(book_data['date_start'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d') + ' 23:00:00',
            'state': 'booked',
            'booked_uid': api_context['co_uid'],
            'booked_date': datetime.now(),
            'carrier_name': book_data['carrier_name'],
            'additional_vendor_pricing_info': json.dumps(def_service_charges)
        }
        res.append(provider_insurance_obj.create(values))
        name['provider'] = list(set(name['provider']))
        name['carrier'] = list(set([book_data['carrier_name']]))
        if book_data.get('product_type_code'):
            res[-1].product_type = book_data['product_type_code']
        return res, name

    #to generate sale service charge
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
                        'booking_insurance_id': self.id,
                        'description': provider.pnr,
                        'ho_id': self.ho_id.id if self.ho_id else ''
                    }
                    # curr_dict['pax_type'] = p_type
                    # curr_dict['booking_insurance_id'] = self.id
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

    # May 11, 2020 - SAM
    def set_provider_detail_info(self):
        hold_date = None
        pnr_list = []
        values = {}
        for rec in self.provider_booking_ids:
            if rec.hold_date:
                rec_hold_date = datetime.strptime(rec.hold_date[:19], '%Y-%m-%d %H:%M:%S')
                if not hold_date or rec_hold_date < hold_date:
                    hold_date = rec_hold_date
            if rec.pnr:
                pnr_list.append(rec.pnr)

        if hold_date:
            user_tz = pytz.timezone('Asia/Jakarta')
            hold_date_utc = user_tz.localize(fields.Datetime.from_string(hold_date.strftime('%Y-%m-%d %H:%M:%S')))
            hold_date = hold_date_utc.astimezone(pytz.timezone('UTC'))
            hold_date_str = hold_date.strftime('%Y-%m-%d %H:%M:%S')
            if self.hold_date != hold_date_str:
                values['hold_date'] = hold_date_str
        if pnr_list:
            pnr = ', '.join(pnr_list)
            if self.pnr != pnr:
                values['pnr'] = pnr

        if values:
            self.write(values)
    # END

    @api.multi
    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        insurance_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_insurance')

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = insurance_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = insurance_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Insurance Ticket',
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

        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        insurance_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_insurance')

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = insurance_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = insurance_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance Ticket (Price) %s.pdf' % book_obj.name,
                    'file_reference': 'Insurance Ticket with Price',
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

    def save_eticket_original_api(self, data, ctx):
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name
        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)
        if book_obj.agent_id:
            co_agent_id = book_obj.agent_id.id
        else:
            co_agent_id = self.env.user.agent_id.id

        if book_obj.user_id:
            co_uid = book_obj.user_id.id
        else:
            co_uid = self.env.user.id
        attachments = []
        for response in data['response']:
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance Ticket Original %s %s.pdf' % (book_obj.name, response['name']),
                    'file_reference': 'Insurance Ticket Original',
                    'file': response['base64'],
                    'delete_date': datetime.strptime(book_obj.end_date,'%Y-%m-%d') + timedelta(days=7)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid
                }
            )
            attachments.append(book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1).id)
        book_obj.printout_ticket_original_ids = [(6, 0, attachments)]

    @api.multi
    def print_eticket_original(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)



        if not book_obj.printout_ticket_original_ids:
            # gateway get ticket
            req = {"data": [], "provider": '','ho_id': book_obj.agent_id.ho_id.id}
            for provider_booking_obj in book_obj.provider_booking_ids:
                req.update({
                    'provider': provider_booking_obj.provider_id.code
                })
                for ticket_obj in provider_booking_obj.ticket_ids:
                    if ticket_obj.ticket_url:
                        req['data'].append({
                            'pnr': ticket_obj.ticket_number,
                            'ticket_url': ticket_obj.ticket_url,
                            'name': ticket_obj.passenger_id.name
                        })
            res = self.env['tt.insurance.api.con'].send_get_original_ticket(req)
            if res['error_code'] == 0:
                data.update({
                    'response': res['response']
                })
                self.save_eticket_original_api(data, ctx)
            else:
                return 0 # error
        if self.name != False:
            return 0
        else:
            url = []
            for ticket in book_obj.printout_ticket_original_ids:
                url.append({
                    'url': ticket.url
                })
            return url

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
        insurance_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_insurance')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = insurance_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = insurance_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Insurance HO Invoice',
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
        # return insurance_ho_invoice_id.report_action(self, data=datas)

    @api.multi
    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        insurance_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_insurance')
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = insurance_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = insurance_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Insurance Itinerary',
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

    @api.multi
    def print_itinerary_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.insurance'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        insurance_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_insurance')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = insurance_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = insurance_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Insurance Itinerary %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Insurance Itinerary',
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

    # def action_expired(self):
    #     super(ReservationAirline, self).action_expired()
    #     for provider in self.provider_booking_ids:
    #         provider.action_expired()

    def calculate_pnr_provider_carrier(self):
        pnr_name = ''
        provider_name = ''
        carrier_name = ''
        str_list_dict = {
            'pnr': [],
            'provider': [],
            'carrier': []
        }
        for seg in self.segment_ids:
            if str(seg.pnr) not in str_list_dict['pnr']:
                pnr_name += str(seg.pnr) + ', '
                str_list_dict['pnr'].append(str(seg.pnr))
            if str(seg.provider_id.code) not in str_list_dict['provider']:
                provider_name += str(seg.provider_id.code) + ', '
                str_list_dict['provider'].append(str(seg.provider_id.code))
            if str(seg.carrier_id.name) not in str_list_dict['carrier']:
                carrier_name += str(seg.carrier_id.name) + ', '
                str_list_dict['carrier'].append(str(seg.carrier_id.name))

        self.sudo().write({
            'pnr': pnr_name[:-2] if pnr_name else '',
            'provider_name': provider_name[:-2] if provider_name else '',
            'carrier_name': carrier_name[:-2] if carrier_name else '',
        })

    def get_aftersales_desc(self):
        desc_txt = ''
        for rec in self.segment_ids:
            desc_txt += 'PNR: ' + rec.pnr + '<br/>'
            desc_txt += 'Carrier: ' + rec.carrier_id.name + ' (' + rec.name + ')<br/>'
            desc_txt += 'Start: ' + rec.origin+ ' (' + datetime.strptime(rec.start_date, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y %H:%M') + ')<br/>'
            desc_txt += 'End: ' + rec.destination+ ' (' + datetime.strptime(rec.end_date, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y %H:%M') + ')<br/><br/>'
        return desc_txt

