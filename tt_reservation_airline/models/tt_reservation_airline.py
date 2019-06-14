from odoo import api,models,fields, _
from ...tt_base.models.destinations import TRANSPORT_TYPE_TO_DESTINATION_TYPE
from ...tools import util
import logging,traceback
import datetime
import copy



#controller
#booking
#update pnr
#update tb seat
#issued

_logger = logging.getLogger(__name__)

BOOKING_STATE = [
    ('draft', 'New'),
    ('confirm', 'Confirmed'),
    ('cancel', 'Cancelled'),
    ('cancel2', 'Expired'),
    ('error', 'Connection Loss'), #diganti failed issue
    ('fail_booking', 'Failed (Book)'),
    ('booked', 'Booked'),
    ('partial_booked', 'Partial Booked'),
    ('in_progress', 'In Progress'),
    ('fail_issue', 'Failed (Issue)'),
    ('partial_issued', 'Partial Issued'),
    ('issued', 'Issued'),
    ('done', 'Done'),
    ('fail_refunded', 'Failed (REFUNDED)'),
    ('refund', 'Refund'),
    ('reroute', 'Reroute'), #diganti reissue
]

JOURNEY_DIRECTION = [('OW', 'One Way'), ('RT', 'Return')]


class ReservationAirline(models.Model):

    _name = "tt.reservation.airline"
    _inherit = "tt.reservation"
    _order = "id desc"


    direction = fields.Selection(JOURNEY_DIRECTION, string='Direction', default='OW', required=True, readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True, states={'draft': [('readonly', False)]})
    sector_type = fields.Char('Sector', readonly=True, compute='_compute_sector_type', store=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'booking_airline_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})


    passenger_ids = fields.Many2many('tt.customer', 'tt_reservation_airline_passengers_rel', 'booking_id', 'passenger_id',
                                     string='List of Passenger', readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', domain=[('res_model','=','tt.reservation.airline')])

    provider_booking_ids = fields.One2many('tt.tb.provider.airline', 'booking_id', string='Provider Booking', readonly=True, states={'draft': [('readonly', False)]})

    journey_ids = fields.One2many('tt.tb.journey.airline', 'booking_id', 'Journeys', readonly=True, states={'draft': [('readonly', False)]})
    segment_ids = fields.One2many('tt.tb.segment.airline', 'booking_id', string='Segments',
                                  readonly=True, states={'draft': [('readonly', False)]})

    provider_type = fields.Many2one('tt.provider.type','Provider Type',
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


    @api.one
    def action_draft(self):
        self.state = 'draft'


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
        pass


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
    def validate_issue(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise Exception('User NOT FOUND...')
        if user_obj.agent_id.id != self.agent_id.id:
            raise Exception('Invalid order...')
        #fixme uncomment later
        #
        # if user_obj.agent_id.agent_type_id.id == self.env.ref('tt_base_rodex.agent_type_ho').id:
        #     raise Exception('User HO cannot Issuing...')

        return True


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

    param_contact_data = {
        "first_name": "Contact Satu",
        "last_name": "Testing",
        "country_code": "ID",
        "nationality_code": "ID",
        "title": "MR",
        "work_phone": "0218531246",
        "company_city_1": "SURABAYA",
        "company_phone_2": "62315662000",
        "company_phone_1": "62315662000",
        "company_email_2": "rodexbooking@gmail.com",
        "mobile": "628123456789",
        "company_email_1": "booking@rodextravel.tours",
        "company_postal_code": "60241",
        "home_phone": "0218531246",
        "company_country_1": "ID",
        "company_state_1": "JTM",
        "email": "test@skytors.id",
        "company_address_1": "JL. RAYA DARMO 177B"
    }

    param_passenger_data = [
        {
            "country_of_issued_code": "ID",
            "first_name": "Adult Satu",
            "last_name": "Testing",
            "pax_type": "ADT",
            "nationality_code": "ID",
            "title": "MR",
            "gender": "male",
            "passenger_number": 0,
            "passport_expdate": "2020-06-16",
            "birth_date": "1990-06-16",
            "passport_issued_date": "2010-06-16",
            "partner_id": False,
            "passenger_id": False,
            "passport_number": "BO31254"
        },
        {
            "country_of_issued_code": "ID",
            "first_name": "Adult Dua",
            "last_name": "Testing",
            "pax_type": "ADT",
            "nationality_code": "ID",
            "title": "MRS",
            "gender": "female",
            "passenger_number": 1,
            "passport_expdate": "2020-06-16",
            "birth_date": "1990-06-16",
            "passport_issued_date": "2010-06-16",
            "partner_id": False,
            "passenger_id": False,
            "passport_number": "BG31254"
        },
        {
            "country_of_issued_code": "ID",
            "first_name": "Child Satu",
            "last_name": "Testing",
            "pax_type": "CHD",
            "nationality_code": "ID",
            "title": "MSTR",
            "gender": "male",
            "passenger_number": 2,
            "passport_expdate": "2020-06-16",
            "birth_date": "2010-06-16",
            "passport_issued_date": "2010-06-16",
            "partner_id": False,
            "passenger_id": False,
            "passport_number": "GO31254"
        }
    ]

    param_search_RQ = {
        "origin": "SUB",
        "direction": "RT",
        "cabin_class": "Y",
        "departure_date": "2019-07-15 00:00:00",
        "destination": "DPS",
        "infant": 0,
        "is_international_flight": False,
        "adult": 2,
        "child": 1,
        "provider": "sabre",
        "return_date": "2019-07-22 23:59:59"
    }

    param_select_RQ = {
        "agent_voucher_code": "",
        "promotion_codes_request": [],
        "paxs": {
            "INF": 0,
            "CHD": 1,
            "ADT": 2
        },
        "journeys_booking": [
            {
                "segments": [
                    {
                        "fare_code": "Y",
                        "leg_codes": "GA,338,SUB,DPS,2019-07-15 17:10:00,2019-07-15 19:15:00,,,,,sabre/GA",
                        "provider": "sabre",
                        "segment_code": "GA,338,SUB,DPS,2019-07-15 17:10:00,2019-07-15 19:15:00,,,,,sabre/GA"
                    },
                    {
                        "fare_code": "Y",
                        "leg_codes": "GA,347,DPS,SUB,2019-07-22 13:55:00,2019-07-22 14:20:00,,,,,sabre/GA",
                        "provider": "sabre",
                        "segment_code": "GA,347,DPS,SUB,2019-07-22 13:55:00,2019-07-22 14:20:00,,,,,sabre/GA"
                    }
                ],
                "journey_type": "DP"
            }
        ]
    }

    param_context = {
        "is_company_website": True,
        "uid": 22,
        "remote_addr": "127.0.0.1",
        "transport_type": "airline",
        "sid": "e942085ff9e63fd86d3562834c5c3c0d4344a290",
        "expire_time": 1556763471.900867,
        "api_key": "c2bafdb6-1eca-449a-ac2f-3e38118e908e",
        "error_code": 0,
        "error_msg": False,
        "co_uid": 8
    }

    param_pax = {
        'ADT': 2,
        'CHD': 1,
        'INF': 0
    }

    param_book_info = {
        "status": "BOOKED",
        "balance_due": 5041500,
        "pnr": "BKBFIL",
        "hold_date": "2020-05-02 02:51:29",
        "currency": "IDR",
        "total": 5041500
    }

    param_provider = 'sabre'

    param_provider_sequence = 1

    param_passenger_ids = [
        {
            "first_name": "Customer",
            "last_name": "Limo",
            "name": "Customer LIMOOO",
            "ticket_number": "AEXPR020800000001"
        }
    ]

    param_get_booking_2 = {
        "error_code": 0,
        "error_msg": False,
        "response": {
            "status": "BOOKED",
            "journeys": [],
            "pnr": "UDNKEW",
            "hold_date": "2020-05-07 03:45:00",
            "currency": "IDR",
            "expired_date": "2019-05-07 03:45:00",
            "total": 5041500,
            "balance_due": 5041500,
            "passengers": [],
            "contacts": [],
            "segments": [
                {
                    "origin": "SUB",
                    "segment_code": "GA,0338,SUB,DPS,2019-07-15 17:10:00,2019-07-15 19:15:00,,,,,",
                    "destination": "DPS",
                    "origin_terminal": "2",
                    "sequence": 0,
                    "operating_airline_code": "GA",
                    "departure_date": "2019-07-15 17:10:00",
                    "destination_terminal": "D",
                    "carrier_number": "0338",
                    "free_baggage": "",
                    "airline_pnr_ref": "DCGA*VEADUV",
                    "segment_code2": "SUB-DPS",
                    "carrier_name": "GA0338",
                    "equipment_type": "CRK",
                    "transit_count": 0,
                    "free_meal": "",
                    "arrival_date": "2019-07-15 19:15:00",
                    "transit_duration": "0h 0m",
                    "is_international_flight": "false",
                    "journey_type": "",
                    "carrier_code": "GA",
                    "elapsed_time": "00:00",
                    "provider": "",
                    "fares": [],
                    "legs": []
                },
                {
                    "origin": "DPS",
                    "segment_code": "GA,0347,DPS,SUB,2019-07-22 13:55:00,2019-07-22 14:20:00,,,,,",
                    "destination": "SUB",
                    "origin_terminal": "D",
                    "sequence": 1,
                    "operating_airline_code": "GA",
                    "departure_date": "2019-07-22 13:55:00",
                    "destination_terminal": "2",
                    "carrier_number": "0347",
                    "free_baggage": "",
                    "airline_pnr_ref": "DCGA*VEADUV",
                    "segment_code2": "DPS-SUB",
                    "carrier_name": "GA0347",
                    "equipment_type": "738",
                    "transit_count": 0,
                    "free_meal": "",
                    "arrival_date": "2019-07-22 14:20:00",
                    "transit_duration": "6d 18h 40m",
                    "is_international_flight": "false",
                    "journey_type": "",
                    "carrier_code": "GA",
                    "elapsed_time": "00:00",
                    "provider": "",
                    "fares": [],
                    "legs": []
                }
            ],
            "service_charge_summary": [
                {
                    "service_charges": [
                        {
                            "description": "Base Fare",
                            "sequence": 0,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 2956000,
                            "foreign_amount": 1478000,
                            "charge_type": "",
                            "charge_code": "fare",
                            "pax_count": 2,
                            "amount": 1478000
                        },
                        {
                            "description": "",
                            "sequence": 1,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 380000,
                            "foreign_amount": 0,
                            "charge_type": "",
                            "charge_code": "D5",
                            "pax_count": 2,
                            "amount": 190000
                        },
                        {
                            "description": "",
                            "sequence": 2,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 295600,
                            "foreign_amount": 0,
                            "charge_type": "",
                            "charge_code": "ID",
                            "pax_count": 2,
                            "amount": 147800
                        },
                        {
                            "charge_type": "",
                            "description": "R.OC",
                            "sequence": 2,
                            "amount": 5810.560000000056,
                            "charge_code": "r.oc",
                            "pax_count": 2,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 11621.120000000112,
                            "foreign_amount": 5810.560000000056
                        },
                        {
                            "charge_type": "R.AC",
                            "foreign_currency": "IDR",
                            "description": "R.AC",
                            "sequence": 2,
                            "commision_agent_id": 2,
                            "charge_code": "r.ac",
                            "pax_count": 2,
                            "currency": "IDR",
                            "amount": -100720.25600000005,
                            "pax_type": "ADT",
                            "total": -201440.5120000001,
                            "foreign_amount": -100720.25600000005
                        }
                    ],
                    "flight_code": "GA",
                    "pax_type": "ADT"
                },
                {
                    "service_charges": [
                        {
                            "description": "Base Fare",
                            "sequence": 0,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 1109000,
                            "foreign_amount": 1109000,
                            "charge_type": "",
                            "charge_code": "fare",
                            "pax_count": 1,
                            "amount": 1109000
                        },
                        {
                            "description": "",
                            "sequence": 1,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 190000,
                            "foreign_amount": 0,
                            "charge_type": "",
                            "charge_code": "D5",
                            "pax_count": 1,
                            "amount": 190000
                        },
                        {
                            "description": "",
                            "sequence": 2,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 110900,
                            "foreign_amount": 0,
                            "charge_type": "",
                            "charge_code": "ID",
                            "pax_count": 1,
                            "amount": 110900
                        },
                        {
                            "charge_type": "",
                            "description": "R.OC",
                            "sequence": 2,
                            "amount": 4511.679999999935,
                            "charge_code": "r.oc",
                            "pax_count": 1,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 4511.679999999935,
                            "foreign_amount": 4511.679999999935
                        },
                        {
                            "charge_type": "R.AC",
                            "foreign_currency": "IDR",
                            "description": "R.AC",
                            "sequence": 2,
                            "commision_agent_id": 2,
                            "charge_code": "r.ac",
                            "pax_count": 1,
                            "currency": "IDR",
                            "amount": -75498.36800000002,
                            "pax_type": "CHD",
                            "total": -75498.36800000002,
                            "foreign_amount": -75498.36800000002
                        }
                    ],
                    "flight_code": "GA",
                    "pax_type": "CHD"
                }
            ],
            "sale_service_charge_summary": [
                {
                    "service_charges": [
                        {
                            "charge_type": "",
                            "description": "Basis Fare",
                            "sequence": 2,
                            "amount": 1478000,
                            "charge_code": "fare",
                            "pax_count": 2,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 2956000,
                            "foreign_amount": 1478000
                        },
                        {
                            "charge_type": "",
                            "foreign_currency": "IDR",
                            "description": "Tax - All Tax",
                            "sequence": 2,
                            "charge_code": "tax",
                            "pax_count": 2,
                            "currency": "IDR",
                            "amount": 337800,
                            "pax_type": "ADT",
                            "total": 675600,
                            "foreign_amount": 337800
                        },
                        {
                            "charge_type": "",
                            "description": "R.OC",
                            "sequence": 2,
                            "amount": 5810.560000000056,
                            "charge_code": "r.oc",
                            "pax_count": 2,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "ADT",
                            "total": 11621.120000000112,
                            "foreign_amount": 5810.560000000056
                        },
                        {
                            "charge_type": "R.AC",
                            "foreign_currency": "IDR",
                            "description": "R.AC",
                            "sequence": 2,
                            "commision_agent_id": 2,
                            "charge_code": "r.ac",
                            "pax_count": 2,
                            "currency": "IDR",
                            "amount": -100720.25600000005,
                            "pax_type": "ADT",
                            "total": -201440.5120000001,
                            "foreign_amount": -100720.25600000005
                        }
                    ],
                    "pax_type": "ADT"
                },
                {
                    "service_charges": [
                        {
                            "charge_type": "",
                            "description": "Basis Fare",
                            "sequence": 2,
                            "amount": 1109000,
                            "charge_code": "fare",
                            "pax_count": 1,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 1109000,
                            "foreign_amount": 1109000
                        },
                        {
                            "charge_type": "",
                            "foreign_currency": "IDR",
                            "description": "Tax - All Tax",
                            "sequence": 2,
                            "charge_code": "tax",
                            "pax_count": 1,
                            "currency": "IDR",
                            "amount": 300900,
                            "pax_type": "CHD",
                            "total": 300900,
                            "foreign_amount": 300900
                        },
                        {
                            "charge_type": "",
                            "description": "R.OC",
                            "sequence": 2,
                            "amount": 4511.679999999935,
                            "charge_code": "r.oc",
                            "pax_count": 1,
                            "currency": "IDR",
                            "foreign_currency": "IDR",
                            "pax_type": "CHD",
                            "total": 4511.679999999935,
                            "foreign_amount": 4511.679999999935
                        },
                        {
                            "charge_type": "R.AC",
                            "foreign_currency": "IDR",
                            "description": "R.AC",
                            "sequence": 2,
                            "commision_agent_id": 2,
                            "charge_code": "r.ac",
                            "pax_count": 1,
                            "currency": "IDR",
                            "amount": -75498.36800000002,
                            "pax_type": "CHD",
                            "total": -75498.36800000002,
                            "foreign_amount": -75498.36800000002
                        }
                    ],
                    "pax_type": "CHD"
                }
            ]
        }
    }

    def create_booking(self, contact_data, passengers, pax, searchRQ, select_buyRQ, context):
        contact_data = copy.deepcopy(self.param_contact_data)
        passengers = copy.deepcopy(self.param_passenger_data)
        pax = copy.deepcopy(self.param_pax)
        searchRQ = copy.deepcopy(self.param_search_RQ)
        select_buyRQ = copy.deepcopy(self.param_select_RQ)
        context = copy.deepcopy(self.param_context)

        ##SEMENTARA DI SINIII, NANTI DARI GATEWAY SUDAH BENAR SENDIRI
        context.update({
            'co_uid': self.env.user.id
        })

        try:
            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            self.validate_booking(api_context=context)
            try:
                agent_id = contact_data.get('agent_id') and int(contact_data.get('agent_id')) or False
            except:
                agent_id = False

            context = self.update_api_context(agent_id, context)


            if not context['agent_id']:
                raise Exception(_('Create booking failure, Customer or User, not have Agent (Agent ID)\n'
                                'Please contact Administrator, to complete the data !'))



            header_val = self._prepare_booking(searchRQ, pax, context)
            contact_obj = self._create_contact(contact_data, context)
            psg_ids = self._create_passengers(passengers, contact_obj, context)
            header_val.update({
                'contact_id': contact_obj.id,
                'passenger_ids': [(6, 0, psg_ids)],
                'sid': context['sid'],
                'display_mobile': contact_obj.mobile,
            })

            # create header & Update SUB_AGENT_ID
            book_obj = self.create(header_val)
            # book_obj.sub_agent_id = contact_data.get('agent_id', book_obj.agent_id.id)
            # self._create_book_provider(select_buyRQ, book_obj.id, context)
            # With Leg
            voucher_code = select_buyRQ.get('agent_voucher_code')
            if voucher_code:
                voucher_obj = self.env['tt.promo.voucher'].search([('voucher_code', '=', str(voucher_code))], limit=1)
                if voucher_obj:
                    voucher_obj = voucher_obj[0]
                    self.env['tt.tb.service.charge'].create({
                        'charge_code': 'disc',
                        'charge_type': 'VOUCHER',
                        'currency_id': voucher_obj.currency_id.id,
                        'amount': voucher_obj.amount * -1,
                        'pax_count': 1,
                        'pax_type': 'ADT',
                        'description': str(voucher_code),
                        'booking_id': book_obj.id
                    })

            provider_id_dict = self._create_book_provider_2(select_buyRQ, book_obj.id, context)

            book_obj.action_set_segments_sequence()

            self.env.cr.commit()

            book_info = copy.deepcopy(self.param_book_info)

            self.update_provider_pnr(book_obj.id,self.param_provider,self.param_provider_sequence,book_info,context)


            return {
                'error_code': 0,
                'error_msg': 'Success',
                'order_id': book_obj.id,
                'provider_id_dict': provider_id_dict,
                'order_number': book_obj.name,
            }
        except Exception as e:
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def validate_booking(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise Exception('User NOT FOUND...')
        return True

    def create_booking_test(self):
        contact_data = copy.deepcopy(self.param_contact_data)
        passengers = copy.deepcopy(self.param_passenger_data)
        pax = copy.deepcopy(self.param_pax)
        searchRQ = copy.deepcopy(self.param_search_RQ)
        select_buyRQ = copy.deepcopy(self.param_select_RQ)
        context = copy.deepcopy(self.param_context)

        ##SEMENTARA DI SINIII, NANTI DARI GATEWAY SUDAH BENAR SENDIRI
        context.update({
            'co_uid': self.env.user.id
        })

        try:
            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            self.validate_booking(api_context=context)
            try:
                agent_id = contact_data.get('agent_id') and int(contact_data.get('agent_id')) or False
            except:
                agent_id = False
            context = self.update_api_context(agent_id, context)

            if not context['agent_id']:
                raise Exception(('Create booking failure, Customer or User, not have Agent (Agent ID)\n'
                                'Please contact Administrator, to complete the data !'))

            header_val = self._prepare_booking(searchRQ, pax, context)
            contact_obj = self._create_contact(contact_data, context)
            psg_ids = self._create_passengers(passengers, contact_obj, context)
            header_val.update({
                'contact_id': contact_obj.id,
                'passenger_ids': [(6, 0, psg_ids)],
                'sid': context['sid'],
                # 'display_mobile': contact_obj.phone_ids[0],
            })

            # create header & Update SUB_AGENT_ID
            book_obj = self.create(header_val)

            # book_obj.sub_agent_id = contact_data.get('agent_id', book_obj.agent_id.id)
            # self._create_book_provider(select_buyRQ, book_obj.id, context)
            # With Leg

            ##fixme di comment dahulu
            # voucher_code = select_buyRQ.get('agent_voucher_code')
            # if voucher_code:
            #     voucher_obj = self.env['tt.promo.voucher'].search([('voucher_code', '=', str(voucher_code))],
            #                                                       limit=1)
            #     if voucher_obj:
            #         voucher_obj = voucher_obj[0]
            #         self.env['tt.tb.service.charge'].create({
            #             'charge_code': 'disc',
            #             'charge_type': 'VOUCHER',
            #             'currency_id': voucher_obj.currency_id.id,
            #             'amount': voucher_obj.amount * -1,
            #             'pax_count': 1,
            #             'pax_type': 'ADT',
            #             'description': str(voucher_code),
            #             'booking_id': book_obj.id
            #         })

            provider_id_dict = self._create_book_provider_2(select_buyRQ, book_obj.id, context)

            book_obj.action_set_segments_sequence()

            self.env.cr.commit()

            book_info = copy.deepcopy(self.param_book_info)
            # self._create_tb_seat_TRAIN(book_obj,book_info)

            self.update_provider_pnr(book_obj.id,self.param_provider,self.param_provider_sequence,book_info,context)

            return {
                'error_code': 0,
                'error_msg': 'Success',
                'order_id': book_obj.id,
                'provider_id_dict': provider_id_dict,
                'order_number': book_obj.name,
            }

        except Exception as e:
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            print(e)
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def _prepare_booking(self, searchRQ, pax, context_gateway):

        dest_obj = self.env['tt.destinations']
        booking_tmp = {
            'direction': searchRQ['direction'],
            'departure_date': searchRQ['departure_date'],
            'return_date': searchRQ['return_date'],
            'origin': searchRQ['origin'],
            'destination': searchRQ['destination'],
            'transport_type': context_gateway['transport_type'],##masih perlukah?
            'destination_type': context_gateway['transport_type'],##fixme
            'adult': pax['ADT'],
            'child': pax['CHD'],
            'infant': pax['INF'],
            'agent_id': context_gateway['agent_id'],
            'sub_agent_id': context_gateway['sub_agent_id'],
            'user_id': context_gateway['co_uid'],
        }


        booking_tmp.update({
            'origin_id': dest_obj.get_id(searchRQ['origin'], self.provider_type),
            'destination_id': dest_obj.get_id(searchRQ['destination'], self.provider_type),
        })

        return booking_tmp

    def _create_contact(self, vals, context):
        country_obj = self.env['res.country'].sudo()
        contact_obj = self.env['tt.customer'].sudo()
        if vals.get('contact_id'):
            vals['contact_id'] = int(vals['contact_id'])
            contact_rec = contact_obj.browse(vals['contact_id'])
            if contact_rec:
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                })
            return contact_rec

        # country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
        # vals['nationality_id'] = country and country[0].id or False

        if context['booker_type'] in ['COR', 'POR']:
            vals['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]

        country = country_obj.search([('code', '=', vals.pop('country_code'))])
        vals.update({
            'booker_mobile': vals.get('mobile', ''),
            'commercial_agent_id': context['agent_id'],
            'agent_id': context['agent_id'],
            'country_id': country and country[0].id or False,
            'pax_type': 'ADT',
            'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
            'mobile_orig': vals.get('mobile', ''),
            'email': vals.get('email', vals['email']),
            'mobile': vals.get('mobile', vals['mobile']),
        })
        return contact_obj.create(vals)

    def _create_passengers(self, passengers, contact_obj, context):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()
        res_ids = []
        for psg in passengers:
            # country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            # psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False

            vals_for_update = {}
            update_list = ['passport_number', 'passport_expdate', 'nationality_id', 'country_of_issued_id', 'passport_issued_date', 'identity_type', 'identity_number', 'birth_date']
            [vals_for_update.update({
                key: psg[key]
            }) for key in update_list if psg.get(key)]

            psg_exist = False
            if 'passenger_id' in psg:
                psg['passenger_id'] = int(psg['passenger_id'])
                passenger_obj = self.env['tt.customer'].sudo().browse(psg['passenger_id'])
                if passenger_obj:
                    psg_exist = True
                    # if context['booker_type'] == 'COR/POR':
                    #     vals_for_update['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]
                    passenger_obj.write(vals_for_update)
                    res_ids.append(passenger_obj.id)
            if not psg_exist:
                # Cek Booker sama dengan Passenger
                if [psg['title'], psg['first_name'], psg['last_name']] == [contact_obj.title, contact_obj.first_name, contact_obj.last_name]:
                    contact_obj.write(vals_for_update)
                    psg_exist = True
                    res_ids.append(contact_obj.id)

            if not psg_exist:
                if context['booker_type'] == 'COR/POR':
                    psg['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]
                    psg['agent_id'] = context['sub_agent_id']
                else:
                    psg['agent_id'] = context['agent_id']

                psg.update({
                    'commercial_agent_id': context['agent_id'],
                    'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone:</span>'.format(**psg),
                })
                psg_obj = passenger_obj.create(psg)
                res_ids.append(psg_obj.id)
        return res_ids


    def _create_book_provider_2(self, select_buyRQ, booking_id, api_context):
        dest_obj = self.env['tt.destinations']
        provider_booking_obj = self.env['tt.tb.provider.airline']
        journey_obj = self.env['tt.tb.journey.airline']
        segment_obj = self.env['tt.tb.segment.airline']
        carrier_obj = self.env['tt.transport.carrier']
        country_obj = self.env['res.country']
        leg_obj = self.env['tt.tb.leg.airline']
        _destination_type = self.provider_type
        _carrier_type = api_context['transport_type']
        # _logger.info('TEST select_buyRQ : %s' % json.dumps(select_buyRQ))
        # ======== process : Group By PROVIDER base on DP RT ======
        book_providers, provider_ids = util._jouneys_booking_groupby_provider_2(select_buyRQ['journeys_booking'])
        leg_sequence = 1

        country_data_obj = country_obj.sudo().search([('code', '=', 'ID')], limit=1)

        res = {}

        for provider in provider_ids:
            direction = 'OW'
            for provider_sequence in book_providers[provider].keys():
                provider_booking = {
                    'direction': direction,
                    'provider': provider,
                    'booking_id': booking_id,
                    'sequence': provider_sequence,
                }
                provider_booking_obj = provider_booking_obj.create(provider_booking)

                segments_DP = []
                segments_RT = []
                for seg in book_providers[provider][provider_sequence]:
                    if seg['journey_type'] == 'RT':
                        segments_RT.append(seg)
                    else:
                        segments_DP.append(seg)

                jrnl_idx = 0
                journey_ids = []
                seg_jrnl = []
                if segments_DP:
                    jrnl_idx += 1
                    jrn_val = {
                        'provider': provider,
                        'sequence': jrnl_idx,
                        'origin': segments_DP[0]['origin'],
                        'destination': segments_DP[-1]['destination'],
                        'departure_date': segments_DP[0]['departure_date'],
                        'arrival_date': segments_DP[0]['arrival_date'],
                        'journey_type': 'DP',
                        'provider_booking_id': provider_booking_obj.id,
                    }
                    journey_ids.append(jrn_val)
                    journey_obj = journey_obj.create(jrn_val)
                    for seg in segments_DP:
                        carrier_id = carrier_obj.get_id(seg['carrier_code'], _carrier_type)
                        if _carrier_type == 'train':
                            carrier_name = seg['fare_code'].split(',')[3]
                            if not carrier_id:
                                data = carrier_obj.create({
                                    'name': carrier_name,
                                    'transport_type': _carrier_type,
                                    'code': seg['carrier_code'],
                                    'country_id': country_data_obj.id,
                                })
                                carrier_id = data.id
                            else:
                                carrier_data = carrier_obj.sudo().browse(carrier_id)
                                if carrier_data.name != carrier_name:
                                    _logger.error('{} || {}'.format(carrier_data.name, carrier_name))
                                    carrier_data.write({
                                        'name': carrier_name
                                    })

                                if seg['carrier_name'] != carrier_name:
                                    seg['carrier_name'] = carrier_name

                        seg_jrnl.append(seg)
                        seg.pop('provider_sequence')
                        seg.update({
                            'journey_id': journey_obj.id,
                            'origin_id': dest_obj.get_id(seg['origin'], _destination_type),
                            'destination_id': dest_obj.get_id(seg['destination'], _destination_type),
                            'carrier_id': carrier_id,
                            # 'carrier_type': 'ariline',
                            # todo: set route_id
                        })
                        seg_obj = segment_obj.sudo().create(seg)
                        for leg_idx, leg in enumerate(seg['legs']):
                            leg.update({
                                'segment_id': seg_obj.id,
                                'sequence': leg_idx + 1,
                                'leg_id': seg_obj.id,
                                'origin_id': leg['origin'] and dest_obj.get_id(leg['origin'],
                                                                               _destination_type) or False,
                                'destination_id': leg['destination'] and dest_obj.get_id(leg['destination'],
                                                                                         _destination_type) or False,
                                'carrier_id': carrier_id,
                                # 'carrier_type': 'ariline',
                                # todo: set route_id
                            })

                            if _carrier_type == 'train':
                                leg['carrier_name'] = seg['fare_code'].split(',')[3]
                            leg_obj.sudo().create(leg)

                seg_jrnl = []
                if segments_RT:
                    direction = 'RT'
                    jrnl_idx += 1
                    jrn_val = {
                        'provider': provider,
                        'sequence': jrnl_idx,
                        'origin': segments_RT[0]['origin'],
                        'destination': segments_RT[-1]['destination'],
                        'departure_date': segments_RT[0]['departure_date'],
                        'arrival_date': segments_RT[0]['arrival_date'],
                        'journey_type': 'RT',
                        'provider_booking_id': provider_booking_obj.id,
                    }
                    journey_ids.append(jrn_val)
                    journey_obj = journey_obj.create(jrn_val)
                    for seg in segments_RT:
                        carrier_id = carrier_obj.get_id(seg['carrier_code'], _carrier_type)
                        if _carrier_type == 'train':
                            carrier_name = seg['fare_code'].split(',')[3]
                            if not carrier_id:
                                data = carrier_obj.create({
                                    'name': carrier_name,
                                    'transport_type': _carrier_type,
                                    'code': seg['carrier_code'],
                                    'country_id': country_data_obj.id,
                                })
                                carrier_id = data.id
                            else:
                                carrier_data = carrier_obj.sudo().browse(carrier_id)
                                if carrier_data.name != carrier_name:
                                    carrier_data.write({
                                        'name': carrier_name
                                    })
                        seg_jrnl.append(seg)
                        # seg.pop('provider_group')
                        seg.update({
                            'journey_id': journey_obj.id,
                            'origin_id': dest_obj.get_id(seg['origin'], _destination_type),
                            'destination_id': dest_obj.get_id(seg['destination'],_destination_type),
                            'carrier_id': carrier_id,
                            # todo: set route_id
                        })
                        seg_obj = segment_obj.sudo().create(seg)
                        for leg_idx, leg in enumerate(seg['legs']):
                            leg.update({
                                'segment_id': seg_obj.id,
                                'sequence': leg_idx + 1,
                                'leg_id': seg_obj.id,
                                'origin_id': leg['origin'] and dest_obj.get_id(leg['origin'],
                                                                               _destination_type) or False,
                                'destination_id': leg['destination'] and dest_obj.get_id(leg['destination'],
                                                                                         _destination_type) or False,
                                'carrier_id': carrier_id,
                                # todo: set route_id
                            })
                            leg_obj.sudo().create(leg)

                voucher_code = select_buyRQ.get('agent_voucher_code')
                if voucher_code:
                    voucher_obj = self.env['tt.promo.voucher'].search([('voucher_code', '=', str(voucher_code))],
                                                                      limit=1)
                    if voucher_obj:
                        voucher_obj = voucher_obj[0]
                        self.env['tt.tb.service.charge'].create({
                            'charge_code': 'disc',
                            'charge_type': 'VOUCHER',
                            'currency_id': voucher_obj.currency_id.id,
                            'amount': voucher_obj.amount * -1,
                            'pax_count': 1,
                            'pax_type': 'ADT',
                            'description': str(voucher_code),
                            'provider_booking_id': provider_booking_obj.id
                        })

                # ======== Update PROVIDER BOOKING =========
                provider_booking = {
                    'direction': direction,
                    'origin': journey_ids[0]['origin'],
                    'destination': journey_ids[0]['destination'],
                    'departure_date': journey_ids[0]['departure_date'],
                    'return_date': journey_ids[-1]['departure_date'],
                }
                provider_booking_obj.write(provider_booking)
                if not res.get(provider):
                    res[provider] = {}
                res[provider].update({
                    str(provider_sequence): provider_booking_obj.id
                })
        return res

    def action_set_segments_sequence(self):
        # provider_list = sorted([prov for prov in self.provider_booking_ids], key=lambda r: datetime.strptime(r.departure_date, '%Y-%m-%d %H:%M:%S'))
        segment_list = sorted([seg for seg in self.segment_ids], key=lambda r: datetime.datetime.strptime(r.departure_date, '%Y-%m-%d %H:%M:%S'))
        leg_list = [leg for seg in segment_list for leg in seg.leg_ids]
        [seg.write({'sequence': idx+1}) for idx, seg in enumerate(segment_list)]
        [leg.write({'sequence': idx+1}) for idx, leg in enumerate(leg_list)]

    def update_api_context(self, sub_agent_id, context):
        context['co_uid'] = int(context['co_uid'])
        user_obj = self.env['res.users'].sudo().browse(context['co_uid']) ##frontend credential
        #if int(context['co_uid']) == 744:
        #    _logger.error('JUST Test : "Anta Utama" ' +  str(context))

        if context['is_company_website']:
            #============================================
            #====== Context dari WEBSITE/FRONTEND =======
            #============================================
            if user_obj.agent_id.agent_type_id.id in \
                    (12,13):
                # ===== COR/POR User =====
                context.update({
                    'agent_id': user_obj.agent_id.parent_agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif sub_agent_id:
                # ===== COR/POR in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': sub_agent_id,
                    'booker_type': 'COR/POR',
                })

            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })

        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context

    def _create_tb_seat_TRAIN(self, book_obj, book_info):
        seat_obj = self.env['tt.tb.seat.airline']
        for idx, seat in enumerate(book_info['seats']):
            psg = book_obj.passenger_ids[idx]
            seat_obj.create({
                'segment_id': book_obj.segment_ids[0].id,
                'passenger_id': psg.id,
                'seat': seat['wagon_name'] + '/' + seat['seat_no'],
            })


    def action_get_provider_booking_info(self):
        hold_date = False
        pnr = set()
        for rec in self.provider_booking_ids:
            if rec.pnr:
                pnr = pnr.union([rec.pnr])
            try:
                #punya pak edy
                # rec_hold_date = datetime.datetime.strptime(rec.hold_date[:19], '%Y-%m-%d %H:%M:%S')
                # if not hold_date:
                #     hold_date = rec.hold_date
                # else:
                #     hold_date = rec_hold_date if hold_date > rec_hold_date else hold_date
                hold_date = rec.hold_date
            except:
                pass
        res = {
            'hold_date': hold_date,
            'pnr': ', '.join(pnr),
        }
        return res

    @api.one
    def action_booked(self, api_context=None):
        if not api_context:
            api_context = {
                'co_uid': self.provider_booking_ids[0].booked_uid.id
            }
        if self.name == 'New':
            now_date = datetime.datetime.now()
            hold_date = now_date + datetime.timedelta(minutes=30)
            self.write({
                'name': self.env['ir.sequence'].next_by_code('dummy.airline'),
                'state': 'partial_booked',
                'booked_uid': api_context['co_uid'],
                'booked_date': now_date,
                'hold_date': hold_date,
                'expired_date': hold_date,
            })

class ReservationAirlineApi(models.Model):
    _inherit = 'tt.reservation.airline'

    def update_provider_pnr(self, booking_id, provider, provider_sequence, book_info, api_context):

        try:
            provider_obj = self.env['tt.tb.provider.airline'].search(
                [('booking_id', '=', booking_id), ('provider', '=', provider), ('sequence', '=', provider_sequence)])
            booking_obj = self.browse(booking_id)


            # self._create_tb_seat_TRAIN(booking_obj, book_info)000


            provider_obj.action_booked(book_info['pnr'], api_context)
            # booking_obj.action_booked()
            self._cr.commit()

            kwargs = {
                'book_info': book_info,
                'direction': booking_obj.direction  #for compute r.ac per pax/route(OW/RT)
            }



            res = booking_obj._update_service_charges(book_info['pnr'], provider_obj, api_context, **kwargs)

            if res['error_code'] != 0:
                raise Exception(res['error_msg'])

            # Jika semua provider_booking sudah booked, maka transport_booked.state = booked

            return {
                'error_code': 0,
                'error_msg': 'Success',
                'order_number': booking_obj.name,
                'status': 'booked',
            }

        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nUpdate PNR failure'
            }

    @api.one
    def _create_service_charge_sale(self, provider_name, sale_service_charge_summary):
        # self.sale_service_charge_ids
        service_chg_obj = self.env['tt.service.charge']
        for scs in sale_service_charge_summary:
            for val in scs['service_charges']:
                if val['amount']:
                    val.update({
                        'booking_airline_id': self.id,
                        'description': provider_name
                    })
                    val['booking_id'] = self.id
                    service_chg_obj.create(val)

    def _update_service_charges(self, pnr, provider_obj, api_context=None, **kwargs):
        self.ensure_one()
        # Fungsi melakukan insert service_charge per porvider
        if not api_context:
            api_context['co_uid'] = self.env.user.id

        try:
            #later for now hard coded
            # res = self.get_booking2(pnr, provider_obj.provider, kwargs['direction'], self.sid, api_context)
            res = copy.deepcopy(self.param_get_booking_2)

            if res['error_code'] != 0:
                raise Exception(res['result']['error_msg'])

            # res = res['result']['response']
            res = res['response']

            provider_obj.sudo().write({
                'hold_date': res['hold_date'],
                'expired_date': res.get('expired_date'),
                'notes': res.get('notes'),
                'pnr': pnr,
            })

            segments = res.get('segments', [])
            seg_count = 0
            is_available = True if seg_count < len(segments) else False
            if 'sabre' in provider_obj.provider:
                for journey in provider_obj.journey_ids:
                    for seg in journey.segment_ids:
                        if is_available:
                            seg.sudo().write({
                                'airline_pnr_ref': segments[seg_count].get('airline_pnr_ref')
                            })
                            seg_count += 1
                            is_available = True if seg_count < len(segments) else False

            if not res['service_charge_summary']:
                return {
                    'error_code': 0,
                    'error_msg': 'Success, But not service_charge_summary',
                    'state': 'booked'
                }
            provider_obj._create_service_charge(res['service_charge_summary'])

            self._create_service_charge_sale(provider_obj.provider, res['sale_service_charge_summary'])
            self._cr.commit()
            res = {}
            res['status'] = 'BOOKED'

            if res['status'] == 'BOOKED':
                provider_obj.action_booked(pnr, api_context)
                self.action_booked(api_context)
            if res['status'] == 'ISSUED':
                provider_obj.action_booked(pnr, api_context)
                self.action_booked(api_context)
                provider_obj.action_issued(api_context)
                provider_obj.action_create_ledger()
                # self.action_issued(api_context)

            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': res
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e) + '\nUpdate Service Charge failure'
            }

    @api.multi
    def action_check_provider_state(self, api_context=None):
        if not api_context:
            api_context = {
                'co_uid': self.env.user.id
            }
        if 'co_uid' not in api_context:
            api_context.update({
                'co_uid': self.env.user.id
            })
        for rec in self:
            book_info = rec.action_get_provider_booking_info()
            vals = {
                'state': 'fail_issue',
                'pnr': book_info['pnr'],
                'hold_date': book_info['hold_date'],
                'expired_date': book_info['hold_date'],
            }
            if all(provider.state == 'issued' for provider in rec.provider_booking_ids):
                vals.update({
                    'state': 'issued',
                    'issued_uid': api_context['co_uid'],
                    'issued_date': datetime.datetime.now(),
                })
            elif all(provider.state == 'fail_refunded' for provider in rec.provider_booking_ids):
                vals['state'] = 'fail_refunded'
            elif all(provider.state == 'booked' for provider in rec.provider_booking_ids):
                vals['state'] = 'booked'
            elif any(provider.state == 'issued' for provider in rec.provider_booking_ids):
                vals.update({
                    'state': 'partial_issued',
                    'issued_uid': api_context['co_uid'],
                    'issued_date': datetime.datetime.now(),
                })
            elif any(provider.state == 'booked' for provider in rec.provider_booking_ids):
                vals['state'] = 'partial_booked'
            elif rec.name.lower() == 'new':
                vals['state'] = 'fail_booking'
            else:
                vals.update({
                    'issued_uid': api_context['co_uid'],
                    'issued_date': datetime.datetime.now(),
                })

            # Trial 2018/07/19 -> Request berhenti di sini dan tidak jalan
            rec.write(vals)
            rec.env.cr.commit()
            # rec.state = vals['state']
            # rec.issued_uid = vals['issued_uid']
            # rec.issued_date = vals['issued_date']

            #fixme uncomment later
            # rec.message_post(body=_("Order {}".format(BOOKING_STATE_TO_STR.get(vals['state'], '').upper())))

    def action_booked(self, api_context=None):
        res = super(ReservationAirlineApi, self).action_booked(api_context)
        self.action_check_provider_state(api_context)
        return res

    def action_issued_api(self, order_number=None, api_context=None):
        # This function call from button on form
        # This function call by GATEWAY API also

        api_context = copy.deepcopy(self.param_context)

        # api_context['co_uid']
        # Cek co_uid adalah owner dari order_number
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        temp_order_number = self.sudo().search([], order='id desc', limit=1)
        order_number = temp_order_number.name
        print(user_obj)
        order_obj = self.sudo().search([('name', '=', order_number), '|', ('agent_id', '=', user_obj.agent_id.id), ('sub_agent_id', '=', user_obj.agent_id.id)])
        if not order_obj:
            print('Order not found')
            _logger.error('Just Test : OrderNo %s, agent_id : %s' % (order_number, user_obj.agent_id.id))
            return {
                'error_code': 1,
                'error_msg': 'Order not found or you not allowed access the order.'
                # 'error_msg': _('Order not found or you not allowed access the order.')
            }

        print('Test State')
        if order_obj.state == 'issued':
            return {
                'error_code': 0,
                'error_msg': 'Success'
            }

        if order_obj.state not in ['booked', 'partial_booked', 'partial_issued']:
            _logger.info(msg='TEST {} : {}'.format('Request Terminated', 'state not booked, {}'.format(order_obj.state)))
            return {
                'error_code': 1,
                'error_msg': ("You cannot issued that Reservation have been set '%s'") % order_obj.state
                # 'error_msg': _("You cannot issued that Reservation have been set '%s'") % order_obj.state
            }
        #FIXME : Issued hanya boleh jika holdate masih berlaku
        if order_obj.hold_date < datetime.datetime.now():
            order_obj.state = 'cancel2'
            return {
                'error_code': 1,
                'error_msg': ("You cannot issued that Reservation have been set expired")
                # 'error_msg': _("You cannot issued that Reservation have been set expired")
            }

        #Check Saldo
        #fixme uncomment later
        # is_enough = order_obj.env['tt.agent'].check_balance_limit(order_obj.sub_agent_id.id, order_obj.total_nta)
        print('Test')
        is_enough = {}
        is_enough['error_code'] = 0
        if is_enough['error_code'] != 0:
            return {
                'error_code': 1,
                'error_msg': is_enough['error_msg']
            }

        try:
            # order_obj.validate_issue(api_context=api_context)
            error_msg = []
            for provider in order_obj.provider_booking_ids:
                res = {}
                ##fixme uncomment later
                provider.action_issued_provider_api(provider.id,api_context)
                # if provider.provider[:3] == 'kai' and provider.state == 'booked':
                #     res = API_CN_TRAIN.ISSUED2(provider.pnr, provider.notes, provider.id, order_obj.name, provider.provider, api_context)
                # elif provider.provider == 'garuda' and provider.state == 'booked':
                #     res = API_CN_AIRLINES.ISSUED2(provider.notes, provider.id, order_obj.name, provider.provider,api_context)
                provider.action_create_ledger_api()
                if not res:
                    continue
                res = res['result']
                # if res['error_code'] != 0:
                #     return {
                #         'error_code': res['error_code'],
                #         'error_msg': res['error_msg'],
                #     }

                if res['error_code'] != 0:
                    error_msg.append('Provider {} : {}'.format(provider.provider, res['error_msg']))

                # GET TICKET NUMBER DI SINI
                # todo cari di sini get_ticket ticket ticket
                # try:
                #     if provider.provider[:3] != 'kai' and res['error_code'] == 0:
                #         res = API_CN_AIRLINES.GetTicketNumber(provider.pnr, provider.notes, provider.provider, api_context)
                #         if res['error_code'] == 0:
                #             provider.create_ticket_number(res['response']['passengers'])
                # except Exception as e:
                #     _logger.error('Error Get Ticket Number, {}'.format(str(e)))

                # self.env['tt.api.tb.issued.onprocess'].sudo().create_new(
                #     order_obj.pnr, provider.provider, order_obj.id, order_obj.sid,
                #     order_obj.user_id.id,
                #     'call from action_issued_api'
                # )
                # self.env.cr.commit()

                # provider.action_issued(api_context)
            # order_obj.action_issued(api_context)

            # self.env['tt.api.tb.issued.onprocess'].unlink_by_order(order_obj.id)
            if error_msg:
                return {
                    'error_code': -1,
                    'error_msg': ', '.join(error_msg)
                }
        except Exception as e:
            order_obj.state = 'error'
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

        # try:
        #     count = False
        #     for rec in order_obj.sale_service_charge_ids:
        #         if rec.charge_type == 'VOUCHER':
        #             count = True
        #             voucher_obj = self.env['tt.promo.voucher'].search([('voucher_code', '=', str(rec.description))],
        #                                                               limit=1)
        #             if voucher_obj:
        #                 voucher_obj = voucher_obj[0]
        #                 voucher_obj.action_redeem()
        #     if not count:
        #         order_obj.generate_promo_voucher()
        # except Exception as e:
        #     _logger.error('Failed to handle Voucher.' + '\n' + traceback.format_exc())

        return {
            'error_code': 0,
            'error_msg': 'Success'
        }


