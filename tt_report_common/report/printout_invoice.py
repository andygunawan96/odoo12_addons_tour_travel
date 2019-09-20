from odoo import models, fields, api
import datetime


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
        else:
            for rec2 in rec.segment_ids:
                if not a.get(rec2.pnr):
                    a[rec2.pnr] = {'paxs': paxs, 'descs': [], 'total': rec.total}
                a[rec2.pnr]['descs'].append(rec2.origin_id.name + ' - ' + rec2.destination_id.name + '; ' +
                                            rec2.departure_date + ' - ' + rec2.arrival_date + '; ' +
                                            rec2.carrier_id.name + ' ' + rec2.name)
        return a

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
        separator1 = ['', 'Puluh', 'Ratus']
        separator2 = ['', 'Ribu', 'Juta', 'Miliar', 'Triliun']

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

    def compute_terbilang(self, recs, currency_str='Rupiah'):
        a = {}
        for rec2 in recs:
            terbilang = self.get_terbilang(rec2.total)
            ongoing_list = terbilang.split(' ')
            new_list = []
            skip_idx = []
            for idx, rec in enumerate(ongoing_list):
                if idx in skip_idx:
                    continue
                if rec == 'Satu':
                    if idx >= len(ongoing_list)-1:
                        continue
                    if ongoing_list[idx + 1] == 'Puluh':
                        if ongoing_list[idx + 2] in ["Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan"]:
                            new_list.append(ongoing_list[idx + 2])
                            new_list.append('Belas')
                            skip_idx.append(idx + 2)
                        elif ongoing_list[idx + 2] == 'Satu':
                            new_list.append('Sebelas')
                        else:
                            new_list.append('Se' + ongoing_list[idx + 1].lower())
                        skip_idx.append(idx + 1)
                    elif ongoing_list[idx + 1] in ['Ratus', 'Ribu']:
                        new_list.append('Se' + ongoing_list[idx + 1].lower() )
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
            for rec3 in rec.passenger_ids:
                a = {'fare': 0, 'tax': 0, 'name': rec3.name, 'pax_type': 'ADT'}
                for rec2 in rec3.cost_service_charge_ids:
                    if rec2.charge_code == 'tax':
                        a['tax'] += rec2.amount
                    elif rec2.charge_type == 'RAC':
                        pass
                    else:
                        a['fare'] += rec2.amount
                    a['pax_type'] = rec2.pax_type
                values[rec.id].append(a)
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
            'price_lines': values,
            'date_now': fields.Date.today()
        }


class PrintoutBilling(models.AbstractModel):
    _name = 'report.tt_report_common.printout_billing'
    _description = 'Rodex Model'

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
        separator1 = ['', 'Puluh', 'Ratus']
        separator2 = ['', 'Ribu', 'Juta', 'Miliar', 'Triliun']

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

    def compute_terbilang(self, recs, currency_str='Rupiah'):
        a = {}
        for rec2 in recs:
            terbilang = self.get_terbilang(rec2.amount_total)
            ongoing_list = terbilang.split(' ')
            new_list = []
            skip_idx = []
            for idx, rec in enumerate(ongoing_list):
                if idx in skip_idx:
                    continue
                if rec == 'Satu':
                    if idx >= len(ongoing_list)-1:
                        continue
                    if ongoing_list[idx + 1] == 'Puluh':
                        if ongoing_list[idx + 2] in ["Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan"]:
                            new_list.append(ongoing_list[idx + 2])
                            new_list.append('Belas')
                            skip_idx.append(idx + 2)
                        elif ongoing_list[idx + 2] == 'Satu':
                            new_list.append('Sebelas')
                        else:
                            new_list.append('Se' + ongoing_list[idx + 1].lower())
                        skip_idx.append(idx + 1)
                    elif ongoing_list[idx + 1] in ['Ratus', 'Ribu']:
                        new_list.append('Se' + ongoing_list[idx + 1].lower() )
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


class PrintoutTopUp(models.AbstractModel):
    _name = 'report.tt_report_common.printout_topup'
    _description = 'Rodex Model'

    def get_terbilang(self, amount, separator_index=0, separator_index2=0):
        angka = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
        separator1 = ['', 'Puluh', 'Ratus']
        separator2 = ['', 'Ribu', 'Juta', 'Miliar', 'Triliun']

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

    def compute_terbilang(self, recs, currency_str='Rupiah'):
        a = {}
        for rec2 in recs:
            terbilang = self.get_terbilang(rec2.total_with_fees)
            ongoing_list = terbilang.split(' ')
            new_list = []
            skip_idx = []
            for idx, rec in enumerate(ongoing_list):
                if idx in skip_idx:
                    continue
                if rec == 'Satu':
                    if idx >= len(ongoing_list)-1:
                        continue
                    if ongoing_list[idx + 1] == 'Puluh':
                        if ongoing_list[idx + 2] in ["Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan"]:
                            new_list.append(ongoing_list[idx + 2])
                            new_list.append('Belas')
                            skip_idx.append(idx + 2)
                        elif ongoing_list[idx + 2] == 'Satu':
                            new_list.append('Sebelas')
                        else:
                            new_list.append('Se' + ongoing_list[idx + 1].lower())
                        skip_idx.append(idx + 1)
                    elif ongoing_list[idx + 1] in ['Ratus', 'Ribu']:
                        new_list.append('Se' + ongoing_list[idx + 1].lower() )
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
