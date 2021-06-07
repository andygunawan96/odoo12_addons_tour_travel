import pytz

from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta, time
import base64
import json


_logger = logging.getLogger(__name__)

class ReservationPeriksain(models.Model):
    _name = "tt.reservation.periksain"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation Periksain"

    timeslot_type = fields.Selection([('fixed','Fixed'),
                                      ('flexible','Flexible')],'Time Slot Type',readonly=True, states={'draft': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_periksain_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    pending_date = fields.Datetime('Pending Date', readonly=True, states={'draft': [('readonly', False)]})
    
    passenger_ids = fields.One2many('tt.reservation.passenger.periksain', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    issued_pending_uid = fields.Many2one('res.users', 'Issued Pending by', readonly=True)
    issued_pending_date = fields.Datetime('Issued Pending Date', readonly=True)

    origin_id = fields.Many2one('tt.destinations', 'Test Area', readonly=True, states={'draft': [('readonly', False)]})

    test_address = fields.Char('Test Address', readonly=True, states={'draft': [('readonly', False)]})

    test_address_map_link = fields.Char('Test Address Map Link', readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.periksain', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    timeslot_ids = fields.Many2many('tt.timeslot.periksain','tt_reservation_periksain_timeslot_rel', 'booking_id', 'timeslot_id', 'Timeslot(s)')

    used_timeslot_id = fields.Many2one('tt.timeslot.periksain', 'Timeslot(s)')

    test_datetime = fields.Datetime('Test Datetime',related='used_timeslot_id.datetimeslot', store=True)

    analyst_ids = fields.Many2many('tt.analyst.periksain', 'tt_reservation_periksain_analyst_rel', 'booking_id',
                                   'analyst_id', 'Analyst(s)')

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_periksain.tt_provider_type_periksain'))

    def get_form_id(self):
        return self.env.ref("tt_reservation_periksain.tt_reservation_periksain_form_views")

    @api.multi
    def action_set_as_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.multi
    def action_set_as_booked(self):
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        for rec in self:
            rec.state = 'issued'

    def action_booked_api_periksain(self,context,hold_date=False):
        if type(hold_date) != datetime:
            hold_date = False

        write_values = {
            'state': 'booked',
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_periksain')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'periksain',
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

    def action_issued_api_periksain(self,acquirer_id,customer_parent_id,context):
        self.action_issued_periksain(context['co_uid'],customer_parent_id,acquirer_id)

    def action_issued_pending_api_periksain(self,context):
        current_wib_datetime = datetime.now(pytz.timezone('Asia/Jakarta'))
        if '08:00' < str(current_wib_datetime) < '18:00':
            pending_date = datetime.now() + timedelta(hours=1)
        else:
            pending_date = current_wib_datetime.replace(hour=10, minute=0)
            if current_wib_datetime > current_wib_datetime.replace(hour=10,minute=0):
                pending_date = pending_date+timedelta(days=1)

        write_values = {
            'state': 'issued_pending',
            'pending_date': pending_date,
            'issued_pending_uid': context['co_uid'],
            'issued_pending_date': datetime.now()
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_periksain')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'periksain',
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

    def action_reverse_periksain(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_refund_failed_periksain(self,context):
        self.write({
            'state':  'refund_failed',
        })

    def action_issued_periksain(self,co_uid,customer_parent_id,acquirer_id = False):
        values = {
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        }
        if not self.booked_date:
            values.update({
                'booked_date': values['issued_date'],
                'booked_uid': values['issued_uid'],
            })
        self.write(values)

        try:
            mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_final_periksain')], limit=1)
            if not mail_created:
                temp_data = {
                    'provider_type': 'periksain',
                    'order_number': self.name,
                    'type': 'issued_final',
                }
                temp_context = {
                    'co_agent_id': self.agent_id.id
                }
                self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
            else:
                _logger.info('Issued Final email for {} is already created!'.format(self.name))
                raise Exception('Issued Final email for {} is already created!'.format(self.name))
        except Exception as e:
            _logger.info('Error Create Email Queue')

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
        super(ReservationPeriksain, self).action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'


    @api.one
    def create_refund(self):
        self.state = 'refund'

    def get_price_periksain_api(self, req, context):
        #parameter
        #timeslot_list
        #jumlah pax
        overtime_surcharge = False
        timeslot_objs = self.env['tt.timeslot.periksain'].search('seq_id', 'in', req['timeslot_list'])
        for rec in timeslot_objs:
            if rec.datetimeslot.time() > time(11,0):
                overtime_surcharge = True
                break

        single_suplement = False
        if req['pax_count'] <= 1:
            single_suplement = True
        total_price = 150000+ (overtime_surcharge and 25000 or 0) + (single_suplement and 25000 or 0)
        return ERR.get_no_error({
            "pax_count": req['pax_count'],
            "price_per_pax": total_price,
            "commission_per_pax": 25000
        })

    def create_booking_periksain_api(self, req, context):
        _logger.info("Create\n" + json.dumps(req))
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        booking_data = req['provider_bookings']

        try:
            values = self._prepare_booking_api(booking_data,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            list_passenger_value = self.create_passenger_value_api(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
                rec[2].update({
                    'customer_id': list_customer_id[idx].id,
                    'email': passengers[idx]['email'],
                    'phone_number': passengers[idx]['phone_number'],
                    'sample_method': passengers[idx]['sample_method']
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
                'contact_phone': contact_obj.phone_ids and "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number) or '-',
                'passenger_ids': list_passenger_value,
            })

            book_obj = self.create(values)

            for idx,provider_obj in enumerate(book_obj.provider_booking_ids):
                provider_obj.create_ticket_api(passengers)

                service_charges_val = []
                for svc in booking_data[idx]['service_charges']:
                    ## currency di skip default ke company
                    service_charges_val.append((0, 0, {
                        "pax_type": svc['pax_type'],
                        "pax_count": svc['pax_count'],
                        "amount": svc['amount'],
                        "total_amount": svc['total_amount'],
                        "foreign_amount": svc['foreign_amount'],
                        "charge_code": svc['charge_code'],
                        "charge_type": svc['charge_type']
                    }))

                provider_obj.create_service_charge(service_charges_val)

            book_obj.calculate_service_charge()
            book_obj.check_provider_state(context)

            response_provider_ids = []
            for provider in book_obj.provider_booking_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })

            #channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)

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

    def update_pnr_provider_periksain_api(self, req, context):
        _logger.info("Update\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.periksain'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.periksain'].search([('name', '=', req['order_number'])])
            else:
                raise Exception('Booking ID or Number not Found')
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            any_provider_changed = False

            for provider in req['provider_booking']:
                provider_obj = self.env['tt.provider.periksain'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)

                if provider['status'] == 'ISSUED_PENDING':
                    provider_obj.action_issued_pending_api_periksain(context)
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

    def get_booking_periksain_api(self,req, context):
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

            if book_obj.agent_id.id == context.get('co_agent_id',-1) or \
                    self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or \
                    book_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or \
                    book_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
                res = book_obj.to_dict(context['co_agent_id'] == self.env.ref('tt_base.rodex_ho').id)
                psg_list = []
                for rec_idx, rec in enumerate(book_obj.passenger_ids):
                    rec_data = rec.to_dict()
                    rec_data.update({
                        'passenger_number': rec.sequence
                    })
                    psg_list.append(rec_data)
                prov_list = []
                for rec in book_obj.provider_booking_ids:
                    prov_list.append(rec.to_dict())

                res.update({
                    'origin': book_obj.origin_id.code,
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

    def payment_periksain_api(self,req,context):
        payment_res = self.payment_reservation_api('periksain',req,context)
        return payment_res

    def update_cost_service_charge_airline_api(self,req,context):
        try:
            _logger.info('Update cost\n' + json.dumps(req))
            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)

                # May 12, 2020 - SAM
                if not provider.get('force_update_service_charge') and (not provider.get('total_price') or provider_obj.total_price == provider['total_price']):
                    continue
                # provider_obj.write({
                    # 'pnr': provider['pnr'],
                    # 'balance_due': provider['balance_due'],
                    # 'total_price': provider['total_price'],
                # })
                # END
                ledger_created = provider_obj.delete_service_charge()
                # May 13, 2020 - SAM
                if ledger_created:
                    # September 3, 2020 - SAM
                    # Apabila terissued di backend dan error di vendor dengan status book dan perubahan harga akan di reverse
                    # if not req.get('force_issued'):
                    #     raise RequestException(1027)
                    provider_obj.action_reverse_ledger()
                    provider_obj.delete_service_charge()

                provider_obj.delete_passenger_fees()
                provider_obj.delete_passenger_tickets()
                # END

                # May 14, 2020 - SAM
                # Rencana awal mau melakukan compare passenger sequence
                # Dilapangan sequence passenger pada tiap provider bisa berbeda beda, tidak bisa digunakan sebagai acuan
                provider_obj.create_ticket_api(provider['passengers'], provider['pnr'])
                for journey in provider['journeys']:
                    for segment in journey['segments']:
                        for fare in segment['fares']:
                            provider_obj.create_service_charge(fare['service_charges'])
                # May 13, 2020 - SAM
                if ledger_created and req.get('force_issued'):
                    provider_obj.action_create_ledger(context['co_uid'])
                # END

            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            book_obj.calculate_service_charge()
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error("Update Cost Service Charge Error")

    def _prepare_booking_api(self, booking_data, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_periksain.tt_provider_type_periksain')
        provider_obj = self.env['tt.provider'].sudo().search([('code', '=', booking_data['provider']), ('provider_type_id', '=', provider_type_id.id)])
        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', booking_data['carrier_code']), ('provider_type_id', '=', provider_type_id.id)])

        # "pax_type": "ADT",
        # "pax_count": 1,
        # "amount": 150000,
        # "total_amount": 150000,
        # "foreign_amount": 150000,
        # "currency": "IDR",
        # "foreign_currency": "IDR",
        # "charge_code": "fare",
        # "charge_type": "FARE"

        provider_vals = {
            'state': 'booked',
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now(),
            'hold_date': fields.Datetime.now() + timedelta(hours=1),
            'balance_due': booking_data['total'],
            'total_price': booking_data['total'],
            'sequence': 1,
            'provider_id': provider_obj and provider_obj.id or False,
            'carrier_id': carrier_obj and carrier_obj.id or False,
            'carrier_code': carrier_obj and carrier_obj.code or False,
            'carrier_name': carrier_obj and carrier_obj.name or False
        }

        timeslot_write_data = []

        booking_tmp = {
            'origin_id': dest_obj.get_id(booking_data['origin'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': booking_data['adult'],
            'agent_id': context_gateway['co_agent_id'],
            'customer_parent_id': context_gateway.get('co_customer_parent_id',False),
            'user_id': context_gateway['co_uid'],
            'provider_name': provider_obj.code,
            'carrier_name': carrier_obj.code,
            'timeslot_type': booking_data['timeslot_type'],
            'test_address': booking_data['test_address'],
            'test_address_map_link': booking_data['test_address_map_link'],
            'provider_booking_ids': [(0,0,provider_vals)],

            'hold_date': fields.Datetime.now() + timedelta(hours=1),## ini gantiin action booked, gak ada action booked
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now()
        }
        #"timeslot_list"

        return booking_tmp

    # April 24, 2020 - SAM
    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'issued' for rec in self.provider_booking_ids):
            pass
            # self.action_issued_api_airline(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_issued_api_airline(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
        elif all(rec.state == 'booked' for rec in self.provider_booking_ids):
            self.action_booked_api_periksain(context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif any(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif any(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_periksain(context)
        elif any(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
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
            self.action_booked_api_periksain(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            if req.get('force_issued'):
                self.calculate_service_charge()
                self.action_booked_api_periksain(context, pnr_list, hold_date)
                payment_res = self.payment_airline_api({'book_id': req['book_id'],
                                                        'member': req.get('member', False),
                                                        'acquirer_seq_id': req.get('acquirer_seq_id', False)}, context)
                if payment_res['error_code'] != 0:
                    try:
                        self.env['tt.airline.api.con'].send_force_issued_not_enough_balance_notification(self.name, context)
                    except Exception as e:
                        _logger.error("Send TOP UP Approve Notification Telegram Error\n" + traceback.format_exc())
                    raise RequestException(payment_res['error_code'],additional_message=payment_res['error_msg'])

            self.action_issued_api_airline(acquirer_id and acquirer_id.id or False, customer_parent_id, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif all(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_airline(context)
        elif all(rec.state == 'refund_failed' for rec in self.provider_booking_ids):
            self.action_refund_failed_airline(context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_partial_issued_api_airline(context['co_uid'],customer_parent_id)
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.calculate_service_charge()
            self.action_partial_booked_api_airline(context, pnr_list, hold_date)
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

    def update_pnr_booked(self,provider_obj,provider,context):
        provider_obj.action_booked_api_airline(provider, context)

    #to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        # April 30, 2020 - SAM
        this_service_charges = []
        # END
        for idx, provider in enumerate(self.provider_booking_ids):
            sc_value = {}
            for p_sc in provider.cost_service_charge_ids:
                p_charge_code = p_sc.charge_code
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_pax_type):
                    sc_value[p_pax_type] = {}
                c_code = ''
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
                    'commission_agent_id': p_sc.commission_agent_id.id
                })

            # values = []
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    # April 27, 2020 - SAM
                    curr_dict = {
                        'pax_type': p_type,
                        'booking_periksain_id': self.id,
                        'description': provider.pnr,
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

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')

        if not book_obj.printout_ticket_id:
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
                    'filename': 'Airline Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Airline Ticket',
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
        }
        return url

    @api.multi
    def print_eticket_with_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')

        if not book_obj.printout_ticket_price_id:
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
                    'filename': 'Airline Ticket (Price) %s.pdf' % book_obj.name,
                    'file_reference': 'Airline Ticket with Price',
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
        }
        return url

    @api.multi
    def print_eticket_original(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')


        if not book_obj.printout_ticket_original_ids:
            # gateway get ticket
            req = {"data": []}
            for provider_booking_obj in book_obj.provider_booking_ids:
                req['data'].append({
                    'pnr': provider_booking_obj.pnr,
                    'provider': provider_booking_obj.provider_id.code,
                    'last_name': book_obj.passenger_ids[0].last_name,
                    'pnr2': provider_booking_obj.pnr2
                })
            res = self.env['tt.airline.api.con'].send_get_original_ticket(req)
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

    @api.multi
    def print_ho_invoice(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        airline_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_airline')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = airline_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = airline_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Airline HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Airline HO Invoice',
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
        # return airline_ho_invoice_id.report_action(self, data=datas)

    @api.multi
    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        airline_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_airline')
        if not book_obj.printout_itinerary_id:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = airline_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = airline_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Airline Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Airline Itinerary',
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

    def get_passenger_list_email(self):
        passengers = '<br/>'
        psg_count = 0
        for rec in self.passenger_ids:
            psg_count += 1
            passengers += str(psg_count) + '. ' + (rec.title + ' ' if rec.title else '') + (rec.first_name if rec.first_name else '') + ' ' + (rec.last_name if rec.last_name else '') + '<br/>'
        return passengers
