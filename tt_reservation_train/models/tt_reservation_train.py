from odoo import api,models,fields
from odoo.exceptions import UserError
import json,traceback,logging
from ...tools.ERR import RequestException
from ...tools import ERR,util,variables
from datetime import date, datetime, timedelta
import base64
import copy

_logger = logging.getLogger(__name__)

class TtReservationTrain(models.Model):
    _name = "tt.reservation.train"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = "Reservation Train"

    direction = fields.Selection(variables.JOURNEY_DIRECTION, string='Direction', default='OW', required=True, readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True, states={'draft': [('readonly', False)]})
    sector_type = fields.Char('Sector', readonly=True, compute='_compute_sector_type', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_train_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.train', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})

    total_channel_upsell = fields.Monetary(string='Total Channel Upsell', default=0,
                                           compute='_compute_total_channel_upsell', store=True)

    provider_booking_ids = fields.One2many('tt.provider.train', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    journey_ids = fields.One2many('tt.journey.train', 'booking_id', 'Journeys', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                       default= lambda self: self.env.ref('tt_reservation_train.tt_provider_type_train'))

    boarding_pass_id = fields.Many2one('tt.upload.center', 'Boarding Pass', readonly=True)
    train_name = fields.Char('Train Name', compute='_compute_train_name', store=True)


    def get_form_id(self):
        return self.env.ref("tt_reservation_train.tt_reservation_train_form_views")

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

    @api.depends("journey_ids.carrier_name")
    def _compute_train_name(self):
        for rec in self:
            train_names = []
            for journ in rec.journey_ids:
                if journ.carrier_name:
                    train_names.append(journ.carrier_name)
            rec.train_name = '\r\n'.join(train_names)

    @api.multi
    def action_set_as_draft(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 320')
        for rec in self:
            rec.state = 'draft'


    @api.multi
    def action_set_as_booked(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 321')
        for rec in self:
            rec.state = 'booked'

    @api.multi
    def action_set_as_issued(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 322')
        for rec in self:
            rec.state = 'issued'

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 323')
        super(TtReservationTrain, self).action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'

    @api.depends('origin_id','destination_id')
    def _compute_sector_type(self):
        for rec in self:
            if rec.origin_id and rec.destination_id:
                if rec.origin_id.country_id == rec.destination_id.country_id:
                    rec.sector_type = "Domestic"
                else:
                    rec.sector_type = "International"
            else:
                rec.sector_type = "Not Defined"

    def action_booked_api_train(self,context,pnr_list,hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        write_values = {
            'state': 'booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        }

        if hold_date:
            write_values['hold_date'] = hold_date
        if pnr_list:
            write_values['pnr'] = ', '.join(pnr_list)

        self.write(write_values)
        try:
            if self.agent_type_id.is_send_email_booked:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'booked_train')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'train',
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

    def action_issued_api_train(self,req,context):
        data = {
            'co_uid': context['co_uid'],
            'customer_parent_id': req['customer_parent_id'],
            'acquirer_id': req['acquirer_id'],
            'payment_reference': req.get('payment_reference', ''),
            'payment_ref_attachment': req.get('payment_ref_attachment', []),
        }
        self.action_issued_train(data)

    def action_partial_booked_api_train(self,context,pnr_list=[],hold_date=False):
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

    def action_reverse_train(self,context):
        self.write({
            'state': 'fail_refunded',
            'refund_uid': context['co_uid'],
            'refund_date': datetime.now()
        })

    def action_issued_train(self,data):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': data.get('co_uid', self.env.user.id),
            'customer_parent_id': data['customer_parent_id']
        })
        try:
            if self.agent_type_id.is_send_email_issued:
                mail_created = self.env['tt.email.queue'].sudo().with_context({'active_test':False}).search([('res_id', '=', self.id), ('res_model', '=', self._name), ('type', '=', 'issued_train')], limit=1)
                if not mail_created:
                    temp_data = {
                        'provider_type': 'train',
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

    def action_partial_issued_api_train(self,co_uid,customer_parent_id):
        self.write({
            'state': 'partial_issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        })

    def create_booking_train_api(self, req, context):
        # req = copy.deepcopy(self.param_global)
        # req = self.hardcode_req_cr8_booking
        # context = self.hardcode_context

        _logger.info("Create\n" + json.dumps(req))
        search_RQ = req['searchRQ']
        booker = req['booker']
        contacts = req['contacts'][0]
        passengers = req['passengers']
        passengers_data = copy.deepcopy(req['passengers'])  # waktu create passenger fungsi odoo field kosong di hapus cth: work_place
        schedules = req['schedules']

        try:
            values = self._prepare_booking_api(search_RQ,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts,booker_obj,context)

            list_passenger_value = self.create_passenger_value_api(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)

            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
                rec[2].update({
                    'customer_id': list_customer_id[idx].id
                })
                if passengers_data[idx].get('description'):
                    rec[2].update({
                        "description": passengers_data[idx]['description']
                    })

            for psg in list_passenger_value:
                util.pop_empty_key(psg[2])

            voucher_code = False
            if req.get('voucher'): #agar b2c bisa pakai voucher
                voucher_code = req['voucher']['voucher_reference']

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_title': contacts['title'],
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number),
                'passenger_ids': list_passenger_value,
                'voucher_code': voucher_code
            })

            book_obj = self.create(values)
            provider_ids,name_ids = book_obj._create_provider_api(schedules,context)
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

            if context.get('co_job_position_rules'):
                if context['co_job_position_rules'].get('callback'):
                    if context['co_job_position_rules']['callback'].get('source'):
                        if context['co_job_position_rules']['callback']['source'] == 'ptr':
                            third_party_data = copy.deepcopy(context['co_job_position_rules']['train'])
                            third_party_data.update({
                                "callback": context['co_job_position_rules']['callback'],
                                "source": context['co_job_position_rules']['callback']['source']
                            })
                            book_obj.update({
                                "third_party_webhook_data": json.dumps(third_party_data)
                            })

            if not req.get("bypass_psg_validator",False):
                self.psg_validator(book_obj)

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

    def psg_validator(self,book_obj):
        ho_agent_obj = book_obj.agent_id.ho_id
        for provider in book_obj.provider_booking_ids:
            for journey in provider['journey_ids']:
                rule = self.env['tt.limiter.rule'].sudo().search([('carrier_code', '=', journey.carrier_code), ('provider_type_id.code', '=', book_obj.provider_type_id.code), ('ho_id','=',ho_agent_obj.id)])

                if rule:
                    limit = rule.rebooking_limit
                else:
                    continue

                for name in book_obj.passenger_ids:
                    if name.identity_number:
                        search_query = [('journey_code','=',journey.journey_code),
                                        '|',
                                        ('booking_id.passenger_ids.identity_number','=ilike',name.identity_number),
                                        ('booking_id.passenger_ids.name','=ilike',name.name)]
                    else:
                        search_query = [('journey_code','=',journey.journey_code),
                                        ('booking_id.passenger_ids.name','=ilike',name.name)]

                    found_segments = self.env['tt.journey.train'].search(search_query,order='id DESC')

                    valid_segments = found_segments.filtered(lambda x: x.booking_id.state in ['booked', 'issued', 'cancel2', 'fail_issue'])
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
                        # whitelist di sini
                        whitelist_name = self.env['tt.whitelisted.name'].sudo().search(
                            [('name', 'ilike', name.name), ('chances_left', '>', 0)],limit=1)

                        if whitelist_name:
                            whitelist_name.chances_left -= 1
                            return True

                        whitelist_passport = self.env['tt.whitelisted.passport'].sudo().search(
                            [('passport','=',name.identity_number),('chances_left','>',0)],limit=1)

                        if whitelist_passport:
                            whitelist_passport.chances_left -= 1
                            return True

                        raise RequestException(1026,additional_message="Passenger validator failed on %s because of rebooking with same name and same route." % (name.name))

    def update_pnr_provider_train_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        _logger.info("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            book_obj = self.env['tt.reservation.train'].browse(req['book_id'])
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            book_status = []
            pnr_list = []
            hold_date = datetime.max
            any_provider_changed = False

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.train'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                book_status.append(provider['state'])

                if provider['state'] == 'booked' and not provider.get('error_code'):
                    curr_hold_date = datetime.strptime(provider['hold_date'], '%Y-%m-%d %H:%M:%S')
                    if curr_hold_date < hold_date:
                        hold_date = curr_hold_date
                    if provider_obj.state == 'booked' and hold_date == provider_obj.hold_date:
                        continue
                    self.update_pnr_booked(provider_obj,provider,context)
                    any_provider_changed = True
                    for idx, ticket_obj in enumerate(provider['tickets']):
                        if ticket_obj.get('covid'):
                            provider_obj.update_temporary_field_per_pax_api(idx, ticket_obj['covid'])

                    ## 22 JUN 2023 - IVAN
                    ## GET CURRENCY CODE
                    currency = provider['currency']
                    if currency:
                        currency_obj = self.env['res.currency'].search([('name', '=', currency)], limit=1)
                        if currency_obj:
                            book_obj.currency_id = currency_obj.id
                elif provider['state'] == 'issued' and not provider.get('error_code'):
                    for idx, ticket_obj in enumerate(provider['tickets']):
                        if ticket_obj.get('web_check_in'):
                            provider_obj.update_temporary_field_per_pax_api(idx, ticket_obj['web_check_in'])
                    if provider_obj.state == 'issued':
                        continue
                    if req.get('force_issued'):
                        self.update_pnr_booked(provider_obj,provider,context)

                    #action issued dan create ticket number
                    provider_obj.action_issued_api_train(context)
                    # provider_obj.update_ticket_api(provider['passengers'])
                    any_provider_changed = True


                    ## 23 Mar 2021, di pindahkan ke gateway tidak lagi sync sendiri
                    #get balance vendor
                    # if provider_obj.provider_id.track_balance:
                    #     try:
                    #         provider_obj.provider_id.sync_balance()
                    #     except Exception as e:
                    #         _logger.error(traceback.format_exc())
                elif provider['state'] == 'cancel':
                    provider_obj.action_cancel()
                    any_provider_changed = True
                elif provider['state'] == 'cancel2':
                    provider_obj.action_expired()
                    any_provider_changed = True
                elif provider['state'] == 'fail_booked':
                    provider_obj.action_failed_booked_api_train(provider.get('error_code'),provider.get('error_msg'))
                    any_provider_changed = True
                elif provider['state'] == 'fail_issued':
                    provider_obj.action_failed_issued_api_train(provider.get('error_code'),provider.get('error_msg'))
                    any_provider_changed = True

            if book_obj.state == 'booked' and book_obj.voucher_code:  ##karena baru dapet harga waktu update pnr
                book_obj.add_voucher(book_obj.voucher_code, context)


            for rec in book_obj.provider_booking_ids:
                if rec.pnr:
                    pnr_list.append(rec.pnr)

            if any_provider_changed:
                book_obj.check_provider_state(context,pnr_list,hold_date,req)
                book_obj.create_svc_upsell()
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

    def payment_train_api(self,req,context):
        return self.payment_reservation_api('train', req, context)

    def _prepare_booking_api(self, searchRQ, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_train.tt_provider_type_train')

        dest1= searchRQ['journey_list'][0]['origin']
        dest_idx = 0
        dest2=dest1

        if len(searchRQ['journey_list']) > 1:
            while(dest1 == dest2):
                dest_idx -= 1
                dest2 = searchRQ['journey_list'][dest_idx]['destination']

        booking_tmp = {
            'direction': searchRQ.get('direction'),
            'departure_date': searchRQ['journey_list'][0]['departure_date'],
            'arrival_date': searchRQ['journey_list'][-1]['departure_date'],
            'origin_id': dest_obj.get_id(searchRQ['journey_list'][0]['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['journey_list'][dest_idx]['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ['adult'],
            'infant': searchRQ['infant'],
            'ho_id': context_gateway['co_ho_id'],
            'agent_id': context_gateway['co_agent_id'],
            'customer_parent_id': context_gateway.get('co_customer_parent_id', False),
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            self.action_booked_api_train(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            acquirer_id,customer_parent_id = self.get_acquirer_n_c_parent_id(req)

            if req.get('force_issued'):
                self.calculate_service_charge()
                self.action_booked_api_train(context, pnr_list, hold_date)
                payment_res = self.payment_train_api({'book_id': req['book_id']}, context)
                if payment_res['error_code'] != 0:
                    raise RequestException(payment_res['error_code'])

            issued_req = {
                'acquirer_id': acquirer_id and acquirer_id.id or False,
                'customer_parent_id': customer_parent_id,
                'payment_reference': req.get('payment_reference', ''),
                'payment_ref_attachment': req.get('payment_ref_attachment', []),
            }
            self.action_issued_api_train(issued_req, context)
        elif all(rec.state == 'refund' for rec in self.provider_booking_ids):
            self.write({
                'state': 'refund',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
        elif any(rec.state == 'issued' for rec in self.provider_booking_ids):
            # partial issued
            acquirer_id, customer_parent_id = self.get_acquirer_n_c_parent_id(req)
            self.action_partial_issued_api_train(context['co_uid'],customer_parent_id)
        elif any(rec.state == 'booked' for rec in self.provider_booking_ids):
            # partial booked
            self.calculate_service_charge()
            self.action_partial_booked_api_train(context, pnr_list, hold_date)
        elif any(rec.state == 'fail_refunded' for rec in self.provider_booking_ids):
            self.action_reverse_train(context)
        elif all(rec.state == 'cancel' for rec in self.provider_booking_ids):
            # failed issue
            self.action_cancel()
        elif all(rec.state == 'cancel2' for rec in self.provider_booking_ids):
            # failed issue
            self.action_expired()
        elif all(rec.state == 'fail_issued' for rec in self.provider_booking_ids):
            # failed issue
            self.action_failed_issue()
        elif all(rec.state == 'fail_booked' for rec in self.provider_booking_ids):
            # failed book
            self.action_failed_book()
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    def _create_provider_api(self, schedules, api_context):
        dest_obj = self.env['tt.destinations']
        provider_train_obj = self.env['tt.provider.train']
        carrier_obj = self.env['tt.transport.carrier']
        provider_obj = self.env['tt.provider']

        _destination_type = self.provider_type_id

        #lis of providers ID
        res = []
        name = {'provider':[],'carrier':[]}
        sequence = 0
        for schedule in schedules:
            provider_id = provider_obj.get_provider_id(schedule['provider'],_destination_type)
            name['provider'].append(schedule['provider'])
            _logger.info(schedule['provider'])
            this_pnr_journey = []
            journey_sequence = 0
            for journey in schedule['journeys']:
                ##create journey
                carrier_id = carrier_obj.get_id(journey['carrier_code'],_destination_type)
                org_id = dest_obj.get_id(journey['origin'],_destination_type)
                dest_id = dest_obj.get_id(journey['destination'],_destination_type)

                name['carrier'].append(carrier_id.name)

                journey_sequence+=1

                this_pnr_journey.append((0,0, {
                    'provider_id': provider_id,
                    'sequence': journey_sequence,
                    'origin_id': org_id,
                    'destination_id': dest_id,
                    'departure_date': journey['departure_date'],
                    'arrival_date': journey['arrival_date'],
                    'carrier_id': carrier_id.id,
                    'carrier_code': journey['carrier_code'],
                    'carrier_number': journey['carrier_number'],
                    'journey_code': journey['journey_code'],
                    'fare_code': journey['fare_code']
                }))

            JRN_len = len(this_pnr_journey)
            _logger.info("JRNlen : %s" % (JRN_len))
            dest_idx = self.pick_destination(this_pnr_journey)
            provider_origin = this_pnr_journey[0][2]['origin_id']
            provider_destination = this_pnr_journey[dest_idx][2]['destination_id']
            provider_departure_date = this_pnr_journey[0][2]['departure_date']
            provider_arrival_date = this_pnr_journey[-1][2]['arrival_date']

            sequence+=1
            values = {
                'provider_id': provider_id,
                'booking_id': self.id,
                'sequence': sequence,
                'origin_id': provider_origin,
                'destination_id': provider_destination,
                'departure_date': provider_departure_date,
                'arrival_date': provider_arrival_date,

                'booked_uid': api_context['co_uid'],
                'booked_date': datetime.now(),
                'journey_ids': this_pnr_journey
            }

            res.append(provider_train_obj.create(values))
        name['provider'] = list(set(name['provider']))
        name['carrier'] = list(set(name['carrier']))
        return res,name

    def update_pnr_booked(self,provider_obj,provider,context):

        old_state = provider_obj.state
        provider_obj.action_booked_api_train(provider, context)
        if old_state != 'draft':
            return

        ##generate leg data
        provider_obj.create_ticket_api(provider['tickets'],provider['pnr'])

        # August 16, 2019 - SAM
        # Mengubah mekanisme update booking backend
        journey_dict = provider['journey_dict']

        # create service charge, update seatf
        for idx, journey in enumerate(provider_obj.journey_ids):
            try:
                param_journey = journey_dict[journey.journey_code]
            except:
                raise RequestException(1005,additional_message="Journey Code not found")
            for fare in param_journey['fares']:
                provider_obj.create_service_charge(fare['service_charges'])
            journey.create_seat(param_journey['seats'])
            journey.write({
                'cabin_class': param_journey.get('fares')[0].get('cabin_class',''),
                'class_of_service': param_journey.get('fares')[0].get('class_of_service',''),
                'carrier_name': param_journey.get('carrier_name')
            })

    def pick_destination(self, data):
        dest1 = data[0][2]['origin_id']
        if len(data) == 1:
            return 0
        else:
            dest2 = dest1
            count = 0
            while (dest1 == dest2):
                count -= 1
                dest2 = data[count][2]['destination_id']
            return count

    def get_booking_train_api(self,req, context):
        try:
            # _logger.info("Get req train\n" + json.dumps(context))
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
            # if book_obj and book_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids or book_obj.agent_type_id.name == self.env.ref('tt_base.agent_b2c').agent_type_id.name or book_obj.user_id.login == self.env.ref('tt_base.agent_b2c_user').login:
            # SEMUA BISA LOGIN PAYMENT DI IF CHANNEL BOOKING KALAU TIDAK PAYMENT GATEWAY ONLY
            _co_user = self.env['res.users'].sudo().browse(int(context['co_uid']))
            if book_obj.ho_id.id == context.get('co_ho_id', -1) or _co_user.has_group('base.group_erp_manager'):
                res = book_obj.to_dict(context, req)
                psg_list = []
                for rec in book_obj.sudo().passenger_ids:
                    psg_list.append(rec.to_dict())
                prov_list = []
                for rec in book_obj.provider_booking_ids:
                    prov_list.append(rec.to_dict())
                res.update({
                    'direction': book_obj.direction,
                    'origin': book_obj.origin_id.code,
                    'origin_display_name': book_obj.origin_id.name,
                    'destination': book_obj.destination_id.code,
                    'destination_display_name': book_obj.destination_id.name,
                    'sector_type': book_obj.sector_type,
                    'passengers': psg_list,
                    'provider_bookings': prov_list,
                    # 'provider_type': book_obj.provider_type_id.code
                })

                # _logger.info("Get resp\n" + json.dumps(res))
                return ERR.get_no_error(res)
            else:
                raise RequestException(1035)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_seat_train_api(self,req,context):
        try:
            _logger.info("Update Seat train\n" + json.dumps(req))
            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)
            for provider in req['provider_bookings']:
                if provider['status'] == 'SUCCESS':
                    for journey in provider['journeys']:
                        provider_obj = book_obj.provider_booking_ids.filtered(lambda x: x.sequence == provider['sequence'])
                        journey_obj = provider_obj.journey_ids.filtered(lambda x: x.sequence == journey['sequence'])
                        journey_obj.update_ticket(
                            journey['seats']
                        )
            return ERR.get_no_error()

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def update_cost_service_charge_train_api(self,req,context):
        _logger.info('update cost\n' + json.dumps(req))
        for provider in req['provider_bookings']:
            provider_obj = self.env['tt.provider.train'].browse(provider['provider_id'])
            try:
                provider_obj.create_date
            except:
                raise RequestException(1002)
            ledger_created = provider_obj.delete_service_charge()
            if ledger_created:
                raise RequestException(1027)
            provider_obj.write({
                'balance_due': provider['balance_due']
            })
            for journey in provider['journeys']:
                for fare in journey['fares']:
                    provider_obj.create_service_charge(fare['service_charges'])

        book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
        book_obj.calculate_service_charge()
        book_obj.create_svc_upsell()
        return ERR.get_no_error()

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
                    curr_dict['booking_train_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict['ho_id'] = self.ho_id.id if self.ho_id else ''
                    curr_dict.update(c_val)
                    values.append((0,0,curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    @api.multi
    def print_eticket(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.train'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        train_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_train')

        if not book_obj.printout_ticket_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id
            pdf_report = train_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = train_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Train Ticket %s.pdf' % book_obj.name,
                    'file_reference': 'Train Ticket',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.strptime(book_obj.arrival_date or book_obj.departure_date,"%Y-%m-%d") + timedelta(days=7)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
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

        book_obj = self.env['tt.reservation.train'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', []), 'is_hide_agent_logo': data.get('is_hide_agent_logo', False)}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        train_ticket_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_train')

        if not book_obj.printout_ticket_price_id or data.get('is_hide_agent_logo', False) or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = train_ticket_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = train_ticket_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Train Ticket (Price) %s.pdf' % book_obj.name,
                    'file_reference': 'Train Ticket with Price',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.strptime(book_obj.arrival_date or book_obj.departure_date,"%Y-%m-%d") + timedelta(days=7)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
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
        # return self.env.ref('tt_report_common.action_report_printout_reservation_train').report_action(self,
        #                                                                                                data=datas)

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
        train_ho_invoice_id = self.env.ref('tt_report_common.action_report_printout_invoice_ho_train')
        if not self.printout_ho_invoice_id:
            if self.agent_id:
                co_agent_id = self.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if self.user_id:
                co_uid = self.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = train_ho_invoice_id.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = train_ho_invoice_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Train HO Invoice %s.pdf' % self.name,
                    'file_reference': 'Train HO Invoice',
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
        # return train_ho_invoice_id.report_action(self, data=datas)

    @api.multi
    def print_itinerary(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.train'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        train_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_airline')
        if not book_obj.printout_itinerary_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = train_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = train_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Train Itinerary %s.pdf' % book_obj.name,
                    'file_reference': 'Train Itinerary',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
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
        # return self.env.ref('tt_report_common.action_printout_itinerary_airline').report_action(self, data=datas)

    @api.multi
    def print_itinerary_price(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.train'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        train_itinerary_id = book_obj.env.ref('tt_report_common.action_printout_itinerary_airline')
        if not book_obj.printout_itinerary_price_id or data.get('is_force_get_new_printout', False):
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = train_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = train_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Train Itinerary %s (Price).pdf' % book_obj.name,
                    'file_reference': 'Train Itinerary',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
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
        # return self.env.ref('tt_report_common.action_printout_itinerary_airline').report_action(self, data=datas)

    def get_transaction_additional_info(self):
        text = ''
        if self.origin_id:
            text = self.origin_id.code
            if self.destination_id:
                if text != '':
                    text += ' - %s' % self.destination_id.code
        if self.departure_date:
            if text != '':
                text += '<br/>'
            text += self.departure_date.split(' ')[0]
            if self.arrival_date and self.direction != 'OW':
                text += ' - %s' % self.arrival_date.split(' ')[0]
        return text

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
                for rec3 in rec2.cost_service_charge_ids.filtered(lambda y: rec.id in y.passenger_train_ids.ids):
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

    @api.multi
    def print_boarding_pass(self, data, ctx=None):
        # jika panggil dari backend
        if 'order_number' not in data:
            data['order_number'] = self.name
        if 'provider_type' not in data:
            data['provider_type'] = self.provider_type_id.name

        book_obj = self.env['tt.reservation.train'].search([('name', '=', data['order_number'])], limit=1)
        datas = {'ids': book_obj.env.context.get('active_ids', [])}
        res = book_obj.read()
        res = res and res[0] or {}
        datas['form'] = res
        train_itinerary_id = book_obj.env.ref('tt_report_common.action_report_printout_reservation_train_boarding_pass')
        is_web_checkin = False
        for passenger_obj in book_obj.passenger_ids:
            if passenger_obj.temporary_field:
                for temp_field in json.loads(passenger_obj.temporary_field):
                    if temp_field.get('web_check_in'):
                        is_web_checkin = True
                        break
        if book_obj.boarding_pass_id:
            book_obj.boarding_pass_id.unlink()
        if not book_obj.boarding_pass_id and is_web_checkin:
            if book_obj.agent_id:
                co_agent_id = book_obj.agent_id.id
            else:
                co_agent_id = self.env.user.agent_id.id

            if book_obj.user_id:
                co_uid = book_obj.user_id.id
            else:
                co_uid = self.env.user.id

            pdf_report = train_itinerary_id.report_action(book_obj, data=datas)
            pdf_report['context'].update({
                'active_model': book_obj._name,
                'active_id': book_obj.id
            })
            pdf_report_bytes = train_itinerary_id.render_qweb_pdf(data=pdf_report)
            res = book_obj.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Boarding Pass Train %s.pdf' % book_obj.name,
                    'file_reference': 'Boarding PassTrain',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = book_obj.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            book_obj.boarding_pass_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': book_obj.boarding_pass_id.url,
        }
        return url