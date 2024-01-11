import pytz

from odoo import api,models,fields, _
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta, time
import base64
import json
import copy


_logger = logging.getLogger(__name__)


class ReservationLabPintar(models.Model):
    _name = "tt.reservation.labpintar"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation Lab Pintar"

    timeslot_type = fields.Selection([('fixed','Fixed'),
                                      ('flexible','Flexible')],'Time Slot Type',readonly=True, states={'draft': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_labpintar_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.labpintar', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    # issued_pending_uid = fields.Many2one('res.users', 'Issued Pending by', readonly=True)
    # issued_pending_date = fields.Datetime('Issued Pending Date', readonly=True)
    # issued_pending_hold_date = fields.Datetime('Pending Date', readonly=True)

    state_vendor = fields.Selection(variables.STATE_VENDOR, 'State Vendor', default='draft')

    origin_id = fields.Many2one('tt.destinations', 'Test Area', readonly=True, states={'draft': [('readonly', False)]})

    test_address = fields.Char('Test Address', readonly=True, states={'draft': [('readonly', False)]})

    test_address_map_link = fields.Char('Test Address Map Link', readonly=True, states={'draft': [('readonly', False)]})

    cancellation_reason = fields.Char('Cancellation Reason', readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.labpintar', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    timeslot_ids = fields.Many2many('tt.timeslot.labpintar','tt_reservation_labpintar_timeslot_rel', 'booking_id', 'timeslot_id', 'Timeslot(s)')

    picked_timeslot_id = fields.Many2one('tt.timeslot.labpintar', 'Picked Timeslot', readonly=True, states={'draft': [('readonly', False)]})

    test_datetime = fields.Datetime('Test Datetime',related='picked_timeslot_id.datetimeslot', store=True)

    analyst_ids = fields.Many2many('tt.analyst.labpintar', 'tt_reservation_labpintar_analyst_rel', 'booking_id',
                                   'analyst_id', 'Analyst(s)', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_labpintar.tt_provider_type_labpintar'))

    split_from_resv_id = fields.Many2one('tt.reservation.labpintar', 'Splitted From', readonly=1)
    split_to_resv_ids = fields.One2many('tt.reservation.labpintar', 'split_from_resv_id', 'Splitted To', readonly=1)
    split_uid = fields.Many2one('res.users', 'Splitted by', readonly=True)
    split_date = fields.Datetime('Splitted Date', readonly=True)

    def get_form_id(self):
        return self.env.ref("tt_reservation_labpintar.tt_reservation_labpintar_form_views")

    @api.depends("passenger_ids.channel_service_charge_ids")
    def _compute_total_channel_upsell(self):
        for rec in self:
            chan_upsell_total = 0
            for pax in rec.passenger_ids:
                for csc in pax.channel_service_charge_ids:
                    chan_upsell_total += csc.amount
            rec.total_channel_upsell = chan_upsell_total

    @api.multi
    def action_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 158')
        for rec in self:
            rec.state = 'draft'

    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 159')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 160')
        for rec in self:
            rec.state = 'issued'

    def action_set_state_vendor_as_test_completed(self):
        if not ({self.env.ref('tt_base.group_external_vendor_labpintar_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 161')
        self.state_vendor = 'test_completed'

    def action_set_state_vendor_as_no_show(self):
        if not ({self.env.ref('tt_base.group_external_vendor_labpintar_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 162')
        self.state_vendor = 'no_show'

    def action_set_state_vendor_as_refund(self):
        if not ({self.env.ref('tt_base.group_external_vendor_labpintar_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 163')
        self.state_vendor = 'refund'

    def action_booked_api_labpintar(self,context):
        write_values = {
            'state': 'booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_labpintar')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'labpintar',
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

    def action_issued_labpintar(self, data):
        # issued_pending_hold_date = datetime.max
        # for provider_obj in self.provider_booking_ids:
        #     if issued_pending_hold_date > provider_obj.issued_pending_hold_date:
        #         issued_pending_hold_date = provider_obj.issued_pending_hold_date

        write_values = {
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': data.get('co_uid', self.env.user.id),
            # 'issued_pending_hold_date': issued_pending_hold_date,
            # 'issued_pending_date': datetime.now(),
            # 'issued_pending_uid': co_uid,
            'customer_parent_id': data['customer_parent_id'],
            'state_vendor': 'new_order',
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_labpintar')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'labpintar',
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

    def action_reverse_labpintar(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_refund_failed_labpintar(self,context):
        self.write({
            'state':  'refund_failed',
        })

    def action_issued_api_labpintar(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_labpintar(data)

    # def action_issued_labpintar(self,context):
    #     values = {
    #         'state': 'issued',
    #         'issued_date': datetime.now(),
    #         'issued_uid': context.get('co_uid', False)
    #     }
    #     self.write(values)
    #
    #     try:
    #         mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_final_labpintar')], limit=1)
    #         if not mail_created:
    #             temp_data = {
    #                 'provider_type': 'labpintar',
    #                 'order_number': self.name,
    #                 'type': 'issued_final',
    #             }
    #             temp_context = {
    #                 'co_agent_id': self.agent_id.id
    #             }
    #             self.env['tt.email.queue'].create_email_queue(temp_data, temp_context)
    #         else:
    #             _logger.info('Issued Final email for {} is already created!'.format(self.name))
    #             raise Exception('Issued Final email for {} is already created!'.format(self.name))
    #     except Exception as e:
    #         _logger.info('Error Create Email Queue')

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

    def action_cancel(self, backend_context=False, gateway_context=False):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 164')
        super(ReservationLabPintar, self).action_cancel(gateway_context=gateway_context)
        for rec in self.provider_booking_ids:
            rec.action_cancel(gateway_context)
        self.state_vendor = 'refund'
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    @api.one
    def create_refund(self):
        self.state = 'refund'

    def get_price_labpintar_api(self, req, context):
        #parameter
        #timeslot_list
        #jumlah pax
        overtime_surcharge = False
        timeslot_objs = self.env['tt.timeslot.labpintar'].search([('seq_id', 'in', req['timeslot_list'])])
        carrier_id = self.env['tt.transport.carrier'].search([('code', '=', req['carrier_code'])]).id

        for rec in timeslot_objs:
            if rec.datetimeslot.time() > time(11,0):
                overtime_surcharge = True
                break

        single_suplement = False
        if req['pax_count'] <= 1 and \
                carrier_id == self.env.ref('tt_reservation_labpintar.tt_transport_carrier_labpintar_antigen').id:
            single_suplement = True

        cito_surcharge = False
        if timeslot_objs.datetimeslot <= datetime.now() + timedelta(hours=6):
            cito_surcharge = True


        base_price = 0
        commission_price = 0
        overtime_price = 0
        single_suplement_price = 0
        cito_suplement_price = 0
        #ASUMSI HARGA URUT DARI MIN PAX TERKECIL
        if carrier_id == self.env.ref('tt_reservation_labpintar.tt_transport_carrier_labpintar_antigen').id:
            for rec in timeslot_objs:
                for antigen_price_pax in rec.antigen_price_ids:## di berikan asumsi data dari backend ada dan minimal ad 1 pax.
                    if req['pax_count'] >= antigen_price_pax['min_pax']:
                        base_price = antigen_price_pax.base_price
                        commission_price = antigen_price_pax.commission
                        overtime_price = timeslot_objs.overtime_surcharge
                        single_suplement_price = timeslot_objs.single_supplement
                        cito_suplement_price = timeslot_objs.cito_surcharge
                    else:
                        break
        elif carrier_id == self.env.ref('tt_reservation_labpintar.tt_transport_carrier_labpintar_pcr').id:
            for rec in timeslot_objs:
                for pcr_price_pax in rec.pcr_price_ids:
                    if req['pax_count'] >= pcr_price_pax['min_pax']:
                        base_price = pcr_price_pax.base_price
                        commission_price = pcr_price_pax.commission
                        overtime_price = timeslot_objs.overtime_surcharge
                        single_suplement_price = timeslot_objs.single_supplement
                        cito_suplement_price = timeslot_objs.cito_surcharge
                    else:
                        break
        elif carrier_id == self.env.ref('tt_reservation_labpintar.tt_transport_carrier_labpintar_pcr_express').id:
            for rec in timeslot_objs:
                for pcr_price_pax in rec.pcr_express_price_ids:
                    if req['pax_count'] >= pcr_price_pax['min_pax']:
                        base_price = pcr_price_pax.base_price
                        commission_price = pcr_price_pax.commission
                        overtime_price = timeslot_objs.overtime_surcharge
                        single_suplement_price = timeslot_objs.single_supplement
                        cito_suplement_price = timeslot_objs.cito_surcharge
                    else:
                        break
        elif carrier_id == self.env.ref('tt_reservation_labpintar.tt_transport_carrier_labpintar_pcr_priority').id:
            for rec in timeslot_objs:
                for pcr_price_pax in rec.pcr_priority_price_ids:
                    if req['pax_count'] >= pcr_price_pax['min_pax']:
                        base_price = pcr_price_pax.base_price
                        commission_price = pcr_price_pax.commission
                        overtime_price = timeslot_objs.overtime_surcharge
                        single_suplement_price = timeslot_objs.single_supplement
                        cito_suplement_price = timeslot_objs.cito_surcharge
                    else:
                        break
        else:
            for rec in timeslot_objs:
                for pcr_price_pax in rec.srbd_price_ids:
                    if req['pax_count'] >= pcr_price_pax['min_pax']:
                        base_price = pcr_price_pax.base_price
                        commission_price = pcr_price_pax.commission
                        overtime_price = timeslot_objs.overtime_surcharge
                        single_suplement_price = timeslot_objs.single_supplement
                        cito_suplement_price = timeslot_objs.cito_surcharge
                    else:
                        break


        extra_charge_per_pax = (overtime_surcharge and overtime_price or 0) + (single_suplement and single_suplement_price or 0) + (cito_surcharge and cito_suplement_price or 0)
        return ERR.get_no_error({
            "pax_count": req['pax_count'],
            "base_price_per_pax": base_price,
            "extra_price_per_pax": extra_charge_per_pax,#50000
            "commission_per_pax": commission_price
        })

    def create_booking_labpintar_api(self, req, context):
        _logger.info("Create\n" + json.dumps(req))
        booker = req['booker']
        contacts = req['contacts']
        passengers_data = copy.deepcopy(req['passengers']) # waktu create passenger fungsi odoo field kosong di hapus cth: work_place
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
                    'address_ktp': passengers[idx]['address_ktp'],
                })
                if passengers_data[idx].get('description'):
                    rec[2].update({
                        'description': passengers_data[idx]['description']
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

            for provider_obj in book_obj.provider_booking_ids:
                provider_obj.create_ticket_api(passengers)

                service_charges_val = []
                for svc in booking_data['service_charges']:
                    ## currency di skip default ke company
                    service_charges_val.append({
                        "pax_type": svc['pax_type'],
                        "pax_count": svc['pax_count'],
                        "amount": svc['amount'],
                        "total": svc['total'],
                        "foreign_amount": svc['foreign_amount'],
                        "charge_code": svc['charge_code'],
                        "charge_type": svc['charge_type'],
                        "commission_agent_id": svc.get('commission_agent_id', False)
                    })

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
                book_obj.create_svc_upsell()
            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_ids': response_provider_ids
            }

            ## PAKAI VOUCHER
            if req.get('voucher'):
                book_obj.add_voucher(req['voucher']['voucher_reference'], context)

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

    def update_pnr_provider_labpintar_api(self, req, context):
        _logger.info("Update\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.labpintar'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.labpintar'].search([('name', '=', req['order_number'])])
            else:
                raise Exception('Booking ID or Number not Found')
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            any_provider_changed = False

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.labpintar'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)

                if provider.get('extra_action') == 'save_result_url':
                    for idx, ticket_obj in enumerate(provider['tickets']):
                        provider_obj.update_result_url_per_pax_api(idx, ticket_obj['result_url'])
                    continue
                if provider.get('messages') and provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_phc(provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True
                if provider['status'] == 'ISSUED':
                    provider_obj.pnr = provider['pnr']
                    for css in provider_obj.cost_service_charge_ids:
                        css.description = provider['pnr']
                    book_obj.calculate_service_charge()
                    provider_obj.action_issued_api_labpintar(context)
                    any_provider_changed = True
                if provider['status'] == 'CANCEL':
                    provider_obj.action_cancel(context)
                    any_provider_changed = True

                #jaga jaga kalau gagal issued
                for idx, ticket_obj in enumerate(provider['tickets']):
                    if ticket_obj['ticket_number']:
                        provider_obj.update_ticket_per_pax_api(idx, ticket_obj['ticket_number'])

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

    def get_booking_labpintar_api(self,req, context):
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

            # if book_obj.agent_id.id == context.get('co_agent_id',-1) or \
            #         self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids or \
            #         book_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or \
            #         book_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
                res = book_obj.to_dict(context)
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

                timeslot_list = []
                for timeslot_obj in book_obj.timeslot_ids:
                    timeslot_list.append(timeslot_obj.to_dict())

                picked_timeslot = {}
                if book_obj.picked_timeslot_id:
                    picked_timeslot = book_obj.picked_timeslot_id.to_dict()

                res.update({
                    'origin': book_obj.origin_id.code,
                    'passengers': psg_list,
                    'provider_bookings': prov_list,
                    'test_address': book_obj.test_address,
                    'test_address_map_link': book_obj.test_address_map_link,
                    'picked_timeslot': picked_timeslot,
                    'timeslot_list': timeslot_list
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

    def payment_labpintar_api(self,req,context):
        payment_res = self.payment_reservation_api('labpintar',req,context)
        return payment_res

    def _prepare_booking_api(self, booking_data, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_labpintar.tt_provider_type_labpintar')
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
            'pnr': 1,
            'pnr2': 2,
            'state': 'booked',
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now(),
            'hold_date': fields.Datetime.now() + timedelta(minutes=10),
            'balance_due': booking_data['total'],
            'total_price': booking_data['total'],
            'sequence': 1,
            'provider_id': provider_obj and provider_obj.id or False,
            'carrier_id': carrier_obj and carrier_obj.id or False,
            'carrier_code': carrier_obj and carrier_obj.code or False,
            'carrier_name': carrier_obj and carrier_obj.name or False
        }

        timeslot_write_data = self.env['tt.timeslot.labpintar'].search([('seq_id','in',booking_data['timeslot_list'])])

        booking_tmp = {
            'state': 'booked',
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
            'timeslot_ids': [(6,0,timeslot_write_data.ids)],
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now()
        }
        if booking_data['timeslot_type'] == 'fixed':
            booking_tmp.update({
                'picked_timeslot_id': timeslot_write_data and timeslot_write_data[0].id
            })
        return booking_tmp

    # April 24, 2020 - SAM
    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        # if all(rec.state == 'issued' for rec in self.provider_booking_ids):
        #     self.action_issued_labpintar(context)
        if all(rec.state == 'issued' for rec in self.provider_booking_ids):
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_labpintar(issued_req, context)
        elif all(rec.state == 'booked' for rec in self.provider_booking_ids):
            self.action_booked_api_labpintar(context)
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
            self.action_reverse_labpintar(context)
        elif any(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed book
            self.action_cancel(gateway_context=context)
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
                        'booking_labpintar_id': self.id,
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

        # book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        book_obj = self.search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        labpintar_ticket_id = self.env.ref('tt_report_common.action_report_printout_reservation_labpintar')

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = labpintar_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = labpintar_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Lab Pintar Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Lab Pintar Ticket',
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

        # book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        book_obj = self.search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        labpintar_ticket_id = self.env.ref('tt_report_common.action_report_printout_reservation_labpintar')

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = labpintar_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = labpintar_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Lab Pintar Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Lab Pintar Ticket',
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

    # @api.multi
    # def print_eticket_original(self, data, ctx=None):
    #     # jika panggil dari backend
    #     if 'order_number' not in data:
    #         data['order_number'] = self.name
    #     if 'provider_type' not in data:
    #         data['provider_type'] = self.provider_type_id.name
    #
    #     book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
    #     datas = {'ids': book_obj.env.context.get('active_ids', [])}
    #     # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
    #     res = book_obj.read()
    #     res = res and res[0] or {}
    #     datas['form'] = res
    #     datas['is_with_price'] = True
    #     airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')
    #
    #
    #     if not book_obj.printout_ticket_original_ids:
    #         # gateway get ticket
    #         req = {"data": []}
    #         for provider_booking_obj in book_obj.provider_booking_ids:
    #             req['data'].append({
    #                 'pnr': provider_booking_obj.pnr,
    #                 'provider': provider_booking_obj.provider_id.code,
    #                 'last_name': book_obj.passenger_ids[0].last_name,
    #                 'pnr2': provider_booking_obj.pnr2
    #             })
    #         res = self.env['tt.airline.api.con'].send_get_original_ticket(req)
    #         if res['error_code'] == 0:
    #             data.update({
    #                 'response': res['response']
    #             })
    #             self.save_eticket_original_api(data, ctx)
    #         else:
    #             return 0 # error
    #     if self.name != False:
    #         return 0
    #     else:
    #         url = []
    #         for ticket in book_obj.printout_ticket_original_ids:
    #             url.append({
    #                 'url': ticket.url
    #             })
    #         return url

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
        labpintar_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_labpintar')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = labpintar_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = labpintar_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Lab Pintar HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Lab Pintar HO Invoice',
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

        # book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        book_obj = self.search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        labpintar_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_labpintar')

        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = labpintar_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = labpintar_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Itinerary',
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

        # book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        book_obj = self.search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        labpintar_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_labpintar')

        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = labpintar_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = labpintar_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'LabPintar Itinerary %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Itinerary',
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

    def get_passenger_list_email(self):
        passengers = '<br/>'
        psg_count = 0
        for rec in self.passenger_ids:
            psg_count += 1
            passengers += str(psg_count) + '. ' + (rec.title + ' ' if rec.title else '') + (rec.first_name if rec.first_name else '') + ' ' + (rec.last_name if rec.last_name else '') + '<br/>'
        return passengers

    def get_terms_conditions_email(self):
        if self.carrier_name == 'LPHCKATG':
            template_obj = self.env.ref('tt_reservation_labpintar.labpintar_antigen_information')
        elif self.carrier_name == 'LPHCKPCR':
            template_obj = self.env.ref('tt_reservation_labpintar.labpintar_pcr_information')
        else:
            template_obj = self.env.ref('tt_reservation_labpintar.labpintar_pcr_priority_information')
        return template_obj.html

    def get_terms_conditions_email_old(self):
        terms_txt = "<u><b>Terms and Conditions</b></u><br/>"
        terms_txt += "1. Payment must be made in advance.<br/>"
        terms_txt += "2. Cancellation Policy:<br/>"
        terms_txt += "<ul>"
        terms_txt += "<li>Before D-1: Free</li>"
        terms_txt += "<li>D-1: Rp.50,000,- per participants, can only be processed before 16:00 WIB</li>"
        terms_txt += "<li>On the day of the test: Forfeited with no refund</li>"
        terms_txt += "</ul>"
        terms_txt += "3. Reschedule Policy:<br/>"
        terms_txt += "<ul>"
        terms_txt += "<li>Before D-1: Free</li>"
        terms_txt += "<li>D-1: Rp.50,000,- per participants, can only be processed before 16:00 WIB</li>"
        terms_txt += "<li>You cannot reschedule on the day of the test</li>"
        terms_txt += "<li>Reschedule can only be done 1 time, and it depends on the availability of our nurses/officers and our schedules.</li>"
        terms_txt += "</ul>"
        terms_txt += "4. Participant names cannot be changed.<br/>"
        terms_txt += "5. Addition of participants:<br/>"
        terms_txt += "<ul>"
        terms_txt += "<li>D-1: Ask our operator whether it can be done or not</li>"
        terms_txt += "<li>You cannot add any participants on the day of the test. Please issue a new order.</li>"
        terms_txt += "</ul>"
        terms_txt += "6. Reduction of participants refers to the Cancellation Policy.<br/>"
        if self.carrier_name in ['PRKPCR']:
            terms_txt += "7. Under normal circumstances, test results will be released by RSJ Menur (Menur Mental Hospital) Surabaya around 24-72 hours after the test.<br/>"
        else:
            terms_txt += "7. Under normal circumstances, test results will be sent via Email by Lab Pintar around 2-4 hours after the test.<br/>"
        terms_txt += "8. In case our nurses/officers do not come for the scheduled test, you can file a complaint at most 24 hours after the supposedly test schedule."
        return terms_txt


    def get_aftersales_desc(self):
        desc_txt = 'PNR: ' + self.pnr + '<br/>'
        desc_txt += 'Test Type: ' + self.provider_booking_ids[0].carrier_id.name + '<br/>'
        desc_txt += 'Test Address: ' + self.test_address + '<br/>'
        desc_txt += 'Test Date/Time: ' + self.picked_timeslot_id.get_datetimeslot_str() + '<br/>'
        return desc_txt

    def confirm_order(self, req, context):
        try:
            provider_obj = self.env['tt.provider.labpintar'].search([('pnr', '=', req['pnr'])], limit=1)
            if provider_obj:
                book_obj = self.browse(provider_obj.booking_id.id)
                if book_obj.state_vendor == 'new_order':
                    # check analyst
                    analyst_list = []
                    for analyst_req_dict in req['analysts']:
                        analyst_obj = self.env['tt.analyst.labpintar'].create({
                            "name": analyst_req_dict['name'],
                        })
                        analyst_list.append(analyst_obj.id)
                    book_obj.write({
                        'analyst_ids': [(6, 0, analyst_list)],
                        'state_vendor': 'confirmed_order'
                    })
                    return ERR.get_no_error({
                        "no_booking": req['pnr'],
                        "state": book_obj.state_vendor
                    })
                else:
                    _logger.error('pnr has been confirm / refund')
                    return ERR.get_error(500, additional_message='no_booking already confirm')
            else:
                _logger.error('pnr not found')
                return ERR.get_error(500, additional_message='no_booking not found')
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def cancel_order(self, req, context):
        try:
            provider_obj = self.env['tt.provider.labpintar'].search([('pnr', '=', req['pnr'])], limit=1)
            if provider_obj:
                book_obj = self.browse(provider_obj.booking_id.id)
                if book_obj.state_vendor == 'new_order' or book_obj.state_vendor == 'confirmed_order':
                    book_obj.state_vendor = 'refund'
                    book_obj.cancellation_reason = req['reason']
                    return ERR.get_no_error({
                        "no_booking": req['pnr'],
                        "state": book_obj.state_vendor
                    })
                else:
                    _logger.error('pnr has been refund')
                    return ERR.get_error(500, additional_message='no_booking has been refund')
            else:
                _logger.error('pnr not found')
                return ERR.get_error(500, additional_message='no_booking not found')
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_result_url(self, req, context):
        try:
            provider_obj = self.env['tt.provider.labpintar'].search([('pnr', '=', req['pnr'])], limit=1)
            if provider_obj:
                list_passenger_update = []
                book_obj = self.browse(provider_obj.booking_id.id)
                for rec in book_obj.passenger_ids:
                    for passenger_request_dict in req['passengers']:
                        if rec.ticket_number == passenger_request_dict['ticket_number']:
                            rec.result_url = passenger_request_dict['result_url']
                            list_passenger_update.append(passenger_request_dict['ticket_number'])
                if len(list_passenger_update):
                    return ERR.get_no_error({
                        "no_booking": req['pnr'],
                        "list_passenger": list_passenger_update
                    })
                else:
                    _logger.error('no passenger update')
                    return ERR.get_error(500, additional_message='no_booking found but, no registration not found')
            else:
                _logger.error('pnr not found')
                return ERR.get_error(500, additional_message='no_booking not found')
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)