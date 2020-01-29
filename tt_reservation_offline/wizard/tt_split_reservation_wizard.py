from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TtSplitReservationWizard(models.TransientModel):
    _name = "tt.split.reservation.offline.wizard"
    _description = 'Offline Split Reservation Wizard'

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    referenced_document = fields.Char('Ref. Document', required=True, readonly=True)
    new_pnr = fields.Char('New PNR(s) separated by comma')
    new_pnr_text = fields.Text('Information', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    vendor_amount = fields.Monetary('New Vendor Amount', default=0)

    def get_split_provider_domain(self):
        return [('booking_id', '=', self.res_id)]

    def get_split_passenger_domain(self):
        return [('booking_id', '=', self.res_id)]

    provider_ids = fields.Many2many('tt.provider.offline', 'offline_provider_split_rel', 'split_wizard_id',
                                    'provider_id', 'PNR', domain=get_split_provider_domain)
    passenger_ids = fields.Many2many('tt.reservation.offline.passenger', 'offline_passenger_split_rel',
                                     'split_wizard_id', 'passenger_id', 'Passenger',
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

    def input_new_line(self, lines, new_pnr, provider_type, new_book_obj):
        line_env = self.env['tt.reservation.offline.lines']
        for line in lines:
            line_obj = line_env.search([('id', '=', line.id)])
            if provider_type in ['airline', 'train']:
                line_vals = {
                    'booking_id': new_book_obj.id,
                    'pnr': new_pnr,
                    'origin_id': line_obj.origin_id.id,
                    'destination_id': line_obj.destination_id.id,
                    "provider_id": line_obj.provider_id.id,
                    "departure_date": line_obj.departure_date,
                    "departure_hour": line_obj.departure_hour,
                    "departure_minute": line_obj.departure_minute,
                    "return_date": line_obj.return_date,
                    "return_hour": line_obj.return_hour,
                    "return_minute": line_obj.return_minute,
                    "carrier_id": line_obj.carrier_id.id,
                    "carrier_code": line_obj.carrier_code,
                    "carrier_number": line_obj.carrier_number,
                    "subclass": line_obj.subclass,
                    "class_of_service": line_obj.class_of_service,
                }
            elif provider_type == 'activity':
                line_vals = {
                    'booking_id': new_book_obj.id,
                    'pnr': new_pnr,
                    "provider_id": line_obj.provider_id.id,
                    "activity_name": line_obj.activity_name,
                    "activity_package": line_obj.activity_package,
                    "qty": int(line_obj.qty),
                    "description": line_obj.description,
                    "visit_date": line_obj.visit_time,
                }
            elif provider_type == 'hotel':
                line_vals = {
                    'booking_id': new_book_obj.id,
                    'pnr': new_pnr,
                    "provider_id": line_obj.provider_id.id,
                    "hotel_name": line_obj.hotel_name,
                    "room": line_obj.room,
                    "meal_type": line_obj.meal_type,
                    "qty": int(line_obj.qty),
                    "description": line_obj.description,
                    "check_in": line_obj.check_in,
                    "check_out": line_obj.check_out,
                }
            elif provider_type == 'cruise':
                line_vals = {
                    'booking_id': new_book_obj.id,
                    'pnr': new_pnr,
                    "provider_id": line_obj.provider_id.id,
                    "cruise_package": line_obj.cruise_package,
                    "carrier_id": line_obj.carrier_id.id,
                    "departure_location": line_obj.departure_location,
                    "arrival_location": line_obj.arrival_location,
                    "room": line_obj.room,
                    "check_in": line_obj.check_in,
                    "check_out": line_obj.check_out,
                    "description": line_obj.description
                }
            else:
                line_vals = {
                    'booking_id': new_book_obj.id,
                    'pnr': new_pnr,
                    "provider_id": line_obj.provider_id.id,
                    "description": line_obj.description
                }
            line_env.sudo().create(line_vals)

    def submit_split_reservation(self):
        book_obj = self.env['tt.reservation.offline'].sudo().browse(int(self.res_id))
        provider_list = []
        pax_list = []
        is_provider_full = True
        is_pax_full = True
        provider_len = 0

        for rec in self.provider_ids:
            provider_list.append(rec.id)
        for rec in self.passenger_ids:
            pax_list.append(rec.id)
        for rec in book_obj.provider_booking_ids:
            if rec.id not in provider_list:
                is_provider_full = False
            provider_len += 1
        for rec in book_obj.passenger_ids:
            if rec.id not in pax_list:
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

        # Error checking
        if is_provider_full and is_pax_full:
            raise UserError(_('You cannot split all Provider(s) and Passenger(s) in this reservation. Please leave at least 1 Provider or 1 Passenger!'))
        if is_provider_full and len(pax_list) <= 0:
            raise UserError(_('You cannot split all Provider(s) in this reservation without any Passenger(s).'))
        if len(provider_list) <= 0 and is_pax_full:
            raise UserError(_('You cannot split all Passenger(s) in this reservation without any Provider(s).'))
        if len(provider_list) <= 0 and len(pax_list) <= 0:
            raise UserError(_('You need to input at least 1 Provider or 1 Passenger to split this reservation.'))
        if len(pax_list) > 0 and len(provider_list) <= 0 and len(new_pnr_list) < provider_len:
            raise UserError(_('You need to input New PNR for the split Passenger(s) in the new reservation, need {} more.'.format(provider_len - len(new_pnr_list))))
        if len(pax_list) > 0 and len(provider_list) > 0 and len(new_pnr_list) < len(provider_list):
            raise UserError(_('You need to input New PNR for the split Passenger(s) in the new reservation, need {} more.'.format(len(provider_list) - len(new_pnr_list))))

        # Prepare new booking vals
        new_vals = {
            'split_from_resv_id': book_obj.id,
            'pnr': book_obj.pnr,
            'agent_id': book_obj.agent_id and book_obj.agent_id.id or False,
            'customer_parent_id': book_obj.customer_parent_id and book_obj.customer_parent_id.id or False,
            'offline_provider_type': book_obj.offline_provider_type,
            'hold_date': book_obj.hold_date,
            'expired_date': book_obj.expired_date,
            'user_id': book_obj.user_id and book_obj.user_id.id or False,
            'create_date': book_obj.create_date,
            'incentive_amount': book_obj.incentive_amount,
            'description': book_obj.description,
            'sector_type': book_obj.sector_type,
            'total_commission_amount': book_obj.total_commission_amount,
            'vendor_amount': self.vendor_amount,
            'resv_code': book_obj.resv_code,
            'social_media_type': book_obj.social_media_type.id,
            'booked_uid': book_obj.booked_uid and book_obj.booked_uid.id or False,
            'booked_date': book_obj.booked_date,
            'confirm_uid': book_obj.confirm_uid and book_obj.confirm_uid.id or False,
            'confirm_date': book_obj.confirm_date,
            'sent_uid': book_obj.sent_uid and book_obj.sent_uid.id or False,
            'sent_date': book_obj.sent_date,
            'issued_uid': book_obj.issued_uid and book_obj.issued_uid.id or False,
            'issued_date': book_obj.issued_date,
            'done_uid': book_obj.done_uid and book_obj.done_uid.id or False,
            'done_date': book_obj.done_date,
            'cancel_uid': book_obj.cancel_uid and book_obj.cancel_uid.id or False,
            'cancel_date': book_obj.cancel_date,
            'refund_uid': book_obj.refund_uid and book_obj.refund_uid.id or False,
            'refund_date': book_obj.refund_date,
            'booker_id': book_obj.booker_id and book_obj.booker_id.id or False,
            'contact_id': book_obj.contact_id and book_obj.contact_id.id or False,
            'contact_title': book_obj.contact_title,
            'contact_email': book_obj.contact_email,
            'contact_phone': book_obj.contact_phone,
            'state': book_obj.state,
            'state_offline': book_obj.state_offline
        }
        new_book_obj = self.env['tt.reservation.offline'].sudo().create(new_vals)
        book_obj.vendor_amount -= self.vendor_amount

        # jika provider only
        if len(pax_list) <= 0:
            # new_book_obj.sudo().write({
            #     'adult': book_obj.adult,
            #     'child': book_obj.child,
            #     'infant': book_obj.infant
            # })
            old_pax_id_list = []  # list id old pax
            old_pax_dict = {}

            for rec in self.provider_ids:
                for rec2 in book_obj.provider_booking_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id
                for rec2 in rec.cost_service_charge_ids:
                    new_pax_id_list = []
                    for rec3 in rec2.passenger_offline_ids:
                        if rec3.id not in old_pax_id_list:
                            old_pax_id_list.append(rec3.id)
                            pax_val = {
                                'booking_id': new_book_obj.id,
                                'name': rec3.name,
                                'last_name': rec3.last_name,
                                'title': rec3.title,
                                'first_name': rec3.first_name,
                                'gender': rec3.gender,
                                'birth_date': rec3.birth_date,
                                'pax_type': rec3.pax_type,
                                'ticket_number': rec3.ticket_number,
                                'seat': rec3.seat,
                                'passenger_id': rec3.passenger_id.id
                            }
                            new_pax_obj = self.env['tt.reservation.offline.passenger'].sudo().create(pax_val)
                            old_pax_dict.update({
                                str(rec3.id): new_pax_obj.id
                            })
                            new_pax_id_list.append(new_pax_obj.id)
                        else:
                            new_pax_id_list.append(int(old_pax_dict[str(rec3.id)]))
                    rec2.sudo().write({
                        'passenger_offline_ids': [(6, 0, new_pax_id_list)]
                    })

            for rec in self.provider_ids:
                for rec2 in book_obj.line_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id

            # set is ledger cost service charge = false di provider
            for rec in book_obj.provider_booking_ids:
                for rec2 in rec.cost_service_charge_ids:
                    rec2.is_ledger_created = False

            for rec in new_book_obj.provider_booking_ids:
                for rec2 in rec.cost_service_charge_ids:
                    rec2.is_ledger_created = False

            if book_obj.ledger_ids:
                for led in book_obj.ledger_ids:
                    if not led.is_reversed:
                        led.reverse_ledger()
                for prov in book_obj.provider_booking_ids:
                    prov.action_create_ledger(book_obj.issued_uid.id)
                new_book_obj.get_provider_name_from_provider()
                new_book_obj.get_pnr_list_from_provider()
                for prov in new_book_obj.provider_booking_ids:
                    prov.action_create_ledger(new_book_obj.issued_uid.id)

        # jika pax only
        elif len(provider_list) <= 0:
            moved_line_list = []
            old_provider_list = []
            provider_dict = {}

            # Pindahkan pricing ke provider yg baru
            for rec in book_obj.provider_booking_ids:
                old_cost_list = []
                old_cost_dict = {}
                # Looping semua cost service charge di provider
                for rec2 in rec.cost_service_charge_ids:
                    # Set semua is ledger created = False
                    rec2.is_ledger_created = False
                    # Looping semua pax yg ada di cost service charge
                    for prov_pax in rec2.passenger_offline_ids:
                        # Jika pax ada di dalam self.passenger_ids
                        if prov_pax.id in self.passenger_ids.ids:
                            prov_pax.booking_id = new_book_obj.id
                            # jika id cost service charge tidak ada di old cost list
                            if rec2.id not in old_cost_list:
                                # Buat service charge baru
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
                                    'passenger_offline_ids': [(4, prov_pax.id)]
                                }
                                new_cost_obj = self.env['tt.service.charge'].sudo().create(cost_val)
                                old_cost_list.append(rec2.id)
                                old_cost_dict.update({
                                    str(rec2.id): new_cost_obj.id
                                })
                            # Jika sudah ada, edit
                            else:
                                new_cost_obj = self.env['tt.service.charge'].sudo().browse(
                                    int(old_cost_dict[str(rec2.id)]))
                                new_cost_obj.sudo().write({
                                    'passenger_offline_ids': [(4, prov_pax.id)],
                                    'pax_count': new_cost_obj.pax_count + 1,
                                    'total': new_cost_obj.amount * (new_cost_obj.pax_count + 1),
                                })

                            cost_write_vals = {
                                'passenger_offline_ids': [(3, prov_pax.id)],
                                'pax_count': rec2.pax_count - 1,
                                'total': rec2.amount * (rec2.pax_count - 1),
                            }

                            if (rec2.pax_count - 1) <= 0:
                                cost_write_vals.update({
                                    'provider_offline_booking_id': False
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
                        'issued_uid': rec.issued_uid and rec.issued_uid.id or False,
                        'issued_date': rec.issued_date,
                        'confirm_uid': rec.confirm_uid and rec.confirm_uid.id or False,
                        'confirm_date': rec.confirm_date,
                        'sent_uid': rec.sent_uid and rec.sent_uid.id or False,
                        'sent_date': rec.sent_date,
                        'currency_id': rec.currency_id and rec.currency_id.id or False,
                    }
                    new_prov_obj = self.env['tt.provider.offline'].sudo().create(prov_val)
                    provider_dict.update({
                        str(rec.id): new_prov_obj.id
                    })
                    for val in old_cost_dict.values():
                        dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                        dict_cost_obj.sudo().write({
                            'provider_offline_booking_id': new_prov_obj.id,
                            'description': new_prov_obj.pnr
                        })
                else:
                    new_prov_obj = self.env['tt.provider.offline'].sudo().browse(int(provider_dict[str(rec.id)]))
                    for val in old_cost_dict.values():
                        dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                        dict_cost_obj.sudo().write({
                            'provider_offline_booking_id': new_prov_obj.id,
                            'description': new_prov_obj.pnr
                        })

            new_book_obj.update({
                'provider_name': new_book_obj.get_provider_name_from_provider()
            })

            if book_obj.ledger_ids:
                for led in book_obj.ledger_ids:
                    if not led.is_reversed:
                        led.reverse_ledger()
                for prov in book_obj.provider_booking_ids:
                    prov.action_create_ledger(book_obj.issued_uid.id)
                for prov in new_book_obj.provider_booking_ids:
                    prov.action_create_ledger(new_book_obj.issued_uid.id)

        # jika both provider dan pax
        else:
            moved_pax_list = []
            line_list = []
            old_provider_list = []
            provider_dict = {}
            temp_pax_list = []
            temp_pax_dict = {}
            for rec in book_obj.provider_booking_ids:
                for rec2 in rec.cost_service_charge_ids:
                    rec2.is_ledger_created = False
                if rec.id in self.provider_ids.ids:
                    old_cost_list = []
                    old_cost_dict = {}
                    for rec2 in rec.cost_service_charge_ids:
                        for prov_pax in rec2.passenger_offline_ids:
                            if prov_pax.id in self.passenger_ids.ids:
                                # Catat data pax. jika pax belum ada, buat pax baru di new res.
                                if prov_pax.id not in temp_pax_list:
                                    new_pax_obj = self.env['tt.reservation.offline.passenger'].sudo().create({
                                        'booking_id': new_book_obj.id,
                                        'first_name': prov_pax.first_name,
                                        'last_name': prov_pax.last_name,
                                        'name': prov_pax.name,
                                        'title': prov_pax.title,
                                        'gender': prov_pax.gender,
                                        'birth_date': prov_pax.birth_date,
                                        'sequence': prov_pax.sequence,
                                        'passenger_id': prov_pax.passenger_id and prov_pax.passenger_id.id or False,
                                    })
                                    temp_pax_list.append(prov_pax.id)
                                    temp_pax_dict.update({
                                        str(prov_pax.id): new_pax_obj.id
                                    })
                                # Jika sudah ada, get pax obj dari id provider pax
                                else:
                                    new_pax_obj = self.env['tt.reservation.offline.passenger'].sudo().browse(int(temp_pax_dict[str(prov_pax.id)]))

                                # Jika id cost service charge belum ada di old cost list, buat baru
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
                                        'passenger_offline_ids': [(4, new_pax_obj.id)]
                                    }
                                    new_cost_obj = self.env['tt.service.charge'].sudo().create(cost_val)
                                    old_cost_list.append(rec2.id)
                                    old_cost_dict.update({
                                        str(rec2.id): new_cost_obj.id
                                    })
                                # Otherwise, edit dari cost service charge yg sudah ada
                                else:
                                    new_cost_obj = self.env['tt.service.charge'].sudo().browse(
                                        int(old_cost_dict[str(rec2.id)]))
                                    new_cost_obj.sudo().write({
                                        'passenger_offline_ids': [(4, new_pax_obj.id)],
                                        'pax_count': new_cost_obj.pax_count + 1,
                                        'total': new_cost_obj.amount * (new_cost_obj.pax_count + 1),
                                    })

                                cost_write_vals = {
                                    'passenger_offline_ids': [(3, prov_pax.id)],
                                    'pax_count': rec2.pax_count - 1,
                                    'total': rec2.amount * (rec2.pax_count - 1),
                                }

                                if (rec2.pax_count - 1) <= 0:
                                    cost_write_vals.update({
                                        'provider_offline_booking_id': False
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
                            'issued_uid': rec.issued_uid and rec.issued_uid.id or False,
                            'issued_date': rec.issued_date,
                            'confirm_uid': rec.confirm_uid and rec.confirm_uid.id or False,
                            'confirm_date': rec.confirm_date,
                            'sent_uid': rec.sent_uid and rec.sent_uid.id or False,
                            'sent_date': rec.sent_date,
                            'currency_id': rec.currency_id and rec.currency_id.id or False,
                        }
                        new_prov_obj = self.env['tt.provider.offline'].sudo().create(prov_val)
                        provider_dict.update({
                            str(rec.id): new_prov_obj.id
                        })

                        for val in old_cost_dict.values():
                            dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                            dict_cost_obj.sudo().write({
                                'provider_offline_booking_id': new_prov_obj.id,
                                'description': new_prov_obj.pnr
                            })
                    else:
                        new_prov_obj = self.env['tt.provider.offline'].sudo().browse(int(provider_dict[str(rec.id)]))
                        for val in old_cost_dict.values():
                            dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                            dict_cost_obj.sudo().write({
                                'provider_offline_booking_id': new_prov_obj.id,
                                'description': new_prov_obj.pnr
                            })

            for rec in self.provider_ids:
                for rec2 in book_obj.line_ids:
                    if rec2.pnr == rec.pnr:
                        # buat line baru
                        line_list.append(rec2)

            if line_list:
                for idx, line in enumerate(line_list):
                    self.input_new_line(line, new_pnr_list[idx], new_book_obj.offline_provider_type, new_book_obj)

            if book_obj.ledger_ids:
                for led in book_obj.ledger_ids:
                    if not led.is_reversed:
                        led.reverse_ledger()
                for prov in book_obj.provider_booking_ids:
                    prov.action_create_ledger(book_obj.issued_uid.id)
                new_book_obj.get_provider_name_from_provider()
                new_book_obj.get_pnr_list_from_provider()
                for prov in new_book_obj.provider_booking_ids:
                    prov.action_create_ledger(new_book_obj.issued_uid.id)

        book_obj.get_provider_name_from_provider()
        book_obj.get_pnr_list_from_provider()
        new_book_obj.get_provider_name_from_provider()
        new_book_obj.get_pnr_list_from_provider()
        book_obj.calculate_service_charge()
        new_book_obj.calculate_service_charge()
