from odoo import models, fields, api
from datetime import date, datetime, timedelta


class HotelDestination(models.Model):
    _name = "tt.hotel.destination"
    _desc = "Model ini digunakan untuk menyimpan seluruh data destination / city / satuan terkecil non hotel dari vendor yg dpat digunakan untuk pencarian"

    name = fields.Char('Name', required=True)
    auto_complete_name = fields.Char('Auto Complete Name', help='Display this record in auto complete as this field')

    # Vendor Data
    city_str = fields.Char('City', help='Real Name for destination / City from vendor')
    state_str = fields.Char('State', help='Related State name from vendor if Exist')
    country_str = fields.Char('Country', help='Related Country name from vendor')

    # Match Record
    city_id = fields.Many2one('res.city', 'City Obj', help='Object with same name as City field')
    state_id = fields.Many2one('res.country.state', 'State Obj', help='Object with same name as State field')
    country_id = fields.Many2one('res.country', 'Country Obj', help='Object with same name as Country field')

    active = fields.Boolean('Active', default=True)

    # Func Find City
    def find_city_obj(self):
        self.city_id = self.env['res.city'].find_city_by_name(self.city_str, 1)
        if self.city_id.state_id and self.state_id:
            if self.city_id.state_id == self.state_id:
                return True
            else:
                # TODO langkah jika hasil tidak sama diapakan
                return True
        else:
            if self.city_id.country_id == self.country_id:
                return True
            else:
                # TODO langkah jika hasil tidak sama diapakan
                return True

    # Func Find State
    def find_state_obj(self):
        self.state_id = self.env['res.country.state'].find_state_by_name(self.state_str, 1)
        if self.state_id.country_id == self.country_id:
            return True
        else:
            # TODO langkah jika hasil tidak sama diapakan
            return True

    # Func Find Country
    def find_country_obj(self):
        self.country_id = self.env['res.country'].find_country_by_name(self.country_str, 1)

    # Func Find All (city, state, country)
    def fill_obj_by_str(self):
        for rec in self:
            rec.find_country_obj()
            rec.find_state_obj()
            rec.find_city_obj()

    # Func render Name

    # Func Find Similar Destination
    def find_similar_obj(self):
        params = [('id','!=',self.id)]

        country_exist = self.country_id or self.country_str
        state_exist = self.state_id or self.state_str
        city_exist = self.city_id or self.city_str

        if self.country_id:
            params.append(('country_id','=',self.country_id.id))
        elif self.country_str:
            params.append(('country_str','=',self.country_str))

        if self.city_id:
            params.append(('city_id', '=', self.city_id.id))
        elif self.city_str:
            params.append(('city_str', '=', self.city_str))

        if self.state_id:
            params.append(('state_id','=',self.state_id.id))
        elif self.state_str:
            params.append(('state_str','=',self.state_str))

        similar_rec = self.env['tt.hotel.destination'].search(params, limit=1)

        if similar_rec:
            is_exact = country_exist and state_exist and city_exist
            return is_exact, similar_rec
        else:
            return False, similar_rec

    # In Active Record jika sdah exist
    def in_active_this_record_if_similar(self):
        for rec in self:
            is_exact, resp = rec.find_similar_obj()
            if is_exact:
                # Pindah Code nya current data ke data yg telah exist
                for provider_id in rec.provider_ids:
                    provider_id.res_id = resp[-1].id
                rec.active = False
            else:
                # Create Notif to Merge Possible Similar
                return True
        return True