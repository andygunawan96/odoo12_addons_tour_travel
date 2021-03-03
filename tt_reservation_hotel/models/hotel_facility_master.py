from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class HotelFacility(models.Model):
    _name = 'tt.hotel.facility'
    _description = 'Hotel Facility'

    name = fields.Char('Facility / Service Name', required=True)
    facility_type_id = fields.Many2one('tt.hotel.facility.type', 'Type of Facility / Service', required="True")
    description = fields.Char('Description')
    is_room_facility = fields.Boolean('Is Room Facility', default="False")
    is_hotel_facility = fields.Boolean('Is Hotel Facility', default="True")
    currency_id = fields.Many2one('res.currency', 'Currency')
    is_paid = fields.Boolean('Need Payment', default="False")
    css_class = fields.Char('Website CSS Class')
    internal_code = fields.Char('Internal Code')

    image_url = fields.Char('Image URL #1')
    image_url2 = fields.Char('Image URL #2')
    image_url3 = fields.Char('Image URL #3')

    # Create new Facility harus di tmbah ke new record untuk di re check dan merge supaya tau itu file baru
    # Inherit di new obj
    def notify_user(self, fac_obj):
        self.env['tt.temporary.record'].sudo().create({
            'name': fac_obj.name,
            'remove_rec_id': fac_obj.id,
            'rec_model': self._name,
        })
        _logger.info(msg='Newly add ' + fac_obj.name.lower())

    # Search Facility by name + alias name
    def find_by_name(self, fac_name):
        # parse_name = fac_name.replace('(s)', '').replace("`s", '').replace('facilities', 'facility').replace('(chargeable)', '')
        parse_name = fac_name.replace('_', ' ').replace('-', ' ')
        fac_id = self.env['tt.hotel.facility'].search([('name', '=ilike', parse_name)], limit=1)
        if not fac_id:
            found_obj = False
            for fac_master in self.env['tt.hotel.facility'].search([]):
                if fac_name.lower() in [a.code.lower() for a in fac_master.provider_ids]:
                    found_obj = True
                    fac_id = fac_master
                    break

            if not found_obj:
                fac_id = self.env['tt.hotel.facility'].create({
                    'name': parse_name,
                    'facility_type_id': self.env.ref('tt_reservation_hotel.tt_facility_type_1').id
                })
                # Todo: Create Provider Code for this facility Here
                # Add ke new data biar bisa di pantau pindah ke dependency baru
                self.notify_user(fac_id)
        return fac_id.id


class HotelTopFacility(models.Model):
    _name = 'tt.hotel.top.facility'
    _description = 'Hotel Top Facility'
    _order = 'sequence, id'

    name = fields.Char('Name')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    image_url = fields.Char('Image URL #1')
    image_url2 = fields.Char('Image URL #2')
    image_url3 = fields.Char('Image URL #3')
    sequence = fields.Integer('Sequence')
    internal_code = fields.Integer('Internal Code')
    active = fields.Boolean('Active', default=True)