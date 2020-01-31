from odoo import api, fields, models, _
import json
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
        wizard_form = self.env.ref('tt_reservation_airline_get_booking_from_vendor_review_form_view', False)
        view_id = self.env['tt.get.booking.from.vendor.review']
        journey_values = ""
        price_values = ""
        prices = {}
        for rec in get_booking_res['journeys']:
            journey_values += "%s\n%s %s - %s %s\n\n" % (",".join(rec['carrier_code_list']),
                                                             rec['origin'],
                                                             rec['departure_date'],
                                                             rec['destination'],
                                                             rec['arrival_date'])
            for segment in rec['segments']:
                for fare in segment['fares']:
                    for svc in filter(lambda x : x['charge_type'] != 'RAC',fare['service_charges']):
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
        for pax_type,pax_val in prices.items():
            for charge_type,charge_val in pax_val.items():
                price_values += "%s x %s %s @ %s = %s" % (charge_val['pax_count'],
                                                          charge_type,
                                                          pax_type,
                                                          charge_val['amount'],
                                                          charge_val['total'])

        passenger_values = ""
        for rec in get_booking_res['passengers']:
            passenger_values += "%s %s %s %s" % (rec['title'],rec['first_name'],rec['last_name'],rec['pax_type'])

        vals = {
            'pnr': get_booking_res['pnr'],
            'status': get_booking_res['status'],
            'user_id': self.user_id.id,
            'agent_id': self.agent_id.id,
            'booker_id': self.booker_id and self.booker_id.id or self.booker_first_name,
            'journey_ids_char': journey_values,
            'passenger_ids_char': passenger_values,
            'price_itinerary': price_values,
            # 'grand_total': html_content,
            # 'total_commission': html_content,
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
    journey_ids_char = fields.Char("Journeys")

    booker_id = fields.Many2one("tt.customer","Booker")

    passenger_ids_char = fields.Char("Passengers")

    price_itinerary = fields.Char("Price Itinerary")

    grand_total = fields.Char("Grand Total")
    total_commission = fields.Char("Total Commission")