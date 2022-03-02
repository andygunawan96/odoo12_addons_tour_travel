from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtSplitReservationWizard(models.TransientModel):
    _name = "tt.split.reservation.groupbooking.wizard"
    _description = 'Group Booking Split Reservation Wizard'

    is_split_provider = fields.Boolean('Split Provider (PNR)', default=False)
    is_split_passenger = fields.Boolean('Split Passenger', default=False)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    referenced_document = fields.Char('Ref. Document', required=True, readonly=True)
    new_pnr = fields.Char('New PNR(s) separated by comma')
    new_pnr_text = fields.Text('Information', readonly=True)

    def get_split_provider_domain(self):
        return [('booking_id', '=', self.res_id)]

    def get_split_passenger_domain(self):
        return [('booking_id', '=', self.res_id)]

    def get_split_journey_domain(self):
        return [('booking_id', '=', self.res_id)]

    provider_ids = fields.Many2many('tt.provider.groupbooking', 'groupbooking_provider_split_rel', 'split_wizard_id', 'provider_id', 'PNR',
                           domain=get_split_provider_domain)
    passenger_ids = fields.Many2many('tt.reservation.passenger.groupbooking', 'groupbooking_passengers_split_rel', 'split_wizard_id', 'passenger_id', 'Passenger',
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

    @api.onchange('res_id')
    def _onchange_domain_journey(self):
        return {'domain': {
            'journey_ids': self.get_split_journey_domain()
        }}

    @api.onchange("is_split_provider")
    def _compute_split_by_provider(self):
        if self.is_split_provider:
            self.is_split_journey = False
        else:
            self.provider_ids = [(5,0,0)]

    @api.onchange("is_split_passenger")
    def _compute_split_by_passenger(self):
        if self.is_split_passenger:
            self.is_split_journey = False
        else:
            self.passenger_ids = [(5,0,0)]

    @api.onchange('new_pnr')
    def _onchange_new_pnr(self):
        if self.passenger_ids:
            new_pnr_list = self.new_pnr and self.new_pnr.strip().split(',') or []
            def_txt = ''
            book_obj = self.env['tt.reservation.groupbooking'].sudo().browse(int(self.res_id))
            for idx, rec in enumerate(book_obj.provider_booking_ids):
                if idx < len(new_pnr_list):
                    def_txt += str(rec.pnr) + ' will be converted to ' + str(new_pnr_list[idx]) + ' in the new reservation. \n'
            self.new_pnr_text = def_txt

    def submit_split_reservation(self):
        book_obj = self.env['tt.reservation.groupbooking'].sudo().browse(int(self.res_id))
        provider_list = []
        pax_list = []
        journey_list = []
        journey_provider_list = []
        is_provider_full = True
        is_pax_full = True
        provider_len = len(book_obj.provider_booking_ids.ids)
        passenger_len = len(book_obj.passenger_ids.ids)
        journey_len = 0

        for rec in self.provider_ids:
            provider_list.append(rec.id)
        for rec in self.passenger_ids:
            pax_list.append(rec.id)

        if len(journey_provider_list) > 1:
            raise UserError(_('You can only split Journey(s) from one provider at a time.'))


        if len(provider_list) != provider_len:
            is_provider_full = False
        if len(pax_list) != passenger_len:
            is_pax_full = False

        new_pnr_list = self.new_pnr and self.new_pnr.strip().split(',') or []
        new_pnr_dict = {}
        if len(provider_list) <= 0:
            for idx, rec in enumerate(book_obj.provider_booking_ids):
                if idx < len(new_pnr_list):
                    new_pnr_dict.update({
                        str(rec.pnr): str(new_pnr_list[idx])
                    })
        else:
            for idx, rec in enumerate(self.provider_ids):
                if idx < len(new_pnr_list):
                    new_pnr_dict.update({
                        str(rec.pnr): str(new_pnr_list[idx])
                    })

        if not self.is_split_provider and not self.is_split_passenger:
            raise UserError(_('Please select what split you want to perform (Provider/Passenger).'))
        if is_provider_full and is_pax_full:
            raise UserError(_('You cannot split all Provider(s) and Passenger(s) in this reservation. Please leave at least 1 Provider or 1 Passenger!'))
        if is_provider_full and len(pax_list) <= 0:
            raise UserError(_('You cannot split all Provider(s) in this reservation without any Passenger(s).'))
        if len(provider_list) <= 0 and is_pax_full:
            raise UserError(_('You cannot split all Passenger(s) in this reservation without any Provider(s).'))
        if self.is_split_provider and len(provider_list) <= 0:
            raise UserError(_('You need to input at least 1 Provider to perform split provider in this reservation.'))
        if self.is_split_passenger and len(pax_list) <= 0:
            raise UserError(_('You need to input at least 1 Passenger to perform split passenger in this reservation.'))
        if self.is_split_provider and self.is_split_passenger and (len(provider_list) <= 0 or len(pax_list) <= 0):
            raise UserError(_('You need to input at least 1 Provider and 1 Passenger to perform split provider-passenger in this reservation.'))
        if self.is_split_provider and provider_len <= 1:
            raise UserError(_('You cannot split Provider as there is only 1 Provider in this reservation.'))
        if self.is_split_passenger and passenger_len <= 1:
            raise UserError(_('You cannot split Passenger as there is only 1 Passenger in this reservation.'))
        if self.is_split_passenger and not self.is_split_provider and len(new_pnr_list) < provider_len:
            raise UserError(_('You need to input New PNR for the splitted Passenger(s) in the new reservation, need {} more.'.format(provider_len - len(new_pnr_list))))
        if self.is_split_passenger and self.is_split_provider and len(new_pnr_list) < len(provider_list):
            raise UserError(_('You need to input New PNR for the splitted Passenger(s) in the new reservation, need {} more.'.format(len(provider_list) - len(new_pnr_list))))

        book_obj.write({
            'split_uid': self.env.user.id,
            'split_date': fields.Datetime.now(),
        })

        new_vals = {
            'split_from_resv_id': book_obj.id,
            'split_uid': self.env.user.id,
            'split_date': fields.Datetime.now(),
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
            'issued_date': datetime.now(),
            'origin_id': book_obj.origin_id and book_obj.origin_id.id or False,
            'destination_id': book_obj.destination_id and book_obj.destination_id.id or False,
            'departure_date': str(book_obj.departure_date),
            'arrival_date': book_obj.arrival_date,
            'booker_id': book_obj.booker_id and book_obj.booker_id.id or False,
            'contact_id': book_obj.contact_id and book_obj.contact_id.id or False,
            'contact_title': book_obj.contact_title,
            'contact_email': book_obj.contact_email,
            'contact_phone': book_obj.contact_phone,
            'is_invoice_created': book_obj.is_invoice_created,
            'state': book_obj.state,

            'journey_type': book_obj.journey_type,
            'cabin_class': book_obj.cabin_class,
            'carrier_code_id': book_obj.carrier_code_id.id,
            'groupbooking_provider_type': book_obj.groupbooking_provider_type,
            'state_groupbooking': book_obj.state_groupbooking,
            'return_date': str(book_obj.return_date) if book_obj.return_date else False
        }

        new_book_obj = self.env['tt.reservation.groupbooking'].create(new_vals)
        if self.is_split_provider and self.is_split_passenger:
            aff_pnr_list = []
            aff_prov_list = []
            new_aff_prov_list = []

            tot_adult = 0
            tot_child = 0
            tot_infant = 0
            moved_pax_list = []
            old_provider_list = []
            provider_dict = {}
            temp_pax_list = []
            temp_pax_dict = {}

            unlink_provider_booking_ids = []
            exists_passenger_ids = []
            exists_passenger_type = {'ADT': 0, 'CHD': 0, 'INF': 0}
            for rec in book_obj.provider_booking_ids:
                if rec.id in self.provider_ids.ids:
                    if rec.pnr:
                        if rec.pnr not in aff_pnr_list:
                            aff_pnr_list.append(rec.pnr)
                    else:
                        if rec.sequence not in aff_pnr_list:
                            aff_pnr_list.append(rec.sequence)
                    aff_prov_list.append(rec)

                    old_cost_list = []
                    old_cost_dict = {}
                    for rec2 in rec.cost_service_charge_ids:
                        rec2.is_ledger_created = False
                        for prov_pax in rec2.passenger_groupbooking_ids:
                            if prov_pax.id in self.passenger_ids.ids:
                                if prov_pax.id not in temp_pax_list:
                                    new_pax_obj = self.env['tt.reservation.passenger.groupbooking'].sudo().create({
                                        'booking_id': new_book_obj.id,
                                        'first_name': prov_pax.first_name,
                                        'last_name': prov_pax.last_name,
                                        'name': prov_pax.name,
                                        'title': prov_pax.title,
                                        'gender': prov_pax.gender,
                                        'birth_date': prov_pax.birth_date,
                                        'sequence': prov_pax.sequence,
                                        'nationality_id': prov_pax.nationality_id and prov_pax.nationality_id.id or False,
                                        'customer_id': prov_pax.customer_id and prov_pax.customer_id.id or False,
                                        'identity_type': prov_pax.identity_type,
                                        'identity_number': prov_pax.identity_number,
                                        'identity_expdate': prov_pax.identity_expdate,
                                        'identity_country_of_issued_id': prov_pax.identity_country_of_issued_id and prov_pax.identity_country_of_issued_id.id or False,
                                    })
                                    temp_pax_list.append(prov_pax.id)
                                    temp_pax_dict.update({
                                        str(prov_pax.id): new_pax_obj.id
                                    })
                                else:
                                    new_pax_obj = self.env['tt.reservation.passenger.groupbooking'].sudo().browse(
                                        int(temp_pax_dict[str(prov_pax.id)]))

                                if rec2.id not in old_cost_list:
                                    cost_val = {
                                        'charge_code': rec2.charge_code,
                                        'charge_type': rec2.charge_type,
                                        'pax_type': rec2.pax_type,
                                        'currency_id': rec2.currency_id and rec2.currency_id.id or False,
                                        'amount': rec2.amount,
                                        'foreign_currency_id': rec2.foreign_currency_id and rec2.foreign_currency_id.id or False,
                                        'foreign_amount': rec2.foreign_amount,
                                        'sequence': rec2.sequence,
                                        'pax_count': 1,
                                        'total': rec2.amount * 1,
                                        'commission_agent_id': rec2.commission_agent_id and rec2.commission_agent_id.id or False,
                                        'passenger_groupbooking_ids': [(4, new_pax_obj.id)]
                                    }
                                    new_cost_obj = self.env['tt.service.charge'].sudo().create(cost_val)
                                    old_cost_list.append(rec2.id)
                                    old_cost_dict.update({
                                        str(rec2.id): new_cost_obj.id
                                    })
                                else:
                                    new_cost_obj = self.env['tt.service.charge'].sudo().browse(
                                        int(old_cost_dict[str(rec2.id)]))
                                    new_cost_obj.sudo().write({
                                        'passenger_groupbooking_ids': [(4, new_pax_obj.id)],
                                        'pax_count': new_cost_obj.pax_count + 1,
                                        'total': new_cost_obj.amount * (new_cost_obj.pax_count + 1),
                                    })

                                cost_write_vals = {
                                    'passenger_groupbooking_ids': [(3, prov_pax.id)],
                                    'pax_count': rec2.pax_count - 1,
                                    'total': rec2.amount * (rec2.pax_count - 1),
                                }

                                if (rec2.pax_count - 1) <= 0:
                                    cost_write_vals.update({
                                        'provider_groupbooking_booking_id': False
                                    })

                                rec2.sudo().write(cost_write_vals)

                    if rec.id not in old_provider_list:
                        old_provider_list.append(rec.id)
                        prov_val = {
                            'sequence': rec.sequence,
                            'booking_id': new_book_obj.id,
                            'state': rec.state,
                            'pnr': new_pnr_dict[rec.pnr],
                            'pnr2': new_pnr_dict[rec.pnr],
                            'provider_id': rec.provider_id and rec.provider_id.id or False,
                            'hold_date': rec.hold_date,
                            'expired_date': rec.expired_date,
                            'booked_uid': rec.booked_uid and rec.booked_uid.id or False,
                            'booked_date': rec.booked_date,
                            'issued_uid': rec.issued_uid and rec.issued_uid.id or False,
                            'issued_date': datetime.now(),
                            'refund_uid': rec.refund_uid and rec.refund_uid.id or False,
                            'refund_date': rec.refund_date,
                            'origin_id': rec.origin_id and rec.origin_id.id or False,
                            'destination_id': rec.destination_id and rec.destination_id.id or False,
                            'departure_date': rec.departure_date,
                            'arrival_date': rec.arrival_date,
                            'sid_issued': rec.sid_issued,
                            'promotion_code': rec.promotion_code,
                            'currency_id': rec.currency_id and rec.currency_id.id or False,
                        }
                        new_prov_obj = self.env['tt.provider.groupbooking'].sudo().create(prov_val)
                        new_aff_prov_list.append(new_prov_obj)
                        provider_dict.update({
                            str(rec.id): new_prov_obj.id
                        })
                        for rec3 in rec.journey_ids:
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
                            new_journey_obj = self.env['tt.journey.groupbooking'].sudo().create(journey_val)
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
                                new_segment_obj = self.env['tt.segment.groupbooking'].sudo().create(segment_val)
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
                                    new_leg_obj = self.env['tt.leg.groupbooking'].sudo().create(leg_val)
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
                                    new_addons_obj = self.env['tt.segment.addons.groupbooking'].sudo().create(addons_val)

                        for val in old_cost_dict.values():
                            dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                            dict_cost_obj.sudo().write({
                                'provider_groupbooking_booking_id': new_prov_obj.id,
                                'description': new_prov_obj.pnr
                            })
                    else:
                        new_prov_obj = self.env['tt.provider.groupbooking'].sudo().browse(int(provider_dict[str(rec.id)]))
                        new_aff_prov_list.append(new_prov_obj)
                        for val in old_cost_dict.values():
                            dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                            dict_cost_obj.sudo().write({
                                'provider_groupbooking_booking_id': new_prov_obj.id,
                                'description': new_prov_obj.pnr
                            })

                    for rec3 in rec.ticket_ids:
                        if rec3.passenger_id.id in self.passenger_ids.ids:
                            if rec3.passenger_id.id not in moved_pax_list:
                                moved_pax_list.append(rec3.passenger_id.id)
                                if rec3.pax_type == 'ADT':
                                    tot_adult += 1
                                elif rec3.pax_type == 'CHD':
                                    tot_child += 1
                                elif rec3.pax_type == 'INF':
                                    tot_infant += 1
                            rec3.provider_id = new_prov_obj.id
                    if len(rec.ticket_ids) == 0:
                        unlink_provider_booking_ids.append(rec.id)

                for tkt in rec.ticket_ids:
                    if tkt.passenger_id.id not in exists_passenger_ids:
                        exists_passenger_ids.append(tkt.passenger_id.id)
                        exists_passenger_type[tkt.pax_type] += 1
            for x in unlink_provider_booking_ids:
                book_obj.provider_booking_ids = [(3, x)]  # use 2 / 3

            if len(book_obj.passenger_ids) != len(exists_passenger_ids):
                for x in book_obj.passenger_ids:
                    if x.id not in exists_passenger_ids:
                        x.booking_id = False
                        # x.unlink() # Pertimbangkan untuk remove object
                book_obj.sudo().write({
                    'adult': exists_passenger_type['ADT'],
                    'child': exists_passenger_type['CHD'],
                    'infant': exists_passenger_type['INF'],
                })

            new_book_obj.sudo().write({
                'adult': int(tot_adult),
                'child': int(tot_child),
                'infant': int(tot_infant)
            })

            for led in book_obj.ledger_ids.filtered(lambda x: x.pnr in aff_pnr_list and not x.is_reversed):
                led.reverse_ledger()
            for aff_prov in aff_prov_list:
                aff_prov.action_create_ledger(book_obj.issued_uid.id)
            for aff_prov in new_aff_prov_list:
                aff_prov.action_create_ledger(new_book_obj.issued_uid.id)

        elif self.is_split_provider:
            aff_pnr_list = []
            aff_prov_list = []
            new_aff_prov_list = []
            new_book_obj.sudo().write({
                'adult': book_obj.adult,
                'child': book_obj.child,
                'infant': book_obj.infant
            })
            old_pax_id_list = []
            old_pax_dict = {}
            for rec in self.provider_ids:
                for rec2 in book_obj.segment_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id
                for rec2 in book_obj.provider_booking_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id
                        if rec2.pnr:
                            if rec2.pnr not in aff_pnr_list:
                                aff_pnr_list.append(rec2.pnr)
                        else:
                            if rec2.sequence not in aff_pnr_list:
                                aff_pnr_list.append(rec2.sequence)
                        new_aff_prov_list.append(rec2)
                for rec2 in rec.cost_service_charge_ids:
                    new_pax_id_list = []
                    for rec3 in rec2.passenger_groupbooking_ids:
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
                            new_pax_obj = self.env['tt.reservation.passenger.groupbooking'].sudo().create(pax_val)
                            old_pax_dict.update({
                                str(rec3.id): new_pax_obj.id
                            })
                            new_pax_id_list.append(new_pax_obj.id)
                            for rec4 in rec.ticket_ids:
                                if rec4.passenger_id.id == rec3.id:
                                    rec4.sudo().write({
                                        'passenger_id': new_pax_obj.id
                                    })
                        else:
                            new_pax_id_list.append(int(old_pax_dict[str(rec3.id)]))
                    rec2.sudo().write({
                        'passenger_groupbooking_ids': [(6,0,new_pax_id_list)]
                    })

            for rec in new_book_obj.provider_booking_ids:
                for rec2 in rec.cost_service_charge_ids:
                    rec2.is_ledger_created = False

            for led in book_obj.ledger_ids.filtered(lambda x: x.pnr in aff_pnr_list and not x.is_reversed):
                led.reverse_ledger()
            for aff_prov in aff_prov_list:
                aff_prov.action_create_ledger(book_obj.issued_uid.id)
            for aff_prov in new_aff_prov_list:
                aff_prov.action_create_ledger(new_book_obj.issued_uid.id)

        elif self.is_split_passenger:
            aff_pnr_list = []
            aff_prov_list = []
            new_aff_prov_list = []

            tot_adult = 0
            tot_child = 0
            tot_infant = 0
            moved_pax_list = []
            old_provider_list = []
            provider_dict = {}
            for rec in book_obj.provider_booking_ids:
                if rec.pnr:
                    if rec.pnr not in aff_pnr_list:
                        aff_pnr_list.append(rec.pnr)
                else:
                    if rec.sequence not in aff_pnr_list:
                        aff_pnr_list.append(rec.sequence)
                aff_prov_list.append(rec)

                old_cost_list = []
                old_cost_dict = {}
                for rec2 in rec.cost_service_charge_ids:
                    rec2.is_ledger_created = False
                    for prov_pax in rec2.passenger_groupbooking_ids:
                        if prov_pax.id in self.passenger_ids.ids:
                            prov_pax.booking_id = new_book_obj.id
                            if rec2.id not in old_cost_list:
                                cost_val = {
                                    'charge_code': rec2.charge_code,
                                    'charge_type': rec2.charge_type,
                                    'pax_type': rec2.pax_type,
                                    'currency_id': rec2.currency_id and rec2.currency_id.id or False,
                                    'amount': rec2.amount,
                                    'foreign_currency_id': rec2.foreign_currency_id and rec2.foreign_currency_id.id or False,
                                    'foreign_amount': rec2.foreign_amount,
                                    'sequence': rec2.sequence,
                                    'pax_count': 1,
                                    'total': rec2.amount * 1,
                                    'commission_agent_id': rec2.commission_agent_id and rec2.commission_agent_id.id or False,
                                    'passenger_groupbooking_ids': [(4, prov_pax.id)]
                                }
                                new_cost_obj = self.env['tt.service.charge'].sudo().create(cost_val)
                                old_cost_list.append(rec2.id)
                                old_cost_dict.update({
                                    str(rec2.id): new_cost_obj.id
                                })
                            else:
                                new_cost_obj = self.env['tt.service.charge'].sudo().browse(int(old_cost_dict[str(rec2.id)]))
                                new_cost_obj.sudo().write({
                                    'passenger_groupbooking_ids': [(4, prov_pax.id)],
                                    'pax_count': new_cost_obj.pax_count + 1,
                                    'total': new_cost_obj.amount * (new_cost_obj.pax_count + 1),
                                })

                            cost_write_vals = {
                                'passenger_groupbooking_ids': [(3, prov_pax.id)],
                                'pax_count': rec2.pax_count - 1,
                                'total': rec2.amount * (rec2.pax_count - 1),
                            }

                            if (rec2.pax_count - 1) <= 0:
                                cost_write_vals.update({
                                    'provider_groupbooking_booking_id': False
                                })

                            rec2.sudo().write(cost_write_vals)

                if rec.id not in old_provider_list:
                    old_provider_list.append(rec.id)
                    prov_val = {
                        'sequence': rec.sequence,
                        'booking_id': new_book_obj.id,
                        'state': rec.state,
                        'pnr': new_pnr_dict[rec.pnr],
                        'pnr2': new_pnr_dict[rec.pnr],
                        'provider_id': rec.provider_id and rec.provider_id.id or False,
                        'hold_date': rec.hold_date,
                        'expired_date': rec.expired_date,
                        'confirm_uid': rec.confirm_uid and rec.confirm_uid.id or False,
                        'confirm_date': datetime.now(),
                        'sent_uid': rec.sent_uid and rec.sent_uid.id or False,
                        'sent_date': datetime.now(),
                        'issued_uid': rec.issued_uid and rec.issued_uid.id or False,
                        'issued_date': datetime.now(),
                        'refund_uid': rec.refund_uid and rec.refund_uid.id or False,
                        'refund_date': rec.refund_date,
                        'sid_issued': rec.sid_issued,
                        'promotion_code': rec.promotion_code,
                        'currency_id': rec.currency_id and rec.currency_id.id or False,
                    }
                    new_prov_obj = self.env['tt.provider.groupbooking'].sudo().create(prov_val)
                    new_aff_prov_list.append(new_prov_obj)
                    provider_dict.update({
                        str(rec.id): new_prov_obj.id
                    })

                    for val in old_cost_dict.values():
                        dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                        dict_cost_obj.sudo().write({
                            'provider_groupbooking_booking_id': new_prov_obj.id,
                            'description': new_prov_obj.pnr
                        })
                else:
                    new_prov_obj = self.env['tt.provider.groupbooking'].sudo().browse(int(provider_dict[str(rec.id)]))
                    new_aff_prov_list.append(new_prov_obj)
                    for val in old_cost_dict.values():
                        dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                        dict_cost_obj.sudo().write({
                            'provider_groupbooking_booking_id': new_prov_obj.id,
                            'description': new_prov_obj.pnr
                        })

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

            for led in book_obj.ledger_ids.filtered(lambda x: x.pnr in aff_pnr_list and not x.is_reversed):
                led.reverse_ledger()
            for aff_prov in aff_prov_list:
                aff_prov.action_create_ledger(book_obj.issued_uid.id)
            for aff_prov in new_aff_prov_list:
                aff_prov.action_create_ledger(new_book_obj.issued_uid.id)

        book_obj.calculate_service_charge()
        new_book_obj.calculate_service_charge()

        provider_state_context = {
            'co_uid': self.env.user.id,
            'co_agent_id': self.env.user.agent_id.id,
        }

        book_obj.check_provider_state(context=provider_state_context)
        new_book_obj.check_provider_state(context=provider_state_context)