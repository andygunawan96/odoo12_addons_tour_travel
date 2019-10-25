from odoo import models, fields, api
import datetime


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

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
        separator1 = ['', 'puluh', 'ratus']
        separator2 = ['', 'ribu', 'juta', 'miliar', 'triliun']

        n = int(amount)
        a = int(n / 10)
        sisa = n % 10

        amount_to_str = sisa and angka[sisa] + ' ' + separator1[separator_index] or ''
        amount_to_str = separator_index and amount_to_str or amount_to_str[:-1]

        if a:
            separator_index += 1
            if separator_index % 3 == 0:
                separator_index = 0
                separator_index2 += 1
                amount_to_str = separator2[separator_index2] + ' ' + amount_to_str

        if a != 0:
            amount_to_str = self.get_terbilang(a, separator_index, separator_index2) + ' ' + amount_to_str
        return amount_to_str

    def compute_terbilang_from_objs(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            a.update({rec2.name: self.compute_terbilang(rec2.total, currency_str)})
        return a

    def compute_terbilang(self, total, currency_str='rupiah'):
        separator2 = ['ribu', 'juta', 'miliar', 'triliun']
        terbilang = self.get_terbilang(total)
        ongoing_list = []
        for rec in terbilang.split(' '):
            if rec:
                ongoing_list.append(rec)
        new_list = []
        skip_idx = []
        for idx, rec in enumerate(ongoing_list):
            if idx in skip_idx:
                continue
            if rec == 'satu':
                if idx >= len(ongoing_list)-1:
                    new_list.append(rec)
                    continue
                if ongoing_list[idx + 1] == 'puluh':
                    if ongoing_list[idx + 2] in ["dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]:
                        new_list.append(ongoing_list[idx + 2])
                        new_list.append('belas')
                        skip_idx.append(idx + 2)
                    elif ongoing_list[idx + 2] == 'satu':
                        new_list.append('sebelas')
                        skip_idx.append(idx + 2)
                    skip_idx.append(idx + 1)
                elif ongoing_list[idx + 1] in ['ratus', 'ribu']:
                    new_list.append('se' + ongoing_list[idx + 1].lower() )
                    skip_idx.append(idx + 1)
                else:
                    new_list.append(rec)
            elif rec in separator2:
                if new_list[-1] not in separator2:
                    new_list.append(rec)
            else:
                new_list.append(rec)

        new_list.append(currency_str)
        return ' '.join(filter(None, new_list))

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

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
        separator1 = ['', 'puluh', 'ratus']
        separator2 = ['', 'ribu', 'juta', 'miliar', 'triliun']

        n = int(amount)
        a = int(n / 10)
        sisa = n % 10

        amount_to_str = sisa and angka[sisa] + ' ' + separator1[separator_index] or ''
        amount_to_str = separator_index and amount_to_str or amount_to_str[:-1]

        if a:
            separator_index += 1
            if separator_index % 3 == 0:
                separator_index = 0
                separator_index2 += 1
                amount_to_str = separator2[separator_index2] + ' ' + amount_to_str

        if a != 0:
            amount_to_str = self.get_terbilang(a, separator_index, separator_index2) + ' ' + amount_to_str
        return amount_to_str

    def compute_terbilang(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            terbilang = self.get_terbilang(rec2.amount_total)
            ongoing_list = terbilang.split(' ')
            new_list = []
            skip_idx = []
            for idx, rec in enumerate(ongoing_list):
                if idx in skip_idx:
                    continue
                if rec == 'satu':
                    if idx >= len(ongoing_list)-1:
                        continue
                    if ongoing_list[idx + 1] == 'puluh':
                        if ongoing_list[idx + 2] in ["dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]:
                            new_list.append(ongoing_list[idx + 2])
                            new_list.append('belas')
                            skip_idx.append(idx + 2)
                        elif ongoing_list[idx + 2] == 'satu':
                            new_list.append('sebelas')
                        else:
                            new_list.append('Se' + ongoing_list[idx + 1].lower())
                        skip_idx.append(idx + 1)
                    elif ongoing_list[idx + 1] in ['ratus', 'ribu']:
                        new_list.append('se' + ongoing_list[idx + 1].lower() )
                        skip_idx.append(idx + 1)
                else:
                    new_list.append(rec)

            new_list.append(currency_str)
            a.update({rec2.name: ' '.join(filter(None, new_list))})
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
            'terbilang': self.compute_terbilang(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
            'last_billing': self.last_billing(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }


class PrintoutTopUp(models.AbstractModel):
    _name = 'report.tt_report_common.printout_topup'
    _description = 'Rodex Model'

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]
        separator1 = ['', 'puluh', 'ratus']
        separator2 = ['', 'ribu', 'juta', 'miliar', 'triliun']

        n = int(amount)
        a = int(n / 10)
        sisa = n % 10

        amount_to_str = sisa and angka[sisa] + ' ' + separator1[separator_index] or ''
        amount_to_str = separator_index and amount_to_str or amount_to_str[:-1]

        if a:
            separator_index += 1
            if separator_index % 3 == 0:
                separator_index = 0
                separator_index2 += 1
                amount_to_str = separator2[separator_index2] + ' ' + amount_to_str

        if a != 0:
            amount_to_str = self.get_terbilang(a, separator_index, separator_index2) + ' ' + amount_to_str
        return amount_to_str

    def compute_terbilang(self, recs, currency_str='rupiah'):
        a = {}
        for rec2 in recs:
            terbilang = self.get_terbilang(rec2.total_with_fees)
            ongoing_list = terbilang.split(' ')
            new_list = []
            skip_idx = []
            for idx, rec in enumerate(ongoing_list):
                if idx in skip_idx:
                    continue
                if rec == 'satu':
                    if idx >= len(ongoing_list)-1:
                        continue
                    if ongoing_list[idx + 1] == 'puluh':
                        if ongoing_list[idx + 2] in ["dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]:
                            new_list.append(ongoing_list[idx + 2])
                            new_list.append('belas')
                            skip_idx.append(idx + 2)
                        elif ongoing_list[idx + 2] == 'satu':
                            new_list.append('sebelas')
                        else:
                            new_list.append('se' + ongoing_list[idx + 1].lower())
                        skip_idx.append(idx + 1)
                    elif ongoing_list[idx + 1] in ['ratus', 'ribu']:
                        new_list.append('se' + ongoing_list[idx + 1].lower() )
                        skip_idx.append(idx + 1)
                else:
                    new_list.append(rec)

            new_list.append(currency_str)
            a.update({rec2.name: ' '.join(filter(None, new_list))})
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
            'terbilang': self.compute_terbilang(
                self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }
