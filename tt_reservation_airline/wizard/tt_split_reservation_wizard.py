from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class TtSplitReservationWizard(models.TransientModel):
    _name = "tt.split.reservation.wizard"
    _description = 'Airline Split Reservation Wizard'

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    referenced_document = fields.Char('Ref. Document', required=True, readonly=True)
    new_pnr = fields.Char('New PNR')

    def get_split_provider_domain(self):
        return [('booking_id', '=', self.res_id)]

    def get_split_passenger_domain(self):
        return [('booking_id', '=', self.res_id)]

    provider_ids = fields.Many2many('tt.provider.airline', 'airline_provider_split_rel', 'split_wizard_id', 'provider_id', 'PNR',
                           domain=get_split_provider_domain)
    passenger_ids = fields.Many2many('tt.reservation.passenger.airline', 'airline_passenger_split_rel', 'split_wizard_id', 'passenger_id', 'Passenger',
                           domain=get_split_passenger_domain)

    @api.onchange('res_id')
    def _onchange_domain_provider(self):
        return {'domain': {
            'provider_ids': self.get_split_provider_domain()
        }}

    @api.onchange('res_id')
    def _onchange_domain_passenger(self):
        return {'domain': {
            'passenger_ids': self.get_split_passenger_domain()
        }}

    def submit_split_reservation(self):
        book_obj = self.env['tt.reservation.airline'].sudo().browse(int(self.res_id))
        provider_list = []
        pax_list = []
        is_provider_full = True
        is_pax_full = True
        for rec in self.provider_ids:
            provider_list.append(rec.id)
        for rec in self.passenger_ids:
            pax_list.append(rec.id)
        for rec in book_obj.provider_booking_ids:
            if rec.id not in provider_list:
                is_provider_full = False
        for rec in book_obj.passenger_ids:
            if rec.id not in pax_list:
                is_pax_full = False

        if is_provider_full and is_pax_full:
            raise UserError(_('You cannot split all PNR(s) and Passenger(s) in this reservation. Please leave at least 1 PNR or 1 Passenger!'))
        if is_provider_full and len(pax_list) <= 0:
            raise UserError(_('You cannot split all PNR(s) in this reservation without any Passenger(s).'))
        if len(provider_list) <= 0 and is_pax_full:
            raise UserError(_('You cannot split all Passenger(s) in this reservation without any PNR(s).'))
        if len(provider_list) <= 0 and len(pax_list) <= 0:
            raise UserError(_('You need to input at least 1 PNR or 1 Passenger to split this reservation.'))
        if len(pax_list) > 0 and not self.new_pnr:
            raise UserError(_('You need to input New PNR to split Passenger(s).'))

        new_vals = {
            'split_from_resv_id': book_obj.id,
            'pnr': book_obj.pnr,
            'agent_id': book_obj.agent_id and book_obj.agent_id.id or False,
            'customer_parent_id': book_obj.customer_parent_id and book_obj.customer_parent_id.id or False,
            'provider_type_id': book_obj.provider_type_id.id,
            'provider_name': book_obj.provider_name,
            'carrier_name': book_obj.carrier_name,
            'date': book_obj.date,
            'hold_date': book_obj.hold_date,
            'user_id': book_obj.user_id and book_obj.user_id.id or False,
            'create_date': book_obj.create_date,
            'booked_uid': book_obj.booked_uid and book_obj.booked_uid.id or False,
            'booked_date': book_obj.booked_date,
            'issued_uid': book_obj.issued_uid and book_obj.issued_uid.id or False,
            'issued_date': book_obj.issued_date,
            'origin_id': book_obj.origin_id and book_obj.origin_id.id or False,
            'destination_id': book_obj.destination_id and book_obj.destination_id.id or False,
            'sector_type': book_obj.sector_type,
            'direction': book_obj.direction,
            'departure_date': book_obj.departure_date,
            'return_date': book_obj.return_date,
            'booker_id': book_obj.booker_id and book_obj.booker_id.id or False,
            'contact_id': book_obj.contact_id and book_obj.contact_id.id or False,
            'contact_title': book_obj.contact_title,
            'contact_email': book_obj.contact_email,
            'contact_phone': book_obj.contact_phone,
            'state': book_obj.state
        }

        new_book_obj = self.env['tt.reservation.airline'].sudo().create(new_vals)
        if len(pax_list) <= 0:
            new_book_obj.sudo.write({
                'adult': book_obj.adult,
                'child': book_obj.child,
                'infant': book_obj.infant
            })
            for rec in self.provider_ids:
                for rec2 in book_obj.segment_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id
                for rec2 in book_obj.provider_booking_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id
                old_pax_id_list = []
                for rec2 in rec.cost_service_charge_ids:
                    new_pax_id_list = []
                    for rec3 in rec2.passenger_airline_ids:
                        if rec3.id not in old_pax_id_list:
                            old_pax_id_list.append(rec3.id)
                            pax_val = {
                                'booking_id': new_book_obj.id,
                                'name': rec3.name,
                                'last_name': rec3.last_name,
                                'title': rec3.title,
                                'nationality_id': rec3.nationality_id and rec3.nationality_id.id or False,
                                'identity_number': rec3.identity_number,
                                'identity_country_of_issued_id': rec3.identity_country_of_issued_id and rec3.identity_country_of_issued_id.id or False,
                                'sequence': rec3.sequence,
                                'is_ticketed': rec3.is_ticketed,
                                'first_name': rec3.first_name,
                                'gender': rec3.gender,
                                'birth_date': rec3.birth_date,
                                'identity_type': rec3.identity_type,
                                'identity_expdate': rec3.identity_expdate,
                                'customer_id': rec3.customer_id and rec3.customer_id.id or False,
                            }
                            new_pax_obj = self.env['tt.reservation.passenger.airline'].sudo().create(pax_val)
                            new_pax_id_list.append(new_pax_obj.id)
                            for rec4 in rec.ticket_ids:
                                if rec4.passenger_id.id == rec3.id:
                                    rec4.sudo().write({
                                        'passenger_id': new_pax_obj.id
                                    })
                    rec2.sudo().write({
                        'passenger_airline_ids': [(6,0,new_pax_id_list)]
                    })
                for rec2 in book_obj.ledger_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.sudo().write({
                            'res_id': new_book_obj.id,
                            'ref': new_book_obj.name
                        })

        elif len(provider_list) <= 0:
            tot_adult = 0
            tot_child = 0
            tot_infant = 0
            for rec in self.passenger_ids:
                for rec2 in book_obj.passenger_ids:
                    if rec2.id == rec.id:
                        rec2.booking_id = new_book_obj.id
                old_provider_list = []
                for rec2 in rec.cost_service_charge_ids:
                    if rec2.provider_airline_booking_id.id not in old_provider_list:
                        old_provider_list.append(rec2.provider_airline_booking_id.id)
                        prov_val = {
                            'sequence': rec2.provider_airline_booking_id.sequence,
                            'booking_id': new_book_obj.id,
                            'pnr': self.new_pnr,
                            'pnr2': self.new_pnr,
                            'provider_id': rec2.provider_airline_booking_id.provider_id and rec2.provider_airline_booking_id.provider_id.id or False,
                            'hold_date': rec2.provider_airline_booking_id.hold_date,
                            'expired_date': rec2.provider_airline_booking_id.expired_date,
                            'booked_uid': rec2.provider_airline_booking_id.booked_uid and rec2.provider_airline_booking_id.booked_uid.id or False,
                            'booked_date': rec2.provider_airline_booking_id.booked_date,
                            'issued_uid': rec2.provider_airline_booking_id.issued_uid and rec2.provider_airline_booking_id.issued_uid.id or False,
                            'issued_date': rec2.provider_airline_booking_id.issued_date,
                            'refund_uid': rec2.provider_airline_booking_id.refund_uid and rec2.provider_airline_booking_id.refund_uid.id or False,
                            'refund_date': rec2.provider_airline_booking_id.refund_date,
                            'origin_id': rec2.provider_airline_booking_id.origin_id and rec2.provider_airline_booking_id.origin_id.id or False,
                            'destination_id': rec2.provider_airline_booking_id.destination_id and rec2.provider_airline_booking_id.destination_id.id or False,
                            'departure_date': rec2.provider_airline_booking_id.departure_date,
                            'return_date': rec2.provider_airline_booking_id.return_date,
                            'sid_issued': rec2.provider_airline_booking_id.sid_issued,
                            'promotion_code': rec2.provider_airline_booking_id.promotion_code,
                            'currency_id': rec2.provider_airline_booking_id.currency_id and rec2.provider_airline_booking_id.currency_id.id or False,
                        }
                        new_prov_obj = self.env['tt.provider.airline'].sudo().create(prov_val)
                        for rec3 in rec2.provider_airline_booking_id.journey_ids:
                            journey_val = {
                                'booking_id': new_book_obj.id,
                                'provider_booking_id': new_prov_obj.id,
                                'sequence': rec3.sequence,
                                'provider_id': rec3.provider_id and rec3.provider_id.id or False,
                                'origin_id': rec3.origin_id and rec3.origin_id.id or False,
                                'destination_id': rec3.destination_id and rec3.destination_id.id or False,
                                'departure_date': rec3.departure_date,
                                'arrival_date': rec3.arrival_date,
                            }
                            new_journey_obj = self.env['tt.journey.airline'].sudo().create(journey_val)
                            for rec4 in rec3.segment_ids:
                                segment_val = {
                                    'booking_id': new_book_obj.id,
                                    'journey_id': new_journey_obj.id,
                                    'segment_code': rec4.segment_code,
                                    'fare_code': rec4.fare_code,
                                    'sequence': rec4.sequence,
                                    'name': rec4.name,
                                    'carrier_id': rec4.carrier_id and rec4.carrier_id.id or False,
                                    'carrier_code': rec4.carrier_code,
                                    'carrier_number': rec4.carrier_number,
                                    'provider_id': rec4.provider_id and rec4.provider_id.id or False,
                                    'origin_id': rec4.origin_id and rec4.origin_id.id or False,
                                    'destination_id': rec4.destination_id and rec4.destination_id.id or False,
                                    'departure_date': rec4.departure_date,
                                    'arrival_date': rec4.arrival_date,
                                    'cabin_class': rec4.cabin_class,
                                    'class_of_service': rec4.class_of_service,
                                }
                                new_segment_obj = self.env['tt.segment.airline'].sudo().create(segment_val)
                                for rec5 in rec4.leg_ids:
                                    leg_val = {
                                        'segment_id': new_segment_obj.id,
                                        'leg_code': rec5.leg_code,
                                        'provider_id': rec5.provider_id and rec5.provider_id.id or False,
                                        'origin_id': rec5.origin_id and rec5.origin_id.id or False,
                                        'destination_id': rec5.destination_id and rec5.destination_id.id or False,
                                        'departure_date': rec5.departure_date,
                                        'arrival_date': rec5.arrival_date,
                                    }
                                    new_leg_obj = self.env['tt.leg.airline'].sudo().create(leg_val)
                                for rec6 in rec4.seat_ids:
                                    if rec6.passenger_id.id == rec.id:
                                        rec6.segment_id = new_segment_obj.id
                                for rec7 in rec4.segment_addons_ids:
                                    addons_val = {
                                        'segment_id': new_segment_obj.id,
                                        'detail_code': rec7.detail_code,
                                        'detail_type': rec7.detail_type,
                                        'detail_name': rec7.detail_name,
                                        'amount': rec7.amount,
                                        'unit': rec7.unit,
                                    }
                                    new_addons_obj = self.env['tt.segment.addons.airline'].sudo().create(addons_val)
                        for rec3 in rec2.provider_airline_booking_id.ticket_ids:
                            if rec3.passenger_id.id == rec.id:
                                if rec3.pax_type == 'ADT':
                                    tot_adult += 1
                                elif rec3.pax_type == 'CHD':
                                    tot_child += 1
                                elif rec3.pax_type == 'INF':
                                    tot_infant += 1
                                rec3.provider_id = new_prov_obj.id
                        rec2.provider_airline_booking_id = new_prov_obj.id
            new_book_obj.sudo().write({
                'adult': int(tot_adult),
                'child': int(tot_child),
                'infant': int(tot_infant)
            })
            book_obj.sudo().write({
                'adult': int(book_obj.adult) - int(tot_adult),
                'child': int(book_obj.child) - int(tot_child),
                'infant': int(book_obj.infant) - int(tot_infant)
            })

        book_obj.calculate_pnr_provider_carrier()
        new_book_obj.calculate_pnr_provider_carrier()
        book_obj.calculate_service_charge()
        new_book_obj.calculate_service_charge()
