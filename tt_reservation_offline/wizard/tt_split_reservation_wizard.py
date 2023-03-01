from odoo import api, fields, models, _
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TtSplitReservationWizard(models.TransientModel):
    _name = "tt.split.reservation.offline.wizard"
    _description = 'Offline Split Reservation Wizard'

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    referenced_document = fields.Char('Ref. Document', required=True, readonly=True)
    total_price = fields.Monetary('Total Price', default=0)
    new_commission = fields.Monetary('Total Commission', default=0)
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
                    "arrival_date": line_obj.arrival_date,
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

    def round_service_charge(self, book_obj, new_book_obj):
        # hitung total dari pricing, lalu bandingkan dg total sale price
        total_pricing = 0
        for provider in book_obj.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    total_pricing += scs.total
        if total_pricing < book_obj.total:
            pricing_diff = book_obj.total - total_pricing
            for scs in book_obj.provider_booking_ids[0].cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    scs.amount += pricing_diff
                    scs.total += pricing_diff
                    break
        elif total_pricing > book_obj.total:
            pricing_diff = total_pricing - book_obj.total
            for scs in book_obj.provider_booking_ids[0].cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    scs.amount -= pricing_diff
                    scs.total -= pricing_diff

        total_commission = []
        for provider in book_obj.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                if scs.charge_type == 'RAC':
                    if not any(d['id'] == scs.commission_agent_id.id for d in total_commission):
                        # if scs.commission_agent_id.id not in total_commission:
                        total_commission.append({
                            'id': scs.commission_agent_id.id,
                            'amount': scs.amount
                        })
                    else:
                        comm_dict = next(
                            (item for item in total_commission if item['id'] == scs.commission_agent_id.id), None)
                        comm_dict['amount'] += scs.amount

        book_obj._get_agent_commission()
        book_obj._get_agent_price()

        for comm in total_commission:
            if comm['id'] == book_obj.agent_id.id:
                # Bandingkan amount komisi agent dg agent commission yang ada di book obj
                agent_diff = book_obj.agent_commission - comm['amount']
                for scs in book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if agent_diff > 0:
                            scs.amount -= agent_diff
                            scs.total -= agent_diff
                            book_obj.agent_commission = comm['amount']
                        elif agent_diff < 0:
                            scs.amount += agent_diff
                            scs.total += agent_diff
                            book_obj.agent_commission = comm['amount']
                        break
            elif comm['id'] == self.env.ref('tt_base.rodex_ho').id:
                # Bandingkan amount komisi HO dg HO commission yang ada di book obj
                ho_diff = book_obj.ho_commission - comm['amount']
                for scs in book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if scs.charge_code != 'hoc' and scs.amount != 0:
                            if ho_diff > 0:
                                scs.amount -= ho_diff
                                scs.total -= ho_diff
                                book_obj.ho_commission = comm['amount']
                            elif ho_diff < 0:
                                scs.amount += ho_diff
                                scs.total += ho_diff
                                book_obj.ho_commission = comm['amount']
                            break
            else:
                # Bandingkan amount komisi parent dg parent commission yang ada di book obj
                parent_diff = book_obj.parent_agent_commission - comm['amount']
                for scs in book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if parent_diff > 0:
                            scs.amount -= parent_diff
                            scs.total -= parent_diff
                            book_obj.parent_agent_commission = comm['amount']
                        elif parent_diff < 0:
                            scs.amount += parent_diff
                            scs.total += parent_diff
                            book_obj.parent_agent_commission = comm['amount']
                        break

        for provider in book_obj.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    _logger.info(scs.to_dict())

        total_pricing_new = 0
        for provider in new_book_obj.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                if scs.charge_type != 'RAC':
                    total_pricing_new += scs.total
        if total_pricing_new > new_book_obj.total:
            pricing_diff = new_book_obj.total - total_pricing
            for scs in new_book_obj.provider_booking_ids[0].cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    scs.amount += pricing_diff
                    scs.total += pricing_diff
                    break
        elif total_pricing_new < new_book_obj.total:
            pricing_diff = total_pricing_new - new_book_obj.total
            for scs in new_book_obj.provider_booking_ids[0].cost_service_charge_ids:
                if scs.charge_type == 'FARE':
                    scs.amount -= pricing_diff
                    scs.total -= pricing_diff
                    break

        total_commission = []
        for provider in new_book_obj.provider_booking_ids:
            for scs in provider.cost_service_charge_ids:
                if scs.charge_type == 'RAC':
                    if not any(d['id'] == scs.commission_agent_id.id for d in total_commission):
                        # if scs.commission_agent_id.id not in total_commission:
                        total_commission.append({
                            'id': scs.commission_agent_id.id,
                            'amount': scs.amount
                        })
                    else:
                        comm_dict = next(
                            (item for item in total_commission if item['id'] == scs.commission_agent_id.id), None)
                        comm_dict['amount'] += scs.amount

        new_book_obj._get_agent_commission()
        new_book_obj._get_agent_price()

        for comm in total_commission:
            if comm['id'] == new_book_obj.agent_id.id:
                agent_diff = new_book_obj.agent_commission - comm['amount']
                for scs in new_book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if agent_diff > 0:
                            scs.amount += agent_diff
                            scs.total += agent_diff
                            new_book_obj.agent_commission = comm['amount']
                        elif agent_diff < 0:
                            scs.amount -= agent_diff
                            scs.total -= agent_diff
                            new_book_obj.agent_commission = comm['amount']
                        break
            elif comm['id'] == self.env.ref('tt_base.rodex_ho').id:
                ho_diff = new_book_obj.ho_commission - comm['amount']
                for scs in new_book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if scs.charge_code != 'hoc' and scs.amount != 0:
                            if ho_diff > 0:
                                scs.amount += ho_diff
                                scs.total += ho_diff
                                new_book_obj.ho_commission = comm['amount']
                            elif ho_diff < 0:
                                scs.amount -= ho_diff
                                scs.total -= ho_diff
                                new_book_obj.ho_commission = comm['amount']
                            break
            else:
                parent_diff = new_book_obj.parent_agent_commission - comm['amount']
                for scs in new_book_obj.provider_booking_ids[0].cost_service_charge_ids:
                    if scs.commission_agent_id.id == comm['id']:
                        if parent_diff > 0:
                            scs.amount -= parent_diff
                            scs.total -= parent_diff
                            new_book_obj.parent_agent_commission = comm['amount']
                        elif parent_diff < 0:
                            scs.amount += parent_diff
                            scs.total += parent_diff
                            new_book_obj.parent_agent_commission = comm['amount']
                        break

    def get_service_charge_value(self, charge_code, charge_type, pax_type, currency_id, amount, total, provider_id,
                                 sequence, foreign_amount, description, pax_count, passenger_ids,
                                 commission_agent_id=False):
        vals = {
            'charge_code': charge_code,
            'charge_type': charge_type,
            'pax_type': pax_type,
            'currency_id': currency_id,
            'amount': amount,
            'provider_offline_booking_id': provider_id,
            'sequence': sequence,
            'description': description,
            'pax_count': pax_count,
            'total': total,
            'passenger_offline_ids': passenger_ids,
        }
        if commission_agent_id:
            vals.update({
                'commission_agent_id': commission_agent_id
            })
        return vals

    def create_service_charge_split_offline(self, provider, pax_list, provider_list, passengers, book_obj, type):
        if book_obj.offline_provider_type != 'other':
            provider_type_id = self.env['tt.provider.type'].search(
                [('code', '=', book_obj.offline_provider_type)], limit=1)
        else:
            provider_type_id = self.env['tt.provider.type'].search(
                [('code', '=', self.env.ref('tt_reservation_offline.tt_provider_type_offline').code)], limit=1)
        scs_list = []
        pricing_obj = self.env['tt.pricing.agent'].sudo()

        div = 0
        for prov in book_obj.provider_booking_ids:
            for psg in book_obj.passenger_ids:
                if type == 'old':
                    if prov in self.provider_ids and psg in self.passenger_ids:
                        pass
                    else:
                        div += 1
                elif type == 'new':
                    div += 1

        real_comm = book_obj.total_commission_amount
        fee_amount_val = book_obj.get_fee_amount(book_obj.agent_id, provider_type_id, book_obj.total_commission_amount)

        """ Hitung fee amount """
        if book_obj.offline_provider_type in ['airline', 'train']:
            """ airline, train """
            real_comm -= fee_amount_val['amount'] * (len(book_obj.provider_booking_ids) * len(book_obj.passenger_ids))
            if type == 'old':
                real_comm += fee_amount_val['amount'] * (len(self.provider_ids) * len(self.passenger_ids))

            for line in book_obj.line_ids:
                if line.pnr == provider.pnr:
                    """ get fee amount per pax """
                    for psg in book_obj.passenger_ids:
                        if type == 'old':
                            if psg in self.passenger_ids and provider in self.provider_ids:
                                pass
                            else:
                                fee_amount_vals = book_obj.sudo().get_fee_amount(book_obj.agent_id, provider_type_id,
                                                                                 book_obj.total_commission_amount, psg)
                                fee_amount_vals['provider_offline_booking_id'] = provider.id
                                scs_list.append(fee_amount_vals)
                        else:
                            fee_amount_vals = book_obj.sudo().get_fee_amount(book_obj.agent_id, provider_type_id,
                                                                             book_obj.total_commission_amount, psg)
                            fee_amount_vals['provider_offline_booking_id'] = provider.id
                            scs_list.append(fee_amount_vals)
                    break
        elif book_obj.offline_provider_type == 'hotel':
            """ hotel """
            real_comm -= fee_amount_val['amount'] * len(book_obj.provider_booking_ids)

            fee_amount_vals = book_obj.sudo().get_fee_amount(book_obj.agent_id, provider_type_id,
                                                             book_obj.total_commission_amount)
            fee_amount_vals['provider_offline_booking_id'] = provider.id
            scs_list.append(fee_amount_vals)
        else:
            """ else """
            real_comm -= fee_amount_val['amount'] * (len(book_obj.provider_booking_ids) * len(book_obj.passenger_ids))

            """ get fee amount per pax """
            for psg in book_obj.passenger_ids:
                fee_amount_vals = book_obj.sudo().get_fee_amount(book_obj.agent_id, provider_type_id,
                                                                 book_obj.total_commission_amount, psg)
                fee_amount_vals['provider_offline_booking_id'] = provider.id
                scs_list.append(fee_amount_vals)

        if book_obj.offline_provider_type != 'hotel':
            for psg in book_obj.passenger_ids:
                if type == 'old':
                    if provider in self.provider_ids and psg in self.passenger_ids:
                        pass
                    else:
                        vals = self.get_service_charge_value('fare', 'FARE', psg.pax_type, provider.currency_id.id,
                                                             book_obj.total/div, book_obj.total/div, provider.id,
                                                             provider.sequence, 0, book_obj.name, 1, [], False)
                        vals['passenger_offline_ids'].append(psg.id)
                        scs_list.append(vals)
                elif type == 'new':
                    vals = self.get_service_charge_value('fare', 'FARE', psg.pax_type, provider.currency_id.id,
                                                         book_obj.total/div, book_obj.total/div, provider.id,
                                                         provider.sequence, 0, book_obj.name, 1, [], False)
                    vals['passenger_offline_ids'].append(psg.id)
                    scs_list.append(vals)
        else:
            for line in book_obj.line_ids:
                vals = self.get_service_charge_value('fare', 'FARE', 'ADT', provider.currency_id.id,
                                                     book_obj.total / div, book_obj.total / div, provider.id,
                                                     provider.sequence, 0, book_obj.name, 1, [], False)
                for psg in book_obj.passenger_ids:
                    vals['passenger_offline_ids'].append(psg.id)
                scs_list.append(vals)
        commission_list = pricing_obj.get_commission(real_comm / div, book_obj.agent_id, provider_type_id)

        # HOC / Hidden Commission
        # for comm in commission_list:
        #     if comm['code'] == 'hoc':
        #         vals = self.get_service_charge_value(comm['code'], comm['type'], 'ADT', provider.currency_id.id,
        #                                              comm['amount'], comm['amount'], provider.id, provider.sequence, 0,
        #                                              book_obj.name, 1, [], comm['commission_agent_id'])
        #         scs_list.append(vals)

        for psg in book_obj.passenger_ids:
            for comm in commission_list:
                if comm['code'] != 'hoc':
                    if type == 'old':
                        if provider in self.provider_ids and psg in self.passenger_ids:
                            pass
                        else:
                            vals = self.get_service_charge_value(comm['code'], comm['type'], psg.pax_type,
                                                                 provider.currency_id.id, comm['amount'],
                                                                 comm['amount'], provider.id, provider.sequence, 0,
                                                                 book_obj.name, 1, [], comm['commission_agent_id'])
                            # vals = {
                            #     'commission_agent_id': comm['commission_agent_id'],
                            #     'charge_code': comm['code'],
                            #     'charge_type': comm['type'],
                            #     'pax_type': psg.pax_type,
                            #     'currency_id': provider.currency_id.id,
                            #     'amount': comm['amount']/len(book_obj.passenger_ids),
                            #     'provider_offline_booking_id': provider.id,
                            #     'sequence': provider.sequence,
                            #     'description': book_obj.name,
                            #     'pax_count': 1,
                            #     'total': comm['amount']/len(book_obj.passenger_ids),
                            #     'passenger_offline_ids': [],
                            # }
                            # /len(book_obj.passenger_ids)
                            vals['passenger_offline_ids'].append(psg.id)
                            scs_list.append(vals)
                    elif type == 'new':
                        vals = self.get_service_charge_value(comm['code'], comm['type'], psg.pax_type,
                                                             provider.currency_id.id, comm['amount'], comm['amount'],
                                                             provider.id, provider.sequence, 0, book_obj.name, 1, [],
                                                             comm['commission_agent_id'])
                        vals['passenger_offline_ids'].append(psg.id)
                        scs_list.append(vals)

        # for pax in passengers:
        #     if pax.id not in pax_list or provider.id not in provider_list:
        #         cost_val_fare = {
        #             'charge_code': 'fare',
        #             'charge_type': 'FARE',
        #             'pax_type': pax.pax_type,
        #             'currency_id': provider.currency_id.id,
        #             'amount': book_obj.total/div,
        #             # 'foreign_currency_id': provider.foreign_currency_id and provider.foreign_currency_id.id or False,
        #             'provider_offline_booking_id': provider.id,
        #             'foreign_amount': 0,
        #             'sequence': provider.sequence,
        #             'description': book_obj.name,
        #             'pax_count': 1,
        #             'total': book_obj.total/div,
        #             'passenger_offline_ids': [],
        #         }
        #         cost_val_fare['passenger_offline_ids'].append(pax.id)
        #         scs_list.append(cost_val_fare)
        #
        #         commission_list = pricing_obj.get_commission(
        #             book_obj.total_commission_amount / div,
        #             book_obj.agent_id, provider_type_id)
        #
        #         for comm in commission_list:
        #             if comm['amount'] > 0:
        #                 vals2 = cost_val_fare.copy()
        #                 vals2.update({
        #                     'commission_agent_id': comm['commission_agent_id'],
        #                     'total': comm['amount'] * -1,
        #                     'amount': comm['amount'] * -1,
        #                     'charge_code': comm['code'],
        #                     'charge_type': 'RAC',
        #                     'passenger_offline_ids': [],
        #                 })
        #                 vals2['passenger_offline_ids'].append(pax.id)
        #                 scs_list.append(vals2)

        service_chg_obj = provider.env['tt.service.charge']
        for scs in scs_list:
            scs['passenger_offline_ids'] = [(6, 0, scs['passenger_offline_ids'])]
            scs_obj = service_chg_obj.create(scs)

    @api.onchange('new_pnr')
    def _onchange_new_pnr(self):
        if self.passenger_ids:
            new_pnr_list = self.new_pnr and self.new_pnr.strip().split(',') or []
            def_txt = ''
            book_obj = self.env['tt.reservation.offline'].sudo().browse(int(self.res_id))
            for idx, rec in enumerate(self.provider_ids):
                if idx < len(new_pnr_list):
                    def_txt += str(rec.pnr) + ' will be converted to ' + str(
                        new_pnr_list[idx]) + ' in the new reservation. \n'
            self.new_pnr_text = def_txt

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
        if self.total_price > book_obj.total:
            raise UserError(_('Total price for split cannot be larger than total sale price.'))
        if self.new_commission > book_obj.total_commission_amount:
            raise UserError(_('Total commission for split cannot be larger than total commission amount.'))
        if is_provider_full:
            raise UserError(_('You cannot split all Provider(s). Please remove 1 or more provider(s)'))
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
            'pnr': book_obj.pnr,
            'agent_id': book_obj.agent_id and book_obj.agent_id.id or False,
            'customer_parent_id': book_obj.customer_parent_id and book_obj.customer_parent_id.id or False,
            'offline_provider_type': book_obj.offline_provider_type,
            'hold_date': book_obj.hold_date,
            # 'expired_date': book_obj.expired_date,
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
        new_book_obj.update({
            'total': self.total_price,
            'total_commission_amount': self.new_commission
        })
        new_book_obj.update({
            'split_from_resv_id': book_obj.id
        })
        book_obj.update({
            'vendor_amount': book_obj.vendor_amount - self.vendor_amount,
            'total': book_obj.total - self.total_price,
            'total_commission_amount': book_obj.total_commission_amount - self.new_commission
        })

        # jika provider only
        if len(pax_list) <= 0:
            for rec in self.provider_ids:
                for rec2 in book_obj.provider_booking_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id

            for rec in self.provider_ids:
                for rec2 in book_obj.line_ids:
                    if rec2.pnr == rec.pnr:
                        rec2.booking_id = new_book_obj.id

            for prov_pax in book_obj.passenger_ids:
                self.env['tt.reservation.offline.passenger'].sudo().create({
                    'booking_id': new_book_obj.id,
                    'first_name': prov_pax.first_name,
                    'last_name': prov_pax.last_name,
                    'name': prov_pax.name,
                    'title': prov_pax.title,
                    'pax_type': prov_pax.pax_type,
                    'agent_id': prov_pax.agent_id.id,
                    'gender': prov_pax.gender,
                    'birth_date': prov_pax.birth_date,
                    'sequence': prov_pax.sequence,
                    'passenger_id': prov_pax.passenger_id and prov_pax.passenger_id.id or False,
                })

            for provider in book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()
            for provider in new_book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()

            for provider in book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, book_obj.passenger_ids,
                                                         book_obj, 'old')
            for provider in new_book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, new_book_obj.passenger_ids,
                                                         new_book_obj, 'new')

            self.round_service_charge(book_obj, new_book_obj)

            book_obj.calculate_service_charge()
            new_book_obj.calculate_service_charge()

            book_obj.get_provider_name_from_provider()
            book_obj.get_pnr_list_from_provider()
            book_obj.get_carrier_name()
            new_book_obj.get_provider_name_from_provider()
            new_book_obj.get_pnr_list_from_provider()
            new_book_obj.get_carrier_name()

            book_obj._get_agent_commission()
            new_book_obj._get_agent_commission()

            if book_obj.ledger_ids:
                for led in book_obj.ledger_ids:
                    if not led.is_reversed:
                        led.reverse_ledger()
                for prov in book_obj.provider_booking_ids:
                    prov.action_create_ledger(book_obj.issued_uid.id)
                for prov in new_book_obj.provider_booking_ids:
                    prov.action_create_ledger(new_book_obj.issued_uid.id)

        # jika pax only
        elif len(provider_list) <= 0:
            old_pnr_list = []
            old_provider_list = []
            provider_dict = {}
            line_list = []

            for line in book_obj.line_ids:
                if line.pnr in old_pnr_list:
                    old_pnr_list.append(line.pnr)

            for rec2 in book_obj.line_ids:
                line_list.append(rec2)

            for line in line_list:
                for old_pnr in old_pnr_list:
                    for new_pnr in new_pnr_list:
                        if old_pnr_list.index(old_pnr) == new_pnr_list.index(new_pnr):
                            line.pnr = new_pnr

            if line_list:
                if book_obj.offline_provider_type in ['airline', 'train']:
                    last_pnr = ''
                    for idx, line in enumerate(line_list):
                        if last_pnr == line.pnr:
                            self.input_new_line(line, last_pnr, new_book_obj.offline_provider_type, new_book_obj)
                        else:
                            self.input_new_line(line, new_pnr_list[idx], new_book_obj.offline_provider_type, new_book_obj)
                            last_pnr = line.pnr
                else:
                    for idx, line in enumerate(line_list):
                        self.input_new_line(line, new_pnr_list[idx], new_book_obj.offline_provider_type, new_book_obj)

            # Pindahkan pax yang dipilih dari wizard ke booking baru
            for prov_pax in book_obj.passenger_ids:
                # Jika pax ada di dalam self.passenger_ids
                if prov_pax.id in self.passenger_ids.ids:
                    prov_pax.booking_id = new_book_obj.id

            # Buat provider baru di booking baru, sesuai dg urutan PNR yang diinput di wizard
            for rec in book_obj.provider_booking_ids:
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
                        # 'expired_date': rec.expired_date,
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

            for provider in book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()
            for provider in new_book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()

            for provider in book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, book_obj.passenger_ids,
                                                         book_obj, 'old')
            for provider in new_book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, new_book_obj.passenger_ids,
                                                         new_book_obj, 'new')

            self.round_service_charge(book_obj, new_book_obj)

            book_obj.calculate_service_charge()
            new_book_obj.calculate_service_charge()

            book_obj.get_provider_name_from_provider()
            book_obj.get_pnr_list_from_provider()
            book_obj.get_carrier_name()
            new_book_obj.get_provider_name_from_provider()
            new_book_obj.get_pnr_list_from_provider()
            new_book_obj.get_carrier_name()

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
            line_list = []
            old_provider_list = []
            old_pnr_list = []
            provider_dict = {}
            temp_pax_list = []
            temp_pax_dict = {}

            for rec in book_obj.provider_booking_ids:
                if rec.id in self.provider_ids.ids:
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
                            # 'expired_date': rec.expired_date,
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

            for rec in self.provider_ids:
                for rec2 in book_obj.line_ids:
                    if rec2.pnr == rec.pnr:
                        # buat line baru
                        line_list.append(rec2)

            if line_list:
                if book_obj.offline_provider_type in ['airline', 'train']:
                    last_pnr = ''
                    idx = -1
                    for line in line_list:
                        if last_pnr != line.pnr:
                            last_pnr = line.pnr
                            idx += 1
                        self.input_new_line(line, new_pnr_list[idx], new_book_obj.offline_provider_type, new_book_obj)
                else:
                    for idx, line in enumerate(line_list):
                        self.input_new_line(line, new_pnr_list[idx], new_book_obj.offline_provider_type, new_book_obj)

            for prov_pax in book_obj.passenger_ids:
                if prov_pax.id in self.passenger_ids.ids:
                    # Catat data pax. jika pax belum ada, buat pax baru di new res.
                    if prov_pax.id not in temp_pax_list:
                        new_pax_obj = self.env['tt.reservation.offline.passenger'].sudo().create({
                            'booking_id': new_book_obj.id,
                            'first_name': prov_pax.first_name,
                            'last_name': prov_pax.last_name,
                            'name': prov_pax.name,
                            'title': prov_pax.title,
                            'pax_type': prov_pax.pax_type,
                            'agent_id': prov_pax.agent_id.id,
                            'gender': prov_pax.gender,
                            'birth_date': prov_pax.birth_date,
                            'sequence': prov_pax.sequence,
                            'passenger_id': prov_pax.passenger_id and prov_pax.passenger_id.id or False,
                        })
                        temp_pax_list.append(prov_pax.id)
                        temp_pax_dict.update({
                            str(prov_pax.id): new_pax_obj.id
                        })

            for provider in book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()
            for provider in new_book_obj.provider_booking_ids:
                for scs in provider.cost_service_charge_ids:
                    scs.unlink()

            for provider in book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, book_obj.passenger_ids,
                                                         book_obj, 'old')
            for provider in new_book_obj.provider_booking_ids:
                # provider.create_service_charge()
                self.create_service_charge_split_offline(provider, pax_list, provider_list, new_book_obj.passenger_ids,
                                                         new_book_obj, 'new')

            self.round_service_charge(book_obj, new_book_obj)

            book_obj.calculate_service_charge()
            new_book_obj.calculate_service_charge()

            book_obj.get_provider_name_from_provider()
            book_obj.get_pnr_list_from_provider()
            book_obj.get_carrier_name()
            new_book_obj.get_provider_name_from_provider()
            new_book_obj.get_pnr_list_from_provider()
            new_book_obj.get_carrier_name()

            if book_obj.ledger_ids:
                for led in book_obj.ledger_ids:
                    if not led.is_reversed:
                        led.reverse_ledger()
                for prov in book_obj.provider_booking_ids:
                    prov.action_create_ledger(book_obj.issued_uid.id)
                for prov in new_book_obj.provider_booking_ids:
                    prov.action_create_ledger(new_book_obj.issued_uid.id)
