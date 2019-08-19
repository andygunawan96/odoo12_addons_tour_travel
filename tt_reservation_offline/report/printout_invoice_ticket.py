from odoo import models, api
import pytz
import datetime


class PrintoutInvoiceTicket(models.AbstractModel):
    _name = 'report.tt_reservation_offline.printout_invoice_ticket'

    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    def invoice_line_select(self, provider_type, ids):
        if provider_type == 'train':
            line_obj = self.env['tt.reservation.offline.lines'].search([('booking_id', 'in', ids)]).read()
            return self.get_train_line(line_obj)
        else:
            return self.get_line(ids)

    def get_train_line(self, line_obj):
        destination_env = self.env['tt.destinations'].sudo()
        print(self.env.user.tz)
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        line_list = []
        for line in line_obj:
            vals = {
                'pnr': line['pnr'],
                'carrier_name': line['carrier_id'][1],
                'carrier_code': line['carrier_code'],
                'departure_date': datetime.datetime.strptime(str(line['departure_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
                'return_date': datetime.datetime.strptime(str(line['return_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
                'origin_id': line['origin_id'],
                'origin_name': line['origin_id'][1],
                'origin_city': destination_env.browse(line['origin_id'][0]).city,
                'destination_id': line['destination_id'],
                'destination_name': line['destination_id'][1],
                'destination_city': destination_env.browse(line['destination_id'][0]).city,
                'subclass': line['subclass']
            }
            if line['class_of_service'] == 'eco':
                vals['class_of_service'] = 'EKONOMI'
            if line['class_of_service'] == 'pre':
                vals['class_of_service'] = 'BISNIS'
            if line['class_of_service'] == 'bus':
                vals['class_of_service'] = 'EKSEKUTIF'
            line_list.append(vals)
        return line_list

    def get_line(self, booking_id):
        self.env['tt.reservation.offline.lines'].search([('booking_id', 'in', booking_id)]).read()
        return self.env['tt.reservation.offline.lines'].search([('booking_id', 'in', booking_id)]).read()

    def get_passenger(self, booking_id):
        passenger_dict = self.env['tt.reservation.offline.passenger'].search([('booking_id', 'in', booking_id)]).read()
        passenger_list = []
        for psg in passenger_dict:
            index = 0
            name_found = False
            if passenger_list:
                for idx, rec in enumerate(passenger_list):
                    if rec['passenger'] == psg['passenger_id'][1]:
                        name_found = True
                        index = idx
            if name_found:
                passenger_list[index]['ticket_number'] += ', ' + psg['ticket_number']
            else:
                passenger_vals = {
                    'ticket_number': psg['ticket_number'],
                    'seat': psg['seat'],
                    'passenger': psg['passenger_id'][1],
                    'pax_type': psg['pax_type']
                }
                if passenger_vals['pax_type'] == 'ADT':
                    passenger_vals['pax_type'] = 'Adult'
                elif passenger_vals['pax_type'] == 'CHD':
                    passenger_vals['pax_type'] = 'Child'
                elif passenger_vals['pax_type'] == 'INF':
                    passenger_vals['pax_type'] = 'Infant'
                passenger_list.append(passenger_vals)
        return passenger_list

    def get_passenger_amount(self, booking_id):
        adult = 0
        child = 0
        infant = 0
        passenger_dict = self.env['tt.reservation.offline.passenger'].search([('booking_id', 'in', booking_id)]).read()
        for psg in passenger_dict:
            if psg['pax_type'] == 'ADT' or psg['pax_type'] == 'adt':
                adult += 1
            if psg['pax_type'] == 'CHD' or psg['pax_type'] == 'chd':
                child += 1
            if psg['pax_type'] == 'INF' or psg['pax_type'] == 'inf':
                infant += 1
        vals = {
            'adult': adult,
            'child': child,
            'infant': infant
        }
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.invoice_line_select(data['provider_type'], data['ids'])
        print(docs)
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.offline'].browse(data['ids']),
            'line_ids': docs,
            'line_length': len(self.env['tt.reservation.offline.lines'].search([('booking_id', 'in', data['ids'])])),
            'passenger_ids': self.get_passenger(data['ids']),
            'passenger_amount': self.get_passenger_amount(data['ids'])
        }
