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

    def calc_segments(self, rec, paxs):
        a = {}
        if rec._name == 'tt.reservation.hotel':
            for rec2 in rec.room_detail_ids:
                if not a.get(rec2.issued_name):
                    a[rec2.issued_name] = {'paxs': paxs, 'descs': [], 'total': 0}
                a[rec2.issued_name]['descs'].append( 'Hotel: ' + rec.hotel_name + '; Room: ' + rec2.room_name + ' ' + str(rec2.room_type) )
                a[rec2.issued_name]['total'] += rec2.sale_price
        elif rec._name == 'tt.reservation.airline':
            for rec2 in rec.segment_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'paxs': paxs, 'descs': [], 'total': rec.total}
                a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
                                            rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
                                            rec2.carrier_id.name + ' ' + rec2.name)
        elif rec._name == 'tt.reservation.activity':
            if not a.get(rec.pnr):
                a[rec.pnr] = {'paxs': paxs, 'descs': [], 'total': rec.total}
            temp_desc = (rec.activity_id.name if rec.activity_id.name else '') + ' - ' + \
                        (rec.activity_product_id.name if rec.activity_product_id.name else '') + '; ' + \
                        (str(rec.visit_date) if rec.visit_date else '')
            if rec.timeslot:
                temp_desc += ' ' + str(rec.timeslot) + '; '
            else:
                temp_desc += '; '
            a[rec.pnr]['descs'].append(temp_desc)
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
            terbilang = self.get_terbilang(rec2.total)
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
        # Print dari BackEnd bisa digunakan untuk Resv maupun invoice
        if not data.get('context'):
            data['context'] = {
                'active_model': 'tt.reservation.airline',
                'active_ids': docids
            }
        values = {}
        for rec in self.env[data['context']['active_model']].browse(data['context']['active_ids']):
            values[rec.id] = []
            for rec2 in rec.invoice_line_ids:
                resv_obj = self.env[rec2.res_model_resv].browse(rec2.res_id_resv)
                values[rec.id] = self.calc_segments(resv_obj, resv_obj.passenger_ids)
        # terbilang = self.get_terbilang(0)
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'inv_lines': values,
            'terbilang': self.compute_terbilang(self.env[data['context']['active_model']].browse(data['context']['active_ids'])),
        }


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
