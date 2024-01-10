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

class Reservationmedical(models.Model):
    _name = "tt.reservation.medical"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation medical"

    timeslot_type = fields.Selection([('fixed','Fixed'),
                                      ('flexible','Flexible')],'Time Slot Type',readonly=True, states={'draft': [('readonly', False)]})

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_medical_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.medical', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    state_vendor = fields.Selection(variables.STATE_VENDOR, 'State Vendor', default='draft')

    origin_id = fields.Many2one('tt.destinations', 'Test Area', readonly=True, states={'draft': [('readonly', False)]})

    test_address = fields.Char('Test Address', readonly=True, states={'draft': [('readonly', False)]})

    test_address_map_link = fields.Char('Test Address Map Link', readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.medical', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    timeslot_ids = fields.Many2many('tt.timeslot.medical','tt_reservation_medical_timeslot_rel', 'booking_id', 'timeslot_id', 'Timeslot(s)')

    picked_timeslot_id = fields.Many2one('tt.timeslot.medical', 'Picked Timeslot', readonly=True, states={'draft': [('readonly', False)]})

    test_datetime = fields.Datetime('Test Datetime',related='picked_timeslot_id.datetimeslot', store=True)

    analyst_ids = fields.Many2many('tt.analyst.medical', 'tt_reservation_medical_analyst_rel', 'booking_id',
                                   'analyst_id', 'Analyst(s)', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_medical.tt_provider_type_medical'))

    split_from_resv_id = fields.Many2one('tt.reservation.medical', 'Splitted From', readonly=1)
    split_to_resv_ids = fields.One2many('tt.reservation.medical', 'split_from_resv_id', 'Splitted To', readonly=1)
    split_uid = fields.Many2one('res.users', 'Splitted by', readonly=True)
    split_date = fields.Datetime('Splitted Date', readonly=True)

    verified_uid = fields.Many2one('res.users', 'Verified by', readonly=True)
    verified_date = fields.Datetime('Verified Date', readonly=True)

    def get_form_id(self):
        return self.env.ref("tt_reservation_medical.tt_reservation_medical_form_views")

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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 175')
        for rec in self:
            rec.state = 'draft'

    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 176')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 177')
        for rec in self:
            rec.state = 'issued'

    @api.multi
    def action_set_state_vendor_as_suspect(self):
        if not ({self.env.ref('tt_base.group_external_vendor_medical_level_2').id, self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 178')
        for rec in self:
            rec.state_vendor = 'suspect'

    def action_booked_api_medical(self,context):
        write_values = {
            'state': 'booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_medical')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'medical',
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

    def action_issued_medical(self,data):
        write_values = {
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': data.get('co_uid', self.env.user.id),
            'customer_parent_id': data['customer_parent_id'],
            'state_vendor': 'new_order',
        }

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test': False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_medical')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'medical',
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

    def action_reverse_medical(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_refund_failed_medical(self,context):
        self.write({
            'state':  'refund_failed',
        })

    def action_issued_api_medical(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_medical(data)

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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 179')
        super(Reservationmedical, self).action_cancel(gateway_context=gateway_context)
        for rec in self.provider_booking_ids:
            rec.action_cancel(gateway_context)
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'


    @api.one
    def create_refund(self):
        self.state = 'refund'

    def get_price_medical_api(self, req, context):
        #parameter
        #timeslot_list
        #jumlah pax
        #carrier_code

        carrier_obj = self.env['tt.transport.carrier'].search([('code', '=', req['carrier_code'])])
        overtime_surcharge = False
        timeslot_objs = self.env['tt.timeslot.medical'].search([('seq_id', 'in', req['timeslot_list'])])

        if not timeslot_objs:
            raise RequestException(1022,"<br/>\nJadwal Habis. Bisa dicoba tanggal/jam yang lain<br/>\nNo Timeslot. Please Try Other Date/Time")
        else:
            if not timeslot_objs.get_availability(carrier_obj.code, req['pax_count']):
                if timeslot_objs.timeslot_type == 'drive_thru':
                    raise RequestException(1022,"<br/>\nJadwal Penuh. %sBisa dicoba tanggal/jam yang lain<br/>\nTimeslot is Full. %sPlease Try Other Date/Time" % ("Only %s Slot(s) Available or " % (timeslot_objs.total_pcr_timeslot - timeslot_objs.used_pcr_count) if timeslot_objs.used_pcr_count < timeslot_objs.total_pcr_timeslot else "", "Only %s Slot(s) Available or " % (timeslot_objs.total_pcr_timeslot - timeslot_objs.used_pcr_count) if timeslot_objs.used_pcr_count < timeslot_objs.total_pcr_timeslot else ""))
                else:
                    raise RequestException(1022,"<br/>\nJadwal Penuh. Bisa dicoba tanggal/jam yang lain<br/>\nTimeslot is Full. Please Try Other Date/Time")

        for rec in timeslot_objs:
            if rec.datetimeslot.time() > time(11,0):
                overtime_surcharge = True
                break

        single_suplement = False
        base_price = 0
        commission_price = 0
        overtime_price = 0
        single_suplement_price = 0
        admin_fee = 0

        # KALAU ADA HOMECARE 1 ORANG BARU DI CHECK
        # if req['pax_count'] <= 1 and \
        #         carrier_obj.id == self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_home_care_antigen').id:
        #     single_suplement = True

        # if carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_home_care_antigen').id]:
        #     for rec in timeslot_objs:
        #         if rec.base_price_antigen > base_price:
        #             base_price = rec.base_price_antigen
        #             commission_price = rec.commission_antigen
        #             overtime_price = rec.overtime_surcharge
        #             single_suplement_price = rec.single_supplement
        #             if carrier_obj.id == self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_drive_thru_nathos_antigen').id:
        #                 admin_fee = rec.admin_fee_antigen_drivethru
        # el
        if carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_rs_nathos').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_nathos > base_price:
                    base_price = rec.base_price_pcr_nathos
                    commission_price = rec.commission_pcr_nathos

        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_poc').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_poc > base_price:
                    base_price = rec.base_price_pcr_poc
                    commission_price = rec.commission_pcr_poc
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_bali').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_bali > base_price:
                    base_price = rec.base_price_pcr_bali
                    commission_price = rec.commission_pcr_bali
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_mutasi').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_mutasi > base_price:
                    base_price = rec.base_price_pcr_mutasi
                    commission_price = rec.commission_pcr_saliva_mutasi

        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_rs_nathos').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_saliva_nathos > base_price:
                    base_price = rec.base_price_pcr_saliva_nathos
                    commission_price = rec.commission_pcr_saliva_nathos

        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_poc').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_saliva_poc > base_price:
                    base_price = rec.base_price_pcr_saliva_poc
                    commission_price = rec.commission_pcr_saliva_poc
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_bali').id]:
            for rec in timeslot_objs:
                if rec.base_price_pcr_saliva_bali > base_price:
                    base_price = rec.base_price_pcr_saliva_bali
                    commission_price = rec.commission_pcr_saliva_bali
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_rs_nathos').id]:
            for rec in timeslot_objs:
                if rec.base_price_antigen_nathos > base_price:
                    base_price = rec.base_price_antigen_nathos
                    commission_price = rec.commission_antigen_nathos
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_poc').id]:
            for rec in timeslot_objs:
                if rec.base_price_antigen_poc > base_price:
                    base_price = rec.base_price_antigen_poc
                    commission_price = rec.commission_antigen_poc
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_tes_antibodi_rbd').id]:
            for rec in timeslot_objs:
                if rec.base_price_tes_antibodi_rbd > base_price:
                    base_price = rec.base_price_tes_antibodi_rbd
                    commission_price = rec.commission_tes_antibodi_rbd
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_nassal').id]:
            for rec in timeslot_objs:
                if rec.base_price_antigen_nassal > base_price:
                    base_price = rec.base_price_antigen_nassal
                    commission_price = rec.commission_antigen_nassal
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup1').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup1 > base_price:
                    base_price = rec.base_price_paket_medical_checkup1
                    commission_price = rec.commission_paket_medical_checkup1
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup2').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup2 > base_price:
                    base_price = rec.base_price_paket_medical_checkup2
                    commission_price = rec.commission_paket_medical_checkup2
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup3').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup3 > base_price:
                    base_price = rec.base_price_paket_medical_checkup3
                    commission_price = rec.commission_paket_medical_checkup3
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup4_male').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup4_male > base_price:
                    base_price = rec.base_price_paket_medical_checkup4_male
                    commission_price = rec.commission_paket_medical_checkup4_male
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup4_female').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup4_female > base_price:
                    base_price = rec.base_price_paket_medical_checkup4_female
                    commission_price = rec.commission_paket_medical_checkup4_female
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup5_male').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup5_male > base_price:
                    base_price = rec.base_price_paket_medical_checkup5_male
                    commission_price = rec.commission_paket_medical_checkup5_male
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup5_female').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_medical_checkup5_female > base_price:
                    base_price = rec.base_price_paket_medical_checkup5_female
                    commission_price = rec.commission_paket_medical_checkup5_female

        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_screening_cvd19 > base_price:
                    base_price = rec.base_price_paket_screening_cvd19
                    commission_price = rec.commission_paket_screening_cvd19
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19_with_pcr').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_screening_cvd19_with_pcr > base_price:
                    base_price = rec.base_price_paket_screening_cvd19_with_pcr
                    commission_price = rec.commission_paket_screening_cvd19_with_pcr
        elif carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19_urban_lifestyle').id]:
            for rec in timeslot_objs:
                if rec.base_price_paket_screening_cvd19_urban_lifestyle > base_price:
                    base_price = rec.base_price_paket_screening_cvd19_urban_lifestyle
                    commission_price = rec.commission_paket_screening_cvd19_urban_lifestyle



        extra_charge_per_pax = (overtime_surcharge and overtime_price or 0) + (single_suplement and single_suplement_price or 0)
        return ERR.get_no_error({
            "pax_count": req['pax_count'],
            "base_price_per_pax": base_price,
            "extra_price_per_pax": extra_charge_per_pax,
            "commission_per_pax": commission_price,
            "admin_fee": admin_fee
        })

    def create_booking_medical_api(self, req, context):
        _logger.info("Create\n" + json.dumps(req))
        booker = req['booker']
        contacts = req['contacts']
        passengers_data = copy.deepcopy(req['passengers']) # waktu create passenger fungsi odoo field kosong di hapus cth: work_place
        passengers = req['passengers']
        booking_data = req['provider_bookings']

        try:
            ##validator pax kembar dan belum verified di medical
            duplicate_pax_list = self.env['tt.reservation.passenger.medical'].find_duplicate_passenger_new_order(passengers,booking_data['carrier_code'])
            if duplicate_pax_list:
                raise RequestException(1026,additional_message=duplicate_pax_list)

            values = self._prepare_booking_api(booking_data,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            list_passenger_value = self.create_passenger_value_api(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
                rec[2].update({
                    'customer_id': list_customer_id[idx].id,
                    'email': passengers_data[idx]['email'],
                    'phone_number': passengers_data[idx]['phone_number'],
                    'address_ktp': passengers_data[idx]['address_ktp'],
                })
                if passengers_data[idx].get('description'):
                    rec[2].update({
                        "description": passengers_data[idx]['description']
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
            _logger.error("##RequestException\n%s" % (traceback.format_exc()))
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error("##Exception\n%s" % (traceback.format_exc()))
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            if "concurrent update" in str(e):
                return ERR.get_error(1036)
            else:
                return ERR.get_error(1004)


    def update_pnr_provider_medical_api(self, req, context):
        _logger.info("Update\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.medical'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.medical'].search([('name', '=', req['order_number'])])
            else:
                raise Exception('Booking ID or Number not Found')
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            any_provider_changed = False
            ## kalau tanpa extra action save result url, menjadi update booking issued normal.
            ## Else menjadi update result url customer

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.medical'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                if provider.get('messages') and provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_medical(provider.get('error_code', -1),provider.get('error_msg', ''))
                if provider['status'] == 'ISSUED':
                    provider_obj.action_issued_api_medical(context)
                if provider['status'] == 'CANCEL':
                    provider_obj.action_cancel(context)
                    any_provider_changed = True
                #jaga jaga kalau gagal issued
                for idx, ticket_obj in enumerate(provider['tickets']):
                    if ticket_obj['ticket_number']:
                        provider_obj.update_ticket_per_pax_api(idx, ticket_obj['ticket_number'])
                    any_provider_changed = True

            if any_provider_changed:
                book_obj.check_provider_state(context, req=req)


            return ERR.get_no_error({
                'order_number': book_obj.name,
                'book_id': book_obj.id
            })
        except RequestException as e:
            _logger.error("##RequestException\n%s" % (traceback.format_exc()))
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error("##Exception\n%s" % (traceback.format_exc()))
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1005)

    def get_booking_medical_api(self,req, context):
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
            co_user_vendor_obj = None
            if user_obj.vendor_id:
                co_user_vendor_obj = user_obj.vendor_id.id

            # if book_obj.agent_id.id == context.get('co_agent_id',-1) or \
            #     vendor_obj in [self.env.ref('tt_base.vendor_national_hospital').id] or \
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
                    if co_user_vendor_obj: #check user vendor atau tidak
                        # if rec.provider_id.id == self.env.ref('tt_reservation_medical.tt_provider_medical').id and vendor_obj == self.env.ref('tt_base.vendor_national_hospital').id: #check vendor sama provider booking sama / tidak
                        if rec.provider_id.id == co_user_vendor_obj:
                            _logger.error(traceback.format_exc())
                            return ERR.get_error(1013)
                    prov_list.append(rec.to_dict())

                timeslot_list = []
                for timeslot_obj in book_obj.timeslot_ids:
                    timeslot_list.append({
                        "datetimeslot": timeslot_obj.datetimeslot.strftime('%Y-%m-%d %H:%M'),
                        "area": timeslot_obj.destination_id.city
                    })

                picked_timeslot = {}
                if book_obj.picked_timeslot_id:
                    picked_timeslot = book_obj.picked_timeslot_id.to_dict()

                res.update({
                    'state_vendor': book_obj.state_vendor,
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

    def confirm_order_api(self, req, context):
        try:
            book_obj = self.get_book_obj(req.get('book_id'), req.get('order_number'))
            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)
            if book_obj and self.env.ref('tt_base.able_to_confirm_order_medical').id in user_obj.frontend_security_ids.ids:
                if book_obj.state_vendor == 'new_order':
                    book_obj.write({
                        'state_vendor': 'confirmed_order'
                    })
                else:
                    _logger.error('pnr has been confirm / refund')
                    return ERR.get_error(500, additional_message='order number already confirm')
            else:
                _logger.error('order number not found')
                return ERR.get_error(500, additional_message='order number not found')
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_result_api(self, req, context):
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
            #tanya jos perlu check context ngga
            if book_obj.agent_id.id == context.get('co_agent_id', -1) or \
                    self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids or \
                    book_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or \
                    book_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
                for rec in book_obj.provider_booking_ids:
                    for idx, pax in enumerate(rec.ticket_ids):
                        pax.ticket_number = req['passenger'][idx]['ticket_number']
            return ERR.get_no_error({
                'order_number': book_obj.name,
                'book_id': book_obj.id
            })
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_data_verif(self, req, context):
        try:
            passenger_obj = self.env['tt.reservation.passenger.medical'].search([('ticket_number','=',req['ticket_number']),('booking_id.carrier_name','ilike',req['test_type'])],limit=1)
            if passenger_obj:
                passenger_obj.update({
                    'name': "%s %s" % (req['first_name'], req['last_name']),
                    'first_name': req['first_name'],
                    'last_name': req['last_name'],
                    'gender': req['gender'],
                    'title': req['title'],
                    'birth_date': req['birth_date'],
                    'identity_number': req['identity_number'],
                    'phone_number': req['phone_number'],
                    'tempat_lahir': req['tempat_lahir'],
                    'address': req['address'],
                    'rt': req['rt'],
                    'rw': req['rw'],
                    'kabupaten': req['kabupaten'],
                    'kecamatan': req['kecamatan'],
                    'kelurahan': req['kelurahan'],
                    'ticket_number': req['ticket_number'],
                    'verify': True,
                    'verified_date': datetime.now(),
                    'verified_uid': context['co_uid'],
                })
                passenger_obj.booking_id.check_reservation_verif(context['co_uid'])

                data = {
                    'code': 9920,
                    'message': "%s\n\n%s" % (passenger_obj.name, self.env['tt.reservation.medical'].get_verified_summary())
                }
                ho_id = passenger_obj.booking_id.agent_id.ho_id.id
                self.env['tt.api.con'].send_request_to_gateway('%s/notification' % (self.env['tt.api.con'].url), data,
                                                               'notification_code', ho_id=ho_id)
                return ERR.get_no_error({
                    "transaction_code": req['ticket_number'],
                    "message": "success"
                })
            else:
                _logger.error('transaction_code not found')
                return ERR.get_error(500, additional_message='transaction_code not found')
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def check_reservation_verif(self, co_uid):##siapa yg melakukan
        verify=True
        for rec in self.passenger_ids:
            if rec.verify == False:
                verify = False
                break
        if verify:
            self.write({
                'state_vendor': 'verified',
                'verified_uid': co_uid,
                'verified_date': datetime.now()
            })
    #req
    # date from
    # date to
    def get_transaction_by_analyst_api(self,req,context):
        try:
            dom = [('test_datetime', '>=',req['date_from']),
                   ('test_datetime', '<=',req['date_to']),
                   ('provider_booking_ids.carrier_id','in',[
                       self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_home_care_antigen').id,
                       self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_home_care_pcr').id,
                   ]),
                   ('state','in',['issued','done']),
                   ('analyst_ids.user_id','=',context['co_uid']),
                   ('picked_timeslot_id','!=',False)]
            res = {}
            for rec in self.search(dom, order="test_datetime asc"):
                picked_timeslot = rec.test_datetime.strftime('%Y-%m-%d %H:%M')

                if picked_timeslot[:10] not in res:
                    res[picked_timeslot[:10]] = []

                res[picked_timeslot[:10]].append({
                    'order_number': rec.name,
                    'agent': rec.agent_id.name if rec.agent_id else '',
                    'adult': rec.adult,
                    'state': rec.state,
                    'origin': rec.origin_id.name,
                    'state_description': variables.BOOKING_STATE_STR[rec.state],
                    'test_address': rec.test_address,
                    'test_address_map_link': rec.test_address_map_link,
                    'time_test': picked_timeslot
                })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1012)

    def payment_medical_api(self,req,context):
        payment_res = self.payment_reservation_api('medical',req,context)
        return payment_res

    def _prepare_booking_api(self, booking_data, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_medical.tt_provider_type_medical')
        provider_obj = self.env['tt.provider'].sudo().search([('code', '=', booking_data['provider']), ('provider_type_id', '=', provider_type_id.id)])
        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', booking_data['carrier_code']), ('provider_type_id', '=', provider_type_id.id)])

        # "pax_type": "ADT",
        # "pax_count": 1
        # "amount": 150000,
        # "total_amount": 150000,
        # "foreign_amount": 150000,
        # "currency": "IDR",
        # "foreign_currency": "IDR",
        # "charge_code": "fare",
        # "charge_type": "FARE"

        #check apakah timeslot tersedia
        timeslot_write_data = self.env['tt.timeslot.medical'].search([('seq_id', 'in', booking_data['timeslot_list'])])
        for rec in timeslot_write_data:
            if not rec.get_availability(carrier_obj.code, booking_data['adult']):
                if rec.timeslot_type == 'drive_thru':
                    raise RequestException(1022,"<br/>\nJadwal Penuh. %sBisa dicoba tanggal/jam yang lain<br/>\nTimeslot is Full. %sPlease Try Other Date/Time" % ("Only %s Slot(s) Available or " % (rec.total_pcr_timeslot - rec.used_pcr_count) if rec.used_pcr_count < rec.total_pcr_timeslot else "","Only %s Slot(s) Available or " % (rec.total_pcr_timeslot - rec.used_pcr_count) if rec.used_pcr_count < rec.total_pcr_timeslot else ""))
                else:
                    raise RequestException(1022,"<br/>\nJadwal Penuh. Bisa dicoba tanggal/jam yang lain<br/>\nTimeslot is Full. Please Try Other Date/Time")

        #check drive thru atau tidak, menentukan hold date
        drive_thru = False
        if carrier_obj and carrier_obj.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_rs_nathos').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_poc').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_bali').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_mutasi').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_rs_nathos').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_poc').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_saliva_bali').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_rs_nathos').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_poc').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_tes_antibodi_rbd').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_antigen_nassal').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup1').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup2').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup3').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup4_male').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup4_female').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup5_male').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_medical_checkup5_female').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19_with_pcr').id,
                                              self.env.ref(
                                                  'tt_reservation_medical.tt_transport_carrier_medical_nathos_paket_screening_cvd19_urban_lifestyle').id
                                              ]:
            # hold_date = fields.Datetime.now().replace(hour=16,minute=30) + timedelta(days=8)
            hold_date = timeslot_write_data[0].datetimeslot.replace(hour=10, minute=0, second=0, microsecond=0)
            drive_thru = True
        else:
            hold_date = fields.Datetime.now() + timedelta(minutes=30)

        #kalau tidak ada timeslot dan dia drive thru maka di pilihkan jadwal drive thru hari itu, jika tidak ada maka di buatkan jadwal baru
        if not timeslot_write_data and drive_thru:
            timeslot_write_data = self.env['tt.timeslot.medical'].search([('timeslot_type', '=', 'drive_thru'), ('datetimeslot', '=', '%s 02:09:09' % datetime.now().strftime('%Y-%m-%d'))])
            if not timeslot_write_data:
                timeslot_write_data = self.env['create.timeslot.medical.wizard'].generate_drivethru_timeslot(datetime.now().strftime('%Y-%m-%d'))

        provider_vals = {
            'pnr': 1,
            'pnr2': 2,
            'state': 'booked',
            'booked_uid': context_gateway['co_uid'],
            'booked_date': fields.Datetime.now(),
            'hold_date': hold_date,
            'balance_due': booking_data['total'],
            'total_price': booking_data['total'],
            'sequence': 1,
            'provider_id': provider_obj and provider_obj.id or False,
            'carrier_id': carrier_obj and carrier_obj.id or False,
            'carrier_code': carrier_obj and carrier_obj.code or False,
            'carrier_name': carrier_obj and carrier_obj.name or False
        }

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
            'booked_date': fields.Datetime.now(),
            'hold_date': hold_date,
        }
        if booking_data['timeslot_type'] == 'fixed':
            booking_tmp.update({
                'picked_timeslot_id': timeslot_write_data and timeslot_write_data[0].id
            })
        return booking_tmp

    # April 24, 2020 - SAM
    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        # if all(rec.state == 'issued' for rec in self.provider_booking_ids):
        #     self.action_issued_medical(context)
        if all(rec.state == 'issued' for rec in self.provider_booking_ids):
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_medical(issued_req, context)
        elif all(rec.state == 'booked' for rec in self.provider_booking_ids):
            self.action_booked_api_medical(context)
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
            self.action_reverse_medical(context)
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

            # values = []
            for p_type,p_val in sc_value.items():
                for c_type,c_val in p_val.items():
                    # April 27, 2020 - SAM
                    curr_dict = {
                        'pax_type': p_type,
                        'booking_medical_id': self.id,
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

    def get_verified_summary(self):
        datetime_now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
        passenger_data = self.env['tt.reservation.passenger.medical'].search([('verify', '=', True),
                                                                          ('booking_id.carrier_name','ilike','KPCR'),
                                                                          ('verified_date', '>=',
                                                                           datetime_now_wib.replace(hour=0, minute=0, second=0,
                                                                                                    microsecond=0)),
                                                                          ('verified_date', '<=', datetime_now_wib)])
        verified_pcr_date = len(passenger_data.ids)

        passenger_data = self.env['tt.reservation.passenger.medical'].search([('verify', '=', True),
                                                                          ('booking_id.carrier_name','ilike','OPCR'),
                                                                          ('verified_date', '>=',
                                                                           datetime_now_wib.replace(hour=0, minute=0, second=0,
                                                                                                    microsecond=0)),
                                                                          ('verified_date', '<=', datetime_now_wib)])
        verified_pcr_priority_date = len(passenger_data.ids)

        passenger_data = self.env['tt.reservation.passenger.medical'].search([('verify', '=', True),
                                                                          ('booking_id.carrier_name', 'ilike', 'KATG'),
                                                                          ('verified_date', '>=',
                                                                           datetime_now_wib.replace(hour=0, minute=0,
                                                                                                    second=0,
                                                                                                    microsecond=0)),
                                                                          ('verified_date', '<=', datetime_now_wib)])

        verified_antigen_date = len(passenger_data.ids)

        passenger_data = self.env['tt.reservation.passenger.medical'].search([('verify', '=', True),
                                                                          ('booking_id.carrier_name','ilike','EPCR'),
                                                                          ('verified_date', '>=',
                                                                           datetime_now_wib.replace(hour=0, minute=0, second=0,
                                                                                                    microsecond=0)),
                                                                          ('verified_date', '<=', datetime_now_wib)])
        verified_pcr_express_date = len(passenger_data.ids)

        return 'MEDICAL Verified By Date:\nAntigen : %s\nPCR : %s\nPCR Priority : %s\nPCR Express: %s' % (verified_antigen_date,
                                                                                                      verified_pcr_date, verified_pcr_priority_date, verified_pcr_express_date)

    def multi_sync_verified_with_medical(self):
        for rec in self:
            rec.sync_verified_with_medical()

    def sync_verified_with_medical(self):
        if self.state_vendor != 'verified':
            for rec in self.passenger_ids:
                if rec.ticket_number:
                    medical_status_res = self.env['tt.medical.api.con'].sync_status_with_medical({
                        'carrier_code': self.carrier_name,
                        'ticket_number': rec.ticket_number,
                        'provider': self.provider_booking_ids[0].provider_id.code
                    })
                    if medical_status_res['error_code'] == 0:
                        if medical_status_res['response']['verified']:
                            rec.verify = medical_status_res['response']['verified']
                            rec.verified_date = datetime.now()
                            rec.verified_uid = self.env.user.id
                            self.check_reservation_verif(self.env.user.id)

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
        medical_ticket_id = self.env.ref('tt_report_common.action_report_printout_reservation_medical') # Vin 2021-06-15 Report sementara sama

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = medical_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = medical_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Medical Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Medical Ticket',
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
        medical_ticket_id = self.env.ref('tt_report_common.action_report_printout_reservation_medical') # Vin 2021-06-15 Report sementara sama

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = medical_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = medical_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'medical Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'medical Ticket',
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
        medical_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_medical')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = medical_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = medical_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Medical HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Medical HO Invoice',
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
        medical_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_medical') # Vin 2021-06-15 Report sementara sama

        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = medical_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = medical_itinerary_id.render_qweb_pdf(data=pdf_report)
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
        medical_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_medical') # Vin 2021-06-15 Report sementara sama

        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = medical_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = medical_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Medical Itinerary %s (Price).pdf' % book_obj.name,
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
        if self.carrier_name == 'NHDTKPCRR':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_rs_nathos_information')
        elif self.carrier_name == 'NHDTKPCRP':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_poc_information')
        elif self.carrier_name == 'NHDTKPCRB':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_bali_information')
        elif self.carrier_name == 'NHDTMPCR':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_mutasi_information')
        elif self.carrier_name == 'NHDTSPCRR':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_saliva_rs_nathos_information')
        elif self.carrier_name == 'NHDTSPCRP':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_saliva_poc_information')
        elif self.carrier_name == 'NHDTSPCRB':
            template_obj = self.env.ref('tt_reservation_medical.nathos_pcr_saliva_bali_information')
        elif self.carrier_name == 'NHDTKATGR':
            template_obj = self.env.ref('tt_reservation_medical.nathos_antigen_rs_nathos_information')
        elif self.carrier_name == 'NHDTKATGP':
            template_obj = self.env.ref('tt_reservation_medical.nathos_antigen_poc_information')
        elif self.carrier_name == 'NHDTKKARBD':
            template_obj = self.env.ref('tt_reservation_medical.nathos_tes_antibodi_rbd_information')
        elif self.carrier_name == 'NHDTNATG':
            template_obj = self.env.ref('tt_reservation_medical.nathos_antigen_nassal_information')
        elif self.carrier_name == 'NHDTKMCU1':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup1_information')
        elif self.carrier_name == 'NHDTKMCU2':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup2_information')
        elif self.carrier_name == 'NHDTKMCU3':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup3_information')
        elif self.carrier_name == 'NHDTKMCU4M':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup4_male_information')
        elif self.carrier_name == 'NHDTKMCU4F':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup4_female_information')
        elif self.carrier_name == 'NHDTKMCU5M':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup5_male_information')
        elif self.carrier_name == 'NHDTKMCU5F':
            template_obj = self.env.ref('tt_reservation_medical.nathos_checkup5_female_information')
        elif self.carrier_name == 'NHDTKPSC':
            template_obj = self.env.ref('tt_reservation_medical.nathos_paket_screening_cvd19_information')
        elif self.carrier_name == 'NHDTKPSCWPCR':
            template_obj = self.env.ref('tt_reservation_medical.nathos_paket_screening_cvd19_with_pcr_information')
        elif self.carrier_name == 'NHDTKPSCUL':
            template_obj = self.env.ref('tt_reservation_medical.nathos_paket_screening_cvd19_urban_lifestyle_information')

        return template_obj.html

    def get_terms_conditions_email_old(self):
        terms_txt = "<u><b>Terms and Conditions</b></u><br/>"
        terms_txt += "1. Payment must be made in advance.<br/>"
        if self.carrier_name in ['NHDTKPCR', 'NHDTKPCR24']:
            terms_txt += "<ul>"
            terms_txt += "<li>For PCR Test participants, it is recommended to immediately complete online payment via BCA VA or MANDIRI BANK VA so your quota can be secured.</li>"
            terms_txt += "<li>If a participant's payment has not been complete and we ran out of quota, the participant can issue a Re-Order for the next day or any other available test schedules.</li>"
            terms_txt += "</ul>"
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
        terms_txt += "<li>You can add any participants as long as the test fee for that participant is paid in advance</li>"
        terms_txt += "</ul>"
        terms_txt += "6. Reduction of participants refers to the Cancellation Policy.<br/>"
        if self.carrier_name in ['NHDTKPCR', 'NHDTKPCR24']:
            terms_txt += "7. Under normal circumstances, test results will be released by National Hospital around 12-24 hours after the test. Test result could be delayed up to 48 hours during high volume condition.<br/>"
        else:
            terms_txt += "7. Under normal circumstances, test results will be sent via Whatsapp by National Hospital around 30-120 minutes after the test.<br/>"
        terms_txt += "8. In case our nurses/officers do not come for the scheduled test, you can file a complaint at most 24 hours after the supposedly test schedule.<br/>"
        if self.carrier_name in ['NHDTKATG', 'NHDTKATG24']:
            terms_txt += "9. If you have registered online for Drive Thru Test, you must arrive at the test location at most 15:30/16:00 WIB during the scheduled test date (depends on the queue length), otherwise the test will have to be done the next day.<br/>"
            terms_txt += "10. Our operational hours: Monday - Saturday (08:00 - 16:00 WIB). The gate will be closed at 15:00 WIB. However, any participants that have arrived at the test location will still be served according to our terms and conditions."
        return terms_txt

    def get_aftersales_desc(self):
        desc_txt = 'PNR: ' + self.pnr + '<br/>'
        if self.provider_booking_ids[0].carrier_id.id in [self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr').id, self.env.ref('tt_reservation_medical.tt_transport_carrier_medical_nathos_pcr_24_hours').id]:
            desc_txt += 'Test Type: PCR TEST\n'
        else:
            desc_txt += 'Test Type: ANTIGEN TEST\n'
        desc_txt += 'Test Address: ' + self.test_address + '<br/>'
        desc_txt += 'Test Date/Time: ' + self.picked_timeslot_id.get_datetimeslot_str(self.provider_booking_ids[0].carrier_id.code) + '<br/>'
        return desc_txt

    def get_timeslot_for_email(self):
        return self.picked_timeslot_id.get_datetimeslot_str(self.provider_booking_ids[0].carrier_id.code)
