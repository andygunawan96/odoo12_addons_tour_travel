from odoo import fields, models, api
from io import StringIO
from werkzeug.wrappers import Response
from datetime import datetime, timedelta
import base64
import csv

ACC_PRODUCT_LIST = [('tt.reservation.airline', 'Reservation Airline'), ('tt.reservation.activity', 'Reservation Activity'),
                    ('tt.reservation.event', 'Reservation Event'), ('tt.reservation.hotel', 'Reservation Hotel'),
                    ('tt.reservation.passport', 'Reservation Passport'), ('tt.reservation.periksain', 'Reservation Periksain'),
                    ('tt.reservation.phc', 'Reservation PHC'), ('tt.reservation.ppob', 'Reservation PPOB'),
                    ('tt.reservation.tour', 'Reservation Tour'), ('tt.reservation.train', 'Reservation Train'),
                    ('tt.reservation.visa', 'Reservation Visa'), ('tt.refund', 'Refund'), ('tt.reschedule', 'Reschedule'),
                    ('tt.reschedule.periksain', 'Reschedule Periksain'), ('tt.reschedule.phc', 'Reschedule PHC'), ('tt.top.up', 'Top Up')]


class AccGenerateCSVWizard(models.TransientModel):
    _name = 'tt.accounting.generate.csv.wizard'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    is_all_models = fields.Boolean('All Products')
    is_all_reservations = fields.Boolean('Only Reservation Products')
    specific_product = fields.Selection(ACC_PRODUCT_LIST, 'Specific Product', default='tt.reservation.airline')

    @api.onchange('is_all_models')
    def _onchange_is_all_models(self):
        if self.is_all_models:
            self.is_all_reservations = False

    @api.onchange('is_all_reservations')
    def _onchange_is_all_reservations(self):
        if self.is_all_reservations:
            self.is_all_models = False

    def generate_report_csv(self):
        search_crit = [('create_date', '>', self.date_from.strftime('%Y-%m-%d')), ('create_date', '<', (self.date_to + timedelta(days=1)).strftime('%Y-%m-%d')),
                       ('res_model', '!=', ''), ('res_id', '!=', 0)]
        if self.is_all_reservations:
            search_crit.append(('res_model', 'not in', ['tt.refund', 'tt.reschedule', 'tt.reschedule.periksain', 'tt.reschedule.phc', 'tt.top.up']))
        elif not self.is_all_models:
            search_crit.append(('res_model', '=', self.specific_product))

        queue_list = self.env['tt.accounting.queue'].search(search_crit)
        final_list = []
        for rec in queue_list:
            data_dict = rec.get_request_data()
            if data_dict.get('passenger_pricings'):
                for pax in data_dict['passenger_pricings']:
                    for pax_pnr in pax['pnr_list']:
                        final_list.append({
                            'booking_type': '%s %s' % (data_dict['category'], data_dict['provider_type_name']),
                            'carrier_name': pax_pnr.get('carrier_name', ''),
                            'agent_type': data_dict['agent_type'],
                            'agent_name': data_dict['agent_name'],
                            'customer_parent_type': data_dict['customer_parent_type'],
                            'customer_parent_name': data_dict['customer_parent_name'],
                            'created_by': data_dict['create_by'],
                            'issued_by': data_dict['issued_by'],
                            'issued_date': data_dict['issued_date'],
                            'departure_date': pax_pnr.get('departure_date', ''),
                            'origin': pax_pnr.get('origin', ''),
                            'destination': pax_pnr.get('destination', ''),
                            'agent_email': data_dict['agent_email'],
                            'provider': pax_pnr['provider'],
                            'order_number': data_dict['order_number'],
                            'adult': data_dict['ADT'],
                            'child': data_dict['CHD'],
                            'infant': data_dict['INF'],
                            'state': data_dict['state'],
                            'pnr': pax_pnr['pnr'],
                            'ledger_reference': data_dict['order_number'],
                            'booking_state': data_dict['state'],
                            'vendor': pax_pnr['provider'],
                            'ticket_number': pax_pnr['ticket_number'],
                            'pax_name': pax['passenger_name'],
                            'currency': pax_pnr['currency_code'],
                            'agent_nta_amount': pax_pnr['agent_nta'],
                            'agent_commission': pax_pnr['agent_commission'],
                            'commission_booker': data_dict['commission_booker'],
                            'upsell': pax_pnr['upsell'],
                            'ho_nta_amount': pax_pnr['ho_nta'],
                            'total_commission': pax_pnr['total_commission'],
                            'ppn': pax_pnr['tax'],
                            'grand_total': pax_pnr['grand_total'],
                        })
            else:
                final_list.append({
                    'booking_type': data_dict['category'],
                    'carrier_name': '',
                    'agent_type': data_dict['agent_type'],
                    'agent_name': data_dict['agent_name'],
                    'customer_parent_type': data_dict.get('customer_parent_type', ''),
                    'customer_parent_name': data_dict.get('customer_parent_name', ''),
                    'created_by': data_dict['create_by'],
                    'issued_by': '',
                    'issued_date': '',
                    'departure_date': '',
                    'origin': '',
                    'destination': '',
                    'agent_email': data_dict['agent_email'],
                    'provider': '',
                    'order_number': data_dict['order_number'],
                    'adult': 0,
                    'child': 0,
                    'infant': 0,
                    'state': data_dict['state'],
                    'pnr': data_dict.get('pnr', ''),
                    'ledger_reference': data_dict['order_number'],
                    'booking_state': data_dict['state'],
                    'vendor': '',
                    'ticket_number': '',
                    'pax_name': '',
                    'currency': data_dict['currency'],
                    'agent_nta_amount': data_dict.get('agent_nta', 0),
                    'agent_commission': data_dict.get('agent_commission', 0),
                    'commission_booker': 0,
                    'upsell': data_dict.get('upsell', 0),
                    'ho_nta_amount': data_dict.get('ho_nta', 0),
                    'total_commission': data_dict.get('total_commission', 0),
                    'ppn': data_dict.get('tax', 0),
                    'grand_total': data_dict.get('grand_total', 0),
                })

        def generate():
            data = StringIO()
            w = csv.writer(data, delimiter=';')

            # write header
            if final_list:
                w.writerow(tuple(final_list[0].keys()))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

            # write each item
            for single_dict in final_list:
                val_list = []
                for item in single_dict.values():
                    val_list.append(item)
                w.writerow(tuple(val_list))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        # stream the response as the data is generated
        response = Response(generate(), mimetype='text/csv')
        # add a filename
        res = self.env['tt.upload.center.wizard'].upload_file_api(
            {
                'filename': 'Accounting Report.csv',
                'file_reference': 'Accounting Report',
                'file': base64.b64encode(response.data),
                'delete_date': datetime.today() + timedelta(minutes=10)
            },
            {
                'co_agent_id': self.env.user.agent_id.id,
                'co_uid': self.env.user.id,
            }
        )
        upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
        url = {
            'type': 'ir.actions.act_url',
            'name': "Accounting Report",
            'target': 'new',
            'url': upc_id.url,
        }
        return url
