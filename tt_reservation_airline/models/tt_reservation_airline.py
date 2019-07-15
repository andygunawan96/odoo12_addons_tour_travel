from odoo import api,models,fields, _
from ...tools import util,variables
import logging,traceback
import datetime
import copy



#controller
#booking
#update pnr
#update tb seat
#issued

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

    passenger_ids = fields.Many2many('tt.customer', 'tt_reservation_airline_passengers_rel', 'booking_id', 'passenger_id',
                                     string='List of Passenger', readonly=True, states={'draft': [('readonly', False)]})

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

    param_global = {
        "force_issued": False,
        "booker": {
            "title": "MR",
            "first_name": "Ali",
            "last_name": "Dalton",
            "email": "john@gmail.com",
            "calling_code": "62",
            "mobile": "8123456789",
            "nationality_code": "ID"
        },
        "contacts": [
            {
                "title": "MR",
                "first_name": "Ali",
                "last_name": "Dalton",
                "email": "john@gmail.com",
                "calling_code": "62",
                "mobile": "8123456789",
                "nationality_code": "ID",
                "sequence": 1,
                "gender": "male",
                "is_also_booker": True
            }
        ],
        "passengers": [
            {
                "title": "MR",
                "first_name": "Lion",
                "last_name": "Dalton",
                "birth_date": "1989-03-20",
                "pax_type": "ADT",
                "nationality_code": "ID",
                "identity_type": "passport",
                "passport_number": "BG123456",
                "passport_expdate": "2022-03-20",
                "country_of_issued_code": "ID",
                "sequence": 1,
                "gender": "male"
            }
        ],
        "searchRQ": {
            "origin": "SUB",
            "destination": "SIN",
            "departure_date": "2019-09-15",
            "return_date": "2019-09-22",
            "direction": "OW",
            "adult": 1,
            "child": 0,
            "infant": 0,
            "cabin_class": "Y",
            "carrier_codes": [],
            "is_combo_price": True,
            "provider": "sia"
        },
        "journeys_booking_data": {
            "sia": {
                "1": {
                    "journey_codes": {
                        "DEP": [
                            {
                                "segment_code": "SQ,931,SUB,2,2019-09-05 10:10:00,SIN,0,2019-09-05 13:30:00,sia",
                                "journey_type": "DEP",
                                "fare_code": "",
                                "carrier_code": "SQ",
                                "carrier_number": "931",
                                "origin": "SUB",
                                "origin_terminal": "2",
                                "departure_date": "2019-09-05 10:10:00",
                                "destination": "SIN",
                                "destination_terminal": "0",
                                "arrival_date": "2019-09-05 13:30:00",
                                "provider": "sia"
                            },
                            {
                                "segment_code": "SQ,976,SIN,2,2019-09-05 16:00:00,BKK,,2019-09-05 17:25:00,sia",
                                "journey_type": "DEP",
                                "fare_code": "",
                                "carrier_code": "SQ",
                                "carrier_number": "976",
                                "origin": "SIN",
                                "origin_terminal": "2",
                                "departure_date": "2019-09-05 16:00:00",
                                "destination": "BKK",
                                "destination_terminal": "",
                                "arrival_date": "2019-09-05 17:25:00",
                                "provider": "sia"
                            }
                        ],
                        "RET": [
                            {
                                "segment_code": "SQ,973,BKK,,2019-09-12 09:40:00,SIN,0,2019-09-12 13:05:00,sia",
                                "journey_type": "RET",
                                "fare_code": "",
                                "carrier_code": "SQ",
                                "carrier_number": "973",
                                "origin": "BKK",
                                "origin_terminal": "",
                                "departure_date": "2019-09-12 09:40:00",
                                "destination": "SIN",
                                "destination_terminal": "0",
                                "arrival_date": "2019-09-12 13:05:00",
                                "provider": "sia"
                            },
                            {
                                "segment_code": "MI,224,SIN,2,2019-09-12 14:20:00,SUB,2,2019-09-12 15:40:00,sia",
                                "journey_type": "RET",
                                "fare_code": "SULH-4024598099257484485-2-1^SQ^1^SEG3,SEG4,SEG14,SEG15",
                                "carrier_code": "MI",
                                "carrier_number": "224",
                                "origin": "SIN",
                                "origin_terminal": "2",
                                "departure_date": "2019-09-12 14:20:00",
                                "destination": "SUB",
                                "destination_terminal": "2",
                                "arrival_date": "2019-09-12 15:40:00",
                                "provider": "sia"
                            }
                        ]
                    },
                    "paxs": {
                        "ADT": 1,
                        "CHD": 0,
                        "INF": 0
                    },
                    "is_combo_price": True
                }
            }
        },
        "context": {
            "uid": 8,
            "user_name": "API Credential",
            "user_login": "rodex.api@skytors.id",
            "agent_id": 2,
            "agent_name": "Rodex Tour and Travel",
            "agent_type_id": 1,
            "agent_type_name": "HO",
            "agent_type_code": "ho",
            "api_role": "manager",
            "host_ips": [],
            "configs": {
                "airlines": {
                    "provider_access": "all",
                    "providers": {}
                }
            },
            "co_uid": 1,
            "co_user_name": "System Credential",
            "co_user_login": "sys.it@rodextravel.tours",
            "co_agent_id": 1,
            "co_agent_name": "Rodex Tour and Travel",
            "co_agent_type_id": 1,
            "co_agent_type_name": "HO",
            "co_agent_type_code": "ho",
            "sid": "22cc554004384961a1e9b0843bbf54ec4389665b",
            "signature": "a6dd1080b66442f6b1c4ffdf4569609f",
            "expired_date": "2019-06-26 06:51:52"
        }
    }

    def create_booking_api(self, req):
        req = copy.deepcopy(self.param_global)
        search_RQ = req['searchRQ']
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        journeys = req['journeys_booking_data']
        context = req['context']

        values = self._prepare_booking_api(search_RQ,context)
        booker_obj = self._create_booker_api(booker,context)
        contact_obj = self._create_contact_api(contacts[0],booker_obj,context)
        list_passengers = self._create_passenger_api(passengers,context,booker_obj.id,contact_obj.id)

        values.update({
            'user_id': context['co_uid'],
            'sid_booked': context['signature'],
            'contact_id': contact_obj.id,
            'contanct_name': contact_obj.name,
            'passenger_ids': [(6,0,list_passengers)]
        })

        book_obj = self.create(values)

        self._create_provider_api(journeys,book_obj.id,context)

        return {
            'error_code': 0,
            'error_msg': 'Success',
            'order_id': book_obj.id,
        }

    def validate_booking(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise Exception('User NOT FOUND...')
        return True

    def _prepare_booking_api(self, searchRQ, context_gateway):
        dest_obj = self.env['tt.destinations']

        booking_tmp = {
            'direction': searchRQ['direction'],
            'departure_date': searchRQ['departure_date'],
            'return_date': searchRQ['return_date'],
            'origin_id': dest_obj.get_id(searchRQ['origin'], self.provider_type_id),
            'destination_id': dest_obj.get_id(searchRQ['destination'], self.provider_type_id),
            'provider_type_id': self.env.ref('tt_reservation_airline.tt_provider_type_airline').id,
            'adult': searchRQ['adult'],
            'child': searchRQ['child'],
            'infant': searchRQ['infant'],
            'agent_id': context_gateway['agent_id'],
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    ##todo kalau kejadian saling tumpuk data customer karena ada yang kosong
    ##dibuatkan mekanisme pop isi dictionary yang valuenya kosong
    def _create_booker_api(self, vals, context):
        booker_obj = self.env['tt.customer'].sudo()

        if vals.get('booker_id'):
            booker_id = int(vals['booker_id'])
            booker_rec = booker_obj.browse(booker_id)
            if booker_rec:
                if vals.get('mobile'):
                    new_phone = [(0,0,{
                        'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile',''))
                    })]
                else:
                    new_phone = False
                booker_rec.update({
                    'email': vals.get('email', booker_rec.email),
                    'phone_ids': new_phone or booker_rec.phone_ids
                })
                return booker_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])


        vals.update({
            'agent_id': context['agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'gender': vals.get('gender'),
            'customer_parent_ids': [(4,agent_obj.customer_parent_walkin_id.id )],
            'can_book': True
        })


        return booker_obj.create(vals)

    def _create_contact_api(self, vals, booker, context):
        contact_obj = self.env['tt.customer'].sudo()

        if vals.get('contact_id') or vals.get('is_also_booker'):
            if 'contact_id' in vals:
                contact_id = int(vals['contact_id'])
            else:
                contact_id = booker.id

            contact_rec = contact_obj.browse(contact_id)
            if contact_rec:
                if vals.get('mobile'):
                    new_phone = [(0,0,{
                        'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile',''))
                    })]
                else:
                    new_phone = False
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    'phone_ids': new_phone or contact_rec.phone_ids
                })
                return contact_rec


        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])

        vals.update({
            'agent_id': context['agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
            'gender': vals.get('gender')
        })

        return contact_obj.create(vals)

    def _create_passenger_api(self,passengers,context,booker_id=False,contact_id=False):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()

        res_ids = []

        for psg in passengers:
            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False
            if psg.get('country_of_issued_code'):
                country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                psg['country_of_issued_id'] = country and country[0].id or False

            vals_for_update = {}
            update_list = ['passport_number', 'passport_expdate', 'nationality_id', 'country_of_issued_id', 'passport_issued_date', 'identity_type', 'birth_date']
            [vals_for_update.update({
                key: psg[key]
            }) for key in update_list if psg.get(key)]

            booker_contact_id = -1
            if psg.get('is_booker'):
                booker_contact_id = booker_id
            elif psg.get('is_contact'):
                booker_contact_id = contact_id

            if psg.get('passenger_id') or booker_contact_id > 0:

                current_passenger = passenger_obj.browse(int(psg.get('passenger_id'),booker_contact_id))
                if current_passenger:
                    current_passenger.update(vals_for_update)
                    res_ids.append(current_passenger.id)
                    continue

            psg['agent_id'] = context['agent_id']
            agent_obj = self.env['tt.agent'].sudo().browse(context['agent_id'])

            psg.update({
                'customer_parent_ids': [(4, agent_obj.customer_parent_walkin_id.id)],
            })
            psg_obj = passenger_obj.create(psg)
            res_ids.append(psg_obj.id)

        return res_ids

    def _create_provider_api(self, providers, book_id, api_context):
        dest_obj = self.env['tt.destinations']
        provider_airline_obj = self.env['tt.provider.airline']
        carrier_obj = self.env['tt.transport.carrier']
        country_obj = self.env['res.country']
        provider_obj = self.env['tt.provider']

        _destination_type = self.provider_type_id

        #lis of providers ID
        res = []

        for provider_name, provider_value in providers.items():
            provider_id = provider_obj.get_provider_id(provider_name,_destination_type)
            print(provider_name)
            for sequence, provider in provider_value.items():
                print(sequence)
                journey_sequence = 0
                this_pnr_journey = []

                for journey_type, journey_value in provider['journey_codes'].items():
                    ###Create Journey
                    print(journey_type)
                    this_journey_seg = []
                    for segment in journey_value:
                        ###Create Segment
                        carrier_id = carrier_obj.get_id(segment['carrier_code'],_destination_type)
                        org_id = dest_obj.get_id(segment['origin'],_destination_type)
                        dest_id = dest_obj.get_id(segment['destination'],_destination_type)

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
                        }))

                    ###journey_type DEP or RET
                    this_pnr_journey.append((0,0, {
                        'provider_id': provider_id,
                        'sequence': journey_sequence+1,
                        'journey_type': journey_type,
                        'origin_id': this_journey_seg[0][2]['origin_id'],
                        'destination_id': this_journey_seg[-1][2]['destination_id'],
                        'departure_date': this_journey_seg[0][2]['departure_date'],
                        'arrival_date': this_journey_seg[-1][2]['arrival_date'],
                        'segment_ids': this_journey_seg
                    }))

                DEP_len = len(this_pnr_journey[0])
                RET_len = len(this_pnr_journey[-1])

                if DEP_len > 0 and RET_len > 0 :
                    provider_direction = 'RT'
                    provider_origin = this_pnr_journey[0][2]['origin_id']
                    provider_destination = this_pnr_journey[0][2]['destination_id']
                    provider_departure_date = this_pnr_journey[0][2]['departure_date']
                    provider_return_date = this_pnr_journey[-1][2]['departure_date']
                elif DEP_len > 0 :
                    provider_direction = 'OW'
                    provider_origin = this_pnr_journey[0][2]['origin_id']
                    provider_destination = this_pnr_journey[0][2]['destination_id']
                elif RET_len > 0 :
                    provider_direction = 'OW'
                    provider_origin = this_pnr_journey[-1][2]['origin_id']
                    provider_destination = this_pnr_journey[-1][2]['destination_id']

                values = {
                    'provider_id': provider_id,
                    'booking_id': book_id,
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

# class ReservationAirlineApi(models.Model):
#     _inherit = 'tt.reservation.airline'
#
#     def update_provider_pnr(self, booking_id, provider, provider_sequence, book_info, api_context):
#
#         try:
#             provider_obj = self.env['tt.tb.provider.airline'].search(
#                 [('booking_id', '=', booking_id), ('provider', '=', provider), ('sequence', '=', provider_sequence)])
#             booking_obj = self.browse(booking_id)
#
#
#             # self._create_tb_seat_TRAIN(booking_obj, book_info)000
#
#
#             provider_obj.action_booked(book_info['pnr'], api_context)
#             # booking_obj.action_booked()
#             self._cr.commit()
#
#             kwargs = {
#                 'book_info': book_info,
#                 'direction': booking_obj.direction  #for compute r.ac per pax/route(OW/RT)
#             }
#
#
#
#             res = booking_obj._update_service_charges(book_info['pnr'], provider_obj, api_context, **kwargs)
#
#             if res['error_code'] != 0:
#                 raise Exception(res['error_msg'])
#
#             # Jika semua provider_booking sudah booked, maka transport_booked.state = booked
#
#             return {
#                 'error_code': 0,
#                 'error_msg': 'Success',
#                 'order_number': booking_obj.name,
#                 'status': 'booked',
#             }
#
#         except Exception as e:
#             self.env.cr.rollback()
#             _logger.error(msg=str(e) + '\n' + traceback.format_exc())
#             return {
#                 'error_code': 1,
#                 'error_msg': str(e) + '\nUpdate PNR failure'
#             }
#
#     @api.one
#     def _create_service_charge_sale(self, provider_name, sale_service_charge_summary):
#         # self.sale_service_charge_ids
#         service_chg_obj = self.env['tt.service.charge']
#         for scs in sale_service_charge_summary:
#             for val in scs['service_charges']:
#                 if val['amount']:
#                     val.update({
#                         'booking_airline_id': self.id,
#                         'description': provider_name
#                     })
#                     val['booking_id'] = self.id
#                     service_chg_obj.create(val)
#
#     def _update_service_charges(self, pnr, provider_obj, api_context=None, **kwargs):
#         self.ensure_one()
#         # Fungsi melakukan insert service_charge per porvider
#         if not api_context:
#             api_context['co_uid'] = self.env.user.id
#
#         try:
#             #later for now hard coded
#             # res = self.get_booking2(pnr, provider_obj.provider, kwargs['direction'], self.sid, api_context)
#             res = copy.deepcopy(self.param_get_booking_2)
#
#             if res['error_code'] != 0:
#                 raise Exception(res['result']['error_msg'])
#
#             # res = res['result']['response']
#             res = res['response']
#
#             provider_obj.sudo().write({
#                 'hold_date': res['hold_date'],
#                 'expired_date': res.get('expired_date'),
#                 'notes': res.get('notes'),
#                 'pnr': pnr,
#             })
#
#             segments = res.get('segments', [])
#             seg_count = 0
#             is_available = True if seg_count < len(segments) else False
#             if 'sabre' in provider_obj.provider:
#                 for journey in provider_obj.journey_ids:
#                     for seg in journey.segment_ids:
#                         if is_available:
#                             seg.sudo().write({
#                                 'airline_pnr_ref': segments[seg_count].get('airline_pnr_ref')
#                             })
#                             seg_count += 1
#                             is_available = True if seg_count < len(segments) else False
#
#             if not res['service_charge_summary']:
#                 return {
#                     'error_code': 0,
#                     'error_msg': 'Success, But not service_charge_summary',
#                     'state': 'booked'
#                 }
#             provider_obj._create_service_charge(res['service_charge_summary'])
#
#             self._create_service_charge_sale(provider_obj.provider, res['sale_service_charge_summary'])
#             self._cr.commit()
#             res = {}
#             res['status'] = 'BOOKED'
#
#             if res['status'] == 'BOOKED':
#                 provider_obj.action_booked(pnr, api_context)
#                 self.action_booked(api_context)
#             if res['status'] == 'ISSUED':
#                 provider_obj.action_booked(pnr, api_context)
#                 self.action_booked(api_context)
#                 provider_obj.action_issued(api_context)
#                 provider_obj.action_create_ledger()
#                 # self.action_issued(api_context)
#
#             return {
#                 'error_code': 0,
#                 'error_msg': 'Success',
#                 'response': res
#             }
#         except Exception as e:
#             self.env.cr.rollback()
#             _logger.error(msg=str(e) + '\n' + traceback.format_exc())
#             return {
#                 'error_code': 1,
#                 'error_msg': str(e) + '\nUpdate Service Charge failure'
#             }
#
#     @api.multi
#     def action_check_provider_state(self, api_context=None):
#         if not api_context:
#             api_context = {
#                 'co_uid': self.env.user.id
#             }
#         if 'co_uid' not in api_context:
#             api_context.update({
#                 'co_uid': self.env.user.id
#             })
#         for rec in self:
#             book_info = rec.action_get_provider_booking_info()
#             vals = {
#                 'state': 'fail_issue',
#                 'pnr': book_info['pnr'],
#                 'hold_date': book_info['hold_date'],
#                 'expired_date': book_info['hold_date'],
#             }
#             if all(provider.state == 'issued' for provider in rec.provider_booking_ids):
#                 vals.update({
#                     'state': 'issued',
#                     'issued_uid': api_context['co_uid'],
#                     'issued_date': datetime.datetime.now(),
#                 })
#             elif all(provider.state == 'fail_refunded' for provider in rec.provider_booking_ids):
#                 vals['state'] = 'fail_refunded'
#             elif all(provider.state == 'booked' for provider in rec.provider_booking_ids):
#                 vals['state'] = 'booked'
#             elif any(provider.state == 'issued' for provider in rec.provider_booking_ids):
#                 vals.update({
#                     'state': 'partial_issued',
#                     'issued_uid': api_context['co_uid'],
#                     'issued_date': datetime.datetime.now(),
#                 })
#             elif any(provider.state == 'booked' for provider in rec.provider_booking_ids):
#                 vals['state'] = 'partial_booked'
#             elif rec.name.lower() == 'new':
#                 vals['state'] = 'fail_booking'
#             else:
#                 vals.update({
#                     'issued_uid': api_context['co_uid'],
#                     'issued_date': datetime.datetime.now(),
#                 })
#
#             # Trial 2018/07/19 -> Request berhenti di sini dan tidak jalan
#             rec.write(vals)
#             rec.env.cr.commit()
#             # rec.state = vals['state']
#             # rec.issued_uid = vals['issued_uid']
#             # rec.issued_date = vals['issued_date']
#
#             #fixme uncomment later
#             # rec.message_post(body=_("Order {}".format(BOOKING_STATE_TO_STR.get(vals['state'], '').upper())))
#
#     def action_booked(self, api_context=None):
#         res = super(ReservationAirlineApi, self).action_booked(api_context)
#         self.action_check_provider_state(api_context)
#         return res
#
#     def action_issued_api(self, order_number=None, api_context=None):
#         # This function call from button on form
#         # This function call by GATEWAY API also
#
#         api_context = copy.deepcopy(self.param_context)
#
#         # api_context['co_uid']
#         # Cek co_uid adalah owner dari order_number
#         user_obj = self.env['res.users'].browse(api_context['co_uid'])
#         temp_order_number = self.sudo().search([], order='id desc', limit=1)
#         order_number = temp_order_number.name
#         print(user_obj)
#         order_obj = self.sudo().search([('name', '=', order_number), '|', ('agent_id', '=', user_obj.agent_id.id), ('sub_agent_id', '=', user_obj.agent_id.id)])
#         if not order_obj:
#             print('Order not found')
#             _logger.error('Just Test : OrderNo %s, agent_id : %s' % (order_number, user_obj.agent_id.id))
#             return {
#                 'error_code': 1,
#                 'error_msg': 'Order not found or you not allowed access the order.'
#                 # 'error_msg': _('Order not found or you not allowed access the order.')
#             }
#
#         print('Test State')
#         if order_obj.state == 'issued':
#             return {
#                 'error_code': 0,
#                 'error_msg': 'Success'
#             }
#
#         if order_obj.state not in ['booked', 'partial_booked', 'partial_issued']:
#             _logger.info(msg='TEST {} : {}'.format('Request Terminated', 'state not booked, {}'.format(order_obj.state)))
#             return {
#                 'error_code': 1,
#                 'error_msg': ("You cannot issued that Reservation have been set '%s'") % order_obj.state
#                 # 'error_msg': _("You cannot issued that Reservation have been set '%s'") % order_obj.state
#             }
#         #FIXME : Issued hanya boleh jika holdate masih berlaku
#         if order_obj.hold_date < datetime.datetime.now():
#             order_obj.state = 'cancel2'
#             return {
#                 'error_code': 1,
#                 'error_msg': ("You cannot issued that Reservation have been set expired")
#                 # 'error_msg': _("You cannot issued that Reservation have been set expired")
#             }
#
#         #Check Saldo
#         #fixme uncomment later
#         # is_enough = order_obj.env['tt.agent'].check_balance_limit(order_obj.sub_agent_id.id, order_obj.total_nta)
#         print('Test')
#         is_enough = {}
#         is_enough['error_code'] = 0
#         if is_enough['error_code'] != 0:
#             return {
#                 'error_code': 1,
#                 'error_msg': is_enough['error_msg']
#             }
#
#         try:
#             # order_obj.validate_issue(api_context=api_context)
#             error_msg = []
#             for provider in order_obj.provider_booking_ids:
#                 res = {}
#                 ##fixme uncomment later
#                 provider.action_issued_provider_api(provider.id,api_context)
#                 # if provider.provider[:3] == 'kai' and provider.state == 'booked':
#                 #     res = API_CN_TRAIN.ISSUED2(provider.pnr, provider.notes, provider.id, order_obj.name, provider.provider, api_context)
#                 # elif provider.provider == 'garuda' and provider.state == 'booked':
#                 #     res = API_CN_AIRLINES.ISSUED2(provider.notes, provider.id, order_obj.name, provider.provider,api_context)
#                 provider.action_create_ledger_api()
#                 if not res:
#                     continue
#                 res = res['result']
#                 # if res['error_code'] != 0:
#                 #     return {
#                 #         'error_code': res['error_code'],
#                 #         'error_msg': res['error_msg'],
#                 #     }
#
#                 if res['error_code'] != 0:
#                     error_msg.append('Provider {} : {}'.format(provider.provider, res['error_msg']))
#
#                 # GET TICKET NUMBER DI SINI
#                 # todo cari di sini get_ticket ticket ticket
#                 # try:
#                 #     if provider.provider[:3] != 'kai' and res['error_code'] == 0:
#                 #         res = API_CN_AIRLINES.GetTicketNumber(provider.pnr, provider.notes, provider.provider, api_context)
#                 #         if res['error_code'] == 0:
#                 #             provider.create_ticket_number(res['response']['passengers'])
#                 # except Exception as e:
#                 #     _logger.error('Error Get Ticket Number, {}'.format(str(e)))
#
#                 # self.env['tt.api.tb.issued.onprocess'].sudo().create_new(
#                 #     order_obj.pnr, provider.provider, order_obj.id, order_obj.sid,
#                 #     order_obj.user_id.id,
#                 #     'call from action_issued_api'
#                 # )
#                 # self.env.cr.commit()
#
#                 # provider.action_issued(api_context)
#             # order_obj.action_issued(api_context)
#
#             # self.env['tt.api.tb.issued.onprocess'].unlink_by_order(order_obj.id)
#             if error_msg:
#                 return {
#                     'error_code': -1,
#                     'error_msg': ', '.join(error_msg)
#                 }
#         except Exception as e:
#             order_obj.state = 'error'
#             _logger.error(msg=str(e) + '\n' + traceback.format_exc())
#             return {
#                 'error_code': 1,
#                 'error_msg': str(e)
#             }
#
#         # try:
#         #     count = False
#         #     for rec in order_obj.sale_service_charge_ids:
#         #         if rec.charge_type == 'VOUCHER':
#         #             count = True
#         #             voucher_obj = self.env['tt.promo.voucher'].search([('voucher_code', '=', str(rec.description))],
#         #                                                               limit=1)
#         #             if voucher_obj:
#         #                 voucher_obj = voucher_obj[0]
#         #                 voucher_obj.action_redeem()
#         #     if not count:
#         #         order_obj.generate_promo_voucher()
#         # except Exception as e:
#         #     _logger.error('Failed to handle Voucher.' + '\n' + traceback.format_exc())
#
#         return {
#             'error_code': 0,
#             'error_msg': 'Success'
#         }


