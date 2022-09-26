from odoo import api, fields, models, _
# import odoo.addons.decimal_precision as dp
from ...tools import variables
import json
from datetime import datetime, timedelta


class TtSegmentAirline(models.Model):
    _name = 'tt.segment.airline'
    _rec_name = 'name'
    _order = 'departure_date_utc'
    _description = 'Segment Airline'

    name = fields.Char('Name', compute='_fill_name')
    segment_code = fields.Char('Segment Code')
    fare_code = fields.Char('Fare Code')

    pnr = fields.Char('PNR', related='journey_id.pnr', store=True)

    carrier_id = fields.Many2one('tt.transport.carrier','Plane')
    carrier_code = fields.Char('Flight Code')
    operating_airline_id = fields.Many2one('tt.transport.carrier', 'Operating Airline', default=None)
    operating_airline_code = fields.Char('Operating Airline Code', default='')
    carrier_number = fields.Char('Flight Number')
    provider_id = fields.Many2one('tt.provider','Provider')
    carrier_type_code = fields.Char('Carrier Type Code')
    carrier_type_id = fields.Many2one('tt.transport.carrier.type', 'Carrier Type', default=None)

    origin_id = fields.Many2one('tt.destinations', 'Origin')
    destination_id = fields.Many2one('tt.destinations', 'Destination')

    origin_terminal = fields.Char('Origin Terminal')
    destination_terminal = fields.Char('Destination Terminal')

    departure_date = fields.Char('Departure Date')
    arrival_date = fields.Char('Arrival Date')
    departure_date_utc = fields.Datetime('Departure Date (UTC)', compute='_compute_departure_date_utc', store=True, readonly=1)

    elapsed_time = fields.Char('Elapsed Time')

    class_of_service = fields.Char('Class of Service')
    cabin_class = fields.Char('Cabin Class')
    tour_code = fields.Char('Tour Code', default='')
    # agent_id = fields.Many2one('res.partner', related='booking_id.agent_id', store=True)

    sequence = fields.Integer('Sequence')

    journey_id = fields.Many2one('tt.journey.airline', 'Journey', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.airline', 'Order Number', related='journey_id.booking_id', store=True)

    # additional_service_charge_ids = fields.One2many('tt.tb.service.charge', 'segment_id')
    seat_ids = fields.One2many('tt.seat.airline', 'segment_id', 'Seat')
    leg_ids = fields.One2many('tt.leg.airline', 'segment_id', 'Legs')

    segment_addons_ids = fields.One2many('tt.segment.addons.airline','segment_id','Addons')

    # April 22, 2020 - SAM
    fare_basis_code = fields.Char('Fare Basis Code', default='')
    fare_class = fields.Char('Fare Class', default='')
    fare_name = fields.Char('Fare Name', default='')
    # END

    # September 2, 2021 - SAM
    cabin_class_str = fields.Char('Cabin Class String', compute='_compute_cabin_class_str', default='', store=True)
    # END

    # September 20, 2022 - SAM
    description = fields.Char('Description Data', default='')
    description_text = fields.Char('Description Text', default='', compute='_compute_description_text', store=True)
    # END

    @api.depends('departure_date', 'origin_id')
    def _compute_departure_date_utc(self):
        for rec in self:
            departure_date = rec.departure_date
            dept_time_obj = None
            try:
                dept_time_obj = datetime.strptime(departure_date, '%Y-%m-%d %H:%M:%S')
            except:
                departure_date = None

            origin_obj = rec.origin_id
            if not origin_obj or not dept_time_obj:
                rec.departure_date_utc = departure_date
                continue

            utc_time = origin_obj.timezone_hour
            rec.departure_date_utc = dept_time_obj - timedelta(hours=utc_time)

    @api.depends('cabin_class')
    def _compute_cabin_class_str(self):
        lib = {
            'Y': 'Economy',
            'W': 'Premium Economy',
            'C': 'Business Class',
            'F': 'First Class',
        }
        for rec in self:
            if not rec.cabin_class:
                rec.cabin_class_str = ''
                continue

            cabin_class_str = lib.get(rec.cabin_class, '')
            rec.cabin_class_str = cabin_class_str

    @api.depends('description')
    def _compute_description_text(self):
        for rec in self:
            try:
                if not rec.description:
                    rec.description_text = ''
                    continue

                desc_list = json.loads(rec.description)
                rec.description_text = ', '.join(desc_list)
            except:
                rec.description_text = ''

    @api.multi
    @api.depends('carrier_id')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (rec.carrier_code,rec.carrier_number)

    def to_dict(self):
        leg_list = []
        for rec in self.leg_ids:
            leg_list.append(rec.to_dict())
        segment_addons_list = []
        for rec in self.segment_addons_ids:
            segment_addons_list.append(rec.to_dict())

        res = {
            'segment_code': self.segment_code,
            'fare_code': self.fare_code,
            'pnr': self.pnr and self.pnr or '',
            'carrier_name': self.carrier_id.name,
            'carrier_code': self.carrier_code,
            'carrier_type_code': self.carrier_code,
            'carrier_type_name': self.carrier_type_id and self.carrier_type_id.name or '',
            'carrier_number': self.carrier_number,
            'provider': self.provider_id.code,
            'origin': self.origin_id.code,
            'origin_terminal': self.origin_terminal and self.origin_terminal or '',
            'destination': self.destination_id.code,
            'destination_terminal': self.destination_terminal and self.destination_terminal or '',
            'departure_date': self.departure_date,
            'arrival_date': self.arrival_date,
            'elapsed_time': self.elapsed_time and self.elapsed_time or '',
            'class_of_service': self.class_of_service and self.class_of_service or '',
            'cabin_class': self.cabin_class and self.cabin_class or '',
            'tour_code': self.tour_code and self.tour_code or '',
            'sequence': self.sequence,
            'seats': [],
            'legs': leg_list,
            'fare_details': segment_addons_list,
            # April 20, 2022 - SAM
            'fare_basis_code': self.fare_basis_code and self.fare_basis_code or '',
            'fare_class': self.fare_class and self.fare_class or '',
            'fare_name': self.fare_name and self.fare_name or '',
            # END
            # April 12, 2022 - SAM
            'operating_airline_code': self.operating_airline_code and self.operating_airline_code or '',
            # END
            'description': [],
        }
        # September 20, 2022 - SAM
        try:
            if self.description:
                desc_list = json.loads(self.description)
                res.update({
                    'description': desc_list
                })
        except:
            pass
        # END
        return res
