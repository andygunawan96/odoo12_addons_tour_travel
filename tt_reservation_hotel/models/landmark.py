from odoo import api, fields, models, tools, _
from math import sin, cos, sqrt, atan2, radians


class Landmark(models.Model):
    _name = 'tt.landmark'
    _description = 'Landmark Description'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    description = fields.Text('Description')

    type_id = fields.Many2one('tt.landmark.type', 'Type', required=True)
    city_id = fields.Many2one('res.city', 'City', required=True)
    lat = fields.Char('Latitude')
    long = fields.Char('Longitude')
    website = fields.Char('Website URL', default='#', help="Website of Landmark Detail")
    image = fields.Binary(attachment=True)

    hotel_ids = fields.One2many('tt.landmark.distance', 'landmark_id', 'Hotel(s)')
    image_ids = fields.One2many('tt.hotel.image', 'landmark_id', 'Image(s)')

    @api.multi
    def find_nearest_hotel(self):
        lat = self.lat
        long = self.long
        query = 'SELECT id, ( 3959 * acos( cos( %d ) * cos( lat ) * ' \
                'cos( long - %d ) + sin( %d ) * ' \
                'sin( lat ) ) ) AS distance FROM tt_hotel HAVING ' \
                'distance < %d ORDER BY distance LIMIT 5;' % (float(lat), float(long), float(lat), 25)
        self.env.cr.execute(query)
        for rec in self.env.cr.dictfetchall():
            self.env['tt.landmark.distance'].create({
                'hotel_id': rec['id'],
                'landmark_id': self.id,
                'distance': rec['distance'],
                'uom_id': 'Km',
            })

    @api.multi
    def find_nearest_landmark(self, hotel_id):
        R = 6373.0
        lat2 = radians(float(hotel_id.lat))
        lon2 = radians(float(hotel_id.long))

        for rec in self.search([('city_id', '=', hotel_id.city_id.id), ('lat', '!=', False), ('long', '!=', False)]):
            lat1 = radians(float(rec.lat))
            lon1 = radians(float(rec.long))

            dlon = lon2 - lon1
            dlat = lat2 - lat1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            distance = R * c
            self.env['tt.landmark.distance'].create({
                'hotel_id': hotel_id.id,
                'landmark_id': rec.id,
                'distance': distance,
                'uom_id': 'Km',
            })


class LandmarkType(models.Model):
    _name = 'tt.landmark.type'
    _description = 'Landmark type for tags(Historical, Shopping, Water Activity etc.)'

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)

    landmark_ids = fields.One2many('tt.landmark', 'type_id', 'LandMark(s)')


class LandmarkDistance(models.Model):
    _name = 'tt.landmark.distance'
    _description = 'Distance between landmark and object near by'

    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    landmark_id = fields.Many2one('tt.landmark', 'Landmark')
    distance = fields.Integer('Distance')
    uom_id = fields.Char('Unit of Measure')
    active = fields.Boolean('Active', default=True)

    def open_record_hotel(self):
        rec_id = self.hotel_id.id
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref('tt_hotel.tt_hotel_view_form_rodex')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Hotel',
            'res_model': 'tt.hotel',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }

    def open_record_landmark(self):
        rec_id = self.landmark_id.id
        # then if you have more than one form view then specify the form id
        form_id = self.env.ref('tt_hotel.tt_landmark_view_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Landmark',
            'res_model': 'tt.landmark',
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            # if you want to open the form in edit mode direclty
            # 'flags': {'initial_mode': 'edit'},
            'target': 'current',
        }


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    landmark_ids = fields.One2many('tt.landmark.distance', 'hotel_id', 'Landmark(s)')

    def get_nearby_landmark(self):
        self.env['tt.landmark'].find_nearest_landmark(self)


class HotelImage(models.Model):
    _inherit = 'tt.hotel.image'

    landmark_id = fields.Many2one('tt.landmark', "Hotel")
