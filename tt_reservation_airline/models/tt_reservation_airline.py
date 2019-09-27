from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
import datetime
import json

_logger = logging.getLogger(__name__)


class ReservationAirline(models.Model):

    _name = "tt.reservation.airline"
    _inherit = "tt.reservation"
    _order = "id desc"
    _description = 'Reservation Airline'

    direction = fields.Selection(variables.JOURNEY_DIRECTION, string='Direction', default='OW', required=True, readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True, states={'draft': [('readonly', False)]})
    sector_type = fields.Char('Sector', readonly=True, compute='_compute_sector_type', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_airline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    passenger_ids = fields.One2many('tt.reservation.passenger.airline', 'booking_id',
                                    readonly=True, states={'draft': [('readonly', False)]})
    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', domain=[('res_model','=','tt.reservation.airline')])

    provider_booking_ids = fields.One2many('tt.provider.airline', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    journey_ids = fields.One2many('tt.journey.airline', 'booking_id', 'Journeys', readonly=True, states={'draft': [('readonly', False)]})
    segment_ids = fields.One2many('tt.segment.airline', 'booking_id', string='Segments',
                                  readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                    default= lambda self: self.env.ref('tt_reservation_airline.tt_provider_type_airline'))
    carrier_name = fields.Char('List of Carriers',readonly=True)


    def get_form_id(self):
        return self.env.ref("tt_reservation_airline.tt_reservation_airline_form_views")


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


    @api.multi
    def action_check_provider_state(self):
        pass##fixme later

    def action_booked_api_airline(self,context,pnr_list,hold_date):
        self.write({
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.datetime.now()
        })

    def action_issued_api_airline(self,acquirer_id,customer_parent_id,context):
        self.action_issued_airline(context['co_uid'],customer_parent_id,acquirer_id)

    def action_issued_airline(self,co_uid,customer_parent_id,acquirer_id = False):
        self.write({
            'state': 'issued',
            'issued_date': datetime.datetime.now(),
            'issued_uid': co_uid,
            'customer_parent_id': customer_parent_id
        })

    def action_partial_booked_api_airline(self,context,pnr_list,hold_date):
        self.write({
            'state': 'partial_booked',
            'booked_uid': context['co_uid'],
            'booked_date': datetime.datetime.now(),
            'hold_date': hold_date,
            'pnr': pnr_list
        })

    def action_partial_issued_api_airline(self):
        self.write({
            'state': 'partial_issued'
        })

    def action_cancel(self):
        self.cancel_date = fields.Datetime.now()
        self.cancel_uid = self.env.user.id
        self.state = 'cancel'

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
    def action_force_issued(self):
        #fixme menunggu create ledger
        #
        # This Function call for BUTTON issued on Backend
        # api_context = {
        #     'co_uid': self.env.user.id
        # }
        #
        # user_obj = self.env['res.users'].browse(api_context['co_uid'])
        # if user_obj.agent_id.agent_type_id.id != self.env.ref('tt_base_rodex.agent_type_ho').id:
        #     raise UserError('Only User HO can Force Issued...')
        #
        # # ## UPDATE by Samvi 2018/07/23
        # for rec in self.provider_booking_ids:
        #     if rec.state == 'booked':
        #         if rec.total <= self.agent_id.balance_actual:
        #             rec.action_create_ledger()
        #             rec.action_issued(api_context)
        #         else:
        #             _logger.info('Force Issued Skipped : Not Enough Balance, Total : {}, Agent Actual Balance : {}, Agent Name : {}'.format(rec.total, self.agent_id.balance_actual, self.agent_id.name))
        #             raise UserError(_('Not Enough Balance.'))
        #     else:
        #         _logger.info('Force Issued Skipped : State not Booked, Provider : {}, State : {}'.format(rec.provider, rec.state))

        self.issued_date = fields.Datetime.now()
        self.issued_uid = self.env.user.id
        self.state = 'issued'


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
        _logger.info("Create\n" + json.dumps(req))
        search_RQ = req['searchRQ']
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        journeys = req['providers_booking_data']

        try:
            values = self._prepare_booking_api(search_RQ,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)
            list_customer_obj = self.create_customer_api(passengers,context,booker_obj.seq_id,contact_obj.seq_id,['title','sequence'])
            list_passenger_id = self.create_passenger_api(list_customer_obj,self.env['tt.reservation.passenger.airline'])

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids[0].phone_number,
                'passenger_ids': [(6,0,list_passenger_id)]
            })

            book_obj = self.create(values)
            provider_ids,name_ids = book_obj._create_provider_api(journeys,context)
            response_provider_ids = []
            for provider in provider_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })

            book_obj.write({
                'provider_name': ','.join(name_ids['provider']),
                'carrier_name': ','.join(name_ids['carrier'])
            })

            response = {
                'book_id': book_obj.id,
                'order_number': book_obj.name,
                'provider_ids': response_provider_ids
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1004)

    def update_pnr_provider_airline_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        _logger.info("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            book_obj = self.env['tt.reservation.airline'].browse(req['book_id'])
            if not book_obj:
                raise RequestException(1001)

            book_status = []
            pnr_list = []
            hold_date = datetime.datetime.max

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                if not provider_obj:
                    raise RequestException(1002)
                book_status.append(provider['status'])

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    curr_hold_date = datetime.datetime.strptime(provider['hold_date'], '%Y-%m-%d %H:%M:%S')
                    if curr_hold_date < hold_date:
                        hold_date = curr_hold_date
                    if provider_obj.state == 'booked':
                        continue
                    self.update_pnr_booked(provider_obj,provider,context)
                elif provider['status'] == 'ISSUED' and not provider.get('error_code'):
                    if provider_obj.state == 'issued':
                        continue
                    if req.get('force_issued'):
                        self.update_pnr_booked(provider_obj,provider,context)

                    #action issued dan create ticket number
                    provider_obj.action_issued_api_airline(context)
                    provider_obj.update_ticket_api(provider['passengers'])
                elif provider['status'] == 'FAIL_BOOKED':
                    provider_obj.action_failed_booked_api_airline(provider.get('error_code'),provider.get('error_msg'))
                elif provider['status'] == 'FAIL_ISSUED':
                    provider_obj.action_failed_issued_api_airline(provider.get('error_msg'))

            for rec in book_obj.provider_booking_ids:
                pnr_list.append(rec.pnr)

            if all(rec == 'BOOKED' for rec in book_status):
                #booked
                book_obj.calculate_service_charge()
                book_obj.action_booked_api_airline(context,pnr_list,hold_date)
            elif all(rec == 'ISSUED' for rec in book_status):
                #issued
                ##get payment acquirer
                if req.get('seq_id'):
                    acquirer_id = self.env['payment.acquirer'].search([('seq_id','=',req['seq_id'])])
                    if not acquirer_id:
                        raise RequestException(1017)
                else:
                    raise RequestException(1017)

                if req.get('member'):
                    customer_parent_id = acquirer_id.agent_id.id
                else:
                    customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id

                if req.get('force_issued'):
                    book_obj.calculate_service_charge()
                    book_obj.action_booked_api_airline(context, pnr_list, hold_date)
                    self.payment_airline_api({'book_id': req['book_id']}, context)

                book_obj.action_issued_api_airline(acquirer_id.id,customer_parent_id,context)
            elif any(rec == 'ISSUED' for rec in book_status):
                #partial issued
                book_obj.action_partial_issued_api_airline()
            elif any(rec == 'BOOKED' for rec in book_status):
                #partial booked
                book_obj.calculate_service_charge()
                book_obj.action_partial_booked_api_airline(context,pnr_list,hold_date)
            elif all(rec == 'FAIL_ISSUED' for rec in book_status):
                #failed issue
                book_obj.action_failed_issue()
            elif all(rec == 'FAIL_BOOKED' for rec in book_status):
                #failed book
                book_obj.action_failed_book()
            else:
                #entah status apa
                _logger.error('Entah status apa')
                raise RequestException(1006)

            return ERR.get_no_error({
                'order_number': book_obj.name,
                'book_id': book_obj.id
            })
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1005)

    def get_booking_airline_api(self,req, context):
        try:
            _logger.info("Get req\n" + json.dumps(context))
            book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
            if book_obj and book_obj.agent_id.id == context.get('co_agent_id',-1):
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
                _logger.info("Get resp\n" + json.dumps(res))
                return Response().get_no_error(res)
            else:
                raise RequestException(1001)

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    ##ini potong ledger
    def payment_airline_api(self,req,context):
        _logger.info("Payment\n" + json.dumps(req))
        try:
            book_obj = self.env['tt.reservation.airline'].browse(req.get('book_id'))
            if book_obj and book_obj.agent_id.id == context.get('co_agent_id',-1):
                #cek balance due book di sini, mungkin suatu saat yang akan datang
                if book_obj.state == 'issued':
                    _logger.error('Transaction Has been paid.')
                    raise RequestException(1009)
                if book_obj.state != 'booked':
                    _logger.error('Cannot issue not [Booked] State.')
                    raise RequestException(1020)
                #cek saldo
                balance_res = self.env['tt.agent'].check_balance_limit_api(context['co_agent_id'],book_obj.total_nta)
                if balance_res['error_code']!=0:
                    _logger.error('Balance not enough')
                    raise RequestException(1007)

                for provider in book_obj.provider_booking_ids:
                    provider.action_create_ledger()

                return ERR.get_no_error()
            else:
                RequestException(1001)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.info(str(e) + traceback.format_exc())
            try:
                book_obj.notes += str(e)+traceback.format_exc()+'\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1011)

    def update_cost_service_charge_airline_api(self,req,context):
        _logger.info('update cost\n' + json.dumps(req))
        for provider in req['provider_bookings']:
            provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
            if not provider_obj:
                raise RequestException(1002)
            provider_obj.delete_service_charge()
            provider_obj.write({
                'balance_due': provider['balance_due']
            })
            for journey in provider['journeys']:
                for segment in journey['segments']:
                    for fare in segment['fares']:
                        provider_obj.create_service_charge(fare['service_charges'])

        book_obj = self.get_book_obj(req.get('book_id'),req.get('order_number'))
        book_obj.calculate_service_charge()
        return ERR.get_no_error()

    def validate_booking(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise Exception('User NOT FOUND...')

        return ERR.get_error()

    def _prepare_booking_api(self, searchRQ, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_airline.tt_provider_type_airline')
        booking_tmp = {
            'direction': searchRQ.get('direction'),
            'departure_date': searchRQ['journey_list'][0]['departure_date'],
            'return_date': searchRQ['journey_list'][-1]['departure_date'],
            'origin_id': dest_obj.get_id(searchRQ['journey_list'][0]['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['journey_list'][-1]['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ['adult'],
            'child': searchRQ['child'],
            'infant': searchRQ['infant'],
            'agent_id': context_gateway['co_agent_id'],
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    def _create_provider_api(self, providers, api_context):
        dest_obj = self.env['tt.destinations']
        provider_airline_obj = self.env['tt.provider.airline']
        carrier_obj = self.env['tt.transport.carrier']
        provider_obj = self.env['tt.provider']

        _destination_type = self.provider_type_id

        #lis of providers ID
        res = []
        name = {'provider':[],'carrier':[]}
        for provider_name, provider_value in providers.items():
            provider_id = provider_obj.get_provider_id(provider_name,_destination_type)
            name['provider'].append(provider_name)
            _logger.info(provider_name)
            for sequence, pnr in provider_value.items():
                _logger.info(sequence)
                journey_sequence = 0
                this_pnr_journey = []

                for journey_type, journey_value in pnr['journey_codes'].items():
                    ###Create Journey
                    _logger.info(journey_type)

                    if len(journey_value) < 1:
                        continue

                    this_journey_seg = []
                    this_journey_seg_sequence = 0

                    for segment in journey_value:
                        ###Create Segment
                        carrier_id = carrier_obj.get_id(segment['carrier_code'],_destination_type)
                        org_id = dest_obj.get_id(segment['origin'],_destination_type)
                        dest_id = dest_obj.get_id(segment['destination'],_destination_type)

                        name['carrier'].append(segment['carrier_code'])

                        this_journey_seg_sequence += 1
                        this_journey_seg.append((0,0,{
                            'segment_code': segment['segment_code'],
                            'fare_code': segment.get('fare_code', ''),
                            'journey_type': journey_type,
                            'carrier_id': carrier_id,
                            'carrier_code': segment['carrier_code'],
                            'carrier_number': segment['carrier_number'],
                            'provider_id': provider_id,
                            'origin_id': org_id,
                            'origin_terminal': segment['origin_terminal'],
                            'destination_id': dest_id,
                            'destination_terminal': segment['destination_terminal'],
                            'departure_date': segment['departure_date'],
                            'arrival_date': segment['arrival_date'],
                            'sequence': this_journey_seg_sequence
                        }))

                    ###journey_type DEP or RET

                    journey_sequence+=1
                    this_pnr_journey.append((0,0, {
                        'provider_id': provider_id,
                        'sequence': journey_sequence,
                        'journey_type': journey_type,
                        'origin_id': this_journey_seg[0][2]['origin_id'],
                        'destination_id': this_journey_seg[-1][2]['destination_id'],
                        'departure_date': this_journey_seg[0][2]['departure_date'],
                        'arrival_date': this_journey_seg[-1][2]['arrival_date'],
                        'segment_ids': this_journey_seg
                    }))

                JRN_len = len(this_pnr_journey)
                _logger.info("JRNlen : %s" % (JRN_len))
                if JRN_len > 1:
                    provider_direction = 'RT'
                    provider_origin = this_pnr_journey[0][2]['origin_id']
                    provider_destination = this_pnr_journey[0][2]['destination_id']
                    provider_departure_date = this_pnr_journey[0][2]['departure_date']
                    provider_return_date = this_pnr_journey[-1][2]['departure_date']
                else:
                    provider_direction = 'OW'
                    provider_origin = this_pnr_journey[0][2]['origin_id']
                    provider_destination = this_pnr_journey[0][2]['destination_id']
                    provider_departure_date = this_pnr_journey[0][2]['departure_date']
                    provider_return_date = False

                values = {
                    'provider_id': provider_id,
                    'booking_id': self.id,
                    'sequence': sequence,
                    'direction': provider_direction,
                    'origin_id': provider_origin,
                    'destination_id': provider_destination,
                    'departure_date': provider_departure_date,
                    'return_date': provider_return_date,

                    'booked_uid': api_context['co_uid'],
                    'booked_date': datetime.datetime.now(),
                    'journey_ids': this_pnr_journey
                }

                res.append(provider_airline_obj.create(values))
        name['provider'] = list(set(name['provider']))
        name['carrier'] = list(set(name['carrier']))
        return res,name

    def update_pnr_booked(self,provider_obj,provider,context):

        ##generate leg data
        provider_type = self.env['tt.provider.type'].search([('code', '=', 'airline')])[0]
        provider_obj.create_ticket_api(provider['passengers'])
        provider_obj.action_booked_api_airline(provider, context)

        # August 16, 2019 - SAM
        # Mengubah mekanisme update booking backend
        segment_dict = provider['segment_dict']

        # update leg dan create service charge
        for idx, journey in enumerate(provider_obj.journey_ids):
            for idx1, segment in enumerate(journey.segment_ids):
                # param_segment = provider['journeys'][idx]['segments'][idx1]
                param_segment = segment_dict[segment.segment_code]
                if segment.segment_code == param_segment['segment_code']:
                    this_segment_legs = []
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

                    segment.write({
                        'leg_ids': this_segment_legs,
                        'cabin_class': param_segment.get('fares')[0].get('cabin_class',''),
                        'class_of_service': param_segment.get('fares')[0].get('class_of_service','')
                    })

                    for fare in param_segment['fares']:
                        provider_obj.create_service_charge(fare['service_charges'])

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

    @api.multi
    def print_eticket(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('tt_report_common.action_report_printout_reservation_airline').report_action(self, data=datas)

    @api.multi
    def print_eticket_with_price(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        # res = self.read(['price_list', 'qty1', 'qty2', 'qty3', 'qty4', 'qty5'])
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        datas['is_with_price'] = True
        return self.env.ref('tt_report_common.action_report_printout_reservation_airline').report_action(self,
                                                                                                         data=datas)

    @api.multi
    def print_itinerary(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('tt_report_common.action_printout_itinerary_airline').report_action(self, data=datas)

    def action_expired(self):
        super(ReservationAirline, self).action_expired()
        for provider in self.provider_booking_ids:
            provider.action_expired()

    # def psg_validator(self,book_obj):
    #     for segment in book_obj.segment_ids:
    #         rule = self.env['tt.limiter.rule'].sudo().search([('code', '=', segment.carrier_code)])
    #
    #         if rule:
    #             limit = rule.rebooking_limit
    #         else:
    #             continue
    #
    #         for name in segment.booking_id.passenger_ids:
    #             found_segments = self.env['tt.segment.airline'].search([('segment_code','=',segment.segment_code),
    #                                                                '|',
    #                                                                ('booking_id.passenger_ids.passport_number','ilike',name.passport_number),
    #                                                                ('booking_id.passenger_ids.name','ilike',name.name)],order='id DESC')
    #
    #             valid_segments = []
    #             for seg in found_segments:
    #                 try:
    #                     curr_state = seg.state
    #                 except:
    #                     curr_state = 'booked'
    #                     print('cache miss error')
    #
    #                 if curr_state in ['booked', 'issued', 'cancel2', 'fail_issue']:
    #                     valid_segments.append(seg)
    #
    #             safe = False
    #
    #             if len(valid_segments) < limit:
    #                 safe = True
    #             else:
    #                 for idx,valid_segment in enumerate(valid_segments[:limit]):
    #                     if valid_segment.booking_id.state == 'issued':
    #                         safe=True
    #                         break
    #
    #             if not safe:
    #                 # whitelist di sini
    #                 whitelist_name = self.env['tt.whitelisted.name'].sudo().search(
    #                     [('name', 'ilike', name.name), ('chances_left', '>', 0)],limit=1)
    #
    #                 if whitelist_name:
    #                     whitelist_name.chances_left -= 1
    #                     return True
    #
    #                 whitelist_passport = self.env['tt.whitelisted.passport'].sudo().search(
    #                     [('passport','=',name.passport_number),('chances_left','>',0)],limit=1)
    #
    #                 if whitelist_passport:
    #                     whitelist_passport.chances_left -= 1
    #                     return True
    #
    #                 raise Exception("Passenger validator failed on %s because of rebooking with same name and same route. %s will be charged for more addtional booking." % (name.name,rule.adm))
    #             print('safe')