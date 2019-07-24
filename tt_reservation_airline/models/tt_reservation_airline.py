from odoo import api,models,fields, _
from ...tools import util,variables
from ...tools.api import Response
import logging,traceback
import datetime
import json
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

    def action_booked_api(self,pnr_list,hold_date):
        self.write({
            'name': self.env['ir.sequence'].next_by_code('reservation.airline'),
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
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

    param_global = {
        "force_issued": True,
        "booker": {
            "title": "MR",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "email": "asd@gmail.com",
            "calling_code": "62",
            "mobile": "82381283812",
            "nationality_code": "ID",
            "booker_id": ""
        },
        "contacts": [
            {
                "title": "MR",
                "first_name": "ivan",
                "last_name": "suryajaya",
                "email": "asd@gmail.com",
                "calling_code": "62",
                "mobile": "82381283812",
                "nationality_code": "ID",
                "is_also_booker": True,
                "sequence": 1,
                "gender": "male",
                "contact_id": ""
            }
        ],
        "passengers": [
            {
                "title": "MR",
                "first_name": "ivan",
                "last_name": "suryajaya",
                "birth_date": "2002-04-08",
                "pax_type": "ADT",
                "nationality_code": "ID",
                "passport_number": "",
                "passport_expdate": "",
                "country_of_issued_code": "",
                "is_also_booker": False,
                "is_also_contact": False,
                "sequence": 1,
                "gender": "male",
                "passenger_id": ""
            }
        ],
        "searchRQ": {
            "origin": "SUB",
            "destination": "SIN",
            "departure_date": "2019-07-18",
            "return_date": "2019-07-18",
            "direction": "OW",
            "adult": 1,
            "child": 0,
            "infant": 0,
            "cabin_class": "Y",
            "carrier_codes": [
                "CX",
                "SQ"
            ],
            "is_combo_price": False,
            "provider": "amadeus"
        },
        "providers_booking_data": {
            "amadeus": {
                "1": {
                    "journey_codes": {
                        "DEP": [
                            {
                                "segment_code": "SQ,5223,SUB,2,2019-07-18 16:30:00,SIN,2,2019-07-18 19:55:00,amadeus",
                                "journey_type": "DEP",
                                "fare_code": "M",
                                "carrier_code": "SQ",
                                "carrier_number": "5223",
                                "origin": "SUB",
                                "origin_terminal": "2",
                                "departure_date": "2019-07-18 16:30:00",
                                "destination": "SIN",
                                "destination_terminal": "2",
                                "arrival_date": "2019-07-18 19:55:00",
                                "provider": "amadeus",
                                "class_of_service": "M"
                            }
                        ],
                        "RET": []
                    },
                    "paxs": {
                        "ADT": 1,
                        "CHD": 0,
                        "INF": 0
                    },
                    "is_combo_price": False
                }
            }
        },
        "context": {
            "uid": 9,
            "user_name": "Ivan Credential",
            "user_login": "mob.it@rodextravel.tours",
            "agent_id": 4,
            "agent_name": "Rodex Bonbin",
            "agent_type_id": 2,
            "agent_type_name": "Agent Citra",
            "agent_type_code": "citra",
            "api_role": "manager",
            "host_ips": [],
            "configs": {
                "airline": {
                    "provider_access": "all",
                    "providers": {}
                }
            },
            "co_uid": 9,
            "co_user_name": "Ivan Credential",
            "co_user_login": "mob.it@rodextravel.tours",
            "co_agent_id": 4,
            "co_agent_name": "Rodex Bonbin",
            "co_agent_type_id": 2,
            "co_agent_type_name": "Agent Citra",
            "co_agent_type_code": "citra",
            "sid": "eee5465b965087dc75f75cd45a80fea1fd4b1822",
            "signature": "f80632a549804274a07b0ee7a29c2323",
            "expired_date": "2019-07-18 09:31:14"
        },
        "provider_type": "airline"
    }

    param_update_pnr = {
        "booking_commit_provider": [
            {
                "id": 70,
                "sequence": "1",
                "pnr": "QPVVFP",
                "pnr2": "QPVVFP",
                "reference": "QPVVFP",
                "expired_date": "2019-07-23 16:00:00",
                "hold_date": "2019-07-23 16:00:00",
                "status": "BOOKED",
                "currency": "IDR",
                "balance_due": 129600000,
                "provider": "amadeus",
                "pax_list": [
                    {
                        "qualifier": "PT",
                        "number": "2"
                    },
                    {
                        "qualifier": "PT",
                        "number": "3"
                    },
                    {
                        "qualifier": "PT",
                        "number": "5"
                    },
                    {
                        "qualifier": "PT",
                        "number": "6"
                    },
                    {
                        "qualifier": "PT",
                        "number": "4"
                    }
                ],
                "journeys": [
                    {
                        "sequence": 1,
                        "origin": "SUB",
                        "origin_terminal": "2",
                        "origin_utc": 0,
                        "departure_date": "2019-09-15 18:40:00",
                        "destination": "BKK",
                        "destination_terminal": "",
                        "destination_utc": 0,
                        "arrival_date": "2019-09-16 11:05:00",
                        "journey_type": "",
                        "departure_date_return": "",
                        "arrival_date_return": "",
                        "elapsed_time_return": "",
                        "transit_count": 1,
                        "transit_count_return": 0,
                        "elapsed_time": "0:16:25:0",
                        "journey_code": "SQ,5225,SUB,2,2019-09-15 18:40:00,SIN,2,2019-09-15 21:55:00,amadeus;SQ,972,SIN,2,2019-09-16 09:35:00,BKK,,2019-09-16 11:05:00,amadeus",
                        "is_combo_price": False,
                        "is_international": False,
                        "provider": "amadeus",
                        "carrier_code_list": [
                            "SQ"
                        ],
                        "cabin_class_list": [
                            ""
                        ],
                        "operating_airline_code_list": [],
                        "segments": [
                            {
                                "sequence": 1,
                                "origin": "SUB",
                                "origin_terminal": "2",
                                "origin_utc": 0,
                                "departure_date": "2019-09-15 18:40:00",
                                "destination": "SIN",
                                "destination_terminal": "2",
                                "destination_utc": 0,
                                "arrival_date": "2019-09-15 21:55:00",
                                "journey_type": "",
                                "transit_count": 0,
                                "transit_duration": "",
                                "elapsed_time": "0:3:15:0",
                                "segment_code": "SQ,5225,SUB,2,2019-09-15 18:40:00,SIN,2,2019-09-15 21:55:00,amadeus",
                                "segment_code2": "SUB-SIN",
                                "carrier_name": "SQ 5225",
                                "carrier_code": "SQ",
                                "carrier_number": "5225",
                                "operating_airline_code": "",
                                "is_international": False,
                                "cabin_class_list": [
                                    ""
                                ],
                                "provider": "amadeus",
                                "legs": [
                                    {
                                        "sequence": 1,
                                        "origin": "SUB",
                                        "origin_terminal": "2",
                                        "origin_utc": 0,
                                        "departure_date": "2019-09-15 18:40:00",
                                        "destination": "SIN",
                                        "destination_terminal": "2",
                                        "destination_utc": 0,
                                        "arrival_date": "2019-09-15 21:55:00",
                                        "transit_duration": "",
                                        "carrier_name": "SQ 5225",
                                        "carrier_code": "SQ",
                                        "carrier_number": "5225",
                                        "elapsed_time": "0:3:15:0",
                                        "journey_type": "",
                                        "leg_code": "SQ,5225,SUB,2,2019-09-15 18:40:00,SIN,2,2019-09-15 21:55:00,amadeus",
                                        "leg_code2": "SUB-SIN",
                                        "is_international": False,
                                        "operating_airline_code": "",
                                        "provider": "amadeus"
                                    }
                                ],
                                "fares": [
                                    {
                                        "sequence": 1,
                                        "fare_code": "M",
                                        "cabin_class": "",
                                        "class_of_service": "M",
                                        "rule_number": "",
                                        "product_class": "M",
                                        "product_name": "",
                                        "description": "",
                                        "available_count": -1,
                                        "service_charges": [],
                                        "fare_basis_codes": [],
                                        "details": [],
                                        "fare_rules": [],
                                        "service_charge_summary": []
                                    }
                                ]
                            },
                            {
                                "sequence": 2,
                                "origin": "SIN",
                                "origin_terminal": "2",
                                "origin_utc": 0,
                                "departure_date": "2019-09-16 09:35:00",
                                "destination": "BKK",
                                "destination_terminal": "",
                                "destination_utc": 0,
                                "arrival_date": "2019-09-16 11:05:00",
                                "journey_type": "",
                                "transit_count": 0,
                                "transit_duration": "0:11:40:0",
                                "elapsed_time": "0:1:30:0",
                                "segment_code": "SQ,972,SIN,2,2019-09-16 09:35:00,BKK,,2019-09-16 11:05:00,amadeus",
                                "segment_code2": "SIN-BKK",
                                "carrier_name": "SQ 972",
                                "carrier_code": "SQ",
                                "carrier_number": "972",
                                "operating_airline_code": "",
                                "is_international": False,
                                "cabin_class_list": [
                                    ""
                                ],
                                "provider": "amadeus",
                                "legs": [
                                    {
                                        "sequence": 1,
                                        "origin": "SIN",
                                        "origin_terminal": "2",
                                        "origin_utc": 0,
                                        "departure_date": "2019-09-16 09:35:00",
                                        "destination": "BKK",
                                        "destination_terminal": "",
                                        "destination_utc": 0,
                                        "arrival_date": "2019-09-16 11:05:00",
                                        "transit_duration": "",
                                        "carrier_name": "SQ 972",
                                        "carrier_code": "SQ",
                                        "carrier_number": "972",
                                        "elapsed_time": "0:1:30:0",
                                        "journey_type": "",
                                        "leg_code": "SQ,972,SIN,2,2019-09-16 09:35:00,BKK,,2019-09-16 11:05:00,amadeus",
                                        "leg_code2": "SIN-BKK",
                                        "is_international": False,
                                        "operating_airline_code": "",
                                        "provider": "amadeus"
                                    }
                                ],
                                "fares": [
                                    {
                                        "sequence": 1,
                                        "fare_code": "M",
                                        "cabin_class": "",
                                        "class_of_service": "M",
                                        "rule_number": "",
                                        "product_class": "M",
                                        "product_name": "",
                                        "description": "",
                                        "available_count": -1,
                                        "service_charges": [
                                            {
                                                "sequence": 1,
                                                "charge_code": "fare",
                                                "charge_type": "FARE",
                                                "currency": "IDR",
                                                "amount": 4800000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 4800000,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 14400000
                                            },
                                            {
                                                "sequence": 2,
                                                "charge_code": "D5",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 210000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 210000,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 630000
                                            },
                                            {
                                                "sequence": 3,
                                                "charge_code": "L7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 31200,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 31200,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 93600
                                            },
                                            {
                                                "sequence": 4,
                                                "charge_code": "SG",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 62400,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 62400,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 187200
                                            },
                                            {
                                                "sequence": 5,
                                                "charge_code": "E7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 16100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 16100,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 48300
                                            },
                                            {
                                                "sequence": 6,
                                                "charge_code": "G8",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 6900,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 6900,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 20700
                                            },
                                            {
                                                "sequence": 7,
                                                "charge_code": "fare",
                                                "charge_type": "FARE",
                                                "currency": "IDR",
                                                "amount": 3600000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 3600000,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 7200000
                                            },
                                            {
                                                "sequence": 8,
                                                "charge_code": "D5",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 210000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 210000,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 420000
                                            },
                                            {
                                                "sequence": 9,
                                                "charge_code": "L7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 31200,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 31200,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 62400
                                            },
                                            {
                                                "sequence": 10,
                                                "charge_code": "SG",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 62400,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 62400,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 124800
                                            },
                                            {
                                                "sequence": 11,
                                                "charge_code": "E7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 16100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 16100,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 32200
                                            },
                                            {
                                                "sequence": 12,
                                                "charge_code": "G8",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 6900,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 6900,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 13800
                                            }
                                        ],
                                        "fare_basis_codes": [],
                                        "details": [],
                                        "fare_rules": [],
                                        "service_charge_summary": [
                                            {
                                                "service_charges": [
                                                    {
                                                        "sequence": 1,
                                                        "charge_code": "fare",
                                                        "charge_type": "FARE",
                                                        "currency": "IDR",
                                                        "amount": 4800000,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 4800000,
                                                        "pax_count": 3,
                                                        "pax_type": "ADT",
                                                        "total": 14400000
                                                    },
                                                    {
                                                        "sequence": 2,
                                                        "charge_code": "tax",
                                                        "charge_type": "TAX",
                                                        "currency": "IDR",
                                                        "amount": 326600,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 326600,
                                                        "pax_count": 3,
                                                        "pax_type": "ADT",
                                                        "total": 979800
                                                    }
                                                ],
                                                "pax_type": "ADT"
                                            },
                                            {
                                                "service_charges": [
                                                    {
                                                        "sequence": 1,
                                                        "charge_code": "fare",
                                                        "charge_type": "FARE",
                                                        "currency": "IDR",
                                                        "amount": 3600000,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 3600000,
                                                        "pax_count": 2,
                                                        "pax_type": "CHD",
                                                        "total": 7200000
                                                    },
                                                    {
                                                        "sequence": 2,
                                                        "charge_code": "tax",
                                                        "charge_type": "TAX",
                                                        "currency": "IDR",
                                                        "amount": 326600,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 326600,
                                                        "pax_count": 2,
                                                        "pax_type": "CHD",
                                                        "total": 653200
                                                    }
                                                ],
                                                "pax_type": "CHD"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "contacts": [],
                "passengers": [
                    {
                        "sequence": 1,
                        "title": "MR",
                        "first_name": "LINA",
                        "last_name": "DALTON",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 2,
                        "title": "MRS",
                        "first_name": "LIO",
                        "last_name": "DALTON",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 3,
                        "title": "MSTR",
                        "first_name": "TIKI",
                        "last_name": "DALTON",
                        "pax_type": "CHD",
                        "gender": "",
                        "birth_date": "2010-10-10",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 4,
                        "title": "MISS",
                        "first_name": "ELLA",
                        "last_name": "",
                        "pax_type": "CHD",
                        "gender": "",
                        "birth_date": "2010-02-14",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 5,
                        "title": "MS",
                        "first_name": "LEA",
                        "last_name": "",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    }
                ]
            },
            {
                "id": 71,
                "sequence": "2",
                "pnr": "QPWB2Y",
                "pnr2": "QPWB2Y",
                "reference": "QPWB2Y",
                "expired_date": "2019-07-19 06:57:15",
                "hold_date": "2019-07-19 06:57:15",
                "status": "BOOKED",
                "currency": "IDR",
                "balance_due": 1785420,
                "provider": "amadeus",
                "pax_list": [
                    {
                        "qualifier": "PT",
                        "number": "2"
                    },
                    {
                        "qualifier": "PT",
                        "number": "3"
                    },
                    {
                        "qualifier": "PT",
                        "number": "5"
                    },
                    {
                        "qualifier": "PT",
                        "number": "6"
                    },
                    {
                        "qualifier": "PT",
                        "number": "4"
                    }
                ],
                "journeys": [
                    {
                        "sequence": 1,
                        "origin": "BKK",
                        "origin_terminal": "",
                        "origin_utc": 0,
                        "departure_date": "2019-09-22 08:15:00",
                        "destination": "SUB",
                        "destination_terminal": "2",
                        "destination_utc": 0,
                        "arrival_date": "2019-09-22 18:00:00",
                        "journey_type": "",
                        "departure_date_return": "",
                        "arrival_date_return": "",
                        "elapsed_time_return": "",
                        "transit_count": 1,
                        "transit_count_return": 0,
                        "elapsed_time": "0:9:45:0",
                        "journey_code": "CX,700,BKK,,2019-09-22 08:15:00,HKG,1,2019-09-22 12:10:00,amadeus;CX,779,HKG,1,2019-09-22 14:10:00,SUB,2,2019-09-22 18:00:00,amadeus",
                        "is_combo_price": False,
                        "is_international": False,
                        "provider": "amadeus",
                        "carrier_code_list": [
                            "CX"
                        ],
                        "cabin_class_list": [
                            ""
                        ],
                        "operating_airline_code_list": [],
                        "segments": [
                            {
                                "sequence": 1,
                                "origin": "BKK",
                                "origin_terminal": "",
                                "origin_utc": 0,
                                "departure_date": "2019-09-22 08:15:00",
                                "destination": "HKG",
                                "destination_terminal": "1",
                                "destination_utc": 0,
                                "arrival_date": "2019-09-22 12:10:00",
                                "journey_type": "",
                                "transit_count": 0,
                                "transit_duration": "",
                                "elapsed_time": "0:3:55:0",
                                "segment_code": "CX,700,BKK,,2019-09-22 08:15:00,HKG,1,2019-09-22 12:10:00,amadeus",
                                "segment_code2": "BKK-HKG",
                                "carrier_name": "CX 700",
                                "carrier_code": "CX",
                                "carrier_number": "700",
                                "operating_airline_code": "",
                                "is_international": False,
                                "cabin_class_list": [
                                    ""
                                ],
                                "provider": "amadeus",
                                "legs": [
                                    {
                                        "sequence": 1,
                                        "origin": "BKK",
                                        "origin_terminal": "",
                                        "origin_utc": 0,
                                        "departure_date": "2019-09-22 08:15:00",
                                        "destination": "HKG",
                                        "destination_terminal": "1",
                                        "destination_utc": 0,
                                        "arrival_date": "2019-09-22 12:10:00",
                                        "transit_duration": "",
                                        "carrier_name": "CX 700",
                                        "carrier_code": "CX",
                                        "carrier_number": "700",
                                        "elapsed_time": "0:3:55:0",
                                        "journey_type": "",
                                        "leg_code": "CX,700,BKK,,2019-09-22 08:15:00,HKG,1,2019-09-22 12:10:00,amadeus",
                                        "leg_code2": "BKK-HKG",
                                        "is_international": False,
                                        "operating_airline_code": "",
                                        "provider": "amadeus"
                                    }
                                ],
                                "fares": [
                                    {
                                        "sequence": 1,
                                        "fare_code": "Y",
                                        "cabin_class": "",
                                        "class_of_service": "Y",
                                        "rule_number": "",
                                        "product_class": "Y",
                                        "product_name": "",
                                        "description": "",
                                        "available_count": -1,
                                        "service_charges": [],
                                        "fare_basis_codes": [],
                                        "details": [],
                                        "fare_rules": [],
                                        "service_charge_summary": []
                                    }
                                ]
                            },
                            {
                                "sequence": 2,
                                "origin": "HKG",
                                "origin_terminal": "1",
                                "origin_utc": 0,
                                "departure_date": "2019-09-22 14:10:00",
                                "destination": "SUB",
                                "destination_terminal": "2",
                                "destination_utc": 0,
                                "arrival_date": "2019-09-22 18:00:00",
                                "journey_type": "",
                                "transit_count": 0,
                                "transit_duration": "0:2:0:0",
                                "elapsed_time": "0:3:50:0",
                                "segment_code": "CX,779,HKG,1,2019-09-22 14:10:00,SUB,2,2019-09-22 18:00:00,amadeus",
                                "segment_code2": "HKG-SUB",
                                "carrier_name": "CX 779",
                                "carrier_code": "CX",
                                "carrier_number": "779",
                                "operating_airline_code": "",
                                "is_international": False,
                                "cabin_class_list": [
                                    ""
                                ],
                                "provider": "amadeus",
                                "legs": [
                                    {
                                        "sequence": 1,
                                        "origin": "HKG",
                                        "origin_terminal": "1",
                                        "origin_utc": 0,
                                        "departure_date": "2019-09-22 14:10:00",
                                        "destination": "SUB",
                                        "destination_terminal": "2",
                                        "destination_utc": 0,
                                        "arrival_date": "2019-09-22 18:00:00",
                                        "transit_duration": "",
                                        "carrier_name": "CX 779",
                                        "carrier_code": "CX",
                                        "carrier_number": "779",
                                        "elapsed_time": "0:3:50:0",
                                        "journey_type": "",
                                        "leg_code": "CX,779,HKG,1,2019-09-22 14:10:00,SUB,2,2019-09-22 18:00:00,amadeus",
                                        "leg_code2": "HKG-SUB",
                                        "is_international": False,
                                        "operating_airline_code": "",
                                        "provider": "amadeus"
                                    }
                                ],
                                "fares": [
                                    {
                                        "sequence": 1,
                                        "fare_code": "Y",
                                        "cabin_class": "",
                                        "class_of_service": "Y",
                                        "rule_number": "",
                                        "product_class": "Y",
                                        "product_name": "",
                                        "description": "",
                                        "available_count": -1,
                                        "service_charges": [
                                            {
                                                "sequence": 1,
                                                "charge_code": "fare",
                                                "charge_type": "FARE",
                                                "currency": "THB",
                                                "amount": 56680,
                                                "foreign_currency": "THB",
                                                "foreign_amount": 56680,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 170040
                                            },
                                            {
                                                "sequence": 2,
                                                "charge_code": "YR",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 473400,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 473400,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 1420200
                                            },
                                            {
                                                "sequence": 3,
                                                "charge_code": "E7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 16100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 16100,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 48300
                                            },
                                            {
                                                "sequence": 4,
                                                "charge_code": "G8",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 6900,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 6900,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 20700
                                            },
                                            {
                                                "sequence": 5,
                                                "charge_code": "TS",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 322000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 322000,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 966000
                                            },
                                            {
                                                "sequence": 6,
                                                "charge_code": "G3",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 126100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 126100,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 378300
                                            },
                                            {
                                                "sequence": 7,
                                                "charge_code": "I5",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 90100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 90100,
                                                "pax_count": 3,
                                                "pax_type": "ADT",
                                                "total": 270300
                                            },
                                            {
                                                "sequence": 8,
                                                "charge_code": "fare",
                                                "charge_type": "FARE",
                                                "currency": "THB",
                                                "amount": 42510,
                                                "foreign_currency": "THB",
                                                "foreign_amount": 42510,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 85020
                                            },
                                            {
                                                "sequence": 9,
                                                "charge_code": "YR",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 473400,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 473400,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 946800
                                            },
                                            {
                                                "sequence": 10,
                                                "charge_code": "E7",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 16100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 16100,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 32200
                                            },
                                            {
                                                "sequence": 11,
                                                "charge_code": "G8",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 6900,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 6900,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 13800
                                            },
                                            {
                                                "sequence": 12,
                                                "charge_code": "TS",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 322000,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 322000,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 644000
                                            },
                                            {
                                                "sequence": 13,
                                                "charge_code": "G3",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 126100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 126100,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 252200
                                            },
                                            {
                                                "sequence": 14,
                                                "charge_code": "I5",
                                                "charge_type": "TAX",
                                                "currency": "IDR",
                                                "amount": 90100,
                                                "foreign_currency": "IDR",
                                                "foreign_amount": 90100,
                                                "pax_count": 2,
                                                "pax_type": "CHD",
                                                "total": 180200
                                            }
                                        ],
                                        "fare_basis_codes": [],
                                        "details": [],
                                        "fare_rules": [],
                                        "service_charge_summary": [
                                            {
                                                "service_charges": [
                                                    {
                                                        "sequence": 1,
                                                        "charge_code": "fare",
                                                        "charge_type": "FARE",
                                                        "currency": "THB",
                                                        "amount": 56680,
                                                        "foreign_currency": "THB",
                                                        "foreign_amount": 56680,
                                                        "pax_count": 3,
                                                        "pax_type": "ADT",
                                                        "total": 170040
                                                    },
                                                    {
                                                        "sequence": 2,
                                                        "charge_code": "tax",
                                                        "charge_type": "TAX",
                                                        "currency": "IDR",
                                                        "amount": 1034600,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 1034600,
                                                        "pax_count": 3,
                                                        "pax_type": "ADT",
                                                        "total": 3103800
                                                    }
                                                ],
                                                "pax_type": "ADT"
                                            },
                                            {
                                                "service_charges": [
                                                    {
                                                        "sequence": 1,
                                                        "charge_code": "fare",
                                                        "charge_type": "FARE",
                                                        "currency": "THB",
                                                        "amount": 42510,
                                                        "foreign_currency": "THB",
                                                        "foreign_amount": 42510,
                                                        "pax_count": 2,
                                                        "pax_type": "CHD",
                                                        "total": 85020
                                                    },
                                                    {
                                                        "sequence": 2,
                                                        "charge_code": "tax",
                                                        "charge_type": "TAX",
                                                        "currency": "IDR",
                                                        "amount": 1034600,
                                                        "foreign_currency": "IDR",
                                                        "foreign_amount": 1034600,
                                                        "pax_count": 2,
                                                        "pax_type": "CHD",
                                                        "total": 2069200
                                                    }
                                                ],
                                                "pax_type": "CHD"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "contacts": [],
                "passengers": [
                    {
                        "sequence": 1,
                        "title": "MR",
                        "first_name": "LINA",
                        "last_name": "DALTON",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 2,
                        "title": "MRS",
                        "first_name": "LIO",
                        "last_name": "DALTON",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 3,
                        "title": "MSTR",
                        "first_name": "TIKI",
                        "last_name": "DALTON",
                        "pax_type": "CHD",
                        "gender": "",
                        "birth_date": "2010-10-10",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 4,
                        "title": "MISS",
                        "first_name": "ELLA",
                        "last_name": "",
                        "pax_type": "CHD",
                        "gender": "",
                        "birth_date": "2010-02-14",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    },
                    {
                        "sequence": 5,
                        "title": "MS",
                        "first_name": "LEA",
                        "last_name": "",
                        "pax_type": "ADT",
                        "gender": "",
                        "birth_date": "",
                        "mobile": "",
                        "identity_type": "",
                        "identity_number": "",
                        "nationality_code": "",
                        "passport_number": "",
                        "passport_expdate": "",
                        "country_of_issue_code": "",
                        "ticket_number": ""
                    }
                ]
            }
        ],
        "book_id": 76,
        "context": {
            "uid": 6,
            "user_name": "sam.api",
            "user_login": "sam.api",
            "agent_id": 2,
            "agent_name": "Rodex PTC",
            "agent_type_id": "",
            "agent_type_name": "",
            "agent_type_code": "",
            "api_role": "operator",
            "host_ips": [],
            "configs": {
                "airline": {
                    "provider_access": "all",
                    "providers": {}
                }
            },
            "co_uid": 6,
            "co_user_name": "sam.api",
            "co_user_login": "sam.api",
            "co_agent_id": 2,
            "co_agent_name": "Rodex PTC",
            "co_agent_type_id": "",
            "co_agent_type_name": "",
            "co_agent_type_code": "",
            "sid": "8964180d6fc024fc135f45f774325463f71072f9",
            "signature": "fc17ac8d2dc642b5a91e7be2db0704e8",
            "expired_date": "2019-07-19 07:26:47"
        }
    }

    def create_booking_airline_api(self, req, context):
        # req = copy.deepcopy(self.param_global)
        print(json.dumps(req))
        search_RQ = req['searchRQ']
        booker = req['booker']
        contacts = req['contacts']
        passengers = req['passengers']
        journeys = req['providers_booking_data']

        try:
            values = self._prepare_booking_api(search_RQ,context)
            booker_obj = self.create_booker_api(booker,context)
            contact_obj = self.create_contact_api(contacts[0],booker_obj,context)
            list_passengers = self.create_passenger_api(passengers,context,booker_obj.id,contact_obj.id)

            values.update({
                'user_id': context['co_uid'],
                'sid_booked': context['signature'],
                'booker_id': booker_obj.id,
                'contact_id': contact_obj.id,
                'contact_name': contact_obj.name,
                'contact_email': contact_obj.email,
                'contact_phone': contact_obj.phone_ids[0].phone_number,
                'passenger_ids': [(6,0,list_passengers)]
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
            return Response().get_error("Internal Server Error",500)

    def update_pnr_provider_airline_api(self, req, context):
        ### dapatkan PNR dan ubah ke booked
        ### kemudian update service charges
        req['booking_commit_provider'][-1]['status'] = 'FAILED'
        print(json.dumps(req))
        # req = self.param_update_pnr
        try:

            book_obj = self.env['tt.reservation.airline'].browse(req['book_id'])
            if not book_obj:
                raise Exception('Booking ID not found')

            book_status = []
            pnr_list = []
            hold_date = datetime.datetime(9999,12,31,23,59,59,999999)
            for provider in req['booking_commit_provider']:
                provider_obj = self.env['tt.provider.airline'].browse(provider['provider_id'])

                if not provider_obj:
                    raise Exception('Provider ID not found')

                if provider['status'] == 'BOOKED' and not provider.get('error_code'):
                    ##generate leg data
                    provider_type = self.env['tt.provider.type'].search([('code','=','airline')])[0]
                    for idx,journey in enumerate(provider_obj.journey_ids):
                        for idx1,segment in enumerate(journey.segment_ids):
                            param_segment = provider['journeys'][idx]['segments'][idx1]
                            if segment.segment_code == param_segment['segment_code']:
                                this_segment_legs = []
                                for idx2,leg in enumerate(param_segment['legs']):
                                    leg_org = self.env['tt.destinations'].get_id(leg['origin'],provider_type)
                                    leg_dest = self.env['tt.destinations'].get_id(leg['destination'],provider_type)
                                    leg_prov = self.env['tt.provider'].get_provider_id(leg['provider'],provider_type)
                                    this_segment_legs.append((0,0,{
                                        'sequence': idx2,
                                        'leg_code': leg['leg_code'],
                                        'origin_terminal': leg['origin_terminal'],
                                        'destination_terminal': leg['destination_terminal'],
                                        'origin_id': leg_org,
                                        'destination_id': leg_dest,
                                        'departure_date': datetime.datetime.strptime(leg['departure_date'],"%Y-%m-%d %H:%M:%S"),
                                        'arrival_date': datetime.datetime.strptime(leg['arrival_date'],"%Y-%m-%d %H:%M:%S"),
                                        'provider_id': leg_prov
                                    }))

                                segment.write({
                                    'leg_ids': this_segment_legs
                                })

                                for fare in param_segment['fares']:
                                    provider_obj.create_service_charge(fare['service_charges'])


                    provider_obj.action_booked_api_airline(provider,context)
                    book_status.append(1)
                    pnr_list.append(provider['pnr'])
                    curr_hold_date =datetime.datetime.strptime(provider['hold_date'],'%Y-%m-%d %H:%M:%S')
                    if curr_hold_date < hold_date:
                        hold_date = curr_hold_date
                else:
                    book_status.append(0)
                    provider_obj.action_failed_booked_api_airline()
                    continue

            if any(book_status) == 1:
                book_obj.calculate_service_charge()
                book_obj.action_booked_api(pnr_list,hold_date)
                return Response().get_no_error({
                    'order_number': book_obj.name
                })
            else:
                raise('Update Booking Failed')


        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return Response().get_error(str(e), 500)

    def get_booking_airline_api(self,req, context):
        try:
            order_number = req.get('order_number')
            if order_number:
                book_obj = self.env['tt.reservation.airline'].search([('name','=',order_number)])
                if book_obj:
                    res = book_obj.to_dict()
                    psg_list = []
                    for rec in book_obj.passenger_ids:
                        psg_list.append(rec.to_dict())
                    prov_list = []
                    for rec in book_obj.provider_booking_ids:
                        prov_list.append(rec.to_dict())
                    seg_list = []
                    for rec in book_obj.segment_ids:
                        seg_list.append(rec.to_dict())
                    res.update({
                        'direction': book_obj.direction,
                        'origin': book_obj.origin_id.code,
                        'destination': book_obj.destination_id.code,
                        'sector_type': book_obj.sector_type,
                        'passenger_ids': psg_list,
                        'provider_booking_ids': prov_list,
                        'segment_ids': seg_list,
                        'provider_type': book_obj.provider_type_id.code
                    })
                    print(json.dumps(res))
                    return Response().get_no_error(res)
                else:
                    raise('Booking not found')
            else:
                raise('No Order Number provided')
        except Exception as e:
            _logger.info(str(e) + traceback.format_exc())
            return Response().get_error(str(e),500)

    def validate_booking(self, api_context=None):
        user_obj = self.env['res.users'].browse(api_context['co_uid'])
        if not user_obj:
            raise Exception('User NOT FOUND...')
        return True

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
            'agent_id': context_gateway['agent_id'],
            'user_id': context_gateway['co_uid']
        }

        return booking_tmp

    ##todo kalau kejadian saling tumpuk data customer karena ada yang kosong
    ##dibuatkan mekanisme pop isi dictionary yang valuenya kosong

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

                    if len(journey_value) < 1:
                        continue
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

    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        sc_value = {}
        for provider in self.provider_booking_ids:
            for p_sc in provider.cost_service_charge_ids:
                p_charge_type = p_sc.charge_type
                p_pax_type = p_sc.pax_type
                if not sc_value.get(p_charge_type):
                    sc_value[p_charge_type] = {}
                if not sc_value[p_charge_type].get(p_pax_type):
                    sc_value[p_charge_type][p_pax_type] = {}
                    sc_value[p_charge_type][p_pax_type].update({
                        'amount': 0,
                        'total': 0,
                        'foreign_amount': 0
                    })

                sc_value[p_charge_type][p_pax_type].update({
                    'charge_code': p_charge_type,
                    'pax_count': p_sc.pax_count,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_charge_type][p_pax_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_charge_type][p_pax_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_charge_type][p_pax_type]['foreign_amount'] + p_sc.foreign_amount,
                })

        print(sc_value)
        values = []
        for c_type,c_val in sc_value.items():
            for p_type,p_val in c_val.items():
                curr_dict = {}
                curr_dict['charge_type'] = c_type
                curr_dict['pax_type'] = p_type
                curr_dict['booking_airline_id'] = self.id
                curr_dict.update(p_val)
                values.append((0,0,curr_dict))

        self.write({
            'sale_service_charge_ids': values
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


