from odoo import api, fields, models, _

JOURNEY_TYPE = [
    ('dp', 'Departure'),
    ('rt', 'Return')
]

CLASS_OF_SERVICE = [
    ('economy', 'Economy'),
    ('Premium', 'Premium'),
    ('Business', 'Business'),
    ('first', 'First'),
]


class FlightSegment(models.Model):
    _name = 'flight.segment'

    journey_type = fields.Selection(JOURNEY_TYPE, 'Journey Type', default='DP')

    carrier_id = fields.Many2one('tt.transport.carrier', 'Airline', domain=[('provider_type_id.name', '=', 'Airline')])
    carrier_code = fields.Char('Flight Code', related='carrier_id.code', store=True)
    carrier_number = fields.Char('Flight Number')

    origin_id = fields.Many2one('tt.destinations', 'Origin', domain=[('provider_type_id.name', '=', 'Airline')])
    origin_terminal = fields.Char('Origin Terminal')

    destination_id = fields.Many2one('tt.destinations', 'Destination', domain=[('provider_type_id.name', '=', 'Airline')])
    destination_terminal = fields.Char('Destination Terminal')

    departure_date_fmt = fields.Datetime('Departure Date (FMT)')
    arrival_date_fmt = fields.Datetime('Arrival Date (FMT)')

    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')

    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Service Class')
    tour_pricelist_id = fields.Many2one('tt.reservation.tour.pricelist', 'Pricelist ID', readonly=True)
