from odoo import api, fields, models, _
import json,copy
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from ...tools import ERR
from ...tools.api import Response
import traceback, logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class TtGetBookingFromVendor(models.TransientModel):
    _name = "tt.get.booking.from.vendor"
    _description = "Get Booking from Vendor"

    pnr = fields.Char('PNR', required=True)

    provider_ho_data_id = fields.Many2one('tt.provider.ho.data', 'Provider')
    parent_agent_id = fields.Many2one('tt.agent', 'Parent Agent', readonly=True, related="agent_id.parent_agent_id")
    ho_id = fields.Many2one('tt.agent', 'Head Office', readonly=True, domain=[('is_ho_agent', '=', True)], required=True, compute='_compute_ho_id')
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', required=True, domain=[('id','=',-1)])
    payment_method_to_ho = fields.Selection([('balance', 'Balance'), ('credit_limit', 'Credit Limit')], 'Payment Method to HO', default='balance')
    user_id = fields.Many2one('res.users', 'User', required=True, domain=[('id','=',-1)])

    is_database_booker = fields.Boolean('Is Database Booker', default=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', domain=[('id','=',-1)])
    booker_title = fields.Selection([('MR', 'Mr.'), ('MSTR', 'Mstr.'), ('MRS', 'Mrs.'), ('MS', 'Ms.'), ('MISS', 'Miss')], string='Title')
    booker_first_name = fields.Char('First Name')
    booker_nationality_id = fields.Many2one('res.country', default=lambda self: self.env.ref('base.id').id)
    booker_last_name = fields.Char('Last Name')
    booker_calling_code = fields.Char('Calling Code')
    booker_mobile = fields.Char('Calling Number')
    booker_email = fields.Char('Email')

    is_bypass_pnr_validator = fields.Boolean('Is Bypass PNR Validator')

    pricing_date = fields.Date('Pricing Date')
    last_name = fields.Char('Pax Last Name')

    @api.depends('agent_id')
    @api.onchange('agent_id')
    def _compute_ho_id(self):
        self.ho_id = self.agent_id.ho_id.id

    @api.onchange('agent_id')
    def _onchange_provider_ho_data_id(self):
        if self.agent_id:
            return {'domain': {
                'provider_ho_data_id': [('ho_id','=', self.agent_id.ho_id.id)]
            }}

    def get_provider_booking_from_vendor_api(self):
        try:
            res = {}
            provider_ho_data_objs = self.env['tt.provider.ho.data'].search([('provider_id.provider_type_id.id','=', self.env.ref('tt_reservation_airline.tt_provider_type_airline').id)])
            for provider_ho_data_obj in provider_ho_data_objs:
                if provider_ho_data_obj.ho_id:
                    if provider_ho_data_obj.ho_id.seq_id not in res:
                        res[provider_ho_data_obj.ho_id.seq_id] = []
                    res[provider_ho_data_obj.ho_id.seq_id].append([provider_ho_data_obj.provider_id.code, provider_ho_data_obj.provider_id.name])
            response = {
                'list_provider': res
            }
            res = Response().get_no_error(response)
        except Exception as e:
            return ERR.get_error(500)
        return res

    @api.onchange("agent_id")
    def _onchange_agent_id(self):
        if self.agent_id:
            self.customer_parent_id = self.agent_id.customer_parent_walkin_id.id
            return {'domain': {
                'user_id': [('agent_id','=',self.agent_id.id)],
                'customer_parent_id': [('parent_agent_id','=',self.agent_id.id)]
            }}

    @api.onchange("customer_parent_id")
    def _onchange_customer_parent_id(self):
        if self.customer_parent_id:
            return {'domain': {
                'booker_id': [('id', 'in', self.customer_parent_id.customer_ids.ids)],
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

    def pnr_validator_api(self, req, context):
        try:
            self.pnr_validator(req['pnr'])
            return ERR.get_no_error()
        except Exception as e:
            return ERR.get_error(additional_message=str('duplicate pnr'))

    def pnr_validator(self,pnr):
        today = date.today()
        date_query = today - relativedelta(days=7)
        airlines = self.env['tt.reservation.airline'].search([
            ('pnr','ilike',pnr),
            ('state','not in',['cancel','draft']),
            ('arrival_date','>=',date_query),
        ])
        if airlines:
            raise UserError('PNR Exists on [%s].' % (','.join([rec.name for rec in airlines])))

    def send_get_booking(self):
        if self.booker_calling_code and not self.booker_calling_code.isnumeric() or False:
            raise UserError("Calling Code Must be Number.")
        if self.booker_mobile and not self.booker_mobile.isnumeric() or False:
            raise UserError("Booker Mobile Must be Number.")
        if not self.is_bypass_pnr_validator:
            self.pnr_validator(self.pnr)

        req = {
            'user_id': self.user_id.id,
            'pnr': self.pnr,
            'provider': self.provider_ho_data_id.provider_id.code
        }

        if self.pricing_date:
            req.update({
                'is_retrieved': True,
                'pricing_date': str(self.pricing_date)
            })
        if self.agent_id:
            req.update({
                'ho_id': self.agent_id.ho_id.id
            })
        if self.last_name:
            req.update({
                'passengers': [{
                    'last_name': self.last_name,
                }]
            })
        res = self.env['tt.airline.api.con'].send_get_booking_from_vendor(req)
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
            price_values += '\n'

        passenger_values = ""
        pax_count = {}
        for rec in get_booking_res['passengers']:
            passenger_values += "%s %s %s %s" % (rec['title'],rec['first_name'],rec['last_name'],rec['pax_type'])
            if rec['pax_type'] not in pax_count:
                pax_count[rec['pax_type']] = 0
            pax_count[rec['pax_type']] += 1
            passenger_values += '\n'
            if rec.get('fees'):
                passenger_values += 'SSR\n'
                for fee in rec['fees']:
                    fee_name = fee['fee_name'] if fee.get('fee_name') else '%s %s %s' % (fee.get('fee_type', ''), fee.get('fee_code', ''), fee.get('fee_value', ''))
                    passenger_values += "%s = %s\n" % (fee_name, fee.get('base_price', '?'))
                    grand_total += fee.get('base_price', 0.0)
            passenger_values += '\n'

        if self.booker_id:
            title = "MR"
            # if self.booker_id.gender == "male":
            #     title = "MR"
            if self.booker_id.gender == "female" and self.booker_id == "married":
                title = "MRS"
            elif self.booker_id.gender == "female":
                title = "MS"

            booker_data = {
                "title": title,
                "first_name": self.booker_id.first_name or "",
                "last_name": self.booker_id.last_name or "",
                "email": self.booker_id.email or self.booker_email,
                "calling_code": self.booker_id.phone_ids and self.booker_id.phone_ids[0].calling_code or self.booker_calling_code,
                "mobile": self.booker_id.phone_ids and self.booker_id.phone_ids[0].calling_number or self.booker_mobile,
                "nationality_code": self.booker_id.nationality_id.code,
                "is_also_booker": True,
                "gender": self.booker_id.gender,
                "booker_seq_id": self.booker_id.seq_id
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
                "gender": "male" if self.booker_title == "MR" or self.booker_title == "MSTR" else "female",
                "is_get_booking_from_vendor": True,
                "is_search_allowed": False
            }

        vals = {
            'pnr': get_booking_res['pnr'],
            'status': get_booking_res['status'],
            'user_id': self.user_id.id,
            'ho_id': self.ho_id.id,
            'agent_id': self.agent_id.id,
            'customer_parent_id': self.customer_parent_id.id,
            'payment_method_to_ho': self.payment_method_to_ho,
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
    _description = "Get Booking from Vendor Review"

    pnr = fields.Char("PNR")
    status = fields.Char("Status")
    user_id = fields.Many2one("res.users","User")
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one("tt.agent","Agent")
    customer_parent_id = fields.Many2one("tt.customer.parent","Customer Parent")
    payment_method_to_ho = fields.Selection([('balance', 'Balance'), ('credit_limit', 'Credit Limit')], 'Payment Method to HO', default='balance')

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

    def create_data_by_api(self, req, context):

        res = req['response']
        get_booking_res = res['response']

        if not req['duplicate_pnr']:
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
                                    'currency': 'IDR',  ###hard code currency
                                    'foreign_amount': 0,
                                    'foreign_currency': 'IDR',
                                }
                            prices[svc['pax_type']][svc['charge_type']]['amount'] += svc['amount']
                            prices[svc['pax_type']][svc['charge_type']]['total'] += svc['total']
                            prices[svc['pax_type']][svc['charge_type']]['foreign_amount'] += svc['foreign_amount']
                            prices[svc['pax_type']][svc['charge_type']]['pax_count'] = svc['pax_count']
                            prices[svc['pax_type']][svc['charge_type']]['currency'] = svc['currency']
                            prices[svc['pax_type']][svc['charge_type']]['foreign_currency'] = svc['foreign_currency']
            grand_total = 0
            commission = 0
            for pax_type, pax_val in prices.items():
                for charge_type, charge_val in pax_val.items():
                    if charge_type != 'RAC':
                        price_values += "%s x %s %s @ %s = %s\n\n" % (charge_val['pax_count'],
                                                                      charge_type,
                                                                      pax_type,
                                                                      charge_val['amount'],
                                                                      charge_val['total'])
                        grand_total += charge_val['total']
                    else:
                        commission += charge_val['total']
                price_values += '\n'

            passenger_values = ""
            pax_count = {}
            for rec in get_booking_res['passengers']:
                passenger_values += "%s %s %s %s\n\n" % (rec['title'], rec['first_name'], rec['last_name'], rec['pax_type'])
                if rec['pax_type'] not in pax_count:
                    pax_count[rec['pax_type']] = 0
                pax_count[rec['pax_type']] += 1

            # booker_data ambil data dari booker_id
            booker_data = {}
            booker_obj = self.env['tt.customer'].search([('seq_id','=',req['booker_id'])], limit=1)
            if booker_obj:
                title = "MR"
                # if self.booker_id.gender == "male":
                #     title = "MR"
                if booker_obj.gender == "female" and booker_obj.marital_status:
                    title = "MS"
                elif booker_obj.gender == "female":
                    title = "MRS"

                booker_data = {
                    "title": title,
                    "first_name": booker_obj.first_name or "",
                    "last_name": booker_obj.last_name or "",
                    "email": booker_obj.email,
                    "calling_code": booker_obj.phone_ids and booker_obj.phone_ids[0].calling_code or '',
                    "mobile": booker_obj.phone_ids and booker_obj.phone_ids[0].calling_number or '',
                    "nationality_code": booker_obj.nationality_id.code,
                    "is_also_booker": True,
                    "gender": booker_obj.gender,
                    "booker_seq_id": booker_obj.seq_id
                }
            customer_parent_id = 0
            if req.get('customer_parent_id') == '':
                customer_parent_id = self.env['res.users'].search([('id','=', context['co_uid'])]).agent_id.customer_parent_walkin_id.id
            else:
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id','=',req.get('customer_parent_id'))]).id

            vals = {
                'pnr': get_booking_res['pnr'],
                'status': get_booking_res['status'],
                'user_id': int(context['co_uid']),
                'ho_id': int(context['co_ho_id']),
                'agent_id': int(context['co_agent_id']),
                'booker_id': booker_obj.id,
                "booker_data": json.dumps(booker_data),
                'customer_parent_id': customer_parent_id,
                'journey_ids_char': journey_values,
                'passenger_ids_char': passenger_values,
                'price_itinerary': price_values,
                'grand_total': grand_total,
                'total_commission': abs(commission),
                'get_booking_json': json.dumps(res),
                'pax_type_data': json.dumps(pax_count),
                'payment_method_to_ho': req.get('payment_method_to_ho', False)
            }
            new = view_id.create(vals)
            return new
        else:
            raise Exception('duplicate pnr')

    def save_booking_api(self, req, context):
        try:
            data_create = self.create_data_by_api(req, context)
            res = data_create.save_booking()
            return ERR.get_no_error(res['response'])
        except Exception as e:
            _logger.error('Error save booking from vendor frontend, %s' % traceback.format_exc())
            return ERR.get_error(500, additional_message=e.args[0])

    def save_booking_button(self):
        temp = self.save_booking()
        return temp

    def save_booking(self, pin=''):
        booking_res = json.loads(self.get_booking_json)
        signature = booking_res['signature']
        retrieve_res = booking_res['response']
        pax_type_res = json.loads(self.pax_type_data)
        booker_res = json.loads(self.booker_data)

        if retrieve_res['status'] == 'ISSUED' and self.env.user.is_using_pin and not pin:
            view = self.env.ref('tt_base.tt_input_pin_wizard_form_view')
            return {
                'name': 'Input Pin Wizard',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tt.input.pin.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': {
                    'default_res_model': self._name,
                    'default_res_id': self.id
                }
            }

        searchRQ_journey_list = []
        # journey_req_list = []
        for journey in retrieve_res['journeys']:
            searchRQ_journey_list.append({
                'origin': journey['origin'],
                'destination': journey['destination'],
                'departure_date': journey['departure_date'][:10]
            })
            ## comment before create booking changes for force issued
            # segment_req_list = []
            # for segment in journey['segments']:
            #     segment_req_list.append({
            #         'segment_code': segment['segment_code'],
            #         "fare_code": "EMPTY",
            #         "carrier_code": segment['carrier_code'],
            #         "carrier_number": segment['carrier_number'],
            #         "origin": segment['origin'],
            #         "departure_date": segment['departure_date'],
            #         "destination": segment['destination'],
            #         "arrival_date": segment['arrival_date'],
            #         "provider": segment['provider']
            #     })
            # journey_req_list.append({
            #     'segments': segment_req_list
            # })

        schedules_req_list = []
        schedules_req_list.append({
            "pnr": retrieve_res['pnr'], ## ini itu pnr
            "pnr2": retrieve_res['pnr2'], ## ini itu pnr2
            "reference": retrieve_res['reference'], ## ini itu reference
            "journeys": retrieve_res['journeys'], ## ini itu schedule
            "passengers": retrieve_res['passengers'], ## yg ini untuk fees passenger
            "provider": retrieve_res['provider'],
            "paxs": {
                "ADT": pax_type_res.get('ADT',0),
                "CHD": pax_type_res.get('CHD',0),
                "INF": pax_type_res.get('INF',0)
            },
            "promo_codes": retrieve_res.get('promo_codes', []),
            "schedule_id": 1
        })

        searchRQ_req = {
            "journey_list": searchRQ_journey_list,
            "adult": pax_type_res.get('ADT',0),
            "child": pax_type_res.get('CHD',0),
            "infant": pax_type_res.get('INF',0),
            "direction": "OTHER",
            "is_get_booking_from_vendor": True,
            "payment_method_to_ho": self.payment_method_to_ho
        }

        for rec in retrieve_res['passengers']:
            rec['is_get_booking_from_vendor'] = True
            rec['is_search_allowed'] = False
            if rec.get('identity'):
                if rec['identity'].get('identity_expdate'):
                    if datetime.strptime(rec['identity']['identity_expdate'], '%Y-%m-%d').year < 1900:
                        rec['identity'] = {}


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
            "booking_state_provider": schedules_req_list, ## ini itu schedule
            "promo_codes": retrieve_res.get('promo_codes', []),
        }

        create_res = self.env['tt.reservation.airline'].create_booking_airline_api(create_req,context={
            'co_uid': self.user_id.id,
            'co_user_name': self.user_id.name,
            'co_agent_id': self.agent_id.id,
            'co_agent_name': self.agent_id.name,
            'co_ho_id': self.agent_id.ho_id.id,
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
            "total_price": retrieve_res['total_price'],
            "origin": retrieve_res['journeys'][0]['origin'],
            "destination": retrieve_res['journeys'][-1]['destination'],
            "departure_date": retrieve_res['journeys'][0]['departure_date'],
            "arrival_date": retrieve_res['journeys'][-1]['arrival_date'],
            "currency": retrieve_res['currency'],
            "hold_date": retrieve_res.get('hold_date'),
            "tickets": ticket_req_list,##
            "error_msg": "",
            "promo_codes": retrieve_res.get('promo_codes', []),
            "reference": retrieve_res['reference'],
            "expired_date": "",
            "status": retrieve_res['status'],
            "balance_due_str": retrieve_res['balance_due_str'],
            "contacts": [],
            "passengers": retrieve_res['passengers'],##
            "order_number": create_res['order_number'],
            "segment_dict": segment_dict_req_list,##
            "journeys": retrieve_res.get('journeys', []),
            "is_hold_date_sync": retrieve_res.get('is_hold_date_sync', True),
            "is_advance_purchase": retrieve_res.get('is_advance_purchase', False),
        })


        update_req = {
            "book_id": create_res['book_id'],
            "order_number": create_res['order_number'],
            "force_issued": True,
            "provider_bookings": provider_bookings_req,
            "agent_payment_method": self.payment_method_to_ho,
            "member": False,
            "acquirer_seq_id": ""
        }

        if self.customer_parent_id.id != self.agent_id.customer_parent_walkin_id.id:
            update_req.update({
                'member': True,
                'acquirer_seq_id': self.customer_parent_id.seq_id
            })

        # June 29, 2020 - SAM
        # Menambahkan mekanisme untuk create ledger required untuk memanggil fungsi add payment
        payment_res = {
            'error_code': 0,
            'error_msg': ''
        }
        if retrieve_res['status'] == 'ISSUED' and self.env['ir.config_parameter'].sudo().get_param('create.ledger.issued.get.booking') in ['True', 'true', '1']:
            if self.env.user.is_using_pin:
                update_req.update({
                    'pin': pin
                })
            payment_res = self.env['tt.reservation.airline'].payment_reservation_api('airline', update_req,context={
                'co_uid': self.env.user.id,
                'co_user_name': self.env.user.name,
                'co_ho_id': self.agent_id.ho_id.id,
                'co_agent_id': self.agent_id.id,
                'co_agent_name': self.agent_id.name,
                'signature': signature
            })
            # co_uid diisi self.env.user.id supaya staff yg click yang di check pin, dan kalau salah pin yang di ban staff yang click

        # END

        update_res = self.env['tt.reservation.airline'].update_pnr_provider_airline_api(update_req,context={
            'co_uid': self.user_id.id,
            'co_user_name': self.user_id.name,
            'co_ho_id': self.agent_id.ho_id.id,
            'co_agent_id': self.agent_id.id,
            'co_agent_name': self.agent_id.name,
            'signature': signature
        })

        if update_res['error_code'] != 0:
            raise UserError(update_res['error_msg'])
        update_res['response'].pop('book_id')

        if payment_res['error_code'] != 0:
            raise UserError(payment_res['error_msg'])
        return update_res
