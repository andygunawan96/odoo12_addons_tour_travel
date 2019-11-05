from odoo import api,models,fields
from ...tools import variables
import json,traceback,logging
from ...tools.ERR import RequestException
from ...tools import ERR
from datetime import datetime

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

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', domain=[('res_model','=','tt.reservation.train')])

    provider_booking_ids = fields.One2many('tt.provider.train', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    journey_ids = fields.One2many('tt.journey.train', 'booking_id', 'Journeys', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',
                                    default= lambda self: self.env.ref('tt_reservation_train.tt_provider_type_train'))

    carrier_name = fields.Char('List of Carriers',readonly=True)



    def create_booking_train_api(self, req, context):
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
            contact_obj = self.create_contact_api(contacts,booker_obj,context)

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

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids[0].phone_number,
                'passenger_ids': list_passenger_value
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

    def _prepare_booking_api(self, searchRQ, context_gateway):
        dest_obj = self.env['tt.destinations']
        provider_type_id = self.env.ref('tt_reservation_train.tt_provider_type_train')

        dest1= searchRQ['journey_list'][0]['origin']
        dest_idx = 0
        dest2=dest1
        while(dest1 == dest2):
            dest_idx -= 1
            dest2 = searchRQ['journey_list'][dest_idx]['destination']


        booking_tmp = {
            'direction': searchRQ.get('direction'),
            'departure_date': searchRQ['journey_list'][0]['departure_date'],
            'return_date': searchRQ['journey_list'][-1]['departure_date'],
            'origin_id': dest_obj.get_id(searchRQ['journey_list'][0]['origin'], provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['journey_list'][dest_idx]['destination'], provider_type_id),
            'provider_type_id': provider_type_id.id,
            'adult': searchRQ['adult'],
            'infant': searchRQ['infant'],
            'agent_id': context_gateway['co_agent_id'],
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

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

                name['carrier'].append(journey['carrier_code'])

                journey_sequence+=1

                this_pnr_journey.append((0,0, {
                    'provider_id': provider_id,
                    'sequence': journey_sequence,
                    'origin_id': org_id,
                    'destination_id': dest_id,
                    'departure_date': journey['departure_date'],
                    'arrival_date': journey['arrival_date'],
                    'carrier_id': carrier_id,
                    'carrier_code': journey['carrier_code'],
                    'carrier_number': journey['carrier_number'],
                }))

            JRN_len = len(this_pnr_journey)
            _logger.info("JRNlen : %s" % (JRN_len))
            dest_idx = self.pick_destination(this_pnr_journey)
            provider_origin = this_pnr_journey[0][2]['origin_id']
            provider_destination = this_pnr_journey[dest_idx][2]['destination_id']
            provider_departure_date = this_pnr_journey[0][2]['departure_date']
            provider_return_date = this_pnr_journey[-1][2]['departure_date']

            sequence+=1
            values = {
                'provider_id': provider_id,
                'booking_id': self.id,
                'sequence': sequence,
                'origin_id': provider_origin,
                'destination_id': provider_destination,
                'departure_date': provider_departure_date,
                'return_date': provider_return_date,

                'booked_uid': api_context['co_uid'],
                'booked_date': datetime.now(),
                'journey_ids': this_pnr_journey
            }

            res.append(provider_train_obj.create(values))
        name['provider'] = list(set(name['provider']))
        name['carrier'] = list(set(name['carrier']))
        return res,name

    def update_pnr_booked(self,provider_obj,provider,context):

        ##generate leg data
        provider_type = self.env['tt.provider.type'].search([('code', '=', 'train')])[0]
        provider_obj.create_ticket_api(provider['passengers'],provider['pnr'])
        provider_obj.action_booked_api_train(provider, context)

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
                    this_segment_fare_details = []
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

                    for fare in param_segment['fares']:
                        provider_obj.create_service_charge(fare['service_charges'])
                        for addons in fare['fare_details']:
                            addons['description'] = json.dumps(addons['description'])
                            addons['segment_id'] = segment.id
                            this_segment_fare_details.append((0,0,addons))

                    segment.write({
                        'leg_ids': this_segment_legs,
                        'cabin_class': param_segment.get('fares')[0].get('cabin_class',''),
                        'class_of_service': param_segment.get('fares')[0].get('class_of_service',''),
                        'segment_addons_ids': this_segment_fare_details
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