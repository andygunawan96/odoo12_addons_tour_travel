from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtSplitReservationPHCWizard(models.TransientModel):
    _name = "tt.split.reservation.phc.wizard"
    _description = 'PHC Split Reservation Wizard'

    is_split_passenger = fields.Boolean('Split Passenger', default=True, readonly=True)
    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    referenced_document = fields.Char('Ref. Document', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Splitted Journey Currency', default=lambda self: self.env.user.company_id.currency_id)

    def get_split_passenger_domain(self):
        return [('booking_id', '=', self.res_id)]

    passenger_ids = fields.Many2many('tt.reservation.passenger.phc', 'phc_passenger_split_rel', 'split_wizard_id', 'passenger_id', 'Passenger',
                           domain=get_split_passenger_domain)

    @api.onchange('res_id')
    def _onchange_domain_passenger(self):
        return {'domain': {
            'passenger_ids': self.get_split_passenger_domain()
        }}

    def submit_split_reservation(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake.')
        book_obj = self.env['tt.reservation.phc'].sudo().browse(int(self.res_id))
        pax_list = []
        is_pax_full = True

        for rec in self.passenger_ids:
            pax_list.append(rec.id)

        for rec in book_obj.passenger_ids:
            if rec.id not in pax_list:
                is_pax_full = False

        if is_pax_full:
            raise UserError(_('You cannot split all Passenger(s) in this reservation. Please leave at least 1 Passenger!'))
        if self.is_split_passenger and len(book_obj.passenger_ids) <= 1:
            raise UserError(_('You cannot split Passenger as there is only 1 Passenger in this reservation.'))
        if self.is_split_passenger and not self.passenger_ids:
            raise UserError(_('Please choose at least 1 Passenger to split.'))

        book_obj.write({
            'split_uid': self.env.user.id,
            'split_date': fields.Datetime.now(),
        })

        new_vals = {
            'split_from_resv_id': book_obj.id,
            'split_uid': self.env.user.id,
            'split_date': fields.Datetime.now(),
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
            'timeslot_type': book_obj.timeslot_type and book_obj.timeslot_type or 'fixed',
            'test_address': book_obj.test_address and book_obj.test_address or '',
            'test_address_map_link': book_obj.test_address_map_link and book_obj.test_address_map_link or '',
            'picked_timeslot_id': book_obj.picked_timeslot_id and book_obj.picked_timeslot_id.id or False,
            'test_datetime': book_obj.test_datetime and book_obj.test_datetime or False,
            'booker_id': book_obj.booker_id and book_obj.booker_id.id or False,
            'contact_id': book_obj.contact_id and book_obj.contact_id.id or False,
            'contact_title': book_obj.contact_title,
            'contact_email': book_obj.contact_email,
            'contact_phone': book_obj.contact_phone,
            'is_invoice_created': book_obj.is_invoice_created,
            'timeslot_ids': [(6, 0, [tms.id for tms in book_obj.timeslot_ids])],
            'analyst_ids': [(6, 0, [anl.id for anl in book_obj.analyst_ids])],
            'state': book_obj.state,
            'state_vendor': book_obj.state_vendor
        }

        new_book_obj = self.env['tt.reservation.phc'].create(new_vals)
        new_book_obj.write({
            'pnr': new_book_obj.name and new_book_obj.name or '1'
        })

        tot_adult = 0
        tot_child = 0
        tot_infant = 0
        moved_pax_list = []
        old_provider_list = []
        provider_dict = {}
        for rec in book_obj.provider_booking_ids:
            old_cost_list = []
            old_cost_dict = {}
            for rec2 in rec.cost_service_charge_ids:
                rec2.is_ledger_created = False
                for prov_pax in rec2.passenger_phc_ids:
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
                                'passenger_phc_ids': [(4, prov_pax.id)]
                            }
                            new_cost_obj = self.env['tt.service.charge'].sudo().create(cost_val)
                            old_cost_list.append(rec2.id)
                            old_cost_dict.update({
                                str(rec2.id): new_cost_obj.id
                            })
                        else:
                            new_cost_obj = self.env['tt.service.charge'].sudo().browse(int(old_cost_dict[str(rec2.id)]))
                            new_cost_obj.sudo().write({
                                'passenger_phc_ids': [(4, prov_pax.id)],
                                'pax_count': new_cost_obj.pax_count + 1,
                                'total': new_cost_obj.amount * (new_cost_obj.pax_count + 1),
                            })

                        cost_write_vals = {
                            'passenger_phc_ids': [(3, prov_pax.id)],
                            'pax_count': rec2.pax_count - 1,
                            'total': rec2.amount * (rec2.pax_count - 1),
                        }

                        if (rec2.pax_count - 1) <= 0:
                            cost_write_vals.update({
                                'provider_phc_booking_id': False
                            })

                        rec2.sudo().write(cost_write_vals)

            if rec.id not in old_provider_list:
                old_provider_list.append(rec.id)
                prov_val = {
                    'sequence': rec.sequence,
                    'booking_id': new_book_obj.id,
                    'state': rec.state,
                    'pnr': new_book_obj.name and new_book_obj.name or '',
                    'pnr2': new_book_obj.name and new_book_obj.name or '',
                    'provider_id': rec.provider_id and rec.provider_id.id or False,
                    'carrier_id': rec.carrier_id and rec.carrier_id.id or False,
                    'hold_date': rec.hold_date,
                    'expired_date': rec.expired_date,
                    'booked_uid': rec.booked_uid and rec.booked_uid.id or False,
                    'booked_date': rec.booked_date,
                    'issued_uid': rec.issued_uid and rec.issued_uid.id or False,
                    'issued_date': datetime.now(),
                    'refund_uid': rec.refund_uid and rec.refund_uid.id or False,
                    'refund_date': rec.refund_date,
                    'sid_issued': rec.sid_issued,
                    'currency_id': rec.currency_id and rec.currency_id.id or False,
                }
                new_prov_obj = self.env['tt.provider.phc'].sudo().create(prov_val)
                provider_dict.update({
                    str(rec.id): new_prov_obj.id
                })

                for val in old_cost_dict.values():
                    dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                    dict_cost_obj.sudo().write({
                        'provider_phc_booking_id': new_prov_obj.id,
                        'description': new_prov_obj.pnr
                    })
            else:
                new_prov_obj = self.env['tt.provider.phc'].sudo().browse(int(provider_dict[str(rec.id)]))
                for val in old_cost_dict.values():
                    dict_cost_obj = self.env['tt.service.charge'].sudo().browse(int(val))
                    dict_cost_obj.sudo().write({
                        'provider_phc_booking_id': new_prov_obj.id,
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

        if book_obj.ledger_ids:
            for led in book_obj.ledger_ids:
                if not led.is_reversed:
                    led.reverse_ledger()
            for prov in book_obj.provider_booking_ids:
                prov.action_create_ledger(book_obj.issued_uid.id)
            for prov in new_book_obj.provider_booking_ids:
                prov.action_create_ledger(new_book_obj.issued_uid.id)

        book_obj.calculate_service_charge()
        new_book_obj.calculate_service_charge()

        provider_state_context = {
            'co_uid': self.env.user.id,
            'co_agent_id': self.env.user.agent_id.id,
        }

        book_obj.check_provider_state(context=provider_state_context)
        book_obj.check_reservation_verif(self.env.user.id)
        new_book_obj.check_provider_state(context=provider_state_context)
        new_book_obj.check_reservation_verif(self.env.user.id)
