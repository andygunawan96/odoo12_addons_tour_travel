from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.api import Response
import logging,traceback
import datetime
import json

_logger = logging.getLogger(__name__)


class ReservationAirline(models.Model):

    _name = "tt.reservation.airline"
    _inherit = "tt.reservation"
    _order = "id desc"

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

    def action_issued_api_airline(self,context):
        self.write({
            'state': 'issued',
            'issued_date': datetime.datetime.now(),
            'issued_uid': context['co_uid'],
        })

    def action_partial_booked_api_airline(self):
        self.write({
            'state': 'partial_booked'
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
        print("Create\n" + json.dumps(req))
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
            list_passenger_id = self.create_passenger_api(list_customer_obj)

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

            provider_ids = book_obj._create_provider_api(journeys,context)
            response_provider_ids = []
            for provider in provider_ids:
                response_provider_ids.append({
                    'id': provider.id,
                    'code': provider.provider_id.code,
                })
            response = {
                'book_id': book_obj.id,
                'provider_ids': response_provider_ids
            }
            return Response().get_no_error(response)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(1004)

    def update_pnr_provider_airline_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        # req['booking_commit_provider'][-1]['status'] = 'FAILED'
        print("Update\n" + json.dumps(req))
        # req = self.param_update_pnr
        try:
            book_obj = self.env['tt.reservation.airline'].browse(req['book_id'])
            if not book_obj:
                return ERR.get_error(1001)

            book_status = []
            pnr_list = []
            hold_date = datetime.datetime(9999, 12, 31, 23, 59, 59, 999999)

            for provider in req['provider_bookings']:
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
                if not provider_obj:
                    return ERR.get_error(1002)
                book_status.append(provider['status'])

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    curr_hold_date = datetime.datetime.strptime(provider['hold_date'], '%Y-%m-%d %H:%M:%S')
                    if curr_hold_date < hold_date:
                        hold_date = curr_hold_date
                    if provider_obj.state == 'booked':
                        continue
                    self.update_pnr_booked(provider_obj,provider,pnr_list,context)
                elif provider['status'] == 'ISSUED' and not provider.get('error_code'):
                    if provider_obj.state == 'issued':
                        continue
                    if req.get('force_issued'):
                        self.update_pnr_booked(provider_obj,provider,pnr_list,context)
                        book_obj.calculate_service_charge()
                        book_obj.action_booked_api_airline(context, pnr_list, hold_date)

                    #action issued dan create ticket number
                    provider_obj.action_issued_api_airline(context)
                    provider_obj.update_ticket_api(provider['passengers'])
                elif provider['status'] == 'FAILED_BOOKED':
                    provider_obj.action_failed_booked_api_airline()
                elif provider['status'] == 'FAILED_ISSUE':
                    provider_obj.action_failed_issued_api_airline()

            if req.get('force_issued'):
                self.payment_airline_api({'book_id': req['book_id']},context)

            if all(rec == 'BOOKED' for rec in book_status):
                #booked
                book_obj.calculate_service_charge()
                book_obj.action_booked_api_airline(context,pnr_list,hold_date)
            elif all(rec == 'ISSUED' for rec in book_status):
                #issued
                book_obj.action_issued_api_airline(context)
            elif any(rec == 'ISSUED' for rec in book_status):
                #partial issued
                book_obj.action_partial_issued_api_airline()
            elif any(rec == 'BOOKED' for rec in book_status):
                #partial booked
                book_obj.calculate_service_charge()
                book_obj.action_partial_booked_api_airline()
            elif all(rec == 'FAILED_ISSUED' for rec in book_status):
                #failed issue
                book_obj.action_failed_issue()
            elif all(rec == 'FAILED_BOOKED' for rec in book_status):
                #failed book
                book_obj.action_failed_book()
            else:
                #entah status apa
                _logger.error('Entah status apa')
                return ERR.get_error(1006)

            return Response().get_no_error({
                'order_number': book_obj.name,
                'book_id': book_obj.id
            })

        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(1005)

    def get_booking_airline_api(self,req, context):
        try:
            print("Get req\n" + json.dumps(context))
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
                print("Get resp\n" + json.dumps(res))
                return Response().get_no_error(res)
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.info(str(e) + traceback.format_exc())
            return ERR.get_error(500)

    ##ini potong ledger
    def payment_airline_api(self,req,context):
        print("Payment\n" + json.dumps(req))
        try:
            book_obj = self.env['tt.reservation.airline'].browse(req.get('book_id'))
            if book_obj and book_obj.agent_id.id == context.get('co_agent_id',-1):
                #cek balance due book di sini, mungkin suatu saat yang akan datang

                #cek saldo
                balance_res = self.env['tt.agent'].check_balance_limit_api(context['co_agent_id'],book_obj.total_nta)
                if balance_res['error_code']!=0:
                    return ERR.get_error(1007)

                for provider in book_obj.provider_booking_ids:
                    provider.action_create_ledger()

                return Response().get_no_error()
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.info(str(e) + traceback.format_exc())
            return Response().get_error(str(e),500)

    def update_cost_service_charge_airline_api(self,req,context):
        print('update cost\n' + json.dumps(req))
        for provider in req['provider_bookings']:
            provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])
            if not provider_obj:
                return ERR.get_error(1002)
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
            'direction': searchRQ['direction'],
            'departure_date': searchRQ['departure_date'],
            'return_date': searchRQ['return_date'],
            'origin_id': dest_obj.get_id(searchRQ['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ['adult'],
            'child': searchRQ['child'],
            'infant': searchRQ['infant'],
            'agent_id': context_gateway['co_agent_id'],
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    def create_passenger_api(self,list_customer):
        try:
            passenger_obj = self.env['tt.reservation.passenger.airline']
            list_passenger = []
            for rec in list_customer:
                vals = rec[0].copy_to_passenger()
                if rec[1]:
                    vals.update(rec[1])
                list_passenger.append(passenger_obj.create(vals).id)
        except Exception as e:
            #logger
            raise Exception(('Create passenger error, %s' % str(e)))
        return list_passenger

    def _create_provider_api(self, providers, api_context):
        dest_obj = self.env['tt.destinations']
        provider_airline_obj = self.env['tt.provider.airline']
        carrier_obj = self.env['tt.transport.carrier']
        provider_obj = self.env['tt.provider']

        _destination_type = self.provider_type_id

        #lis of providers ID
        res = []

        for provider_name, provider_value in providers.items():
            provider_id = provider_obj.get_provider_id(provider_name,_destination_type)
            print(provider_name)
            for sequence, pnr in provider_value.items():
                print(sequence)
                journey_sequence = 0
                this_pnr_journey = []

                for journey_type, journey_value in pnr['journey_codes'].items():
                    ###Create Journey
                    print(journey_type)

                    if len(journey_value) < 1:
                        continue

                    this_journey_seg = []
                    this_journey_seg_sequence = 0

                    for segment in journey_value:
                        ###Create Segment
                        carrier_id = carrier_obj.get_id(segment['carrier_code'],_destination_type)
                        org_id = dest_obj.get_id(segment['origin'],_destination_type)
                        dest_id = dest_obj.get_id(segment['destination'],_destination_type)

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
                print("JRNlen : %s" % (JRN_len))
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

        return res

    def update_pnr_booked(self,provider_obj,provider,pnr_list,context):

        ##generate leg data
        provider_type = self.env['tt.provider.type'].search([('code', '=', 'airline')])[0]
        provider_obj.create_ticket_api(provider['passengers'])
        provider_obj.action_booked_api_airline(provider, context)
        pnr_list.append(provider['pnr'])

        # update leg dan create service charge
        for idx, journey in enumerate(provider_obj.journey_ids):
            for idx1, segment in enumerate(journey.segment_ids):
                param_segment = provider['journeys'][idx]['segments'][idx1]
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
                            'leg_ids': this_segment_legs
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

