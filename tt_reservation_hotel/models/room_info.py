from odoo import api, fields, models, _
from datetime import datetime


class RoomInfo(models.Model):
    _name = 'tt.room.info'
    _description = 'Room Description use for internal room CMS'

    name = fields.Char('Name', required='True', default='_')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel Info Id')
    room_type_id = fields.Many2one('tt.room.type', 'Room Type')
    currency_id = fields.Many2one('res.currency', 'Currency')

    active = fields.Boolean('Active Status', default=True)
    max_guest = fields.Integer('Max Guest', default=1)
    facility_ids = fields.Many2many('tt.hotel.facility', 'room_facility_rel', 'room_id', 'facility_id', 'Facility')

    room_description = fields.Text('Room Info')
    room_size = fields.Integer('Room Size', help='Room Size in Meters')
    bed_type = fields.Selection([
        ('1sb', 'One Single Bed'),
        ('2sb', 'Two Single Bed'),
        ('3sb', 'Triple Single Bed'),
        ('1db', 'One Double Bed'),
        ('2db', 'Two Double Bed'),
        ('sdb', 'Two Single Bed or One Double Bed'),
        ('ott', 'Others'),
    ], default='ott', string='Bed Type')
    image_ids = fields.One2many('tt.hotel.image', 'hotel_id', string='Images')
    # Child Rule
    max_child = fields.Integer('Max Child', default=0)
    child_age = fields.Integer('Child Age Max')
    meal_type_id = fields.Many2one('tt.meal.type', 'Meal Type')
    meal_type = fields.Char('Meal Type Name', related='meal_type_id.name')
    cancellation_policy = fields.Many2one('cancellation.policy', 'Cancel Policy', default=lambda self: self.env.ref('tt_reservation_hotel.hotel_no_refund_policy'))
    message = fields.Char('Message')

    # TODO Field di bwah di gunakan untuk menacatat kamar in pernah di booking di resv apa saja
    # Pertimbangkan untuk di hapus
    # room_booking_ids = fields.One2many('tt.room.info.booking', 'room_info_id', 'Booking History')
    total_voucher = fields.Integer('Total Voucher for this Room', compute='_count_total_voucher')

    @api.multi
    def onchange_room_type_to_name(self):
        for room in self:
            room.name = room.room_type_id.name
