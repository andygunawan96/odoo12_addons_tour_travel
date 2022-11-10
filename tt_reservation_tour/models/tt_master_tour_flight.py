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


class TtMasterTourFlight(models.Model):
    _name = 'flight.segment'
    _description = 'Flight Segment'

    journey_type = fields.Selection(JOURNEY_TYPE, 'Journey Type', default='dp')

    def _get_domain_airline(self):
        airline_type_id = self.env.ref('tt_reservation_airline.tt_provider_type_airline').id
        return [('provider_type_id', '=', airline_type_id)]

    carrier_id = fields.Many2one('tt.transport.carrier', 'Airline', domain=_get_domain_airline)
    carrier_code = fields.Char('Flight Code', related='carrier_id.code', store=True)
    carrier_number = fields.Char('Flight Number')

    origin_id = fields.Many2one('tt.destinations', 'Origin', domain=_get_domain_airline)
    origin_terminal = fields.Char('Origin Terminal')

    destination_id = fields.Many2one('tt.destinations', 'Destination', domain=_get_domain_airline)
    destination_terminal = fields.Char('Destination Terminal')

    departure_date_fmt = fields.Datetime('Departure Date (FMT)')
    return_date_fmt = fields.Datetime('Arrival Date (FMT)')
    arrival_date_fmt = fields.Datetime('Arrival Date (FMT)')

    departure_date = fields.Datetime('Departure Date')
    arrival_date = fields.Datetime('Arrival Date')
    return_date = fields.Datetime('Return Date')

    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Service Class')
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
