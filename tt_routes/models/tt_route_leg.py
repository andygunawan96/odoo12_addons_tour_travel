from odoo import api, fields, models


class RouteSchedule(models.Model):
    _name = 'tt.route.schedule'
    _rec_name = 'Schedule'
    _description = 'Schedule'

    name = fields.Char('Name')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    origin = fields.Char('Origin')
    origin_utc = fields.Float('Origin UTC')
    departure_date = fields.Char('Departure Date')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    destination = fields.Char('Destination')
    destination_utc = fields.Char('Destination UTC')
    arrival_date = fields.Char('Arrival Date')


class RouteJourney(models.Model):
    _name = 'tt.route.journey'
    _rec_name = 'Journey'
    _description = 'Journey'

    name = fields.Char('Name')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    origin = fields.Char('Origin')
    origin_utc = fields.Float('Origin UTC')
    departure_time = fields.Char('Departure Time')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    destination = fields.Char('Destination')
    destination_utc = fields.Char('Destination UTC')
    arrival_time = fields.Char('Arrival Time')


class RouteSegment(models.Model):
    _name = 'tt.route.segment'
    _rec_name = 'Segment'
    _description = 'Segment'

    name = fields.Char('Name')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Transport Carrier Code')
    carrier_code = fields.Char('Carrier Code')
    carrier_number = fields.Char('Carrier Number')
    operating_airline_code = fields.Char('Operating Airline Code')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    origin = fields.Char('Origin')
    origin_utc = fields.Float('Origin UTC')
    departure_time = fields.Char('Departure Time')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    destination = fields.Char('Destination')
    destination_utc = fields.Char('Destination UTC')
    arrival_time = fields.Char('Arrival Time')


class RouteLeg(models.Model):
    _name = 'tt.route.leg'
    _rec_name = 'Leg'
    _description = 'Leg'

    name = fields.Char('Name')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Transport Carrier Code')
    carrier_code = fields.Char('Carrier Code')
    carrier_number = fields.Char('Carrier Number')
    operating_airline_code = fields.Char('Operating Airline Code')
    origin_id = fields.Many2one('tt.destinations', 'Origin')
    origin = fields.Char('Origin')
    origin_utc = fields.Float('Origin UTC')
    departure_time = fields.Char('Departure Time')
    destination_id = fields.Many2one('tt.destinations', 'Destination')
    destination = fields.Char('Destination')
    destination_utc = fields.Char('Destination UTC')
    arrival_time = fields.Char('Arrival Time')


class RouteFare(models.Model):
    _name = 'tt.route.fare'
    _rec_name = 'Fare'
    _description = 'Fare'

    name = fields.Char('Name')
    cabin_class = fields.Char('Cabin Class')
    class_of_service = fields.Char('Class of Service')


class RoutePaxFare(models.Model):
    _name = 'tt.route.pax.fare'
    _rec_name = 'Pax Fare'
    _description = 'Pax Fare'

    name = fields.Char('Name')
    pax_type = fields.Char('Pax Type')


class RouteServiceCharge(models.Model):
    _name = 'tt.route.service.charge'
    _rec_name = 'Service Charge'
    _description = 'Service Charge'

    name = fields.Char('Name')
