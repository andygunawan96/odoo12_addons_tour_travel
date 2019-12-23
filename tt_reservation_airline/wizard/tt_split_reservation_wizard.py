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
            for rec in self.passenger_ids:
                for rec2 in book_obj.passenger_ids:
                    if rec2.id == rec.id:
                        rec2.booking_id = new_book_obj.id
                old_provider_list = []
                for rec2 in rec.cost_service_charge_ids:
                    if rec2.provider_airline_booking_id.id not in old_provider_list:
                        old_provider_list.append(rec2.provider_airline_booking_id.id)
                        prov_val = {

                        }
                        new_prov_obj = self.env['tt.provider.airline'].sudo().create(prov_val)
                        for rec3 in rec2.provider_airline_booking_id.ticket_ids:
                            if rec3.passenger_id.id == rec.id:
                                rec3.provider_id = new_prov_obj.id
                        rec2.provider_airline_booking_id = new_prov_obj.id

        book_obj.calculate_pnr_provider_carrier()
        new_book_obj.calculate_pnr_provider_carrier()
        book_obj.calculate_service_charge()
        new_book_obj.calculate_service_charge()
