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

_logger = logging.getLogger(__name__)


class ReservationAirline(models.Model):

    _name = "tt.reservation.airline"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation Airline"

    direction = fields.Selection(variables.JOURNEY_DIRECTION, string='Direction', default='OW', required=True, readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True, states={'draft': [('readonly', False)]})
    sector_type = fields.Char('Sector', readonly=True, compute='_compute_sector_type', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_airline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.airline', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    provider_booking_ids = fields.One2many('tt.provider.airline', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    journey_ids = fields.One2many('tt.journey.airline', 'booking_id', 'Journeys', readonly=True, states={'draft': [('readonly', False)]})
    segment_ids = fields.One2many('tt.segment.airline', 'booking_id', string='Segments',
                                  readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default= lambda self: self.env.ref('tt_reservation_airline.tt_provider_type_airline'))
    split_from_resv_id = fields.Many2one('tt.reservation.airline', 'Splitted From', readonly=1)
    split_to_resv_ids = fields.One2many('tt.reservation.airline', 'split_from_resv_id', 'Splitted To', readonly=1)
    split_uid = fields.Many2one('res.users', 'Splitted by', readonly=True)
    split_date = fields.Datetime('Splitted Date', readonly=True)

    is_get_booking_from_vendor = fields.Boolean('Get Booking From Vendor')
    printout_ticket_original_ids = fields.Many2many('tt.upload.center', 'reservation_airline_attachment_rel', 'ori_ticket_id',
                                       'attachment_id', string='Attachments', domain=['|', ('active', '=', True), ('active', '=', False)])
    is_hold_date_sync = fields.Boolean('Hold Date Sync', compute='compute_hold_date_sync', default=True, store=True)

    flight_number_name = fields.Char('List of Flight number', readonly=True, compute='_compute_flight_number')

    third_party_ids = fields.One2many('tt.third.party.webhook', 'booking_airline_id', 'Third Party Webhook', readonly=True)

    @api.multi
    @api.depends('provider_booking_ids.is_hold_date_sync')
    def compute_hold_date_sync(self):
        for rec in self:
            is_hold_date_sync = all(prov.is_hold_date_sync for prov in rec.provider_booking_ids)
            rec.update({
                'is_hold_date_sync': is_hold_date_sync
            })

    def compute_journey_code(self):
        objs = self.env['tt.reservation.airline'].sudo().search([])
        for rec in objs:
            for journey in rec.journey_ids:
                journey._compute_journey_code()

    def get_form_id(self):
        return self.env.ref("tt_reservation_airline.tt_reservation_airline_form_views")

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

    @api.depends('provider_booking_ids')
    def _compute_flight_number(self):
        for rec in self:
            flight_number_name = ''
            for provider_booking_obj in rec.provider_booking_ids:
                for journey_obj in provider_booking_obj.journey_ids:
                    for segment_obj in journey_obj.segment_ids:
                        if flight_number_name:
                            flight_number_name += ';'
                        flight_number_name += "%s%s" % (segment_obj.carrier_code, segment_obj.carrier_number)

            rec.flight_number_name = flight_number_name


    @api.depends('segment_ids')
    def _compute_sector_type(self):
        for rec in self:
            destination_country_list = []
            for segment in rec.segment_ids:
                destination_country_list.append(segment.origin_id.country_id.id)
                destination_country_list.append(segment.destination_id.country_id.id)
            destination_set = len(set(destination_country_list))

            if destination_set > 1:
                rec.sector_type = "International"
            elif destination_set == 1:
                rec.sector_type = "Domestic"

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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 109')
        for rec in self:
            rec.state = 'draft'


    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 110')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 111')
        for rec in self:
            rec.state = 'issued'

    def action_booked_api_airline(self,context,pnr_list=[],hold_date=False,is_split=False):
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
            write_values['hold_date'] = hold_date
        if pnr_list:
            write_values['pnr'] = ', '.join(pnr_list)
        # END
        if self.booked_date and is_split:
            write_values.pop('booked_date')
            write_values.pop('booked_uid')

        # if write_values['pnr'] == '':
        #     write_values.pop('pnr')

        self.write(write_values)

        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_airline')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'airline',
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

    def action_issued_api_airline(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
            'is_split': req.get('is_split'),
            'is_mail': req.get('is_mail')
        }
        self.action_issued_airline(data)

    def action_reverse_airline(self,context):
        self.write({
            'state':  'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_refund_failed_airline(self,context):
        self.write({
            'state':  'refund_failed',
        })

    def action_issued_airline(self,data):
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
        if self.issued_date and data.get('is_split'):
            values.pop('issued_date')
            values.pop('issued_uid')
        self.write(values)

        try:
            if self.agent_type_id.is_send_email_issued and data['is_mail']:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_airline')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'airline',
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

    def action_partial_booked_api_airline(self,context,pnr_list=[],hold_date=False,is_split=False):
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
        if self.booked_date and is_split:
            values.pop('booked_date')
            values.pop('booked_uid')

        self.write(values)

    def action_partial_issued_api_airline(self,co_uid,customer_parent_id,is_split=False):
        values = {
            'state': 'partial_issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        }
        if self.issued_date and is_split:
            values.pop('issued_date')
            values.pop('issued_uid')
        self.write(values)

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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 112')
        super(ReservationAirline, self).action_cancel()
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

    @api.one
    def action_reroute(self): ##nama nanti diganti reissue
        self.state = 'reroute'

    @api.one
    def create_refund(self):
        # vals = {
        #     'transport_booking_id': self.id,
        #     'expected_amount': self.total,
        #     'agent_id': self.agent_id.id,
        #     'sub_agent_id': self.sub_agent_id.id,
        #     'contact_id': self.contact_id.id,
        #     'currency_id': self.currency_id.id,
        #     'transaction_type': self.transport_type,
        #     'pnr': self.pnr,
        #     'notes': 'Passengers :\n'
        # }
        # notes = ''
        # list_val = []
        # list_val2 = []
        # for psg in self.passenger_ids:
        #     notes += '%s %s\n' % (psg.first_name, psg.last_name)
        #     serv_charges = self.sale_service_charge_ids.filtered(lambda x: x.charge_code in ['fare', 'tax'] and
        #                                                                    x.pax_type == psg.pax_type)
        #     vals1 = {
        #         'passenger_id': psg.id,
        #         # 'segment_id': segment_id.id,
        #         'ticket_amount': sum(item['amount'] for item in serv_charges),
        #     }
        #     list_val.append(vals1)
        #
        # for segment_id in self.segment_ids:
        #     vals2 = {
        #         'refund_id': self.id,
        #         'pnr': segment_id.pnr,
        #         'carrier_id': segment_id.carrier_id.id,
        #         'carrier_name': segment_id.carrier_name,
        #         'origin_id': segment_id.origin_id.id,
        #         'destination_id': segment_id.destination_id.id,
        #         'departure_date': segment_id.departure_date,
        #         'arrival_date': segment_id.arrival_date,
        #     }
        #     list_val2.append(vals2)
        #
        # vals['notes'] += notes
        # refund_obj = self.env['tt.refund'].create(vals)
        # for value in list_val:
        #     value['refund_id'] = refund_obj.id
        #     self.sudo().env['tt.refund.line'].create(value)
        # for value in list_val2:
        #     value['refund_id'] = refund_obj.id
        #     self.sudo().env['tt.refund.segment'].create(value)
        # self.refund_id = refund_obj
        self.state = 'refund'


    def action_sync_date(self):
        # api_context = {
        #     'co_uid': self.env.user.id,
        # }
        # if not self.provider_booking_ids:
        #     raise UserError("System not detecting your provider")
        # provider = self.provider_booking_ids[0].provider
        # req_data = {
        #     'booking_id': self.id,
        #     'pnr': self.pnr,
        #     'provider': provider,
        # }
        # res = API_CN_AIRLINES.SYNC_HOLD_DATE(req_data, api_context)
        # if res['error_code'] != 0:
        #     raise UserError(res['error_msg'])
        # else:
        #     hold_date = res['response']['hold_date']
        #     if hold_date:
        #         for rec in self.provider_booking_ids:
        #             rec['hold_date'] = hold_date
        #         self.hold_date = hold_date
        pass

    def create_booking_airline_api(self, req, context):
        # req = copy.deepcopy(self.param_global)
        # req = self.hardcode_req_cr8_booking
        # context = self.hardcode_context

        _logger.info("Create\n" + json.dumps(req))
        search_RQ = req['searchRQ']
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        fare_rule_provider = req.get('fare_rule_provider', [])
        # April 20, 2020 - SAM
        # schedules = req['schedules']
        booking_states = req['booking_state_provider']
        is_force_issued = req['force_issued']
        is_halt_process = req.get('halt_process', False)
        # END

        ## 31 AGUSTUS 2022 - IVAN
        ## RETRIEVE DATA TEMPORARY IDENTITY (identity_from_api) JIKA ADA UNTUK DI SIMPAN DI BACKEND
        for rec_pax in passengers:
            if rec_pax.get('identity_from_api'):
                rec_pax['identity'] = rec_pax['identity_from_api']

        try:
            values = self._prepare_booking_api(search_RQ,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            #                                               # 'identity_type','identity_number',
            #                                               # 'identity_country_of_issued_id','identity_expdate'])
            # list_passenger_id = self.create_passenger_api(list_customer_obj,self.env['tt.reservation.passenger.airline'])

            list_passenger_value = self.create_passenger_value_api(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
                is_valid_identity = True
                if passengers[idx].get('identity'): ## DARI FRONTEND / BTBO JIKA TANPA IDENTITY TIDAK ADA KEY IDENTITY
                    is_valid_identity = passengers[idx]['identity'].get('is_valid_identity', True)
                rec[2].update({
                    'customer_id': list_customer_id[idx].id,
                    'is_valid_identity': is_valid_identity,
                })
                if passengers[idx].get('description'):
                    rec[2].update({
                        'description': passengers[idx]['description']
                    })

                if passengers[idx].get('riz_text'):
                    rec[2].update({
                        'riz_text': passengers[idx]['riz_text']
                    })

            for psg in list_passenger_value:
                util.pop_empty_key(psg[2], ['is_valid_identity'])

            ## 22 JUN 2023 - IVAN
            ## GET CURRENCY CODE
            currency = ''
            currency_obj = None
            for provider in booking_states:
                for journey in provider['journeys']:
                    for segment in journey['segments']:
                        for fare in segment['fares']:
                            for svc in fare['service_charges']:
                                if not currency:
                                    currency = svc['currency']
            if currency:
                currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                # if currency_obj:
                #     book_obj.currency_id = currency_obj.id
            contact_phone_obj = contact_obj.phone_ids and contact_obj.phone_ids.sorted(lambda x: x.last_updated_time)[-1] or False
            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_title': contacts[0]['title'],
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_phone_obj and "%s - %s" % (contact_phone_obj.calling_code,contact_phone_obj.calling_number) or '-',
                'passenger_ids': list_passenger_value,
                # April 21, 2020 - SAM
                'is_force_issued': is_force_issued,
                'is_halt_process': is_halt_process,
                'currency_id': currency_obj.id if currency and currency_obj else self.env.user.company_id.currency_id.id
                # END
            })

            book_obj = self.create(values)


            if context.get('co_job_position_rules'):
                if context['co_job_position_rules'].get('callback'):
                    if context['co_job_position_rules']['callback'].get('source'):
                        if context['co_job_position_rules']['callback']['source'] == 'ptr':
                            third_party_data = copy.deepcopy(context['co_job_position_rules']['airline'])
                            third_party_data.update({
                                "callback": context['co_job_position_rules']['callback']
                            })
                            webhook_obj = self.env['tt.third.party.webhook'].create({
                                "third_party_provider": context['co_job_position_rules']['callback']['source'],
                                "third_party_data": json.dumps(third_party_data)
                            })
                            book_obj.update({
                                "third_party_ids": [(4, webhook_obj.id)]
                            })

            provider_ids, name_ids = book_obj._create_provider_api(booking_states, context, fare_rule_provider)

            # June 4, 2020 - SAM
            # Create passenger frequent flyer pada reservasi (di create setelah object passenger dan provider tercreate
            # Karena dibutuhkan provider id saat create ff dan sementara schedule id disamakan dengan array provider
            for prov_idx, prov in enumerate(provider_ids):
                for psg_idx, psg in enumerate(passengers):
                    if not psg.get('ff_numbers') or type(psg['ff_numbers']) != list:
                        continue

                    for ff in psg['ff_numbers']:
                        if ff['schedule_id'] != prov_idx:
                            continue

                        psg_obj = book_obj.passenger_ids[psg_idx]
                        name = '%s %s' % (psg_obj.first_name, psg_obj.last_name)
                        name = name.strip()
                        ff_values = {
                            'name': name,
                            'first_name': psg_obj.first_name,
                            'last_name': psg_obj.last_name,
                            'ff_number': ff['ff_number'],
                            'ff_code': ff['ff_code'],
                            'schedule_id': ff['schedule_id'],
                            'passenger_id': psg_obj.id,
                            'provider_id': prov.id,
                        }
                        if ff['ff_code']:
                            loyalty_id = self.env['tt.loyalty.program'].sudo().get_id(ff_values['ff_code'])
                            if loyalty_id:
                                ff_values['loyalty_program_id'] = loyalty_id
                        psg_obj.frequent_flyer_ids.create(ff_values)
            # END

            # May 6, 2020 - SAM
            for idx, psg in enumerate(book_obj.passenger_ids):
                passengers[idx]['passenger_id'] = psg.id
            # if is_force_issued:
            #     if not is_halt_process:
            #         for vendor_obj in provider_ids:
            #             vendor_obj.action_issued_api_airline(context)
            #         req['book_id'] = book_obj.id
            #         book_obj.check_provider_state(context, req=req)
            #         [vendor_obj.write({'state': 'draft'}) for vendor_obj in provider_ids]
            #         book_obj.write({'state': 'draft'})
            #     else:
            #         for vendor_obj in provider_ids:
            #             vendor_obj.write({'state': 'halt_issued'})
            #         book_obj.write({
            #             'state': 'halt_issued',
            #             'hold_date': datetime.now() + timedelta(minutes=30),
            #         })
            if is_halt_process:
                if is_force_issued:
                    for vendor_obj in provider_ids:
                        vendor_obj.action_halt_issued_api_airline(context)
                else:
                    for vendor_obj in provider_ids:
                        vendor_obj.action_halt_booked_api_airline(context)

            book_obj.calculate_service_charge()
            book_obj.check_provider_state(context)
            # END

            response_provider_ids = []
            for provider in provider_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })

            book_obj.write({
                'provider_name': ','.join(name_ids['provider']),
                'carrier_name': ','.join(name_ids['carrier']),
                'arrival_date': provider_ids[-1].arrival_date[:10]
            })
            # book_obj._compute_flight_number()
            # book_obj._compute_total_pax()
            #channel repricing upsell
            if req.get('repricing_data'):
                req['repricing_data']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data'], context)
            # channel repricing upsell SSR
            if req.get('repricing_data_ssr'):
                req['repricing_data_ssr']['order_number'] = book_obj.name
                self.env['tt.reservation'].channel_pricing_api(req['repricing_data_ssr'], context)

            if req.get('repricing_data') or req.get('repricing_data_ssr'):
                book_obj.create_svc_upsell()

            ##pengecekan segment kembar airline dengan nama passengers
            if not req.get("bypass_psg_validator",False):
                self.psg_validator(book_obj)
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

    def psg_validator(self,book_obj):
        ho_agent_obj = book_obj.agent_id.ho_id
        for segment in book_obj.segment_ids:
            rule = self.env['tt.limiter.rule'].sudo().search([('carrier_code', '=', segment.carrier_code), ('provider_type_id.code', '=', book_obj.provider_type_id.code), ('ho_id','=',ho_agent_obj.id)])

            if rule:
                limit = rule.rebooking_limit
                rule_check_type = rule.passenger_check_type
            else:
                continue

            if rule_check_type == 'passenger' or rule_check_type == False: ## False jika tidak ter isi
                for name in segment.booking_id.passenger_ids:
                    if name.is_valid_identity:
                        search_query = [('segment_code','=',segment.segment_code),
                                        '|',
                                        ('booking_id.passenger_ids.identity_number','=ilike',name.identity_number),
                                        ('booking_id.passenger_ids.name','=ilike',name.name)]
                    else:
                        search_query = [('segment_code','=',segment.segment_code),
                                        ('booking_id.passenger_ids.name','=ilike',name.name)]

                    found_segments = self.env['tt.segment.airline'].search(search_query,order='id DESC')

                    valid_segments = found_segments.filtered(lambda x: x.booking_id.state in ['booked', 'issued', 'cancel2', 'fail_issue', 'void', 'cancel'])
                    # for seg in found_segments:
                    #     try:
                    #         curr_state = seg.state
                    #     except:
                    #         curr_state = 'booked'
                    #         _logger.error("Passenger Validator Cache Miss Error")
                    #
                    #     if curr_state in ['booked', 'issued', 'cancel2', 'fail_issue']:
                    #         valid_segments.append(seg)

                    safe = False

                    if len(valid_segments) < limit:
                        safe = True
                    else:
                        for idx,valid_segment in enumerate(valid_segments[:limit]):
                            if valid_segment.booking_id.state == 'issued':
                                safe=True
                                break

                    if not safe:
                        ## get HO agent
                        ho_agent_obj = None
                        if book_obj.agent_id:
                            ho_agent_obj = book_obj.agent_id.ho_id
                        # whitelist di sini
                        dom = [('name', 'ilike', name.name), ('chances_left', '>', 0)]
                        if ho_agent_obj:
                            dom.append(('ho_id','=', ho_agent_obj.id))
                        whitelist_name = self.env['tt.whitelisted.name'].sudo().search(dom, limit=1)

                        if whitelist_name:
                            whitelist_name.chances_left -= 1
                            return True

                        dom = [('passport','=',name.identity_number),('chances_left','>',0)]
                        if ho_agent_obj:
                            dom.append(('ho_id', '=', ho_agent_obj.id))
                        whitelist_passport = self.env['tt.whitelisted.passport'].sudo().search(dom, limit=1)

                        if whitelist_passport:
                            whitelist_passport.chances_left -= 1
                            return True

                        raise RequestException(1026,additional_message="Passenger validator failed on %s because of rebooking with same name and same route or same identity number and same route." % (name.name))
            elif rule_check_type == 'contact':
                search_query = [('segment_code', '=', segment.segment_code),
                                ('booking_id.contact_id', '=', book_obj.contact_id.id),
                                ('booking_id.state', '=', 'booked')]
                valid_segments = self.env['tt.segment.airline'].search(search_query, order='id DESC')

                total_pax_count = 0
                for valid_segment in valid_segments:
                    total_pax_count += valid_segment.booking_id.elder
                    total_pax_count += valid_segment.booking_id.adult
                    total_pax_count += valid_segment.booking_id.child
                    total_pax_count += valid_segment.booking_id.infant

                if total_pax_count > limit:
                    raise RequestException(1026,additional_message="Contact Validator failed because of rebooking with the same contact info.")



    def update_pnr_provider_airline_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        _logger.info("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.airline'].browse(req['book_id'])
            elif req.get('order_number'):
                book_obj = self.env['tt.reservation.airline'].search([('name', '=', req['order_number'])])
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

            # November 29, 2022 - SAM
            resv_passenger_number_dict = {}
            for psg in book_obj.passenger_ids:
                key_number = str(psg.sequence)
                resv_passenger_number_dict[key_number] = psg
            # END

            for provider in req['provider_bookings']:
                # December 31, 2021 - SAM
                # if 'error_code' not in provider or provider['error_code'] != 0:
                if 'error_code' in provider and provider['error_code'] != 0:
                    # January 18, 2022 - SAM
                    # Update mekanisme kalau fail saat commit booking
                    provider_info = ''
                    if provider.get('pnr'):
                        provider_info = 'PNR : %s' % provider['pnr']
                    elif provider.get('provider_id'):
                        provider_info = 'Provider ID : %s' % provider['provider_id']
                    elif provider.get('sequence'):
                        provider_info = 'Sequence : %s' % provider['sequence']
                    _logger.error('Update info skipped, %s' % (provider_info))

                    if provider.get('provider_id'):
                        provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                        # Sementara flow akan dibuat apabila status draft agar trigger perubahan status
                        # Untuk else komen dulu karena setiap ada error saat sync booking akan tercatat pada historynya
                        if provider.get('pnr') or provider.get('pnr2'):
                            provider_obj.write({
                                'pnr': provider.get('pnr', ''),
                                'pnr2': provider.get('pnr2', ''),
                                'reference': provider.get('reference', ''),
                            })

                        if provider_obj.state == 'draft':
                            if provider['status'] == 'FAIL_BOOKED':
                                provider_obj.action_failed_booked_api_airline(provider.get('error_code', -1), provider.get('error_msg', ''))
                                any_provider_changed = True
                            elif provider['status'] == 'FAIL_ISSUED':
                                provider_obj.action_failed_issued_api_airline(provider.get('error_code', -1),provider.get('error_msg', ''))
                                any_provider_changed = True
                            elif provider['status'] == 'HALT':
                                provider_obj.action_halt_booked_api_airline(context, provider.get('error_code', -1),provider.get('error_msg', ''))
                                book_obj.is_halt_process = True
                                any_provider_changed = True
                            # else:
                            #     provider_obj.write({
                            #         'error_history_ids': [(0, 0, {
                            #             'res_model': provider_obj._name,
                            #             'res_id': provider_obj.id,
                            #             'error_code': provider['error_code'],
                            #             'error_msg': provider['error_msg']
                            #         })]
                            #     })
                        elif provider_obj.state == 'halt_booked':
                            provider_obj.write({
                                'error_history_ids': [(0, 0, {
                                    'res_model': provider_obj._name,
                                    'res_id': provider_obj.id,
                                    'error_code': provider['error_code'],
                                    'error_msg': provider['error_msg']
                                })]
                            })
                    # END
                    continue
                # END
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                # book_status.append(provider['status'])

                # November 29, 2022 - SAM
                if provider['status'] in ['BOOKED', 'ISSUED']:
                    if provider.get('passengers'):
                        provider['passengers'] = util.match_passenger_data(provider['passengers'], book_obj.passenger_ids)
                # END

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    # default_hold_date = datetime.now().replace(microsecond=0) + timedelta(minutes=30)
                    # curr_hold_date = datetime.strptime(util.get_without_empty(provider,'hold_date',str(default_hold_date)), '%Y-%m-%d %H:%M:%S')
                    # if curr_hold_date == default_hold_date:
                    #     provider['hold_date'] = str(curr_hold_date)
                    # if curr_hold_date < hold_date:
                    #     hold_date = curr_hold_date
                    # if provider_obj.state == 'booked' and hold_date == provider_obj.hold_date:
                    #     continue
                    self.update_pnr_booked(provider_obj,provider,context)
                    try:
                        book_obj.update_journey(provider)
                    except:
                        _logger.error('Except Error update journey, %s' % traceback.format_exc())
                    any_provider_changed = True
                    # November 29, 2022 - SAM
                    if provider.get('passengers'):
                        provider_obj.update_ticket_api(provider['passengers'])
                        provider_obj.sudo().delete_passenger_fees()
                        for psg in provider['passengers']:
                            key = str(psg['passenger_number'])
                            if key not in resv_passenger_number_dict:
                                continue
                            psg_obj = resv_passenger_number_dict[key]
                            psg_obj.create_ssr(psg['fees'], provider_obj.pnr, provider_obj.id, is_create_service_charge=False)
                    # END
                elif provider['status'] == 'ISSUED' and not provider.get('error_code'):
                    # May 20, 2020 - SAM
                    # Testing di comment
                    # # if req.get('force_issued'):
                    # if provider_obj.state != 'booked':
                    #     self.update_pnr_booked(provider_obj,provider,context)
                    # END

                    # May 13, 2020 - SAM
                    # if provider.get('pnr', '') != provider_obj.pnr:
                    #     provider_obj.write({'pnr': provider['pnr']})
                    #     for sc in provider_obj.cost_service_charge_ids:
                    #         sc.description = provider['pnr']
                    #     any_pnr_changed = True
                    # END

                    #action issued dan create ticket number
                    # Apabila status sudah issued, biasanya connector tidak melakukan proses sehingga variabel passengers tidak ada
                    if 'passengers' in provider:
                        provider_obj.update_ticket_api(provider['passengers'])

                    # October 12, 2020 - SAM
                    # Hanya akan melakukan update ticket apabila state sebelumnya adalah issued
                    if provider_obj.state == 'issued':
                        continue
                    # END

                    # May 20, 2020 - SAM
                    # provider_obj.action_issued_api_airline(context)
                    provider_obj.action_issued_api_airline(provider, context)
                    # END
                    any_provider_changed = True

                    # November 29, 2022 - SAM
                    try:
                        book_obj.update_journey(provider)
                    except:
                        _logger.error('Except error Update journey, %s' % traceback.format_exc())

                    if provider.get('passengers'):
                        provider_obj.sudo().delete_passenger_fees()
                        for psg in provider['passengers']:
                            key = str(psg['passenger_number'])
                            if key not in resv_passenger_number_dict:
                                continue
                            psg_obj = resv_passenger_number_dict[key]
                            psg_obj.create_ssr(psg['fees'], provider_obj.pnr, provider_obj.id, is_create_service_charge=False)
                    # END

                    ## 23 Mar 2021, di pindahkan ke gateway tidak lagi sync sendiri
                    # #get balance vendor
                    # if provider_obj.provider_id.track_balance:
                    #     try:
                    #         # print("GET BALANCE : "+str(self.env['tt.airline.api.con'].get_balance(provider_obj.provider_id.code)['response']['balance']))
                    #         provider_obj.provider_id.sync_balance()
                    #     except Exception as e:
                    #         _logger.error(traceback.format_exc())
                elif provider['status'] == 'FAIL_BOOKED':
                    provider_obj.action_failed_booked_api_airline(provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_airline(provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'CANCELLED':
                    provider_obj.action_cancel_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'REFUND_PENDING':
                    provider_obj.action_refund_pending_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'CANCEL_PENDING':
                    provider_obj.action_cancel_pending_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID':
                    provider_obj.action_void_api_airline(provider, context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID_PENDING':
                    provider_obj.action_void_pending_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'REFUND':
                    provider_obj.action_refund_api_airline(provider, context)
                    any_provider_changed = True
                elif provider['status'] == 'VOID_FAILED':
                    provider_obj.action_failed_void_api_airline(provider.get('error_code', -1), provider_obj['error_msg'])
                    any_provider_changed = True
                elif provider['status'] == 'REFUND_FAILED':
                    provider_obj.action_refund_failed_api_airline(provider.get('error_code', -1), provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED':
                    provider_obj.action_rescheduled_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED_PENDING':
                    provider_obj.action_rescheduled_pending_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'RESCHEDULED_FAILED':
                    provider_obj.action_failed_rescheduled_api_airline(provider.get('error_code', -1), provider.get('error_msg', ''))
                    any_provider_changed = True
                elif provider['status'] == 'REISSUE':
                    provider_obj.action_reissue_api_airline(context)
                    any_provider_changed = True
                elif provider['status'] == 'HALT':
                    provider_obj.action_halt_booked_api_airline(context, provider.get('error_code', -1),provider.get('error_msg', ''))
                    any_provider_changed = True

            # for rec in book_obj.provider_booking_ids:
            #     if rec.pnr:
            #         pnr_list.append(rec.pnr)

            if any_provider_changed:
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

    # July 2, 2021 - SAM
    # Ubah fungsi update journey
    # def update_journey(self, provider):
    #     if 'sell_reschedule' in provider:
    #         departure_date = ''
    #         arrival_date = ''
    #         for idx, provider_obj in enumerate(self.provider_booking_ids):
    #             if provider_obj.pnr == provider['pnr']:
    #                 for idy, journey_obj in enumerate(provider_obj.journey_ids):
    #                     for idz, segment_obj in enumerate(journey_obj.segment_ids):
    #                         segment_obj.segment_code = provider['journeys'][idy]['segments'][idz]['segment_code']
    #                         segment_obj.carrier_code = provider['journeys'][idy]['segments'][idz]['carrier_code']
    #                         segment_obj.carrier_number = provider['journeys'][idy]['segments'][idz]['carrier_number']
    #                         segment_obj.arrival_date = provider['journeys'][idy]['segments'][idz]['arrival_date']
    #                         segment_obj.departure_date = provider['journeys'][idy]['segments'][idz]['departure_date']
    #                         segment_obj.class_of_service = provider['journeys'][idy]['segments'][idz]['class_of_service']
    #                         for count, leg_obj in enumerate(segment_obj.leg_ids):
    #                             if provider['journeys'][idy]['segments'][idz].get('legs'):
    #                                 leg_obj.leg_code = provider['journeys'][idy]['segments'][idz]['legs'][count]['leg_code']
    #                                 leg_obj.arrival_date = provider['journeys'][idy]['segments'][idz]['legs'][count]['arrival_date']
    #                                 leg_obj.departure_date = provider['journeys'][idy]['segments'][idz]['legs'][count]['departure_date']
    #                     journey_obj.journey_code = "%s,%s,%s,%s,%s,%s,%s" % (journey_obj.segment_ids[0].carrier_code, journey_obj.segment_ids[0].carrier_number, journey_obj.segment_ids[0].origin_id.code, journey_obj.segment_ids[len(journey_obj.segment_ids)-1]['departure_date'], journey_obj.segment_ids[0].destination_id.code, journey_obj.segment_ids[0]['arrival_date'], journey_obj.segment_ids[0].provider_id.code)
    #                     journey_obj.arrival_date = journey_obj.segment_ids[0]['arrival_date']
    #                     journey_obj.departure_date = journey_obj.segment_ids[len(journey_obj.segment_ids)-1]['departure_date']
    #                 provider_obj.arrival_date = provider_obj.journey_ids[len(provider_obj.journey_ids)-1]['arrival_date']
    #                 provider_obj.departure_date = provider_obj.journey_ids[0]['departure_date']
    #             if idx == 0:
    #                 departure_date = provider_obj.departure_date[:10]
    #                 arrival_date = provider_obj.arrival_date[:10]
    #             else:
    #                 arrival_date = provider_obj.departure_date[:10]
    #         self.departure_date = departure_date
    #         if self.direction != 'OW':
    #             self.arrival_date = arrival_date
    #
    #         #add seat here
    #
    #         # if self.direction != 'OW':
    #         #     if len(self.provider_booking_ids) == 0:
    #         #         self.arrival_date = self.provider_booking_ids[len(self.provider_booking_ids)-1].arrival_date[:10]
    #         #     else:
    #         #         self.provider_booking_ids[len(self.provider_booking_ids) - 1].departure_date[:10]

    def update_journey(self, provider):
        if 'sell_reschedule' in provider:
            departure_date = ''
            arrival_date = ''
            prov_segment_dict = {}
            for journey in provider['sell_reschedule']['journeys']:
                for seg in journey['segments']:
                    key = '{origin}{destination}'.format(**seg)
                    prov_segment_dict[key] = seg

            segment_key_list = [key for key in prov_segment_dict.keys()]
            segment_key_str = ';'.join(segment_key_list)
            for idx, provider_obj in enumerate(self.provider_booking_ids):
                if provider_obj.pnr == provider['pnr']:
                    for journey_obj in provider_obj.journey_ids:
                        for segment_obj in journey_obj.segment_ids:
                            origin = segment_obj.origin_id.code if segment_obj.origin_id else '-'
                            destination = segment_obj.destination_id.code if segment_obj.destination_id else '-'
                            key = '%s%s' % (origin, destination)
                            if key not in prov_segment_dict:
                                _logger.error('Update journeys failed, key not found %s, segment key list %s' % (key, segment_key_str))
                                continue

                            segment_data = prov_segment_dict[key]
                            leg_key_dict = {}
                            for leg in segment_data['legs']:
                                leg_key = '{origin}{destination}'.format(**leg)
                                leg_key_dict[leg_key] = leg
                            leg_key_list = [key for key in leg_key_dict.keys()]
                            leg_key_str = ';'.join(leg_key_list)

                            leg_ids = []
                            for leg_obj in segment_obj.leg_ids:
                                origin = leg_obj.origin_id.code if leg_obj.origin_id else '-'
                                destination = leg_obj.destination_id.code if leg_obj.destination_id else '-'
                                leg_key = '%s%s' % (origin, destination)
                                if not leg_key in leg_key_dict:
                                    _logger.error('Update journeys failed, key not found %s, leg key list %s' % (leg_key, leg_key_str))
                                    leg_ids.append((4, leg_obj.id))
                                    continue

                                leg_data = leg_key_dict[leg_key]
                                val = {
                                    'leg_code': leg_data['leg_code'],
                                    'departure_date': leg_data['departure_date'],
                                    'arrival_date': leg_data['arrival_date'],
                                }
                                leg_ids.append((1, leg_obj.id, val))

                            # November 29, 2022 - SAM
                            fare_detail_dict = {}
                            for fare in segment_data.get('fares', []):
                                for fare_detail in fare.get('fare_details', []):
                                    detail_type = fare_detail.get('detail_type', '')
                                    detail_code = fare_detail.get('detail_code', '')
                                    if not detail_type and not detail_code:
                                        continue
                                    key = '%s-%s' % (detail_type, detail_code)
                                    fare_detail_dict[key] = fare_detail

                            segment_addons_ids = []
                            for fare_detail_obj in segment_obj.segment_addons_ids:
                                detail_type = fare_detail_obj.detail_type
                                detail_code = fare_detail_obj.detail_code
                                if not detail_type and not detail_code:
                                    continue
                                key = '%s-%s' % (detail_type, detail_code)
                                if key not in fare_detail_dict:
                                    segment_addons_ids.append((2, fare_detail_obj.id))
                                else:
                                    fare_detail_data = fare_detail_dict.pop(key)
                                    if not fare_detail_data.get('description'):
                                        fare_detail_data['description'] = json.dumps('[]')
                                    else:
                                        fare_detail_data['description'] = json.dumps(
                                            fare_detail_data['description'])
                                    segment_addons_ids.append((1, fare_detail_obj.id, fare_detail_data))
                            for fare_detail_data in fare_detail_dict.values():
                                segment_addons_ids.append((0, 0, fare_detail_data))
                            # END

                            segment_obj.write({
                                'segment_code': segment_data['segment_code'],
                                'carrier_code': segment_data['carrier_code'],
                                'carrier_type_code': segment_data.get('carrier_type_code', ''),
                                'carrier_number': segment_data['carrier_number'],
                                'arrival_date': segment_data['arrival_date'],
                                'departure_date': segment_data['departure_date'],
                                'status': segment_data.get('status', ''),
                                'class_of_service': segment_data['fares'][0]['class_of_service'],
                                'cabin_class': segment_data['fares'][0].get('cabin_class', ''),
                                'fare_basis_code': segment_data['fares'][0].get('fare_basis_code', ''),
                                'tour_code': segment_data['fares'][0].get('tour_code', ''),
                                'leg_ids': leg_ids,
                                'segment_addons_ids': segment_addons_ids,
                            })
                        journey_obj.compute_detail_info()
                    provider_obj.write({
                        'departure_date': provider_obj.journey_ids[0]['departure_date'],
                        'arrival_date': provider_obj.journey_ids[-1]['arrival_date'],
                    })
                if idx == 0:
                    departure_date = provider_obj.departure_date[:10]
                    arrival_date = provider_obj.arrival_date[:10]
                else:
                    arrival_date = provider_obj.departure_date[:10]
            self.departure_date = departure_date
            if self.direction != 'OW':
                self.arrival_date = arrival_date
        else:
            # August 21, 2023 - SAM
            # NEW FLOW
            # Sementara untuk flow perubahan jadwal akan mengganti struktur journeys nya apabila ada perbedaan
            # Antisipasi untuk struktur journey dari SIA yang dapat berubah
            # Kemungkinan karena pengaruh fare class nya juga yang dapat berubah dari sisi SQ
            # Kalau tidak diubah, akan pengaruh ke reschedule nya
            # Contoh :
            # Data Awal
            # Journey 1 : SUB - SIN - MEL
            # Menjadi
            # Journey 1 : SUB - SIN
            # Joruney 2 : SIN - MEL
            rsv_prov_obj = None
            pnr = provider.get('pnr', '')
            for rec in self.provider_booking_ids:
                if rec.pnr == pnr:
                    rsv_prov_obj = rec
                    break

            if not rsv_prov_obj:
                _logger.error('No Update journeys, pnr not found, %s' % pnr)
                return False

            if not provider.get('journeys', []):
                _logger.info('No Update journeys, journeys not found in response, %s' % pnr)
                return False

            prov_segment_key_list = []
            prov_journey_count = 0
            prov_departure_date_list = []
            prov_arrival_date_list = []
            prov_class_of_service_list = []
            prov_fare_basis_code_list = []
            for prov_journey_obj in rsv_prov_obj.journey_ids:
                prov_journey_count += 1
                for prov_seg_obj in prov_journey_obj.segment_ids:
                    origin = prov_seg_obj.origin_id.code if prov_seg_obj.origin_id else ''
                    destination = prov_seg_obj.destination_id.code if prov_seg_obj.destination_id else ''
                    key = '%s-%s' % (origin, destination)
                    prov_segment_key_list.append(key)

                    cos = prov_seg_obj.class_of_service if prov_seg_obj.class_of_service else ''
                    prov_class_of_service_list.append(cos)
                    fbs = prov_seg_obj.fare_basis_code if prov_seg_obj.fare_basis_code else ''
                    prov_fare_basis_code_list.append(fbs)

                    dep_date = prov_seg_obj.departure_date if prov_seg_obj.departure_date else ''
                    prov_departure_date_list.append(dep_date)
                    arr_date = prov_seg_obj.arrival_date if prov_seg_obj.arrival_date else ''
                    prov_arrival_date_list.append(arr_date)

            com_segment_key_list = []
            is_structure_valid = True
            com_journey_count = 0
            com_departure_date_list = []
            com_arrival_date_list = []
            com_class_of_service_list = []
            com_fare_basis_code_list = []
            for journey in provider.get('journeys', []):
                com_journey_count += 1
                segments = journey.get('segments', [])
                if segments:
                    if segments[0].get('origin', '') == segments[-1].get('destination', ''):
                        is_structure_valid = False
                for seg in segments:
                    origin = seg['origin'] if seg.get('origin') else ''
                    destination = seg['destination'] if seg.get('destination') else ''
                    key = '%s-%s' % (origin, destination)
                    com_segment_key_list.append(key)

                    dep_date = seg['departure_date'] if seg.get('departure_date') else ''
                    com_departure_date_list.append(dep_date)
                    arr_date = seg['arrival_date'] if seg.get('arrival_date') else ''
                    com_arrival_date_list.append(arr_date)

                    for fare in seg.get('fares', []):
                        cos = fare['class_of_service'] if fare.get('class_of_service') else ''
                        com_class_of_service_list.append(cos)
                        fbs = fare['fare_basis_code'] if fare.get('fare_basis_code') else ''
                        com_fare_basis_code_list.append(fbs)

            if sorted(prov_segment_key_list) == sorted(com_segment_key_list):
                is_same_journeys = True
                # print('### HERE : same journeys')
            else:
                # print('### HERE : not same journeys')
                is_same_journeys = False

            if prov_journey_count == com_journey_count:
                # print('### HERE : journey count same, %s' % prov_journey_count)
                is_same_journey_count = True
            else:
                # print('### HERE : journey count not same, prov %s, com %s' % (prov_journey_count, com_journey_count))
                is_same_journey_count = False

            if sorted(prov_departure_date_list) == sorted(com_departure_date_list):
                is_same_departure = True
                # print('### HERE : same depart')
            else:
                is_same_departure = False
                # print('### HERE : not same depart')

            if sorted(prov_arrival_date_list) == sorted(com_arrival_date_list):
                is_same_arrival = True
                # print('### HERE : same arrival')
            else:
                is_same_arrival = False
                # print('### HERE : not same arrival')

            if sorted(prov_class_of_service_list) == sorted(com_class_of_service_list):
                is_same_class_of_service = True
                # print('### HERE : same class of service')
            else:
                is_same_class_of_service = False
                # print('### HERE : not same class of service')

            if sorted(prov_fare_basis_code_list) == sorted(com_fare_basis_code_list):
                is_same_fare_basis_code = True
                # print('### HERE : same fare basis code')
            else:
                is_same_fare_basis_code = False
                # print('### HERE : not same fare basis code')

            process_update_segments_info = False
            if not is_same_journeys or not is_same_departure or not is_same_arrival or not is_same_class_of_service or not is_same_fare_basis_code or not is_same_journey_count:
                process_update_segments_info = True

            if process_update_segments_info:
                for prov_journey_obj in rsv_prov_obj.journey_ids:
                    for prov_seg_obj in prov_journey_obj.segment_ids:
                        prov_seg_obj.write({
                            'journey_id': None,
                        })
                    prov_journey_obj.write({
                        'provider_booking_id': None
                    })

                departure_date = ''
                arrival_date = ''
                for journey_idx, journey in enumerate(provider.get('journeys', [])):
                    if journey_idx == 0:
                        departure_date = journey.get('departure_date', '')[:10]
                    arrival_date = journey.get('arrival_date', '')[:10]
                    origin_id = self.env['tt.destinations'].get_id(journey.get('origin', ''), self.provider_type_id)
                    destination_id = self.env['tt.destinations'].get_id(journey.get('destination', ''), self.provider_type_id)
                    prov_jrn_obj = self.env['tt.journey.airline'].create({
                        'sequence': journey_idx,
                        'origin_id': origin_id if origin_id else None,
                        'destination_id': destination_id if destination_id else None,
                        'departure_date': journey.get('departure_date', ''),
                        'arrival_date': journey.get('arrival_date', ''),
                        'journey_code': journey.get('journey_code', ''),
                        'provider_booking_id': rsv_prov_obj.id,
                    })
                    new_segment_obj_list = []
                    for seg in journey['segments']:
                        provider_obj = rsv_prov_obj.provider_id if rsv_prov_obj else None
                        carrier_obj = self.env['tt.transport.carrier'].sudo().search([('code', '=', seg['carrier_code'])], limit=1)
                        origin_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['origin']), ('provider_type_id', '=', self.provider_type_id.id)], limit=1)
                        destination_obj = self.env['tt.destinations'].sudo().search([('code', '=', seg['destination']), ('provider_type_id', '=', self.provider_type_id.id)], limit=1)
                        segment_addons_ids = []
                        n_seg_values = {
                            'segment_code': seg['segment_code'],
                            'pnr': provider['pnr'],
                            'fare_code': '',
                            'carrier_code': seg['carrier_code'],
                            'carrier_number': seg['carrier_number'],
                            'origin_terminal': seg['origin_terminal'],
                            'destination_terminal': seg['destination_terminal'],
                            'departure_date': seg['departure_date'],
                            'arrival_date': seg['arrival_date'],
                            'status': seg.get('status', ''),
                            'class_of_service': '',
                            'cabin_class': '',
                            'sequence': seg.get('sequence', 0),
                        }
                        if carrier_obj:
                            n_seg_values['carrier_id'] = carrier_obj.id
                        if provider_obj:
                            n_seg_values['provider_id'] = provider_obj.id
                        if origin_obj:
                            n_seg_values['origin_id'] = origin_obj.id
                        if destination_obj:
                            n_seg_values['destination_id'] = destination_obj.id

                        for fare in seg['fares']:
                            n_seg_values.update({
                                'fare_code': fare['fare_code'],
                                'class_of_service': fare['class_of_service'],
                                'cabin_class': fare['cabin_class'],
                                'fare_basis_code': fare.get('fare_basis_code', ''),
                                'tour_code': fare.get('tour_code', ''),
                                'fare_class': fare.get('fare_class', ''),
                                'fare_name': fare.get('fare_name', ''),
                            })
                            # for sc in fare['service_charge_summary']:
                            #     total_amount += sc['total_price']
                            for fare_detail in fare.get('fare_details', []):
                                fare_detail_data = copy.deepcopy(fare_detail)
                                if not fare_detail_data.get('description'):
                                    fare_detail_data['description'] = json.dumps('[]')
                                else:
                                    fare_detail_data['description'] = json.dumps(fare_detail_data['description'])
                                segment_addons_ids.append((0, 0, fare_detail_data))

                        n_seg_values.update({
                            'segment_addons_ids': segment_addons_ids
                        })

                        leg_values = {
                            'segment_id': None,
                            'origin_terminal': n_seg_values['origin_terminal'],
                            'destination_terminal': n_seg_values['destination_terminal'],
                            'departure_date': n_seg_values['departure_date'],
                            'arrival_date': n_seg_values['arrival_date'],
                        }
                        if n_seg_values.get('carrier_id'):
                            leg_values.update({
                                'carrier_id': n_seg_values['carrier_id']
                            })

                        if n_seg_values.get('provider_id'):
                            leg_values.update({
                                'provider_id': n_seg_values['provider_id']
                            })

                        if n_seg_values.get('origin_id'):
                            leg_values.update({
                                'origin_id': n_seg_values['origin_id']
                            })

                        if n_seg_values.get('destination_id'):
                            leg_values.update({
                                'destination_id': n_seg_values['destination_id']
                            })

                        # Membuat data baru untuk reservasi
                        n_seg_values.update({
                            'provider_id': provider_obj.id if provider_obj else None,
                            'journey_id': prov_jrn_obj.id,
                        })

                        n_resv_seg_obj = self.env['tt.segment.airline'].sudo().create(n_seg_values)
                        leg_values.update({
                            'segment_id': n_resv_seg_obj.id,
                            'provider_id': provider_obj.id if provider_obj else None,
                        })
                        self.env['tt.leg.airline'].sudo().create(leg_values)

                book_vals = {}
                if departure_date:
                    book_vals['departure_date'] = departure_date
                if arrival_date:
                    book_vals['arrival_date'] = arrival_date
                if book_vals:
                    self.write(book_vals)
            # END
            # August 21, 2023 - SAM
            # OLD FLOW COMMENT
            # departure_date = ''
            # arrival_date = ''
            # prov_segment_dict = {}
            # for journey in provider['journeys']:
            #     for seg in journey['segments']:
            #         key = '{origin}{destination}'.format(**seg)
            #         prov_segment_dict[key] = seg
            #
            # for idx, provider_obj in enumerate(self.provider_booking_ids):
            #     if provider_obj.pnr == provider['pnr']:
            #         for journey_obj in provider_obj.journey_ids:
            #             for segment_obj in journey_obj.segment_ids:
            #                 origin = segment_obj.origin_id.code if segment_obj.origin_id else '-'
            #                 destination = segment_obj.destination_id.code if segment_obj.destination_id else '-'
            #                 key = '%s%s' % (origin, destination)
            #                 if key not in prov_segment_dict:
            #                     _logger.error('Update journeys failed, key not found %s' % (key))
            #                     continue
            #
            #                 segment_data = prov_segment_dict[key]
            #                 leg_key_dict = {}
            #                 for leg in segment_data['legs']:
            #                     leg_key = '{origin}{destination}'.format(**leg)
            #                     leg_key_dict[leg_key] = leg
            #                 leg_key_list = [key for key in leg_key_dict.keys()]
            #                 leg_key_str = ';'.join(leg_key_list)
            #
            #                 leg_ids = []
            #                 for leg_obj in segment_obj.leg_ids:
            #                     origin = leg_obj.origin_id.code if leg_obj.origin_id else '-'
            #                     destination = leg_obj.destination_id.code if leg_obj.destination_id else '-'
            #                     leg_key = '%s%s' % (origin, destination)
            #                     if not leg_key in leg_key_dict:
            #                         _logger.error('Update journeys failed, key not found %s, leg key list %s' % (leg_key, leg_key_str))
            #                         leg_ids.append((4, leg_obj.id))
            #                         continue
            #
            #                     leg_data = leg_key_dict[leg_key]
            #                     val = {
            #                         'leg_code': leg_data['leg_code'],
            #                         'departure_date': leg_data['departure_date'],
            #                         'arrival_date': leg_data['arrival_date'],
            #                     }
            #                     leg_ids.append((1, leg_obj.id, val))
            #
            #                 # November 29, 2022 - SAM
            #                 fare_detail_dict = {}
            #                 for fare in segment_data.get('fares', []):
            #                     for fare_detail in fare.get('fare_details', []):
            #                         detail_type = fare_detail.get('detail_type', '')
            #                         detail_code = fare_detail.get('detail_code', '')
            #                         if not detail_type and not detail_code:
            #                             continue
            #                         key = '%s-%s' % (detail_type, detail_code)
            #                         fare_detail_dict[key] = fare_detail
            #
            #                 segment_addons_ids = []
            #                 for fare_detail_obj in segment_obj.segment_addons_ids:
            #                     detail_type = fare_detail_obj.detail_type
            #                     detail_code = fare_detail_obj.detail_code
            #                     if not detail_type and not detail_code:
            #                         continue
            #                     key = '%s-%s' % (detail_type, detail_code)
            #                     if key not in fare_detail_dict:
            #                         segment_addons_ids.append((2, fare_detail_obj.id))
            #                     else:
            #                         fare_detail_data = fare_detail_dict.pop(key)
            #                         if not fare_detail_data.get('description'):
            #                             fare_detail_data['description'] = json.dumps('[]')
            #                         else:
            #                             fare_detail_data['description'] = json.dumps(fare_detail_data['description'])
            #                         segment_addons_ids.append((1, fare_detail_obj.id, fare_detail_data))
            #                 for fare_detail_data in fare_detail_dict.values():
            #                     segment_addons_ids.append((0, 0, fare_detail_data))
            #                 # END
            #
            #                 segment_obj.write({
            #                     'segment_code': segment_data['segment_code'],
            #                     'carrier_code': segment_data['carrier_code'],
            #                     'carrier_type_code': segment_data.get('carrier_type_code', ''),
            #                     'carrier_number': segment_data['carrier_number'],
            #                     'arrival_date': segment_data['arrival_date'],
            #                     'departure_date': segment_data['departure_date'],
            #                     'status': segment_data.get('status', ''),
            #                     'class_of_service': segment_data['fares'][0]['class_of_service'],
            #                     'cabin_class': segment_data['fares'][0].get('cabin_class', ''),
            #                     'fare_basis_code': segment_data['fares'][0].get('fare_basis_code', ''),
            #                     'tour_code': segment_data['fares'][0].get('tour_code', ''),
            #                     'leg_ids': leg_ids,
            #                     'segment_addons_ids': segment_addons_ids,
            #                 })
            #             journey_obj.compute_detail_info()
            #         provider_obj.write({
            #             'departure_date': provider_obj.journey_ids[0]['departure_date'],
            #             'arrival_date': provider_obj.journey_ids[-1]['arrival_date'],
            #         })
            #     if idx == 0:
            #         departure_date = provider_obj.departure_date[:10]
            #         arrival_date = provider_obj.arrival_date[:10]
            #     else:
            #         arrival_date = provider_obj.departure_date[:10]
            # self.departure_date = departure_date
            # if self.direction != 'OW':
            #     self.arrival_date = arrival_date
            # END

    def get_booking_airline_api(self,req, context):
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

            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            # if book_obj.agent_id.id == context.get('co_agent_id',-1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or book_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or book_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:## mestinya AND jika b2c maka userny harus sma
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
                res = book_obj.to_dict(context)
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

                # July 23, 2020 - SAM
                refund_list = []
                for ref in book_obj.refund_ids:
                    ref_values = ref.get_refund_data()
                    refund_list.append(ref_values)

                ##bisa kelolosan kalau tidak install tt_reschedule
                reschedule_list = book_obj.to_dict_reschedule()
                # END

                res.update({
                    'is_hold_date_sync': book_obj.is_hold_date_sync,
                    'direction': book_obj.direction,
                    'origin': book_obj.origin_id.code,
                    'origin_display_name': book_obj.origin_id.name,
                    'destination': book_obj.destination_id.code,
                    'destination_display_name': book_obj.destination_id.name,
                    'sector_type': book_obj.sector_type,
                    'passengers': psg_list,
                    'provider_bookings': prov_list,
                    'refund_list': refund_list,
                    'reschedule_list': reschedule_list,
                    'signature_booked': book_obj.sid_booked,
                    'expired_date': book_obj.expired_date and book_obj.expired_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                    # 'provider_type': book_obj.provider_type_id.code
                })
                if book_obj.third_party_ids:
                    webhook_request = book_obj.third_party_ids[0].to_dict()
                    res.update({
                        "webhook_request": webhook_request
                    })
                # _logger.info("Get resp\n" + json.dumps(res))
                return Response().get_no_error(res)
            else:
                raise RequestException(1035)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def payment_airline_api(self,req,context):
        payment_res = self.payment_reservation_api('airline',req,context)
        return payment_res

    def update_cost_service_charge_airline_api(self,req,context):
        try:
            _logger.info('Update cost\n' + json.dumps(req))
            for provider in req['provider_bookings']:
                # December 31, 2021 - SAM
                # if 'error_code' not in provider or provider['error_code'] != 0:
                if 'error_code' in provider and provider['error_code'] != 0:
                    _logger.error('Update SC Skipped, pnr : %s' % (provider['pnr']))
                    continue
                # END

                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)

                force_update_service_charge = provider.get('force_update_service_charge', False)
                pricing_data_different = provider.get('pricing_data_different', False)
                # May 12, 2020 - SAM
                if not provider.get('force_update_service_charge') and (not provider.get('total_price') or provider_obj.total_price == provider['total_price']):
                    continue
                # provider_obj.write({
                    # 'pnr': provider['pnr'],
                    # 'balance_due': provider['balance_due'],
                    # 'total_price': provider['total_price'],
                # })
                # END

                # June 10, 2021 - SAM
                _logger.info('Update cost PNR %s' % provider_obj.pnr)
                pricing_data = None
                total_service_charge = 0
                provider_service_charges = []
                for journey in provider['journeys']:
                    for segment in journey['segments']:
                        for fare in segment['fares']:
                            total_service_charge += len(fare['service_charges'])
                            provider_service_charges += copy.deepcopy(fare['service_charges'])
                            # January 12, 2022 - SAM
                            # Menambahkan flow update pricing data
                            if 'pricing_data' in fare:
                                pricing_data = fare['pricing_data']
                            # END

                for psg in provider['passengers']:
                    total_service_charge += len(psg['fees'])
                    provider_service_charges += copy.deepcopy(psg['fees'])

                is_same_service_charge_data = False
                if len(provider_obj.cost_service_charge_ids) == total_service_charge:
                    for sc in provider_obj.cost_service_charge_ids:
                        is_found = False
                        del_idx = -1
                        for psc_id, psc in enumerate(provider_service_charges):
                            if 'fee_type' in psc:
                                amount = sum(sca['amount'] for sca in psc['service_charges'])
                                # NOTE Terkadang untuk fee code bisa berbeda, bisa di ignore
                                # if sc.charge_type == psc['fee_type'] and sc.charge_code == psc['fee_code'] and sc.amount == amount:
                                if sc.charge_type == psc['fee_type'] and sc.amount == amount:
                                    is_found = True
                                    del_idx = psc_id
                                    break
                            else:
                                if sc.charge_type == psc['charge_type'] and sc.charge_code == psc['charge_code'] and sc.amount == psc['amount'] and sc.pax_count == psc['pax_count']:
                                    is_found = True
                                    del_idx = psc_id
                                    break

                        if is_found:
                            provider_service_charges.pop(del_idx)
                        else:
                            break
                    is_same_service_charge_data = False if provider_service_charges else True

                _logger.info('Is Same Service Charge Data %s' % is_same_service_charge_data)
                ledger_created = False
                if not is_same_service_charge_data:
                    ledger_created = provider_obj.delete_service_charge()
                    _logger.info('Ledger Created : %s' % ledger_created)
                    # May 13, 2020 - SAM
                    if ledger_created:
                        _logger.info('Reverse Ledger %s' % provider_obj.pnr)
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
                    currency_id = None
                    provider_obj.create_ticket_api(provider['passengers'], provider['pnr'])
                    for journey in provider['journeys']:
                        for segment in journey['segments']:
                            for fare in segment['fares']:
                                provider_obj.create_service_charge(fare['service_charges'])
                                provider_obj.update_pricing_details(fare)
                                if not currency_id:
                                    for svc in fare['service_charges']:
                                        currency_id = svc['currency_id']
                                        break
                    ### update currency 22 JUN 2023
                    if currency_id and provider_obj.booking_id.currency_id.id != currency_id:
                        provider_obj.booking_id.currency_id = currency_id
                # END

                # May 13, 2020 - SAM
                # June 10, 2021 - SAM
                # if ledger_created and req.get('force_issued'):
                _logger.info('Ledger Created : %s' % ledger_created)
                if ledger_created:
                    _logger.info('Create New Ledger %s' % provider_obj.pnr)
                    provider_obj.action_create_ledger(context['co_uid'])
                # END
                # END

                # January 12, 2022 - SAM
                # Menambahkan mekanisme untuk update pricing data
                try:
                    if pricing_data and (pricing_data_different or not is_same_service_charge_data):
                        pricing_obj = self.env['tt.provider.airline.pricing'].create({
                            'provider_id': provider_obj.id,
                            'raw_data': json.dumps(pricing_data)
                        })
                        pricing_obj.compute_raw_data()
                except:
                    _logger.error('Failed update provider airline pricing, %s' % traceback.format_exc())
                # END

            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            book_obj.calculate_service_charge()
            book_obj.create_svc_upsell()
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error("Update Cost Service Charge Error")

    def _prepare_booking_api(self, searchRQ, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_airline.tt_provider_type_airline')

        dest1= searchRQ['journey_list'][0]['origin']
        dest_idx = 0
        dest2=dest1
        while(dest1 == dest2):
            dest_idx -= 1
            dest2 = searchRQ['journey_list'][dest_idx]['destination']


        booking_tmp = {
            'direction': searchRQ.get('direction', ''),
            'departure_date': searchRQ['journey_list'][0]['departure_date'],
            'arrival_date': searchRQ['journey_list'][-1]['departure_date'],
            'origin_id': dest_obj.get_id(searchRQ['journey_list'][0]['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['journey_list'][dest_idx]['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ.get('adult', 0),
            'child': searchRQ.get('child', 0),
            'infant': searchRQ.get('infant', 0),
            'student': searchRQ.get('student', 0),
            'labour': searchRQ.get('labour', 0),
            'seaman': searchRQ.get('seaman', 0),
            'ho_id': context_gateway['co_ho_id'],
            'agent_id': context_gateway['co_agent_id'],
            'customer_parent_id': context_gateway.get('co_customer_parent_id',False),
            'user_id': context_gateway['co_uid'],
            'is_get_booking_from_vendor': searchRQ.get('is_get_booking_from_vendor', False),
            'payment_method_to_ho': searchRQ.get('payment_method_to_ho', False)
        }

        return booking_tmp

    # April 24, 2020 - SAM
    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            # May 13, 2020 - SAM
            # if req.get('force_issued'):
            #     self.calculate_service_charge()
            #     self.action_booked_api_airline(context, pnr_list, hold_date)
            #     payment_res = self.payment_airline_api({'book_id': req['book_id'],
            #                                             'member': req.get('member', False),
            #                                             'acquirer_seq_id': req.get('acquirer_seq_id', False)}, context)
            #     if payment_res['error_code'] != 0:
            #         try:
            #             self.env['tt.airline.api.con'].send_force_issued_not_enough_balance_notification(self.name, context)
            #         except Exception as e:
            #             _logger.error("Send TOP UP Approve Notification Telegram Error\n" + traceback.format_exc())
            #         raise RequestException(payment_res['error_code'],additional_message=payment_res['error_msg'])
            # END
            # self.calculate_service_charge()
            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
                'is_mail': req.get('is_mail', True)
            }
            if req.get('is_split'):
                issued_req.update({
                    'is_split': True
                })
            self.action_issued_api_airline(issued_req, context)
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            # self.calculate_service_charge()
            self.action_partial_issued_api_airline(context['co_uid'],customer_parent_id,is_split=req.get('is_split'))
        elif all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            # self.calculate_service_charge()
            # self.action_booked_api_airline(context, pnr_list, hold_date)
            self.action_booked_api_airline(context,is_split=req.get('is_split'))
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            # self.calculate_service_charge()
            # self.action_partial_booked_api_airline(context, pnr_list, hold_date)
            self.action_partial_booked_api_airline(context,is_split=req.get('is_split'))
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
            self.action_reverse_airline(context)
        elif any(rec.state == 'refund_failed' for rec in self.provider_booking_ids):
            self.action_refund_failed_airline(context)
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
            self.action_booked_api_airline(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##credit limit
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            if req.get('force_issued'):
                self.calculate_service_charge()
                self.action_booked_api_airline(context, pnr_list, hold_date)
                payment_res = self.payment_airline_api({'book_id': req['book_id'],
                                                        'member': req.get('member', False),
                                                        'acquirer_seq_id': req.get('acquirer_seq_id', False)}, context)
                if payment_res['error_code'] != 0:
                    try:
                        ho_id = self.agent_id.ho_id.id
                        self.env['tt.airline.api.con'].send_force_issued_not_enough_balance_notification(self.name, context, ho_id)
                    except Exception as e:
                        _logger.error("Send TOP UP Approve Notification Telegram Error\n" + traceback.format_exc())
                    raise RequestException(payment_res['error_code'],additional_message=payment_res['error_msg'])

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_airline(issued_req, context)
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

    def _create_provider_api(self, schedules, api_context, fare_rule_provider=[]):
        dest_obj = self.env['tt.destinations']
        provider_airline_obj = self.env['tt.provider.airline']
        carrier_obj = self.env['tt.transport.carrier']
        carrier_type_obj = self.env['tt.transport.carrier.type']
        provider_obj = self.env['tt.provider']
        currency_obj = self.env['res.currency']

        _destination_type = self.provider_type_id

        # April 23, 2020 - SAM
        passenger_id_src = {}
        for psg_id, psg in enumerate(self.passenger_ids):
            passenger_id_src[psg_id] = psg.id
        # END

        #lis of providers ID
        res = []
        name = {'provider':[],'carrier':[]}
        sequence = 0
        for idx, schedule in enumerate(schedules):
            provider_id = provider_obj.get_provider_id(schedule['provider'],_destination_type)
            name['provider'].append(schedule['provider'])
            _logger.info(schedule['provider'])
            this_pnr_journey = []
            journey_sequence = 0
            total_price = 0.0
            # April 20, 2020 - SAM
            this_service_charges = []
            passenger_seat_src = {}
            for psg_seq, psg in enumerate(schedule.get('passengers', [])):
                psg_id = passenger_id_src[psg_seq]
                for fee in psg.get('fees', []):
                    for sc in fee['service_charges']:
                        if sc['charge_type'] not in ['ROC', 'RAC']:
                            total_price += sc['total']

                    if not fee['fee_type'] == 'SEAT':
                        continue
                    leg_key_list = []
                    for leg in fee['legs']:
                        leg_key_list.append('{carrier_code}{carrier_number}{origin}{departure_date}'.format(**leg))
                    leg_key = ';'.join(leg_key_list)
                    fee.update({
                        'passenger_id': psg_id
                    })
                    if not passenger_seat_src.get(leg_key):
                        passenger_seat_src[leg_key] = []
                    passenger_seat_src[leg_key].append(fee)
            # END

            # August 24, 2021 - SAM
            pricing_provider_line_ids = []
            pricing_agent_ids = []
            # END
            pricing_data = None
            for journey in schedule['journeys']:
                ##create journey
                this_journey_banner = []
                this_journey_seg = []
                this_journey_seg_sequence = 0
                for segment in journey['segments']:
                    ###create segment
                    carrier_id = carrier_obj.get_id(segment['carrier_code'],_destination_type)
                    carrier_type_id = None
                    if segment.get('carrier_type_code'):
                        carrier_type_id = carrier_type_obj.get_id(segment.get('carrier_type_code', ''), _destination_type)
                    org_id = dest_obj.get_id(segment['origin'],_destination_type)
                    dest_id = dest_obj.get_id(segment['destination'],_destination_type)
                    operating_id = carrier_obj.get_id(segment['operating_airline_code'],_destination_type) if segment.get('operating_airline_code') else None

                    name['carrier'].append(carrier_id and carrier_id.name or '{} Not Found'.format(segment['carrier_code']))

                    this_journey_seg_sequence += 1

                    # April 23, 2020 - SAM
                    this_segment_legs = []
                    this_segment_fare_details = []
                    this_segment_seats = []
                    leg_key_list = []
                    for leg_seq_id, leg in enumerate(segment.get('legs', []), 1):
                        leg_org = dest_obj.get_id(leg['origin'], _destination_type)
                        leg_dest = dest_obj.get_id(leg['destination'], _destination_type)
                        leg_prov = provider_obj.get_provider_id(leg['provider'], _destination_type)
                        leg_values = {
                            'sequence': leg_seq_id,
                            'leg_code': leg['leg_code'],
                            'origin_terminal': leg['origin_terminal'],
                            'destination_terminal': leg['destination_terminal'],
                            'origin_id': leg_org,
                            'destination_id': leg_dest,
                            'departure_date': leg['departure_date'],
                            'arrival_date': leg['arrival_date'],
                            'provider_id': leg_prov
                        }
                        this_segment_legs.append((0, 0, leg_values))
                        leg_key_list.append('{carrier_code}{carrier_number}{origin}{departure_date}'.format(**leg))
                    leg_key = ';'.join(leg_key_list)

                    for ps in passenger_seat_src.get(leg_key, []):
                        seat_values = {
                            'seat': ps['fee_value'],
                            'passenger_id': ps['passenger_id'],
                        }
                        this_segment_seats.append((0, 0, seat_values))
                    # END

                    # April 20, 2020 - SAM
                    fare_data = {}
                    if segment.get('fares'):
                        fare_data = segment['fares'][0]

                        # September 20, 2022 - SAM
                        description = fare_data.get('description', '')
                        if type(description) == list:
                            description = json.dumps(description)
                        else:
                            description = ''
                        fare_data.update({
                            'description': description
                        })
                        # END

                        # January 10, 2022 - SAM
                        if 'pricing_data' in fare_data:
                            pricing_data = fare_data['pricing_data']
                        # END

                        this_service_charges += fare_data['service_charges']
                        for sc in fare_data['service_charges']:
                            if sc['charge_type'] not in ['ROC', 'RAC']:
                                total_price += sc['total']
                        #     currency_code = sc.pop('currency')
                        #     foreign_currency_code = sc.pop('foreign_currency')
                        #     sc.update({
                        #         'currency_id': currency_obj.get_id(currency_code, default_param_idr=True),
                        #         'foreign_currency_id': currency_obj.get_id(foreign_currency_code, default_param_idr=True),
                        #     })
                        #     this_service_charges.append((0, 0, sc))

                        for addons in fare_data.get('fare_details', []):
                            addons['description'] = json.dumps(addons['description'])
                            this_segment_fare_details.append((0, 0, addons))

                        # August 24, 2021 - SAM
                        if fare_data.get('pricing_provider_list'):
                            for pp in fare_data['pricing_provider_list']:
                                if not pp.get('pricing_provider_line_id'):
                                    continue
                                pricing_provider_line_ids.append((0, 0, pp))
                        if fare_data.get('pricing_agent_list'):
                            for pp in fare_data['pricing_agent_list']:
                                if not pp.get('pricing_agent_id'):
                                    continue
                                pricing_agent_ids.append((0, 0, pp))
                        # END
                    # END

                    segment_values = {
                        'segment_code': segment['segment_code'],
                        'fare_code': segment.get('fare_code', ''),
                        'carrier_id': carrier_id and carrier_id.id or False,
                        'carrier_type_id': carrier_type_id and carrier_type_id.id or False,
                        'carrier_code': segment['carrier_code'],
                        'carrier_type_code': segment.get('carrier_type_code', ''),
                        'carrier_number': segment['carrier_number'],
                        'provider_id': provider_id,
                        'origin_id': org_id and org_id or False,
                        'origin_terminal': segment.get('origin_terminal', ''),
                        'destination_id': dest_id and dest_id or False,
                        'destination_terminal': segment.get('destination_terminal', ''),
                        'departure_date': segment['departure_date'],
                        'arrival_date': segment['arrival_date'],
                        'sequence': this_journey_seg_sequence,
                        # April 23, 2020 - SAM
                        'leg_ids': this_segment_legs,
                        'segment_addons_ids': this_segment_fare_details,
                        'seat_ids': this_segment_seats,
                        # END
                        # April 12, 2022 - SAM
                        'operating_airline_id': operating_id and operating_id.id or False,
                        'operating_airline_code': segment.get('operating_airline_code', ''),
                        # END
                        # August 14, 2023 - SAM
                        'status': segment.get('status', ''),
                        # END
                    }
                    segment_values.update(fare_data)
                    this_journey_seg.append((0, 0, segment_values))

                if journey.get('search_banner'):
                    for banner in journey.get('search_banner'):
                        this_journey_banner.append((0,0,{
                            "name": banner['name'],
                            "banner_color": banner['banner_color'],
                            "description": banner['description'],
                            "text_color": banner['text_color'],
                            "minimum_days": banner['minimum_days']
                        }))

                journey_sequence+=1

                dest_idx = self.pick_destination(this_journey_seg)

                this_pnr_journey.append((0,0, {
                    'provider_id': provider_id,
                    'sequence': journey_sequence,
                    'origin_id': this_journey_seg[0][2]['origin_id'],
                    'destination_id': this_journey_seg[dest_idx][2]['destination_id'],
                    'departure_date': this_journey_seg[0][2]['departure_date'],
                    'arrival_date': this_journey_seg[-1][2]['arrival_date'],
                    'segment_ids': this_journey_seg,
                    'journey_code': journey.get('journey_code',''),
                    'banner_ids': this_journey_banner,
                    'is_vtl_flight': journey.get('is_vtl_flight', False),
                }))

            JRN_len = len(this_pnr_journey)
            _logger.info("JRNlen : %s" % (JRN_len))
            # if JRN_len > 1:
            #     provider_direction = 'RT'
            #     provider_origin = this_pnr_journey[0][2]['origin_id']
            #     provider_destination = this_pnr_journey[0][2]['destination_id']
            #     provider_departure_date = this_pnr_journey[0][2]['departure_date']
            #     provider_arrival_date = this_pnr_journey[-1][2]['departure_date']
            # else:
            #     provider_direction = 'OW'
            #     provider_origin = this_pnr_journey[0][2]['origin_id']
            #     provider_destination = this_pnr_journey[0][2]['destination_id']
            #     provider_departure_date = this_pnr_journey[0][2]['departure_date']
            #     provider_arrival_date = False
            dest_idx = self.pick_destination(this_pnr_journey)
            provider_origin = this_pnr_journey[0][2]['origin_id']
            provider_destination = this_pnr_journey[dest_idx][2]['destination_id']
            provider_departure_date = this_pnr_journey[0][2]['departure_date']
            provider_arrival_date = this_pnr_journey[-1][2]['arrival_date']

            sequence+=1

            # June 28, 2021 - SAM
            rule_ids = []
            if fare_rule_provider:
                try:
                    if idx < len(fare_rule_provider) and 'rules' in fare_rule_provider[idx]:
                        rules = fare_rule_provider[idx].get('rules', [])
                        for rule in rules:
                            description = '\n'.join(rule['description'])
                            val = {
                                'name': rule['name'],
                                'description': description,
                            }
                            rule_ids.append((0, 0, val))
                except:
                    _logger.error('Error Create Fare Rules, %s' % traceback.format_exc())
            # END

            values = {
                'pnr': schedule.get('pnr', ''),
                'pnr2': schedule.get('pnr2', ''),
                'reference': schedule.get('reference', ''),
                'provider_id': provider_id,
                'booking_id': self.id,
                'ho_id': self.ho_id and self.ho_id.id or False,
                'sequence': sequence,
                'origin_id': provider_origin,
                'destination_id': provider_destination,
                'departure_date': provider_departure_date,
                'arrival_date': provider_arrival_date,

                'booked_uid': api_context['co_uid'],
                'booked_date': datetime.now(),
                'journey_ids': this_pnr_journey,
                'total_price': total_price,
                'rule_ids': rule_ids,
                'pricing_provider_line_ids': pricing_provider_line_ids,
                'pricing_agent_ids': pricing_agent_ids,
                'is_advance_purchase': schedule.get('is_advance_purchase', False),
                'notes': schedule.get('notes', '')
                # April 20, 2020 - SAM
                # 'cost_service_charge_ids': this_service_charges,
                # END
            }

            vendor_obj = provider_airline_obj.create(values)
            # April 27, 2020 - SAM
            vendor_obj.create_ticket_api(schedule['passengers'], vendor_obj.pnr and vendor_obj.pnr or str(vendor_obj.sequence), schedule['journeys'][0]['departure_date'] if schedule.get('journeys') else '')
            vendor_obj.create_service_charge(this_service_charges)
            # END
            res.append(vendor_obj)

            # January 10, 2022 - SAM
            try:
                if pricing_data:
                    pricing_obj = self.env['tt.provider.airline.pricing'].create({
                        'provider_id': vendor_obj.id,
                        'raw_data': json.dumps(pricing_data)
                    })
                    pricing_obj.compute_raw_data()
            except:
                _logger.error('Failed create provider airline pricing, %s' % traceback.format_exc())
            # END

            if not hasattr(vendor_obj, 'promo_code_ids'):
                continue

            promo_codes = schedule['promo_codes'] if schedule.get('promo_codes') else []
            for code in promo_codes:
                values = {
                    'promo_code': code['promo_code'],
                    'carrier_code': code['carrier_code'],
                    'booking_airline_id': vendor_obj.booking_id.id,
                    'provider_airline_booking_id': vendor_obj.id,
                }
                vendor_obj.promo_code_ids.create(values)
        name['provider'] = list(set(name['provider']))
        name['carrier'] = list(set(name['carrier']))
        return res,name

    def update_pnr_booked(self,provider_obj,provider,context):

        ##generate leg data
        provider_type = self.env['tt.provider.type'].search([('code', '=', 'airline')])[0]
        old_state = provider_obj.state

        # _logger.info("%s ACTION BOOKED AIRLINE START" % (provider['pnr']))
        provider_obj.action_booked_api_airline(provider, context)
        # _logger.info("%s ACTION BOOKED AIRLINE END" % (provider['pnr']))

        # May 11, 2020 - SAM

        # if old_state != 'draft':
        #     return
        #
        # # _logger.info("%s CREATING TICKET START" % (provider['pnr']))
        # provider_obj.create_ticket_api(provider['passengers'],provider['pnr'])
        # # _logger.info("%s CREATING TICKET END" % (provider['pnr']))
        # # August 16, 2019 - SAM
        # # Mengubah mekanisme update booking backend
        # segment_dict = provider['segment_dict']
        #
        # # update leg dan create service charge
        # # _logger.info("%s LOOP JOURNEY START" % (provider['pnr']))
        # for idx, journey in enumerate(provider_obj.journey_ids):
        #     # _logger.info("%s LOOP SEGMENT START" % (provider['pnr']))
        #     for idx1, segment in enumerate(journey.segment_ids):
        #         # param_segment = provider['journeys'][idx]['segments'][idx1]
        #         param_segment = segment_dict[segment.segment_code]
        #         if segment.segment_code == param_segment['segment_code']:
        #             this_segment_legs = []
        #             this_segment_fare_details = []
        #             # _logger.info("%s LOOP LEG START" % (provider['pnr']))
        #             for idx2, leg in enumerate(param_segment['legs']):
        #                 leg_org = self.env['tt.destinations'].get_id(leg['origin'], provider_type)
        #                 leg_dest = self.env['tt.destinations'].get_id(leg['destination'], provider_type)
        #                 leg_prov = self.env['tt.provider'].get_provider_id(leg['provider'], provider_type)
        #                 this_segment_legs.append((0, 0, {
        #                     'sequence': idx2,
        #                     'leg_code': leg['leg_code'],
        #                     'origin_terminal': leg['origin_terminal'],
        #                     'destination_terminal': leg['destination_terminal'],
        #                     'origin_id': leg_org,
        #                     'destination_id': leg_dest,
        #                     'departure_date': leg['departure_date'],
        #                     'arrival_date': leg['arrival_date'],
        #                     'provider_id': leg_prov
        #                 }))
        #             # _logger.info("%s LOOP LEG END" % (provider['pnr']))
        #
        #             # _logger.info("%s LOOP FARES START" % (provider['pnr']))
        #             for fare in param_segment['fares']:
        #                 provider_obj.create_service_charge(fare['service_charges'])
        #                 for addons in fare['fare_details']:
        #                     addons['description'] = json.dumps(addons['description'])
        #                     addons['segment_id'] = segment.id
        #                     this_segment_fare_details.append((0,0,addons))
        #             # _logger.info("%s LOOP FARES END" % (provider['pnr']))
        #             segment.write({
        #                 'leg_ids': this_segment_legs,
        #                 'cabin_class': param_segment.get('fares')[0].get('cabin_class',''),
        #                 'class_of_service': param_segment.get('fares')[0].get('class_of_service',''),
        #                 'segment_addons_ids': this_segment_fare_details
        #             })
        #             # _logger.info("%s SEGMENT WRITE FINISH" % (provider['pnr']))
        #     # _logger.info("%s LOOP SEGMENT END" % (provider['pnr']))
        # # _logger.info("%s LOOP JOURNEY END" % (provider['pnr']))
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
                        if p_charge_type not in ['SEAT','SSR']:
                            sc_value[p_pax_type][p_charge_type] = {}
                            sc_value[p_pax_type][p_charge_type].update({
                                'amount': 0,
                                'foreign_amount': 0,
                                'pax_count': p_sc.pax_count,  ## ini asumsi yang pertama yg plg benar pax countnya
                                'total': 0
                            })
                            c_type = p_charge_type
                        else:
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
                        'booking_airline_id': self.id,
                        'description': provider.pnr,
                        'ho_id': self.ho_id.id if self.ho_id else ''
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
        expired_date = None
        pnr_list = []
        values = {}
        for rec in self.provider_booking_ids:
            if rec.hold_date:
                rec_hold_date = datetime.strptime(rec.hold_date[:19], '%Y-%m-%d %H:%M:%S')
                if not hold_date or rec_hold_date < hold_date:
                    hold_date = rec_hold_date
            if rec.expired_date:
                rec_expired_date = datetime.strptime(rec.expired_date[:19], '%Y-%m-%d %H:%M:%S')
                if not expired_date or rec_expired_date < expired_date:
                    expired_date = rec_expired_date
            if rec.pnr:
                pnr_list.append(rec.pnr)

        if hold_date:
            hold_date_str = hold_date.strftime('%Y-%m-%d %H:%M:%S')
            if self.hold_date != hold_date_str:
                values['hold_date'] = hold_date_str
        if expired_date:
            expired_date_str = expired_date.strftime('%Y-%m-%d %H:%M:%S')
            if self.expired_date != expired_date_str:
                values['expired_date'] = expired_date_str
        if pnr_list:
            pnr = ', '.join(pnr_list)
            if self.pnr != pnr:
                values['pnr'] = pnr

        if values:
            self.write(values)
    # END

    #retrieve booking utk samakan info dengan vendor
    def sync_booking_with_vendor(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 113')
        req = {
            'order_number': self.name,
            # June 10, 2021 - SAM
            # Booked UID bisa berubah bukan mengikuti pemilik reservasi
            # Contoh ketika auto update sia, booked uid menjadi punya sistem
            # Pengaruh saat deteksi agent untuk pricing
            # 'user_id': self.booked_uid.id
            'user_id': self.user_id.id,
            'ho_id': self.agent_id.ho_id.id
            # END
        }
        self.env['tt.airline.api.con'].send_get_booking_for_sync(req)


    @api.multi
    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
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
            'path': book_obj.printout_ticket_id.path
        }
        return url

    def get_transaction_additional_info(self):
        destination_list = []
        if self.origin_id:
            destination_list.append(self.origin_id.code)
            for segment_obj in self.segment_ids:
                if segment_obj.origin_id and segment_obj.destination_id:
                    if destination_list[-1] != segment_obj.origin_id.code:
                        destination_list.append(segment_obj.origin_id.code)
                    if destination_list[-1] != segment_obj.destination_id.code:
                        destination_list.append(segment_obj.destination_id.code)

        text = "-".join(destination_list)
        if self.departure_date:
            if text != '':
                text += '<br/>'
            text += self.departure_date.split(' ')[0]
            if self.arrival_date and self.direction != 'OW':
                text += ' - %s' % self.arrival_date.split(' ')[0]
        return text

    @api.multi
    def print_eticket_with_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
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
            'path': book_obj.printout_ticket_price_id.path
        }
        return url

    def save_eticket_original_api(self, data, ctx):
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name
        book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)
        if book_obj.agent_id:
            co_agent_id = book_obj.agent_id.id
        else:
            co_agent_id = self.env.user.agent_id.id

        if book_obj.user_id:
            co_uid = book_obj.user_id.id
        else:
            co_uid = self.env.user.id
        attachments = []
        for idx, data_eticket in enumerate(data['response'], start=1):
            is_pdf_found = False
            for printout_ori_obj in book_obj.printout_ticket_original_ids:
                path = printout_ori_obj.path
                with open(path, "rb") as pdf_file:
                    encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
                    if encoded_string == data_eticket['base64']:
                        is_pdf_found = True
                if is_pdf_found:
                    break
            if not is_pdf_found:
                res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                    {
                        'filename': 'Airline Ticket Original %s-%s.pdf' % (book_obj.name, idx),
                        'file_reference': 'Airline Ticket Original',
                        'file': data_eticket['base64'],
                        'delete_date': datetime.strptime(book_obj.arrival_date,'%Y-%m-%d') + timedelta(days=7)
                    },
                    {
                        'co_agent_id': co_agent_id,
                        'co_uid': co_uid
                    }
                )
                attachments.append(book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1).id)
        for rec_attachment in attachments:
            book_obj.printout_ticket_original_ids = [(4, rec_attachment)]

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
        is_force_update = data.get('force_update', False)
        airline_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_airline')

        has_ticket_ori = False
        for rec_ticket_ori in book_obj.printout_ticket_original_ids:
            if rec_ticket_ori.active == True:
                has_ticket_ori = True

        if not has_ticket_ori or is_force_update:
            # gateway get ticket
            req = {"data": [], 'ho_id': book_obj.agent_id.ho_id.id}
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
                if ticket.active == True:
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
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
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

    @api.multi
    def print_itinerary_price(self, data, ctx=None):
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
        datas['is_with_price'] = True
        airline_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_airline')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
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
                    'filename': 'Airline Itinerary %s (Price).pdf' % book_obj.name,
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

    def pick_destination(self,data):
        org1 = data[0][2]['origin_id']
        dest1 = data[0][2]['destination_id']

        segment_len = len(data)
        if segment_len == 1:
            return 0
        # elif segment_len == 2:
        #     return 1
        # elif segment_len > 2:
        #     return (segment_len/2)-1
        else:
            dest2 = org1
            count = 0
            while(org1 == dest2 or dest1 == dest2 and abs(count)<segment_len):
                count -=1
                dest2 = data[count][2]['destination_id']
            return count

    def pick_destination_no_param(self):
        org1 = self.segment_ids[0].origin_id.id
        dest1 = self.segment_ids[0].destination_id.id

        segment_len = len(self.segment_ids)
        if segment_len == 1:
            return 0
        else:
            dest2 = org1
            count = 0
            while (org1 == dest2 or dest1 == dest2 and abs(count) < segment_len):
                count -= 1
                dest2 = self.segment_ids[count].destination_id.id
            return count

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
            desc_txt += 'Departure: ' + rec.origin_id.display_name+ ' (' + datetime.strptime(rec.departure_date, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y %H:%M') + ')<br/>'
            desc_txt += 'Arrival: ' + rec.destination_id.display_name+ ' (' + datetime.strptime(rec.arrival_date, '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y %H:%M') + ')<br/><br/>'
        return desc_txt

    # June 2, 2020 - SAM
    # May 13, 2020 - SAM
    # def get_nta_amount(self, method='full'):
    #     # res = super().get_nta_amount(method=method)
    #     nta_amount = 0.0
    #     for provider_obj in self.provider_booking_ids:
    #         # if provider_obj.state == 'issued':
    #         #     continue
    #
    #         for sc in provider_obj.cost_service_charge_ids:
    #             if sc.is_ledger_created or (sc.charge_type == 'RAC' and sc.charge_code != 'rac'):
    #                 continue
    #             nta_amount += sc.total
    #     return nta_amount

    # def get_total_amount(self, method='full'):
    #     total_amount = 0.0
    #     for provider_obj in self.provider_booking_ids:
    #         # if provider_obj.state == 'issued':
    #         #     continue
    #         for sc in provider_obj.cost_service_charge_ids:
    #             if sc.is_ledger_created or sc.charge_type == 'RAC':
    #                 continue
    #             total_amount += sc.total
    #     return total_amount
    # END

    # July 15, 2020 - SAM
    def create_refund_airline_api(self, data, context):
        try:
            if data.get('book_id'):
                airline_obj = self.env['tt.reservation.airline'].browse(data['book_id'])
            elif data.get('order_number'):
                airline_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])])
            else:
                raise Exception('Book ID or Order Number is not found')

            # VIN: 2021/03/02: admin fee tdak bisa di hardcode
            # TODO: refund type tdak boleh hardcode lagi, jika frontend sdah support pilih refund type regular / quick
            ref_type = data.get('refund_type', 'regular')
            admin_fee_obj = self.env['tt.refund'].get_refund_admin_fee_rule(airline_obj.agent_id.id, ref_type)
            if ref_type == 'quick':
                refund_type = self.env.ref('tt_accounting.refund_type_quick_refund').id
            else:
                refund_type = self.env.ref('tt_accounting.refund_type_regular_refund').id
            # refund_type = 'regular'

            refund_line_ids = []

            # June 3, 2022 - SAM
            # TODO Tambahin pengecekkan untuk pnr yang di proses, untuk yang sekarang asumsi 1 order number ter refund
            # pnr_list = []
            # for prov in data['provider_bookings']:
            #     pnr = prov['pnr']
            #     pnr_list.append(pnr)
            # END

            # July 21, 2020 - SAM
            penalty_amount = 0.0
            for prov_obj in airline_obj.provider_booking_ids:
                # if prov_obj.pnr not in pnr_list:
                #     continue
                penalty_amount += prov_obj.penalty_amount

            total_pax = len(airline_obj.passenger_ids)
            charge_fee = penalty_amount / total_pax
            # END
            # June 6, 2022 - SAM
            total_after_sales_fee = 0.0
            for rsch_obj in airline_obj.reschedule_ids:
                state = rsch_obj.state
                if state not in ['confirm', 'sent', 'validate', 'final', 'done']:
                    continue

                total_amount = rsch_obj.total_amount
                admin_fee = rsch_obj.admin_fee
                rsv_amount = total_amount - admin_fee
                if rsv_amount < 0:
                    rsv_amount = 0
                total_after_sales_fee += rsv_amount
                # total_after_sales_fee += total_amount
            after_sales_fee = total_after_sales_fee / total_pax
            # END
            for pax in airline_obj.passenger_ids:
                # pax_price = 0
                pax_price = after_sales_fee
                additional_charge_fee = 0
                for cost in pax.cost_service_charge_ids:
                    # pnr = cost.description
                    # if pnr and pnr not in pnr_list:
                    #     continue
                    if cost.charge_type not in ['RAC', 'DISC']:
                        pax_price += cost.amount
                        if cost.charge_type == 'ROC':
                            additional_charge_fee += cost.amount

                total_charge_fee = charge_fee + additional_charge_fee
                line_obj = self.env['tt.refund.line'].create({
                    'name': (pax.title or '') + ' ' + (pax.name or ''),
                    'birth_date': pax.birth_date,
                    'pax_price': pax_price,
                    'charge_fee': total_charge_fee,
                })
                refund_line_ids.append(line_obj.id)

            res_vals = {
                'agent_id': airline_obj.agent_id.id,
                'customer_parent_id': airline_obj.customer_parent_id.id,
                'booker_id': airline_obj.booker_id.id,
                'currency_id': airline_obj.currency_id.id,
                'service_type': airline_obj.provider_type_id.id,
                'refund_type_id': refund_type,
                'admin_fee_id': admin_fee_obj.id,
                'referenced_document': airline_obj.name,
                'referenced_pnr': airline_obj.pnr,
                'res_model': airline_obj._name,
                'res_id': airline_obj.id,
                'booking_desc': airline_obj.get_aftersales_desc(),
                'notes': data.get('notes') and data['notes'] or '',
                'created_by_api': True,
            }
            res_obj = self.env['tt.refund'].create(res_vals)
            res_obj.confirm_refund_from_button()
            res_obj.update({
                'refund_line_ids': [(6, 0, refund_line_ids)],
            })
            res_obj.send_refund_from_button()
            res_obj.validate_refund_from_button()
            res_obj.finalize_refund_from_button()
            response = {
                'refund_id': res_obj.id,
                'refund_number': res_obj.name
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Create Refund Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Create Refund Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

    def update_refund_airline_api(self, data, context):
        try:
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error('Error Update Refund Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Update Refund Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)

    def get_refund_airline_api(self, data, context):
        try:
            return ERR.get_no_error()
        except RequestException as e:
            _logger.error('Error Get Refund Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error('Error Get Refund Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1030)
    # END

    # September 8, 2020 - SAM
    def split_reservation_airline_api_1(self, data, context):
        try:
            '''
            data = {
                "order_id": 563",
                "order_number": "AL.2020135484",
                "provider_bookings": [{
                    "provider_id": 56,
                    "pnr": "ABCDEF",
                    "status": "SUCCEED",
                    "journeys": [{
                        "segments": [{
                            "segment_code": "dfghjskdfghjkljhgfdkjhgfdzxcfgadsfg",
                        }],
                    }],
                    "new_data": {
                        "pnr": "TYUIOP",
                        "pnr2": "SQ_TYUIOP",
                        "reference": "TYUIOP",
                        "journeys": [],
                        "passengers": [],
                        ...
                        ...
                    },
                }, {
                    "provider_id": 59,
                    "pnr": "TYUIOP",
                    "status": "FAILED",
                    "new_data": {}
                }],
                "passengers": [{
                    "passenger_number": 0
                }],
            }
            '''
            book_obj = None
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.airline'].browse(data['book_id'])
            elif data.get('order_number'):
                book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)

            if not book_obj:
                raise Exception('Booking Object not Found')

            passenger_data_sequence_list = []
            for psg in data['passengers']:
                passenger_data_sequence_list.append(psg['passenger_number'])

            if not any(prov['status'] == 'SUCCEED' for prov in data['provider_bookings']):
                raise Exception('No provider information found')

            new_booking_obj = None
            pnr_list = []
            new_passenger_id_dict = {}
            for prov in data['provider_bookings']:
                if not prov['status'] == 'SUCCEED':
                    continue

                prov_obj = None
                if prov.get('provider_id'):
                    prov_obj = self.env['tt.provider.airline'].browse(prov['provider_id'])
                elif prov.get('pnr'):
                    for prov_book_obj in book_obj.provider_booking_ids:
                        if prov_book_obj.pnr == prov['pnr']:
                            prov_obj = prov_book_obj
                            break

                if not prov_obj:
                    _logger.error('Provider Booking Object not Found, pnr %s' % prov['pnr'])
                    # raise Exception('Provider Booking Object not Found')
                    continue

                is_ledger_created = False
                if any(sc_obj.is_ledger_created for sc_obj in prov_obj.cost_service_charge_ids):
                    is_ledger_created = True
                    prov_obj.action_reverse_ledger()

                ticket_object_list = []
                passenger_id_list = []
                if data.get('passengers'):
                    passenger_sequence_list = []
                    for tkt in prov_obj.ticket_ids:
                        if not tkt.passenger_id:
                            continue
                        passenger_sequence_list.append(tkt.passenger_id.sequence)
                        if tkt.passenger_id.sequence in passenger_data_sequence_list:
                            passenger_id_list.append(tkt.passenger_id.id)
                            ticket_object_list.append(tkt)

                    if all(seq in passenger_data_sequence_list for seq in passenger_sequence_list):
                        _logger.error('Restricted to split for all passengers in PNR')
                        continue
                else:
                    _logger.error('Restricted to split for all passengers in PNR')
                    continue

                if not new_booking_obj:
                    new_booking_obj = book_obj.copy()
                    new_book_write_vals = {
                        'split_from_resv_id': book_obj.id,
                        'split_uid': context['co_uid'],
                        'split_date': fields.Datetime.now(),
                        'state': book_obj.state,
                        'sale_service_charge_ids': [(5,)]
                    }
                    update_new_vals = book_obj.get_posted_acc_actions()
                    if update_new_vals:
                        new_book_write_vals.update(update_new_vals)
                    new_booking_obj.write(new_book_write_vals)

                new_prov_obj = prov_obj.copy()
                for journey_obj in prov_obj.journey_ids:
                    new_journey_obj = journey_obj.copy()
                    for segment_obj in journey_obj.segment_ids:
                        new_segment_obj = segment_obj.copy()
                        for leg_obj in segment_obj.leg_ids:
                            new_leg_obj = leg_obj.copy()
                            new_leg_obj.write({
                                'segment_id': new_segment_obj.id,
                                'booking_id': new_booking_obj.id,
                            })

                        for seg_add_obj in segment_obj.segment_addons_ids:
                            new_seg_add_obj = seg_add_obj.copy()
                            new_seg_add_obj.write({
                                'segment_id': new_segment_obj.id
                            })

                        for seat_obj in segment_obj.seat_ids:
                            if seat_obj.passenger_id and seat_obj.passenger_id.id in passenger_id_list:
                                seat_obj.write({
                                    'segment_id': new_segment_obj.id,
                                    'booking_id': new_booking_obj.id,
                                })

                        new_segment_obj.write({
                            'journey_id': new_journey_obj.id,
                            'booking_id': new_booking_obj.id,
                        })

                    new_journey_obj.write({
                        'provider_booking_id': new_prov_obj.id
                    })

                new_prov_obj.write({
                    'booking_id': new_booking_obj.id,
                    'hold_date': prov['new_data']['hold_date'] if prov['new_data'].get('hold_date') else False,
                    'pnr': prov['new_data']['pnr'],
                    'pnr2': prov['new_data']['pnr2'] if prov['new_data'].get('pnr2') else '',
                    'reference': prov['new_data']['reference'] if prov['new_data'].get('reference') else '',
                    'balance_due': prov['new_data']['balance_due'] if prov['new_data'].get('balance_due') else 0,
                    'total_price': prov['new_data']['total_price'] if prov['new_data'].get('total_price') else 0,
                    'state': prov_obj.state,
                    'booked_uid': prov_obj.booked_uid and prov_obj.booked_uid.id or False,
                    'booked_date': prov_obj.booked_date and prov_obj.booked_date or False,
                    'issued_uid': prov_obj.issued_uid and prov_obj.issued_uid.id or False,
                    'issued_date': prov_obj.issued_date and prov_obj.issued_date or False,
                    'cancel_uid': prov_obj.cancel_uid and prov_obj.cancel_uid.id or False,
                    'cancel_date': prov_obj.cancel_date and prov_obj.cancel_date or False,
                    'refund_uid': prov_obj.refund_uid and prov_obj.refund_uid.id or False,
                    'refund_date': prov_obj.refund_date and prov_obj.refund_date or False,
                    'reschedule_uid': prov_obj.reschedule_uid and prov_obj.reschedule_uid.id or False,
                    'reschedule_date': prov_obj.reschedule_date and prov_obj.reschedule_date or False,

                    'penalty_currency': prov['new_data']['penalty_currency'] if prov['new_data'].get('penalty_currency') else 'IDR',
                    'penalty_amount': prov['new_data']['penalty_amount'] if prov['new_data'].get('penalty_amount') else 0,
                })
                pnr_list.append(prov['new_data']['pnr'])

                for tkt in ticket_object_list:
                    ticket_number = tkt.ticket_number
                    ff_code = tkt.ff_code
                    ff_number = tkt.ff_number
                    if not new_passenger_id_dict.get(tkt.passenger_id.id):
                        new_psg_obj = tkt.passenger_id.copy()
                        new_psg_obj.update({
                            'booking_id': new_booking_obj.id,
                            'cost_service_charge_ids': [(5,)],
                            'channel_service_charge_ids': [(5,)],
                        })
                        new_passenger_id_dict[tkt.passenger_id.id] = new_psg_obj.id
                        # for ff_obj in tkt.passenger_id.frequent_flyer_ids:
                        #     new_ff_obj = ff_obj.copy()
                        #     new_ff_obj.write({
                        #         'passenger_id': '',
                        #         'provider_id': '',
                        #         'provider_sequence': '',
                        #     })

                    psg_obj = tkt.passenger_id
                    first_name = psg_obj.first_name and ''.join(psg_obj.first_name.split()) or ''
                    psg_obj_key_1 = '%s%s' % (first_name, psg_obj.last_name and ''.join(psg_obj.last_name.split()) or '')
                    psg_obj_key_2 = '%s%s' % (first_name, first_name)
                    for psg_data in prov['new_data'].get('passengers', []):
                        psg_data_key = '%s%s' % (''.join(psg_data['first_name'].split()), psg_data['last_name'] and ''.join(psg_data['last_name'].split()) or '')
                        # if psg_data['first_name'].strip() == psg_data['last_name'].strip():
                        #     pass
                        # else:
                        #     pass
                        if psg_obj_key_1 == psg_data_key or psg_obj_key_2 == psg_data_key:
                            ticket_number = psg_data.get('ticket_number', '')
                            ff_number = psg_data.get('ff_number', '')
                            ff_code = psg_data.get('ff_code', '')
                            break

                    tkt.write({
                        'provider_id': new_prov_obj.id,
                        'passenger_id': new_passenger_id_dict[tkt.passenger_id.id],
                        'ticket_number': ticket_number,
                        'ff_code': ff_code,
                        'ff_number': ff_number,
                    })

                for promo_obj in book_obj.promo_code_ids:
                    new_promo_obj = promo_obj.copy()
                    new_promo_obj.write({
                        'booking_id': new_booking_obj.id
                    })

                new_total_price = 0.0
                for sc_obj in prov_obj.cost_service_charge_ids:
                    total_pax = 0
                    new_sc_obj = None
                    for psg_obj in sc_obj.passenger_airline_ids:
                        if psg_obj.id in passenger_id_list:
                            total_pax += 1
                            if not new_sc_obj:
                                new_sc_obj = sc_obj.copy()
                                new_sc_obj.write({
                                    'provider_airline_booking_id': new_prov_obj.id,
                                    'passenger_airline_ids': [(5,)]
                                })
                            new_sc_obj.write({
                                'passenger_airline_ids': [(4, new_passenger_id_dict[psg_obj.id])]
                            })
                            psg_obj.write({
                                'cost_service_charge_ids': [(3, sc_obj.id)]
                            })

                    if total_pax < 1:
                        continue

                    new_sc_obj.write({
                        'pax_count': total_pax,
                        'total': sc_obj.amount * total_pax,
                    })
                    new_pax_count = sc_obj.pax_count - total_pax

                    if new_sc_obj.charge_type not in ['ROC', 'RAC']:
                        new_total_price += new_sc_obj.total

                    if new_pax_count < 1:
                        sc_obj.unlink()
                    else:
                        sc_obj.write({
                            'pax_count': new_pax_count,
                            'total': sc_obj.amount * new_pax_count,
                        })

                for fee_obj in prov_obj.fee_ids:
                    if fee_obj.passenger_id and fee_obj.passenger_id.id in passenger_id_list:
                        fee_obj.write({
                            'provider_id': new_prov_obj.id,
                            'passenger_id': new_passenger_id_dict[fee_obj.passenger_id.id]
                        })

                if new_total_price != 0:
                    prov_obj.write({
                        'total_price': prov_obj.total_price - new_total_price,
                        'balance_due': float(prov_obj.balance_due - new_total_price) if prov_obj.state == 'booked' else prov_obj.balance_due
                    })
                    new_prov_obj.write({
                        'total_price': new_total_price,
                        'balance_due': new_total_price if prov_obj.state == 'booked' else new_prov_obj.balance_due
                    })

                if is_ledger_created:
                    prov_obj.action_create_ledger(context['co_uid'])
                    new_prov_obj.action_create_ledger(context['co_uid'])

                # Remove smua passenger yg udah dpindah ke resv baru
                book_obj.passenger_ids = [(3, sid) for sid in passenger_id_list]

            book_obj.calculate_pnr_provider_carrier()
            new_booking_obj.calculate_pnr_provider_carrier()
            book_obj.calculate_service_charge()
            new_booking_obj.calculate_service_charge()
            book_obj.check_provider_state(context=context, req={'is_split': True})
            new_booking_obj.check_provider_state(context=context, req={'is_split': True})

            response = new_booking_obj.to_dict()

            psg_list = [rec.to_dict() for rec in new_booking_obj.sudo().passenger_ids]
            prov_list = [rec.to_dict() for rec in new_booking_obj.provider_booking_ids]
            response.update({
                'passengers': psg_list,
                'provider_bookings': prov_list,
            })

            # response = {
            #     'book_id': new_booking_obj.id,
            #     'order_number': new_booking_obj.name,
            #     'provider_bookings': [{'provider_id': n_prov_obj.id, 'pnr': n_prov_obj.pnr} for n_prov_obj in
            #                           new_booking_obj.provider_booking_ids],
            # }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Split Reservation Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Split Reservation Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1034)

    # Vin: Testing Fungsi Split dari api panggil fungsi wizard split reservation airline
    # def split_reservation_airline_api_2(self, data, context):
    def split_reservation_airline_api(self, data, context):
        try:
            '''
                data = {
                    "order_id": 563",
                    "order_number": "AL.2020135484",
                    "provider_bookings": [{
                        "provider_id": 56,
                        "pnr": "ABCDEF",
                        "status": "SUCCEED",
                        "journeys": [{
                            "segments": [{
                                "segment_code": "dfghjskdfghjkljhgfdkjhgfdzxcfgadsfg",
                            }],
                        }],
                        "new_data": {
                            "pnr": "TYUIOP",
                            "pnr2": "SQ_TYUIOP",
                            "reference": "TYUIOP",
                            "journeys": [],
                            "passengers": [],
                            ...
                            ...
                        },
                    }, {
                        "provider_id": 59,
                        "pnr": "TYUIOP",
                        "status": "FAILED",
                        "new_data": {}
                    }],
                    "passengers": [{
                        "passenger_number": 0
                    }],
                }
                '''

            # Prepare Wizard Value
            book_obj = None
            if data.get('book_id'):
                book_obj = self.env['tt.reservation.airline'].browse(data['book_id'])
            elif data.get('order_number'):
                book_obj = self.env['tt.reservation.airline'].search([('name', '=', data['order_number'])], limit=1)

            if not book_obj:
                raise Exception('Booking Object not Found')

            if not any(prov['status'] == 'SUCCEED' for prov in data['provider_bookings']):
                raise Exception('No provider information found')

            book_passenger_seq = {}
            for rec in book_obj.passenger_ids:
                book_passenger_seq.update({rec.sequence: rec.id})

            # Loop per Provider Bookings
            passenger_data_sequence_list = []
            for prov_booking_dict in data['provider_bookings']:
                if len(prov_booking_dict['new_data']['passengers']) != len(book_obj.passenger_ids):
                    for psg in prov_booking_dict['new_data']['passengers']:
                        # Pax sdah pernah ada tidak di add lagi
                        if book_passenger_seq[psg['sequence']] not in passenger_data_sequence_list:
                            passenger_data_sequence_list.append(book_passenger_seq[psg['sequence']])

            provider_data_list = []
            if len(book_obj.provider_booking_ids) > 1:
                if len(data['provider_bookings']) != len(book_obj.provider_booking_ids):
                    provider_data_list = [book_provider_obj.id for book_provider_obj in book_obj.provider_booking_ids if book_provider_obj.pnr in [prov_booking_dict['new_data']['pnr2'] for prov_booking_dict in data['provider_bookings']]]
            # Create Wizard
            wizard_obj = self.env['tt.split.reservation.wizard'].create({
                'res_id': book_obj.id,
                'referenced_document': book_obj.name,
                'new_pnr': ','.join([prov_booking_dict['new_data']['pnr'] for prov_booking_dict in data['provider_bookings']]),
                'provider_ids': [(6,0,provider_data_list)],
                'passenger_ids': [(6,0,passenger_data_sequence_list)],
                'is_split_journey': provider_data_list != [],
                'is_split_passenger': passenger_data_sequence_list != [],
                'is_split_provider': False,
            })
            # Call submit function
            wizard_obj.submit_split_reservation()

            # Find Created Split Document
            # Asumsikan bahwa dia adalah file split yg terbaru
            # Notes: Lbih bagus fungsi ne di wizard mungkin(wizard return object yg baru tersplit krena bisa jadi miss klo pake metode idx 0)
            new_booking_obj = book_obj.split_to_resv_ids[0]

            # Update penalty_currency + penalty_amount(?)
            # Notes: Harus nya update bukan disini tapi di GW setelah split dia panggil update booking
            for new_prov_obj in new_booking_obj.provider_booking_ids:
                for prov_booking_dict in data['provider_bookings']:
                    if new_prov_obj.pnr in [prov_booking_dict['new_data']['pnr'],prov_booking_dict['new_data']['pnr2']]:
                        new_prov_obj.update({
                            'penalty_currency': prov_booking_dict['new_data'].get('penalty_currency') or 'IDR',
                            'penalty_amount': prov_booking_dict['new_data'].get('penalty_amount',0),
                        })

            response = new_booking_obj.to_dict()

            psg_list = [rec.to_dict() for rec in new_booking_obj.sudo().passenger_ids]
            prov_list = [rec.to_dict() for rec in new_booking_obj.provider_booking_ids]
            response.update({
                'passengers': psg_list,
                'provider_bookings': prov_list,
            })

            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Split Reservation Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Split Reservation Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1034)

    def get_booking_number_airline_api(self, data, context):
        try:
            '''
                data = {
                    "pnr": "ABCDEF",
                    "provider": "sia",
                }
                '''

            # Prepare Wizard Value
            book_obj = None
            provider_obj = None
            provider_data_obj = None
            provider_data = {}
            if 'provider' in data:
                provider_obj = self.env['tt.provider'].sudo().search([('code', '=', data['provider'])], limit=1)
                if not provider_obj:
                    raise Exception('Provider not found, %s' % data['provider'])

            if provider_obj and 'pnr' in data:
                provider_data_obj = self.env['tt.provider.airline'].sudo().search([('pnr', '=', data['pnr']), ('provider_id', '=', provider_obj.id), ('state', 'in', ['booked', 'issued'])], limit=1)
                book_obj = provider_data_obj.booking_id
                passengers = []
                for psg in book_obj.passenger_ids:
                    psg_data = psg.to_dict()
                    sequence = psg_data.get('sequence', 0)
                    psg_data['passenger_number'] = sequence
                    passengers.append(psg_data)

                provider_data = provider_data_obj.to_dict()
                provider_data.update({
                    'passengers': passengers,
                })

            if not book_obj:
                raise Exception('Booking Object not Found')

            user_id = book_obj.user_id

            co_user_info = self.env['tt.agent'].sudo().get_agent_level(user_id.agent_id.id)
            # context = {
            #     "co_uid": user_id.id,
            #     "co_user_name": user_id.name,
            #     "co_user_login": user_id.login,
            #     "co_agent_id": user_id.agent_id.id,
            #     "co_agent_name": user_id.agent_id.name,
            #     "co_agent_type_id": user_id.agent_id.agent_type_id.id,
            #     "co_agent_type_name": user_id.agent_id.agent_type_id.name,
            #     "co_agent_type_code": user_id.agent_id.agent_type_id.code,
            #     "co_user_info": co_user_info,
            # }

            context = {
              "co_uid": user_id.id,
              "co_user_name": user_id.name,
              "co_user_login": user_id.login,
              "co_ho_id": user_id.agent_id.ho_id.id,
              "co_agent_id": user_id.agent_id.id,
              "co_agent_name": user_id.agent_id.name,
              "co_agent_type_id": user_id.agent_id.agent_type_id.id,
              "co_agent_type_name": user_id.agent_id.agent_type_id.name,
              "co_agent_type_code": user_id.agent_id.agent_type_id.code,
              "co_ho_seq_id": user_id.agent_id.ho_id.seq_id,
              "co_ho_name": user_id.agent_id.ho_id.name,
              "co_user_info": co_user_info,
            }

            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_id': provider_data_obj.id,
                'provider_data': provider_data,
                'context': context
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Get Booking Number Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Get Booking Number Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1013)

    def update_pax_identity_airline_api(self, req, context, **kwargs):
        try:
            # _logger.info("Get req\n" + json.dumps(context))
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

            if not any(rec['status'] == 'SUCCEED' for rec in req['provider_bookings']):
                raise Exception('No Pax Identity Changed detected')

            country_obj = self.env['res.country'].sudo()
            for psg in req['passengers']:
                psg_number = psg['passenger_number']
                psg_obj = book_obj.passenger_ids[psg_number]
                if psg.get('identity'):
                    identity = psg['identity']
                    if psg_obj.customer_id:
                        psg_obj.customer_id.add_or_update_identity(identity)
                    psg_vals = {
                        'identity_type': identity and identity['identity_type'] or '',
                        'identity_number': identity and identity['identity_number'] or '',
                        'identity_first_name': identity and identity['identity_first_name'] or '',
                        'identity_last_name': identity and identity['identity_last_name'] or '',
                        'identity_expdate': identity and identity['identity_expdate'] or False,
                        'identity_country_of_issued_id': identity and country_obj.search([('code', '=ilike', identity['identity_country_of_issued_code'])], limit=1).id or False,
                        'is_valid_identity': True,
                    }
                    identity_passport = psg.get('identity_passport')
                    if identity_passport:
                        psg_vals.update({
                            'passport_type': identity_passport['identity_type'],
                            'passport_number': identity_passport['identity_number'],
                            'passport_first_name': identity_passport['identity_first_name'],
                            'passport_last_name': identity_passport['identity_last_name'],
                            'passport_expdate': identity_passport['identity_expdate'],
                            'passport_country_of_issued_id': country_obj.search([('code', '=ilike', identity_passport['identity_country_of_issued_code'])], limit=1).id,
                        })
                    psg_obj.write(psg_vals)

            response = {}
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Update Pax Identity Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Update Pax Identity Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1013)

    def update_pax_name_airline_api(self, req, context, **kwargs):
        try:
            # _logger.info("Get req\n" + json.dumps(context))
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

            if not any(rec['status'] == 'SUCCEED' for rec in req['provider_bookings']):
                raise Exception('No Pax Identity Changed detected')

            country_obj = self.env['res.country'].sudo()
            for psg in req['passengers']:
                psg_number = psg['passenger_number']
                psg_obj = book_obj.passenger_ids[psg_number]

                psg_vals = {
                    'first_name': psg.get('first_name', ''),
                    'last_name': psg.get('last_name', ''),
                }
                psg_obj.write(psg_vals)

            response = {}
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Update Pax Name Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Update Pax Name Airline API, %s' % traceback.format_exc())
            return ERR.get_error(1013)

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

                pnr_carrier_list = []
                for seg in self.segment_ids:
                    if rec2.pnr == seg.pnr and seg.carrier_id.name not in pnr_carrier_list:
                        pnr_carrier_list.append(seg.carrier_id.name)

                pax_pnr_data = {
                    'pnr': rec2.pnr,
                    'ticket_number': ticket_num,
                    'currency_code': rec2.currency_id and rec2.currency_id.name or '',
                    'provider': rec2.provider_id and rec2.provider_id.name or '',
                    'carrier_name': ','.join(pnr_carrier_list),
                    'departure_date': rec2.departure_date or '',
                    'origin': rec2.origin_id and rec2.origin_id.display_name or '',
                    'destination': rec2.destination_id and rec2.destination_id.display_name or '',
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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_airline_ids.ids):
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
                pax_pnr_data['parent_agent_commission'] = pax_pnr_data['total_commission'] - pax_pnr_data['agent_commission'] - pax_pnr_data['ho_commission']
                if pax_ticketed:
                    pax_data['pnr_list'].append(pax_pnr_data)
            pax_list.append(pax_data)
        return pax_list

    def apply_pax_name_airline_api(self, req, context, **kwargs):
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

            if not book_obj:
                raise RequestException(1003, req['order_number'])

            ticket_repo = {}
            for rec in book_obj.provider_booking_ids:
                pnr = rec.pnr
                for tkt in rec.ticket_ids:
                    ticket_id = 'TKT_%s' % tkt.id
                    key = '%s_%s' % (pnr, ticket_id)
                    ticket_repo[key] = tkt

            passenger_repo = {}
            for rec in book_obj.passenger_ids:
                key = str(rec.sequence)
                passenger_repo[key] = rec

            passengers = []
            passengers_data = req.get('passengers', [])
            for psg in passengers_data:
                is_success = False
                error_msg_list = []
                psg_number = psg['passenger_number']
                pnr = psg['pnr']
                ticket_id = psg['ticket_id']
                psg_key = str(psg_number)
                ticket_key = '%s_%s' % (pnr, ticket_id)
                psg_obj = passenger_repo[psg_key] if psg_key in passenger_repo else None
                tkt_obj = ticket_repo[ticket_key] if ticket_key in ticket_repo else None
                if psg_obj and tkt_obj:
                    try:
                        name_list = []
                        if tkt_obj.first_name:
                            name_list.append(tkt_obj.first_name)
                        if tkt_obj.last_name:
                            name_list.append(tkt_obj.last_name)
                        name = ' '.join(name_list)
                        psg_vals = {
                            'name': name,
                            'first_name': tkt_obj.first_name,
                            'last_name': tkt_obj.last_name,
                        }
                        if tkt_obj.title:
                            psg_vals['title'] = tkt_obj.title
                        psg_obj.write(psg_vals)
                        if psg_obj.customer_id:
                            psg_obj.customer_id.write({
                                'first_name': tkt_obj.first_name,
                                'last_name': tkt_obj.last_name,
                            })
                        tkt_obj.write({
                            'passenger_id': psg_obj.id
                        })
                        is_success = True
                    except Exception as e:
                        error_msg_list.append(str(e))
                else:
                    if not psg_obj:
                        error_msg_list.append('Passenger number not found in %s' % book_obj.name)
                    if not tkt_obj:
                        error_msg_list.append('Ticket ID not found in %s, PNR %s, Ticket ID %s' % (book_obj.name, pnr, ticket_id))

                error_msg = ', '.join(error_msg_list)
                if is_success:
                    vals = copy.deepcopy(psg)
                    vals.update({
                        'status': 'SUCCESS',
                        'error_code': 0,
                        'error_msg': error_msg
                    })
                else:
                    vals = copy.deepcopy(psg)
                    vals.update({
                        'status': 'FAILED',
                        'error_code': 500,
                        'error_msg': error_msg,
                    })
                passengers.append(vals)
            response = {
                'passengers': passengers,
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error('Error Apply Pax Name Airline API, %s' % traceback.format_exc())
            return e.error_dict()
        except:
            _logger.error('Error Apply Pax Name Airline API, %s' % traceback.format_exc())
            return ERR.get_error(500)
