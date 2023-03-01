from odoo import models, api
import pytz
import datetime
from datetime import timedelta


class PrintoutInvoiceTicket(models.AbstractModel):
    _name = 'report.tt_reservation_groupbooking.printout_invoice_ticket'
    _description = 'Group Booking Printout Invoice Ticket'
    """Abstract Model for report template.

        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
        """

    def invoice_line_select(self, provider_type, ids):
        if provider_type == 'airline':
            line_obj = self.env['tt.reservation.groupbooking.lines'].search([('booking_id', 'in', ids)]).read()
            return self.get_airline_vals_list(line_obj)
        if provider_type == 'train':
            line_obj = self.env['tt.reservation.groupbooking.lines'].search([('booking_id', 'in', ids)]).read()
            return self.get_train_line(line_obj)
        else:
            return self.get_line(ids)

    def get_airline_vals_list(self, line_obj):
        line_list = []
        for line in line_obj:
            found = False
            for val in line_list:
                if val['pnr'] in line['pnr']:
                    found = True
                    val['vals_list'].append(self.get_airline_line(line))
                    break
            if not found:
                vals_list = []
                line_vals = {
                    'pnr': line['pnr'],
                    'vals_list': vals_list,
                }
                line_vals['vals_list'].append(self.get_airline_line(line))
                line_list.append(line_vals)
        return line_list

    def get_airline_line(self, line):
        destination_env = self.env['tt.destinations'].sudo()
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        vals = {
            'carrier_name': line['carrier_id'][1],
            'carrier_code': line['carrier_code'],
            'carrier_number': line['carrier_number'],
            'departure_date': datetime.datetime.strptime(str(line['departure_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
            'arrival_date': datetime.datetime.strptime(str(line['arrival_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
            'origin_id': line['origin_id'],
            'origin_name': destination_env.browse(line['origin_id'][0]).name,
            'origin_city': destination_env.browse(line['origin_id'][0]).city,
            'origin_code': destination_env.browse(line['origin_id'][0]).code,
            'destination_id': line['destination_id'],
            'destination_name': destination_env.browse(line['destination_id'][0]).name,
            'destination_city': destination_env.browse(line['destination_id'][0]).city,
            'destination_code': destination_env.browse(line['destination_id'][0]).code,
            'subclass': line['subclass']
        }
        if line['class_of_service'] == 'eco':
            vals['class_of_service'] = 'Economy'
        if line['class_of_service'] == 'pre':
            vals['class_of_service'] = 'Premium Economy'
        if line['class_of_service'] == 'bus':
            vals['class_of_service'] = 'Business'
        return vals

    def get_train_line(self, line_obj):
        destination_env = self.env['tt.destinations'].sudo()
        tz = pytz.timezone(self.env.user.tz) or pytz.utc
        line_list = []
        for line in line_obj:
            vals = {
                'pnr': line['pnr'],
                'carrier_name': line['carrier_id'][1],
                'carrier_code': line['carrier_code'],
                'departure_date': datetime.datetime.strptime(str(line['departure_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
                'arrival_date': datetime.datetime.strptime(str(line['arrival_date']), "%Y-%m-%d %H:%M:%S").astimezone(tz),
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
        self.env['tt.reservation.groupbooking.lines'].search([('booking_id', 'in', booking_id)]).read()
        return self.env['tt.reservation.groupbooking.lines'].search([('booking_id', 'in', booking_id)]).read()

    def get_passenger(self, booking_id):
        passenger_dict = self.env['tt.reservation.passenger.groupbooking'].search([('booking_id', 'in', booking_id)]).read()
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
        passenger_dict = self.env['tt.reservation.passenger.groupbooking'].search([('booking_id', 'in', booking_id)]).read()
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
        vals = {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': self.env['tt.reservation.groupbooking'].browse(data['ids']),
            'line_ids': docs,
            'passenger_ids': self.get_passenger(data['ids']),
            'passenger_amount': self.get_passenger_amount(data['ids'])
        }
        if data['provider_type'] == 'airline':
            vals.update({
                'line_length': len([i for i in docs])
            })
        else:
            vals.update({
                'line_length': len(self.env['tt.reservation.groupbooking.lines'].search([('booking_id', 'in', data['ids'])])),
            })
        return vals
