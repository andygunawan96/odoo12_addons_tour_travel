from odoo import models, fields, api
import datetime
import json
from num2words import num2words


class PrintoutTicketForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_ticket'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            data['context']['active_ids'] = docids
        values = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }

                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] += 1
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today().strftime('%d %b %Y'),
            'with_price': data.get('is_with_price') or False,
        }


class PrintoutTicketTrainForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_train_ticket'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            data['context']['active_model'] = 'tt.reservation.train'
            data['context']['active_ids'] = docids
        values = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }

                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] += 1
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today().strftime('%d %b %Y'),
            'with_price': data.get('is_with_price') or False,
        }


class PrintoutInvoice(models.AbstractModel):
    _name = 'report.tt_report_common.printout_invoice'
    _description = 'Rodex Model'

    """Abstract Model for report template.
        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    def get_invoice_data(self, line, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.offline':
            for rec2 in rec.line_ids:
                pnr = rec2.pnr if rec2.pnr else '-'
                if not a.get(pnr):
                    a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],'provider_type': ''}
                a[pnr]['descs'].append(line.desc if line.desc else '')
                a[pnr]['provider_type'] = rec.provider_type_id.name
                for line_detail in line.invoice_line_detail_ids:
                    a[pnr]['pax_data'].append({
                        'name': (line_detail.desc if line_detail.desc else ''),
                        'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
                    })
        elif rec._name == 'tt.reservation.hotel':
            if rec.room_detail_ids:
                for rec2 in rec.room_detail_ids:
                    issued_name = rec2.issued_name if rec2.issued_name else '-'
                    if not a.get(issued_name):
                        a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
                                          'provider_type': ''}
                    a[issued_name]['descs'].append(line.desc if line.desc else '')
                    a[issued_name]['provider_type'] = rec.provider_type_id.name
                    for line_detail in line.invoice_line_detail_ids:
                        a[issued_name]['pax_data'].append({
                            'name': (line_detail.desc if line_detail.desc else ''),
                            'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
                        })
            else:
                issued_name = '-'
                if not a.get(issued_name):
                    a[issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [],
                                      'provider_type': ''}
                a[issued_name]['descs'].append(line.desc if line.desc else '')
                a[issued_name]['provider_type'] = rec.provider_type_id.name
                for line_detail in line.invoice_line_detail_ids:
                    a[issued_name]['pax_data'].append({
                        'name': (line_detail.desc if line_detail.desc else ''),
                        'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
                    })
        else:
            if rec.provider_booking_ids:
                for provider in rec.provider_booking_ids:
                    pnr = provider.pnr if provider.pnr else '-'
                    if not a.get(pnr):
                        a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
                    a[pnr]['descs'].append(line.desc if line.desc else '')
                    a[pnr]['provider_type'] = rec.provider_type_id.name
                    for line_detail in line.invoice_line_detail_ids:
                        a[pnr]['pax_data'].append({
                            'name': (line_detail.desc if line_detail.desc else ''),
                            'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
                        })
            else:
                pnr = '-'
                if not a.get(pnr):
                    a[pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': ''}
                a[pnr]['descs'].append(line.desc if line.desc else '')
                a[pnr]['provider_type'] = rec.provider_type_id.name
                for line_detail in line.invoice_line_detail_ids:
                    a[pnr]['pax_data'].append({
                        'name': (line_detail.desc if line_detail.desc else ''),
                        'total': (line_detail.price_subtotal if line_detail.price_subtotal else '')
                    })
        return a

    def calc_segments(self, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            for rec2 in rec.room_detail_ids:
                if not a.get(rec2.issued_name):
                    a[rec2.issued_name] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': 0}
                a[rec2.issued_name]['descs'].append( 'Hotel: ' + rec.hotel_name + '; Room: ' + rec2.room_name + ' ' + str(rec2.room_type) )
                a[rec2.issued_name]['total'] += rec2.sale_price
            for psg in rec.passenger_ids:
                a[rec.pnr]['pax_data'].append({
                    'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                })
        elif rec._name == 'tt.reservation.airline':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                for journey in provider.journey_ids:
                    a[provider.pnr]['descs'].append(journey.origin_id.name + ' - ' + journey.destination_id.name + '; ' +
                                                    journey.departure_date + ' - ' + journey.arrival_date + '; ' +
                                                    journey.carrier_id.name + ' ' + journey.name)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
            # for rec2 in rec.segment_ids:
            #     if not a.get(rec2.pnr):
            #         a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
            #     a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
            #                                 rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
            #                                 rec2.carrier_id.name + ' ' + rec2.name)

        elif rec._name == 'tt.reservation.activity':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.activity_id.name if provider.activity_id.name else '') + ' - ' + \
                            (provider.activity_product_id.name if provider.activity_product_id.name else '') + '; ' + \
                            (str(provider.visit_date) if provider.visit_date else '')
                if rec.timeslot:
                    temp_desc += ' ' + str(rec.timeslot) + '; '
                else:
                    temp_desc += '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total

                # if not a.get(rec.pnr):
                #     a[rec.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                # temp_desc = (rec.activity_id.name if rec.activity_id.name else '') + ' - ' + \
                #             (rec.activity_product_id.name if rec.activity_product_id.name else '') + '; ' + \
                #             (str(rec.visit_date) if rec.visit_date else '')
                # if rec.timeslot:
                #     temp_desc += ' ' + str(rec.timeslot) + '; '
                # else:
                #     temp_desc += '; '
                # a[rec.pnr]['descs'].append(temp_desc)
        elif rec._name == 'tt.reservation.visa':
            pnr = rec.provider_booking_ids[0].pnr
            for rec2 in rec.provider_booking_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'visa', 'total': rec.total}
                for pax in rec2.passenger_ids:
                    a[rec2.pnr]['descs'].append('Visa : ' + (pax.passenger_id.first_name if pax.passenger_id.first_name else '') + ' ' +
                                               (pax.passenger_id.last_name if pax.passenger_id.last_name else '') + ', ' +
                                               (pax.passenger_id.title if pax.passenger_id.title else '') + ' ' +
                                               '( ' + (pax.pax_type if pax.pax_type else '') + ' ) ' +
                                               (pax.pricelist_id.entry_type if pax.pricelist_id.entry_type else '') + ' ' +
                                               (pax.pricelist_id.visa_type if pax.pricelist_id.visa_type else '') + ' ' +
                                               (pax.pricelist_id.process_type if pax.pricelist_id.process_type else '') + ' ' +
                                               '(' + (str(pax.pricelist_id.duration) if pax.pricelist_id.duration else '') + ' days)')
                for psg in rec.passenger_ids:
                    a[rec2.pnr]['pax_data'].append({
                        'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                        'total': psg.pricelist_id.sale_price
                    })
        elif rec._name == 'tt.reservation.tour':
            for provider in rec.provider_booking_ids:
                if not a.get(provider.pnr):
                    a[provider.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'total': rec.total}
                temp_desc = (provider.tour_id.name if provider.tour_id.name else '') + '; ' + (str(provider.departure_date)[:10] if provider.departure_date else '') + ' - ' + (str(provider.return_date)[:10] if provider.return_date else '') + '; '
                a[provider.pnr]['descs'].append(temp_desc)
                for ticket in provider.ticket_ids:
                    a[provider.pnr]['pax_data'].append({
                        'name': ticket.passenger_id.first_name + ' ' + (
                            ticket.passenger_id.last_name if ticket.passenger_id.last_name else ''),
                        'total': 0
                    })
                for pax in a[provider.pnr]['pax_data']:
                    if a[provider.pnr]['pax_data'].get('pax_type'):
                        for price in provider.cost_service_charge_ids:
                            if pax.get('pax_type') == price.pax_type:
                                pax['total'] += price.amount / price.pax_total
        elif rec._name == 'tt.reservation.offline':
            if rec.provider_type_id_name == 'hotel':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'hotel', 'total': rec.total}
                    a[rec2.pnr]['descs'].append('Hotel: ' + (rec2.hotel_name if rec2.hotel_name else '') +
                                                '; Room: ' + (rec2.room if rec2.room else '') + ' ' +
                                                str(rec2.meal_type if rec2.meal_type else ''))
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'hotel',
                            'total': 0
                        })
            elif rec.provider_type_id_name == 'airline':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'airline', 'total': rec.total}
                    a[rec2.pnr]['descs'].append((rec2.origin_id.name if rec2.origin_id.name else '') + ' - ' +
                                                (rec2.destination_id.name if rec2.destination_id.name else '') + '; ' +
                                                str(rec2.departure_date if rec2.departure_date else '') + ' - ' +
                                                str(rec2.return_date if rec2.return_date else '') + '; ' +
                                                (rec2.carrier_id.name if rec2.carrier_id.name else '') + ' ' +
                                                (rec2.carrier_code if rec2.carrier_code else '') + ' - ' +
                                                (rec2.carrier_number if rec2.carrier_number else '') + ' ')
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'provider_type': 'airline',
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
            elif rec.provider_type_id_name == 'activity':
                for rec2 in rec.line_ids:
                    if not a.get(rec2.pnr):
                        a[rec2.pnr] = {'model': rec._name, 'paxs': paxs, 'pax_data': [], 'descs': [], 'provider_type': 'activity', 'total': rec.total}
                    temp_desc = (rec2.activity_name.name if rec2.activity_name.name else '') + ' - ' + \
                                (rec2.activity_package.name if rec2.activity_package.name else '') + '; ' + \
                                (str(rec2.check_in) if rec2.check_in else '')
                    if rec2.activity_timeslot:
                        temp_desc += ' ' + str(rec2.activity_timeslot) + '; '
                    else:
                        temp_desc += '; '
                    a[rec2.pnr]['descs'].append(temp_desc)
                    for psg in rec.passenger_ids:
                        a[rec2.pnr]['pax_data'].append({
                            'name': (psg.first_name if psg.first_name else '') + ' ' + (psg.last_name if psg.last_name else ''),
                            'total': 0
                        })
                    for pax in a[rec2.pnr]['pax_data']:
                        pax['total'] = rec.total / len(rec.passenger_ids)
        return a
    # Get Terbilang dkk di hapus
    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        # Print dari BackEnd bisa digunakan untuk Resv maupun invoice
        if not data.get('context'):
            data['context'] = {
                'active_model': 'tt.reservation.airline',
                'active_ids': docids
            }
        values = {}
        val = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            for rec2 in rec.invoice_line_ids:
                resv_obj = self.env[rec2.res_model_resv].browse(rec2.res_id_resv)
                values[rec.id].append(self.get_invoice_data(rec2, resv_obj, resv_obj.passenger_ids))
                # values[rec.id].append(self.calc_segments(resv_obj, resv_obj.passenger_ids))
        val = {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'inv_lines': values,
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }
        return val


class PrintoutIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_itinerary'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        values = {}
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids

        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }

                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] += 1
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today().strftime('%d %b %Y')
        }


class PrintoutActivityIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_activity_itinerary'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }

                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] += 1
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today().strftime('%d %b %Y')
        }


class PrintoutTourIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_tour_itinerary'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {}
            if internal_model_id == 1:
                data['context']['active_model'] = 'tt.reservation.airline'
            elif internal_model_id == 2:
                data['context']['active_model'] = 'tt.reservation.train'
            elif internal_model_id == 3:
                data['context']['active_model'] = 'tt.reservation.hotel'
            elif internal_model_id == 4:
                data['context']['active_model'] = 'tt.reservation.activity'
            elif internal_model_id == 5:
                data['context']['active_model'] = 'tt.reservation.tour'
            else:
                data['context']['active_model'] = 'tt.agent.invoice'

            data['context']['active_ids'] = docids
        values = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            a = {}
            for rec2 in rec.sale_service_charge_ids:
                if rec2.pax_type not in a.keys():
                    a[rec2.pax_type] = {
                        'pax_type': rec2.pax_type,
                        'fare': 0,
                        'tax': 0,
                        'qty': 0,
                    }

                if rec2.charge_type.lower() == 'fare':
                    a[rec2.pax_type]['fare'] += rec2.amount
                    a[rec2.pax_type]['qty'] += 1
                elif rec2.charge_type.lower() in ['roc', 'tax']:
                    a[rec2.pax_type]['tax'] += rec2.amount
            values[rec.id] = [a[new_a] for new_a in a]
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'doc_type': 'itin',
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today().strftime('%d %b %Y')
        }


class PrintoutJSONIteneraryForm(models.AbstractModel):
    _name = 'report.tt_report_common.printout_json_itinerary'
    _description = 'Rodex Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        '''
        values = {
            'type': 'hotel', ** hotel, activity**
            'line': [
                {** Hotel **
                    'resv': 'qwe123', ** PNR / Resv Code **
                    'checkin': '2019-10-24', ** YYYY-mm-DD **
                    'checkout': '2019-10-26',
                    'hotel_name': 'Hotel Mawar',
                    'room_name': 'Superior Room',
                    'meal_type': 'Room Only',
                },
                {** Activity **
                    'resv': 'qwe123', ** PNR / Resv Code **
                    'checkin': '2019-10-24', ** YYYY-mm-DD **
                    'time_slot': '09:30:00 - 13:30:00',
                    'activity_title': 'KidsSTOP Singapore E-voucher',
                    'product_type': 'Weekday Admission',
                },
            ],
            'passenger': [
                {
                    'ticket_number': '12345678', ** airline/train only **
                    'name': '', **Mr. F_name L_name**
                    'pax_type': 'Elder', **Elder, Adult, Child, Infant**
                    'birth_date': '1993-08-17', ** YYYY-mm-dd **
                    'additional_info': ['Room: 1'],
                        **klo airline: baggage**,
                        **klo hotel: room apa?**,
                }
            ],
            'price_detail': [
                {
                    'name': **Passenger Name**,
                    'pax_type': 'ADT' **ADT, CHD, INF, YCD**,
                    'fare': 0,
                    'tax': 0,
                    'total': 0, ** fare + tax **
                }
            ],
        }
        '''
        values = {}
        if data.get('context'):
            values = json.loads(data['context']['json_content'])
            # values = [{
            #     'agent_id': 1,
            #     'type': 'hotel',
            #     'line': [
            #         {
            #             'resv': 'qwe123',
            #             'checkin': '2019-10-24',
            #             'checkout': '2019-10-26',
            #             'hotel_name': 'Hotel Mawar',
            #             'room_name': 'Superior Room',
            #             'meal_type': 'Room Only',
            #         },
            #     ],
            #     'passenger': [
            #         {
            #             'ticket_number': '',
            #             'name': 'Mr Vincentius Hadi',
            #             'pax_type': 'Adult',
            #             'birth_date': '1993-08-17',
            #             'additional_info': ['Room: 1', 'Special Req: Non Smoking Rooms'],
            #         }
            #     ],
            #     'price_detail': [
            #         {
            #             'name': 'Mr Vincentius Hadi',
            #             'pax_type': 'ADT',
            #             'fare': 50000,
            #             'tax': 1250,
            #             'total': 51250,
            #         }
            #     ],
            # }]

            values['agent_id'] = self.env['tt.agent'].search([('name', '=ilike', values['agent_name'])], limit=1)
        return {
            'doc_ids': False,
            'doc_model': 'tt.reservation.hotel',  # Can be set to as any model
            'doc_type': 'itin', #untuk judul report
            'docs': [values,],
            'date_now': fields.Date.today().strftime('%d %b %Y'),
            'currency_id': self.env.user.company_id.currency_id,
        }


class PrintoutBilling(models.AbstractModel):
    _name = 'report.tt_report_common.printout_billing'
    _description = 'Rodex Model'

    def last_billing(self, recs):
        a = {}
        for rec in recs:
            bill_id = self.env['tt.billing.statement'].search([('customer_parent_id', '=', rec.customer_parent_id.id),('id', '!=', rec.id)],
                                                              limit=1, order='date DESC')
            if bill_id:
                a.update({ rec.name: bill_id.date.strftime('%d/%m/%Y') })
            else:
                # Find lowest Invoice Date
                inv_obj = rec.invoice_ids.sorted(key=lambda x: x.confirmed_date)
                a.update({ rec.name: inv_obj[0].confirmed_date.strftime('%d/%m/%Y') })
        return a

    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' Rupiah'})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.billing.statement',
                'active_ids': docids
            }
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'last_billing': self.last_billing(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }


class PrintoutTopUp(models.AbstractModel):
    _name = 'report.tt_report_common.printout_topup'
    _description = 'Rodex Model'

    def compute_terbilang_from_objs(self, recs, currency_str='Rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: num2words(rec2.total) + ' ' + currency_str})
        return a

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('context'):
            internal_model_id = docids.pop(0)
            data['context'] = {
                'active_model': 'tt.billing.statement',
                'active_ids': docids
            }
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'terbilang': self.compute_terbilang_from_objs(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }
