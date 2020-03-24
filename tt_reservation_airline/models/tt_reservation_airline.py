from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime, timedelta
import base64

import json

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

    def get_form_id(self):
        return self.env.ref("tt_reservation_airline.tt_reservation_airline_form_views")

    @api.depends('segment_ids')
    def _compute_sector_type(self):
        for rec in self:
            sector_type = "Domestic"
            destination_country_list = []
            for segment in rec.segment_ids:
                destination_country_list.append(segment.origin_id.country_id.id)
                destination_country_list.append(segment.destination_id.country_id.id)
            destination_set = len(set(destination_country_list))

            if destination_set > 1:
                rec.sector_type = "International"
            elif destination_set == 1:
                rec.sector_type = "Domestic"

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

    def action_booked_api_airline(self,context,pnr_list,hold_date):
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

    def action_issued_api_airline(self,acquirer_id,customer_parent_id,context):
        self.action_issued_airline(context['co_uid'],customer_parent_id,acquirer_id)

    def action_issued_airline(self,co_uid,customer_parent_id,acquirer_id = False):
        self.write({
            'state': 'issued',
            'issued_date': datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        })

    def action_partial_booked_api_airline(self,context,pnr_list,hold_date):
        if type(hold_date) != datetime:
            hold_date = False
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now(),
            'hold_date': hold_date,
            'pnr': ','.join(pnr_list)
        })

    def action_partial_issued_api_airline(self,co_uid,customer_parent_id):
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
            rec.state = 'refund_pending'

    def action_cancel(self):
        super(ReservationAirline, self).action_cancel()
        for rec in self.provider_booking_ids:
            rec.action_cancel()

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
        schedules = req['schedules']

        try:
            values = self._prepare_booking_api(search_RQ,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)

            #                                               # 'identity_type','identity_number',
            #                                               # 'identity_country_of_issued_id','identity_expdate'])
            # list_passenger_id = self.create_passenger_api(list_customer_obj,self.env['tt.reservation.passenger.airline'])

            list_passenger_value = self.create_passenger_value_api_test(passengers)
            list_customer_id = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id)



            #fixme diasumsikan idxny sama karena sama sama looping by rec['psg']
            for idx,rec in enumerate(list_passenger_value):
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
                'contact_phone': "%s - %s" % (contact_obj.phone_ids[0].calling_code,contact_obj.phone_ids[0].calling_number),
                'passenger_ids': list_passenger_value,
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

            ##pengecekan segment kembar airline dengan nama passengers
            if not req.get("bypass_psg_validator",False):
                self.psg_validator(book_obj)

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
        for segment in book_obj.segment_ids:
            rule = self.env['tt.limiter.rule'].sudo().search([('carrier_code', '=', segment.carrier_code), ('provider_type_id.code', '=', book_obj.provider_type_id.code)])

            if rule:
                limit = rule.rebooking_limit
            else:
                continue

            for name in segment.booking_id.passenger_ids:
                if name.identity_number:
                    search_query = [('segment_code','=',segment.segment_code),
                                    '|',
                                    ('booking_id.passenger_ids.identity_number','=ilike',name.identity_number),
                                    ('booking_id.passenger_ids.name','=ilike',name.name)]
                else:
                    search_query = [('segment_code','=',segment.segment_code),
                                    ('booking_id.passenger_ids.name','=ilike',name.name)]

                found_segments = self.env['tt.segment.airline'].search(search_query,order='id DESC')

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

    def update_pnr_provider_airline_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        _logger.info("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            book_obj = self.env['tt.reservation.airline'].browse(req['book_id'])
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            book_status = []
            pnr_list = []
            hold_date = datetime.max.replace(year=2020)
            any_provider_changed = False
            any_pnr_changed = False

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                book_status.append(provider['status'])

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    default_hold_date = datetime.now().replace(microsecond=0) + timedelta(minutes=30)
                    curr_hold_date = datetime.strptime(util.get_without_empty(provider,'hold_date',str(default_hold_date)), '%Y-%m-%d %H:%M:%S')
                    if curr_hold_date == default_hold_date:
                        provider['hold_date'] = str(curr_hold_date)
                    if curr_hold_date < hold_date:
                        hold_date = curr_hold_date
                    if provider_obj.state == 'booked' and hold_date == provider_obj.hold_date:
                        continue
                    self.update_pnr_booked(provider_obj,provider,context)
                    any_provider_changed = True
                elif provider['status'] == 'ISSUED' and not provider.get('error_code'):
                    if provider_obj.state == 'issued':
                        continue
                    if req.get('force_issued'):
                        self.update_pnr_booked(provider_obj,provider,context)
                    if provider.get('pnr', '') != provider_obj.pnr:
                        provider_obj.write({'pnr': provider['pnr']})
                        for sc in provider_obj.cost_service_charge_ids:
                            sc.description = provider['pnr']
                        any_pnr_changed = True

                    #action issued dan create ticket number
                    provider_obj.action_issued_api_airline(context)
                    provider_obj.update_ticket_api(provider['passengers'])
                    any_provider_changed = True

                    #get balance vendor
                    if provider_obj.provider_id.track_balance:
                        try:
                            # print("GET BALANCE : "+str(self.env['tt.airline.api.con'].get_balance(provider_obj.provider_id.code)['response']['balance']))
                            provider_obj.provider_id.sync_balance()
                        except Exception as e:
                            _logger.error(traceback.format_exc())
                elif provider['status'] == 'FAIL_BOOKED':
                    provider_obj.action_failed_booked_api_airline(provider.get('error_code'),provider.get('error_msg'))
                    any_provider_changed = True
                elif provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_airline(provider.get('error_code'),provider.get('error_msg'))
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

            for rec in book_obj.provider_booking_ids:
                if rec.pnr:
                    pnr_list.append(rec.pnr)

            if any_provider_changed:
                book_obj.check_provider_state(context,pnr_list,hold_date,req)

            if any_pnr_changed:
                book_obj.write({'pnr': ','.join(pnr_list)})

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

    def get_booking_airline_api(self,req, context):
        try:
            # _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            try:
                book_obj.create_date
            except:
                raise RequestException(1001)

            if book_obj.agent_id.id == context.get('co_agent_id',-1):
                res = book_obj.to_dict()
                psg_list = []
                for rec in book_obj.sudo().passenger_ids:
                    psg_list.append(rec.to_dict())
                prov_list = []
                for rec in book_obj.provider_booking_ids:
                    prov_list.append(rec.to_dict())
                res.update({
                    'direction': book_obj.direction,
                    'origin': book_obj.origin_id.code,
                    'destination': book_obj.destination_id.code,
                    'sector_type': book_obj.sector_type,
                    'passengers': psg_list,
                    'provider_bookings': prov_list,
                    # 'provider_type': book_obj.provider_type_id.code
                })
                # _logger.info("Get resp\n" + json.dumps(res))
                return Response().get_no_error(res)
            else:
                raise RequestException(1001)

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
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                try:
                    provider_obj.create_date
                except:
                    raise RequestException(1002)
                provider_obj.write({
                    'balance_due': provider['balance_due']
                })
                ledger_created = provider_obj.delete_service_charge()
                if ledger_created:
                    raise RequestException(1027)
                for journey in provider['journeys']:
                    for segment in journey['segments']:
                        for fare in segment['fares']:
                            provider_obj.create_service_charge(fare['service_charges'])

            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            book_obj.calculate_service_charge()
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
            'direction': searchRQ.get('direction'),
            'departure_date': searchRQ['journey_list'][0]['departure_date'],
            'arrival_date': searchRQ['journey_list'][-1]['departure_date'],
            'origin_id': dest_obj.get_id(searchRQ['journey_list'][0]['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['journey_list'][dest_idx]['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ['adult'],
            'child': searchRQ['child'],
            'infant': searchRQ['infant'],
            'agent_id': context_gateway['co_agent_id'],
            'user_id': context_gateway['co_uid'],
            'is_get_booking_from_vendor': searchRQ.get('is_get_booking_from_vendor', False)
        }

        return booking_tmp

    def check_provider_state(self,context,pnr_list=[],hold_date=False,req={}):
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
                                                        'member': req['member'],
                                                        'acquirer_seq_id': req['acquirer_seq_id']}, context)
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
            self.write({
                'state':  'fail_refunded',
                'refund_uid': context['co_uid'],
                'refund_date': datetime.now()
            })
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

    def _create_provider_api(self, schedules, api_context):
        dest_obj = self.env['tt.destinations']
        provider_airline_obj = self.env['tt.provider.airline']
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
                this_journey_seg = []
                this_journey_seg_sequence = 0
                for segment in journey['segments']:
                    ###create segment
                    carrier_id = carrier_obj.get_id(segment['carrier_code'],_destination_type)
                    org_id = dest_obj.get_id(segment['origin'],_destination_type)
                    dest_id = dest_obj.get_id(segment['destination'],_destination_type)

                    name['carrier'].append(carrier_id and carrier_id.name or '{} Not Found'.format(segment['carrier_code']))

                    this_journey_seg_sequence += 1
                    this_journey_seg.append((0,0,{
                        'segment_code': segment['segment_code'],
                        'fare_code': segment.get('fare_code', ''),
                        'carrier_id': carrier_id and carrier_id.id or False,
                        'carrier_code': segment['carrier_code'],
                        'carrier_number': segment['carrier_number'],
                        'provider_id': provider_id,
                        'origin_id': org_id and org_id or False,
                        # 'origin_terminal': segment['origin_terminal'],
                        'destination_id': dest_id and dest_id or False,
                        # 'destination_terminal': segment['destination_terminal'],
                        'departure_date': segment['departure_date'],
                        'arrival_date': segment['arrival_date'],
                        'sequence': this_journey_seg_sequence
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
                    'segment_ids': this_journey_seg
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

            vendor_obj = provider_airline_obj.create(values)
            res.append(vendor_obj)

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

        if old_state != 'draft':
            return

        # _logger.info("%s CREATING TICKET START" % (provider['pnr']))
        provider_obj.create_ticket_api(provider['passengers'],provider['pnr'])
        # _logger.info("%s CREATING TICKET END" % (provider['pnr']))
        # August 16, 2019 - SAM
        # Mengubah mekanisme update booking backend
        segment_dict = provider['segment_dict']

        # update leg dan create service charge
        # _logger.info("%s LOOP JOURNEY START" % (provider['pnr']))
        for idx, journey in enumerate(provider_obj.journey_ids):
            # _logger.info("%s LOOP SEGMENT START" % (provider['pnr']))
            for idx1, segment in enumerate(journey.segment_ids):
                # param_segment = provider['journeys'][idx]['segments'][idx1]
                param_segment = segment_dict[segment.segment_code]
                if segment.segment_code == param_segment['segment_code']:
                    this_segment_legs = []
                    this_segment_fare_details = []
                    # _logger.info("%s LOOP LEG START" % (provider['pnr']))
                    for idx2, leg in enumerate(param_segment['legs']):
                        leg_org = self.env['tt.destinations'].get_id(leg['origin'], provider_type)
                        leg_dest = self.env['tt.destinations'].get_id(leg['destination'], provider_type)
                        leg_prov = self.env['tt.provider'].get_provider_id(leg['provider'], provider_type)
                        this_segment_legs.append((0, 0, {
                            'sequence': idx2,
                            'leg_code': leg['leg_code'],
                            'origin_terminal': leg['origin_terminal'],
                            'destination_terminal': leg['destination_terminal'],
                            'origin_id': leg_org,
                            'destination_id': leg_dest,
                            'departure_date': leg['departure_date'],
                            'arrival_date': leg['arrival_date'],
                            'provider_id': leg_prov
                        }))
                    # _logger.info("%s LOOP LEG END" % (provider['pnr']))

                    # _logger.info("%s LOOP FARES START" % (provider['pnr']))
                    for fare in param_segment['fares']:
                        provider_obj.create_service_charge(fare['service_charges'])
                        for addons in fare['fare_details']:
                            addons['description'] = json.dumps(addons['description'])
                            addons['segment_id'] = segment.id
                            this_segment_fare_details.append((0,0,addons))
                    # _logger.info("%s LOOP FARES END" % (provider['pnr']))
                    segment.write({
                        'leg_ids': this_segment_legs,
                        'cabin_class': param_segment.get('fares')[0].get('cabin_class',''),
                        'class_of_service': param_segment.get('fares')[0].get('class_of_service',''),
                        'segment_addons_ids': this_segment_fare_details
                    })
                    # _logger.info("%s SEGMENT WRITE FINISH" % (provider['pnr']))
            # _logger.info("%s LOOP SEGMENT END" % (provider['pnr']))
        # _logger.info("%s LOOP JOURNEY END" % (provider['pnr']))

    #to generate sale service charge
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
                    curr_dict['booking_airline_id'] = self.id
                    curr_dict['description'] = provider.pnr
                    curr_dict.update(c_val)
                    values.append((0,0,curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    #retrieve booking utk samakan info dengan vendor
    def sync_booking_with_vendor(self):
        for rec in self.provider_booking_ids:
            if rec.state  == 'booked':
                rec.balance_due += 1
        self.env.cr.commit()
        req = {
            'order_number': self.name,
            'user_id': self.booked_uid.id
        }
        res = self.env['tt.airline.api.con'].send_get_booking_for_sync(req)

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
            'name': "ZZZ",
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
            'name': "ZZZ",
            'target': 'new',
            'url': book_obj.printout_ticket_price_id.url,
        }
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
            'name': "ZZZ",
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
            'name': "ZZZ",
            'target': 'new',
            'url': book_obj.printout_itinerary_id.url,
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

    def calculate_pnr_provider_carrier(self):
        pnr_name = ''
        provider_name = ''
        carrier_name = ''
        for seg in self.segment_ids:
            pnr_name += str(seg.pnr) + ', '
            provider_name += str(seg.provider_id.code) + ', '
            carrier_name += str(seg.carrier_id.name) + ', '
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