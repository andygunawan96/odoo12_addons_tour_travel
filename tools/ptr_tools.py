import json, copy
import logging
from odoo.http import request
from datetime import datetime, timedelta
import base64

_logger = logging.getLogger(__name__)


class PointerTools:
    def __init__(self, provider_type):
        self.provider_type = provider_type

    def request_webhook_issued(self, book_obj):
        ## AMBIL INVOICE
        invoice_url = ''
        for rec in book_obj.invoice_line_ids:
            if rec.invoice_id.state != 'cancel':
                inv_data = rec.invoice_id.print_invoice()
                if inv_data.get('url'):
                    invoice_url += inv_data['url']
                else:
                    _logger.error('Invoice not found')
        ticket_number = ''
        try:
            for provider_booking_obj in book_obj.provider_bookings_ids:
                for ticket_obj in provider_booking_obj.ticket_ids:
                    if hasattr(ticket_obj,'ticket_number'):
                        if ticket_obj.ticket_number:
                            if ticket_number:
                                ticket_number += ', '
                            ticket_number += ticket_obj.ticket_number
                    break
                break
        except:
            _logger.error('NO TICKET NUMBER')
        return {
            "amount": book_obj.total,
            "method": 'POST',
            "status": "issued" if book_obj.state in ['issued', 'done'] else '',
            "ticketcode": book_obj.pnr,
            "bookcode": book_obj.name,
            "id_pegawai": book_obj.third_party_id.third_party_data['callback']['id_pegawai'],
            "name": book_obj.contact_name,
            "email": book_obj.contact_email,
            "issuedimg": invoice_url,
            "ticket_number": ticket_number,
            "urlupdateissued": json.loads(book_obj.third_party_ids[0].third_party_data)['urlupdateissued'] if book_obj.third_party_ids else '',
        }

    def request_webhook_booked(self, book_obj):
        res = {}
        ## ASUMSI PASTI DATA HANYA 1
        if self.provider_type == 'train':
            res = self.train_booked(book_obj)
        elif self.provider_type == 'airline':
            res = self.airline_booked(book_obj)
        elif self.provider_type == 'hotel':
            res = self.hotel_booked(book_obj)
        return res

    def train_booked(self, book_obj):
        train_carrier_name = ''
        train_carrier_number = ''
        train_seat_number = ''
        train_departure_date = ''
        train_arrival_date = ''
        train_class = ''
        for provider_booking_obj in book_obj.provider_booking_ids:
            for journey_obj in provider_booking_obj.journey_ids:
                for seat_obj in journey_obj.seat_ids:
                    if train_seat_number:
                        train_seat_number += ', '
                    train_seat_number += seat_obj.seat and seat_obj.seat.split(',')[1] or ''
                    break
                if train_carrier_name:
                    train_carrier_name += ', '
                if journey_obj.carrier_name not in train_carrier_name:
                    train_carrier_name += journey_obj.carrier_name and journey_obj.carrier_name or ''

                if train_carrier_number:
                    train_carrier_number += ', '
                if journey_obj.carrier_number not in train_carrier_number:
                    train_carrier_name += journey_obj.carrier_number and journey_obj.carrier_number or ''

                if journey_obj.cabin_class == 'K':
                    if 'Economy' not in train_class:
                        if train_class:
                            train_class += ', '
                        train_class += 'Economy'
                elif journey_obj.cabin_class == 'E':
                    if 'Executive' not in train_class:
                        if train_class:
                            train_class += ', '
                        train_class += 'Executive'
                elif journey_obj.cabin_class == 'B':
                    if 'Business' not in train_class:
                        if train_class:
                            train_class += ', '
                        train_class += 'Business'
                break

            if train_departure_date:
                train_departure_date += ', '
            train_departure_date += provider_booking_obj.departure_date and provider_booking_obj.departure_date or ''

            if train_arrival_date:
                train_arrival_date += ', '
            train_arrival_date += provider_booking_obj.arrival_date and provider_booking_obj.arrival_date or ''
            break

        train_passenger_title = ''
        train_passenger_name = ''
        train_identity = ''
        for passenger_obj in book_obj.passenger_ids:
            if train_passenger_title:
                train_passenger_title += ', '
            train_passenger_title += passenger_obj.title and passenger_obj.title or ''
            if train_passenger_name:
                train_passenger_name += ', '
            train_passenger_name += passenger_obj.name and passenger_obj.name or ''
            if train_identity:
                train_identity += ', '
            train_identity += passenger_obj.identity_number and passenger_obj.identity_number or ''
            break
        res = {
            "document_key": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('document_key') if book_obj.third_party_ids else '',
            "id_pegawai": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('id_pegawai') if book_obj.third_party_ids else '',
            "method": 'POST',
            "origin": book_obj.origin_id.code,
            "cityorigin": "%s %s" % (book_obj.origin_id.name, book_obj.origin_id.city),
            "destination": book_obj.destination_id.code,
            "citydestination": "%s %s" % (book_obj.destination_id.name, book_obj.destination_id.city),
            "bookcode": book_obj.name,
            "trainname": train_carrier_name,
            "trainno": train_carrier_number,
            "seatno": train_seat_number,
            "datedepart": train_departure_date,
            "datearrive": train_arrival_date,
            "class": train_class,
            "booktimelimit": book_obj.hold_date,
            "bookingimg": '',
            "amount": book_obj.total,
            "maxprice": json.loads(book_obj.third_party_ids[0].third_party_data).get('max_price', '') if book_obj.third_party_ids else '',
            "status": book_obj.state,
            "title": train_passenger_title,
            "name": train_passenger_name,
            "nik": train_identity,
            "telp": book_obj.contact_phone,
            "email": book_obj.contact_email,
            "urldetail": '%s/train/booking/%s' % (book_obj.ho_id.redirect_url_signup, base64.b64encode(book_obj.name.encode()).decode('utf-8')),
            "urlsavebook": json.loads(book_obj.third_party_ids[0].third_party_data)['urlsavebook'] if book_obj.third_party_ids else '',
        }
        return res

    def airline_booked(self, book_obj):
        airline_passenger_title = ''
        airline_passenger_name = ''
        airline_identity = ''
        for passenger_obj in book_obj.passenger_ids:
            if airline_passenger_title:
                airline_passenger_title += ', '
            airline_passenger_title += passenger_obj.title and passenger_obj.title or ''
            if airline_passenger_name:
                airline_passenger_name += ', '
            airline_passenger_name += passenger_obj.name and passenger_obj.name or ''
            if airline_identity:
                airline_identity += ', '
            airline_identity += passenger_obj.identity_number and passenger_obj.identity_number or ''
            break

        airline_cabin_class = ''
        airline_plane = ''
        airline_flight_number = ''
        airline_origin = ''
        airline_origin_city = ''
        airline_destination = ''
        airline_destination_city = ''
        airline_departure_date = ''
        airline_arrival_date = ''

        for provider_booking_obj in book_obj.provider_booking_ids:
            for journey_obj in provider_booking_obj.journey_ids:
                for segment_obj in journey_obj.segment_ids:
                    ## CLASS
                    if segment_obj.cabin_class == 'Y':
                        if 'Economy' not in airline_cabin_class:
                            if airline_cabin_class:
                                airline_cabin_class += ', '
                            airline_cabin_class += 'Economy'
                    elif segment_obj.cabin_class == 'W':
                        if 'Premium Economy' not in airline_cabin_class:
                            if airline_cabin_class:
                                airline_cabin_class += ', '
                            airline_cabin_class += 'Premium Economy'
                    elif segment_obj.cabin_class == 'C':
                        if 'Business' not in airline_cabin_class:
                            if airline_cabin_class:
                                airline_cabin_class += ', '
                            airline_cabin_class += 'Business'
                    elif segment_obj.cabin_class == 'F':
                        if 'First Class' not in airline_cabin_class:
                            if airline_cabin_class:
                                airline_cabin_class += ', '
                            airline_cabin_class += 'First Class'

                    if segment_obj.carrier_id:
                        if segment_obj.carrier_id.name not in airline_plane:
                            if airline_plane:
                                airline_plane += ', '
                            airline_plane += segment_obj.carrier_id.name
                    if "%s%s" % (segment_obj.carrier_code, segment_obj.carrier_number) not in airline_flight_number:
                        if airline_flight_number:
                            airline_flight_number += ', '
                        airline_flight_number += "%s%s" % (segment_obj.carrier_code, segment_obj.carrier_number)
                    break
                if journey_obj.departure_date not in airline_departure_date:
                    if airline_departure_date:
                        airline_departure_date += ', '
                    airline_departure_date += journey_obj.departure_date

                if journey_obj.arrival_date not in airline_arrival_date:
                    if airline_arrival_date:
                        airline_arrival_date += ', '
                    airline_arrival_date += journey_obj.arrival_date
                break
            if provider_booking_obj.origin_id:
                if provider_booking_obj.origin_id.code not in airline_origin:
                    if airline_origin:
                        airline_origin += ', '
                    airline_origin += provider_booking_obj.origin_id.code
                    if airline_origin_city:
                        airline_origin_city += ', '
                    airline_origin_city += provider_booking_obj.origin_id.name

            if provider_booking_obj.destination_id:
                if provider_booking_obj.destination_id.code not in airline_destination:
                    if airline_destination:
                        airline_destination += ', '
                    airline_destination += provider_booking_obj.destination_id.code
                    if airline_destination_city:
                        airline_destination_city += ', '
                    airline_destination_city += provider_booking_obj.destination_id.name
            break

        res = {
            "document_key": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('document_key') if book_obj.third_party_ids else '',
            "id_pegawai": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('id_pegawai') if book_obj.third_party_ids else '',
            "method": 'POST',
            "title": airline_passenger_title,
            "name": airline_passenger_name,
            "nik": airline_identity,
            "telp": book_obj.contact_phone,
            "email": book_obj.contact_email,
            "class": airline_cabin_class,
            "maxprice": json.loads(book_obj.third_party_ids[0].third_party_data).get('max_price','') if book_obj.third_party_ids else '',
            "airlinename": airline_plane,
            "numberflight": airline_flight_number,
            "origin": airline_origin,
            "cityorigin": airline_origin_city,
            "destination": airline_destination,
            "citydestination": airline_destination_city,
            "bookcode": book_obj.name,
            "datedepart": airline_departure_date,
            "datearrive": airline_arrival_date,
            "amount": book_obj.total,
            "status": book_obj.state,
            "urldetail": '%s/airline/booking/%s' % (book_obj.ho_id.redirect_url_signup, base64.b64encode(book_obj.name.encode()).decode('utf-8')),
            "booktimelimit": book_obj.hold_date,
            "bookingimg": '',
            "urlsavebook": json.loads(book_obj.third_party_ids[0].third_party_data)['urlsavebook'] if book_obj.third_party_ids else '',
        }
        return res

    def hotel_booked(self, book_obj):
        hotel_passenger_name = ''
        hotel_passenger_title = ''
        hotel_passenger_identity = ''
        for passenger_obj in book_obj.passenger_ids:
            if hotel_passenger_title:
                hotel_passenger_title += ', '
            hotel_passenger_title += passenger_obj.title and passenger_obj.title or ''
            if hotel_passenger_name:
                hotel_passenger_name += ', '
            hotel_passenger_name += passenger_obj.name and passenger_obj.name or ''
            if hotel_passenger_identity:
                hotel_passenger_identity += ', '
            hotel_passenger_identity += passenger_obj.identity_number and passenger_obj.identity_number or ''
            break
        res = {
            "document_key": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('document_key') if book_obj.third_party_ids else '',
            "id_pegawai": json.loads(book_obj.third_party_ids[0].third_party_data)['callback'].get('id_pegawai') if book_obj.third_party_ids else '',
            "method": 'POST',
            "city": book_obj.hotel_city,
            "datefrom": book_obj.checkin_date,
            "dateto": book_obj.checkout_date,
            "countnight": book_obj.nights,
            "countperson": len(book_obj.passenger_ids),
            "countroom": book_obj.room_count,
            "bookcode": book_obj.name,
            "hotelname": book_obj.hotel_name,
            "roomname": book_obj.room_detail_ids[0].room_name,
            "class": json.loads(book_obj.third_party_ids[0].third_party_data).get('max_hotel_stars', 'all') if book_obj.third_party_ids else '',
            "booktimelimit": book_obj.hold_date,
            "bookingimg": '',
            "amount": book_obj.total,
            "maxprice": json.loads(book_obj.third_party_ids[0].third_party_data).get('max_price','') if book_obj.third_party_ids else '',
            "status": book_obj.state,
            "title": hotel_passenger_title,
            "name": hotel_passenger_name,
            "nik": hotel_passenger_identity,
            "telp": book_obj.contact_phone,
            "email": book_obj.contact_email,
            "urldetail": '%s/hotel/booking/%s' % (book_obj.ho_id.redirect_url_signup, base64.b64encode(book_obj.name.encode()).decode('utf-8')),
            "urlsavebook": json.loads(book_obj.third_party_ids[0].third_party_data)['urlsavebook'] if book_obj.third_party_ids else '',
        }
        return res
