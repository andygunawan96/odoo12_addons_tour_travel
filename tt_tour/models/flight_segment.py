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

    carrier_id = fields.Char('Airline')
    carrier_code = fields.Char('Flight Code')
    carrier_number = fields.Char('Flight Number')

    origin_id = fields.Char('Origin')
    origin_terminal = fields.Char('Origin Terminal')

    destination_id = fields.Char('Destination')
    destination_terminal = fields.Char('Destination Terminal')

    departure_date_fmt = fields.Char('Departure Date')
    arrival_date_fmt = fields.Char('Arrival Date')

    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')

    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Service Class')
    tour_pricelist_id = fields.Many2one('tt.tour.pricelist', 'Pricelist ID', readonly=True)
