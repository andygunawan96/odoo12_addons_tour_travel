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
        if self.city_id.country_id == self.country_id:
            if self.city_id.state_id == self.state_id:
                return True
            else:
                # TODO langkah jika hasil tidak sama diapakan
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

    def revisi_data_city(self):
        for rec in self.sudo().search([]):
            if rec.city_str and not rec.city_id:
                rec.find_city_obj()

    # Func render Name

    # Func Find Similar Destination
    def find_similar_obj(self, new_dict):
        params = [('id','!=', new_dict['id'])]

        country_exist = new_dict['country_str']
        state_exist = new_dict['state_str']
        city_exist = new_dict['city_str']

        if new_dict['country_str']:
            params.append(('country_str','=',new_dict['country_str']))

        if new_dict['city_str']:
            params.append(('city_str', '=',new_dict['city_str']))

        if new_dict['state_str']:
            params.append(('state_str','=',new_dict['state_str']))

        similar_rec = self.env['tt.hotel.destination'].search(params, limit=1)

        if similar_rec:
            is_exact = country_exist and state_exist and city_exist
            return is_exact, similar_rec
        else:
            return False, similar_rec

    # In Active Record jika sdah exist
    def in_active_this_record_if_similar(self):
        for rec in self:
            is_exact, resp = self.find_similar_obj(rec)
            if is_exact:
                # Pindah Code nya current data ke data yg telah exist
                for provider_id in rec.provider_ids:
                    provider_id.res_id = resp[-1].id
                rec.active = False
            else:
                # Create Notif to Merge Possible Similar
                return True
        return True

    def multi_merge_destination(self):
        code_list = []
        max_len = 0
        max_obj = False
        for rec in self:
            code_list += rec.provider_ids.ids
            if max_len < len(rec.provider_ids.ids):
                max_len = len(rec.provider_ids.ids)
                max_obj = rec
        if max_obj:
            max_obj.provider_ids.update([(6, 0, code_list)])
        return True

    def prepare_destination_for_cache(self, curr_obj):
        return {
            'id': curr_obj.id,
            'name': curr_obj.name,
        }