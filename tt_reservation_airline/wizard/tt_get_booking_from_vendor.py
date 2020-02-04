from odoo import api, fields, models, _
import json,copy
from odoo.exceptions import UserError

class TtGetBookingFromVendor(models.TransientModel):
    _name = "tt.get.booking.from.vendor"
    _description = "Rodex Model Get Booking from Vendor"

    pnr = fields.Char('PNR', required=True)
    provider = fields.Selection([
        # ('sabre', 'Sabre'),
        ('amadeus', 'Amadeus'),
        # ('altea', 'Garuda Altea'),
        # ('lionair', 'Lion Air'),
    ], string='Provider', required=True)

    parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, related ="agent_id.parent_agent_id")
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', required=True, domain=[('id','=',-1)])
    user_id = fields.Many2one('res.users', 'User', required=True, domain=[('id','=',-1)])

    is_database_booker = fields.Boolean('Is Database Booker', default=True)
    booker_id = fields.Many2one('tt.customer', 'Booker')
    booker_title = fields.Selection([('MR', 'Mr.'), ('MSTR', 'Mstr.'), ('MRS', 'Mrs.'), ('MS', 'Ms.'), ('MISS', 'Miss')], string='Title')
    booker_first_name = fields.Char('First Name')
    booker_nationality_id = fields.Many2one('res.country', default=lambda self: self.env.ref('base.id').id)
    booker_last_name = fields.Char('Last Name')
    booker_calling_code = fields.Char('Calling Code')
    booker_mobile = fields.Char('Mobile')
    booker_email = fields.Char('Email')

    @api.onchange("agent_id")
    def _onchange_agent_id(self):
        if self.agent_id:
            self.customer_parent_id = self.agent_id.customer_parent_walkin_id.id
            return {'domain': {
                'user_id': [('agent_id','=',self.agent_id.id)],
                'customer_parent_id': [('parent_agent_id','=',self.agent_id.id)]
            }}

    @api.onchange("pnr")
    def _onchange_pnr(self):
        if self.pnr:
            return {'domain': {
                'agent_id': [('id','!=',self.env.ref('tt_base.rodex_ho').id)]
            }}

    @api.onchange("is_database_contact")
    def _onchange_is_database_contact(self):
        if self.is_database_contact:
            self.booker_title = False
            self.booker_first_name = False
            self.booker_last_name = False
            self.booker_title = False
            self.booker_nationality_id = False
            self.booker_calling_code = False
            self.booker_mobile = False
            self.booker_email = False
        else:
            self.booker_id = False

    def send_get_booking(self):
        if self.booker_calling_code and not self.booker_calling_code.isnumeric() or False:
            raise UserError("Calling Code Must be Number.")
        if self.booker_mobile and not self.booker_mobile.isnumeric() or False:
            raise UserError("Booker Mobile Must be Number.")
        res = self.env['tt.airline.api.con'].send_get_booking_from_vendor(self.pnr,self.provider)
        print(json.dumps(res))
        if res['error_code'] != 0:
            raise UserError(res['error_msg'])
        get_booking_res = res['response']
        wizard_form = self.env.ref('tt_reservation_airline.tt_reservation_airline_get_booking_from_vendor_review_form_view', False)
        view_id = self.env['tt.get.booking.from.vendor.review']
        journey_values = ""
        price_values = ""
        prices = {}
        for rec in get_booking_res['journeys']:
            for segment in rec['segments']:
                journey_values += "%s\n%s %s - %s %s\n\n" % (segment['carrier_name'],
                                                             segment['origin'],
                                                             segment['departure_date'],
                                                             segment['destination'],
                                                             segment['arrival_date'])
                for fare in segment['fares']:
                    for svc in fare['service_charges']:
                        if svc['pax_type'] not in prices:
                            prices[svc['pax_type']] = {}
                        if svc['charge_type'] not in prices[svc['pax_type']]:
                            prices[svc['pax_type']][svc['charge_type']] = {
                                'amount': 0,
                                'total': 0,
                                'pax_count': 0,
                                'currency': 'IDR',###hard code currency
                                'foreign_amount': 0,
                                'foreign_currency': 'IDR',
                            }
                        prices[svc['pax_type']][svc['charge_type']]['amount'] += svc['amount']
                        prices[svc['pax_type']][svc['charge_type']]['total'] += svc['total']
                        prices[svc['pax_type']][svc['charge_type']]['foreign_amount'] += svc['foreign_amount']
                        prices[svc['pax_type']][svc['charge_type']]['pax_count'] = svc['pax_count']
                        prices[svc['pax_type']][svc['charge_type']]['currency'] = svc['currency']
                        prices[svc['pax_type']][svc['charge_type']]['foreign_currency'] = svc['foreign_currency']
        print(json.dumps(prices))
        grand_total = 0
        commission = 0
        for pax_type,pax_val in prices.items():
            for charge_type,charge_val in pax_val.items():
                if charge_type != 'RAC':
                    price_values += "%s x %s %s @ %s = %s\n\n" % (charge_val['pax_count'],
                                                                  charge_type,
                                                                  pax_type,
                                                                  charge_val['amount'],
                                                                  charge_val['total'])
                    grand_total += charge_val['total']
                else:
                    commission += charge_val['total']

        passenger_values = ""
        pax_count = {}
        for rec in get_booking_res['passengers']:
            passenger_values += "%s %s %s %s\n\n" % (rec['title'],rec['first_name'],rec['last_name'],rec['pax_type'])
            if rec['pax_type'] not in pax_count:
                pax_count[rec['pax_type']] = 0
            pax_count[rec['pax_type']] += 1

        if self.booker_id:
            title = "MR"
            # if self.booker_id.gender == "male":
            #     title = "MR"
            if self.booker_id.gender == "female" and self.booker_id == "married":
                title=  "MRS"
            elif self.booker_id.gender == "female":
                title = "MS"

            booker_data = {
                "title": title,
                "first_name": self.booker_id.first_name or "",
                "last_name": self.booker_id.last_name or "",
                "email": self.booker_id.email or "",
                "calling_code": self.booker_id.phone_ids and self.booker_id.phone_ids[0].calling_code or "",
                "mobile": self.booker_id.phone_ids and self.booker_id.phone_ids[0].calling_number or "",
                "nationality_code": self.booker_id.nationality_id.code,
                "is_also_booker": True,
                "gender": self.booker_id.gender
            }
        else:
            booker_data = {
                "title": self.booker_title,
                "first_name": self.booker_first_name,
                "last_name": self.booker_last_name,
                "email": self.booker_email,
                "calling_code": self.booker_calling_code,
                "mobile": self.booker_mobile,
                "nationality_code": self.booker_nationality_id.code,
                "is_also_booker": True,
                "gender": "male" if self.booker_title == "MR" or self.booker_title == "MSTR" else "female"
            }

        vals = {
            'pnr': get_booking_res['pnr'],
            'status': get_booking_res['status'],
            'user_id': self.user_id.id,
            'agent_id': self.agent_id.id,
            'booker_id': self.booker_id and self.booker_id.id or False,
            "booker_data": json.dumps(booker_data),
            'journey_ids_char': journey_values,
            'passenger_ids_char': passenger_values,
            'price_itinerary': price_values,
            'grand_total': grand_total,
            'total_commission': abs(commission),
            'get_booking_json': json.dumps(res),
            'pax_type_data': json.dumps(pax_count)
        }
        new = view_id.create(vals)

        return {
            'name': _('Booking Review'),
            'type': 'ir.actions.act_window',
            'res_model': 'tt.get.booking.from.vendor.review',
            'res_id': new.id,
            'view_id': wizard_form.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }


class TtGetBookingFromVendorReview(models.TransientModel):
    _name = "tt.get.booking.from.vendor.review"
    _description = "Rodex Model Get Booking from Vendor Review"

    pnr = fields.Char("PNR")
    status = fields.Char("Status")
    user_id = fields.Many2one("res.users","User")
    agent_id = fields.Many2one("tt.agent","Agent")

    # journey_ids = fields.One2many("")
    journey_ids_char = fields.Text("Journeys")

    booker_id = fields.Many2one("tt.customer","Booker")

    booker_data = fields.Text("Booker Data")

    passenger_ids_char = fields.Text("Passengers")

    price_itinerary = fields.Text("Price Itinerary")

    grand_total = fields.Char("Grand Total")
    total_commission = fields.Char("Total Commission")

    get_booking_json = fields.Text("Json Data")

    pax_type_data = fields.Text("Pax Type Data")

    def save_booking(self):
        booking_res = json.loads(self.get_booking_json)
        signature = booking_res['signature']
        retrieve_res = booking_res['response']
        pax_type_res = json.loads(self.pax_type_data)
        booker_res = json.loads(self.booker_data)

        searchRQ_journey_list = []
        journey_req_list = []
        for journey in retrieve_res['journeys']:
            searchRQ_journey_list.append({
                'origin': journey['origin'],
                'destination': journey['destination'],
                'departure_date': journey['departure_date']
            })
            segment_req_list = []
            for segment in journey['segments']:
                segment_req_list.append({
                    'segment_code': segment['segment_code'],
                    "fare_code": "EMPTY",
                    "carrier_code": segment['carrier_code'],
                    "carrier_number": segment['carrier_number'],
                    "origin": segment['origin'],
                    "departure_date": segment['departure_date'],
                    "destination": segment['destination'],
                    "arrival_date": segment['arrival_date'],
                    "provider": segment['provider']
                })
            journey_req_list.append({
                'segments': segment_req_list
            })

        schedules_req_list = []
        schedules_req_list.append({
            "journeys": journey_req_list,
            "provider": retrieve_res['provider'],
            "paxs": {
                "ADT": pax_type_res.get('ADT',0),
                "CHD": pax_type_res.get('CHD',0),
                "INF": pax_type_res.get('INF',0)
            },
            "promo_codes": [],
            "schedule_id": 1
        })

        searchRQ_req = {
            "journey_list": searchRQ_journey_list,
            "adult": pax_type_res.get('ADT',0),
            "child": pax_type_res.get('CHD',0),
            "infant": pax_type_res.get('INF',0),
            "direction": "MC",
            "is_get_booking_from_vendor": True
        }

        create_req = {
            "force_issued": False,
            "searchRQ": searchRQ_req,
            "booker": booker_res,
            "contacts": [booker_res],
            "passengers": copy.deepcopy(retrieve_res['passengers']),
            "provider_type": "airline",
            "adult": pax_type_res.get('ADT',0),
            "child": pax_type_res.get('CHD',0),
            "infant": pax_type_res.get('INF',0),
            "schedules": schedules_req_list,
            "promo_codes": [],
        }

        create_res = self.env['tt.reservation.airline'].create_booking_airline_api(create_req,context={
            'co_uid': self.user_id.id,
            'co_agent_id': self.agent_id.id,
            'signature': signature
        })

        if create_res['error_code'] != 0:
            raise UserError(create_res['error_msg'])
        create_res = create_res['response']

        ticket_req_list = []

        for psg in retrieve_res['passengers']:
            ticket_req_list.append({
                "passenger": '%s %s' % (psg['first_name'] or '', psg['last_name'] or ''),
                "pax_type": psg['pax_type'],
                "ticket_number": psg['ticket_number']
            })

        segment_dict_req_list = {}

        for journey in retrieve_res['journeys']:
            for segment in journey['segments']:
                segment_dict_req_list[segment['segment_code']] = segment

        provider_bookings_req = []
        provider_bookings_req.append({
            "pnr": retrieve_res['pnr'],
            "pnr2": retrieve_res['pnr2'],
            "provider": retrieve_res['provider'],
            "provider_id": create_res['provider_ids'][0]['id'],
            "state": retrieve_res['status'],
            "state_description": retrieve_res['status'],
            "sequence": 1,
            "balance_due": retrieve_res['balance_due'],
            "origin": retrieve_res['journeys'][0]['origin'],
            "destination": retrieve_res['journeys'][-1]['destination'],
            "departure_date": retrieve_res['journeys'][0]['departure_date'],
            "return_date": retrieve_res['journeys'][-1]['arrival_date'],
            "currency": retrieve_res['currency'],
            "hold_date": retrieve_res['hold_date'],
            "tickets": ticket_req_list,##
            "error_msg": "",
            "promo_codes": [],
            "reference": retrieve_res['reference'],
            "expired_date": "",
            "status": retrieve_res['status'],
            "balance_due_str": retrieve_res['balance_due_str'],
            "contacts": [],
            "passengers": retrieve_res['passengers'],##
            "order_number": create_res['order_number'],
            "segment_dict": segment_dict_req_list##
        })

        update_req = {
            "book_id": create_res['book_id'],
            "order_number": create_res['order_number'],
            "force_issued": True,
            "provider_bookings": provider_bookings_req,
            "member": False,
            "acquirer_seq_id": ""
        }

        update_res = self.env['tt.reservation.airline'].update_pnr_provider_airline_api(update_req,context={
            'co_uid': self.user_id.id,
            'co_agent_id': self.agent_id.id,
            'signature': signature
        })

        if update_res['error_code'] != 0:
            raise UserError(update_res['error_msg'])