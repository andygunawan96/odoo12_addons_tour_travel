from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class HotelDestination(models.Model):
    _name = "tt.hotel.destination"
    _description = 'Hotel Destination'
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
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('merged', 'Merged')], default='draft')

    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    confirm_date = fields.Datetime('Confirmed Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel by', readonly=True)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)

    hotel_ids = fields.One2many('tt.hotel.master', 'destination_id', 'Hotel Master')
    hotel_raw_ids = fields.One2many('tt.hotel', 'destination_id', 'Hotel Raw')

    # Func Find City
    def find_city_obj(self):
        city_ids = self.env['res.city'].find_city_by_name(self.city_str, 100)

        city_by_country_ids = [city_id for city_id in city_ids if city_id.country_id == self.country_id]
        for city_id in city_by_country_ids:
            if city_id.state_id == self.state_id or not self.state_id:
                self.city_id = city_id

        if not self.city_id and city_by_country_ids:
            self.city_id = city_by_country_ids[0]

    # Func Find State
    def find_state_obj(self):
        state_ids = self.env['res.country.state'].find_state_by_name(self.state_str, 5)
        for state_id in state_ids or []:
            if state_id.country_id == self.country_id:
                self.state_id = state_id

        if not self.state_id and state_ids:
            self.state_id = state_ids[0]

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
    def find_similar_obj(self, new_dict, force_create=False):
        params = [('id','!=', new_dict['id'])]

        country_exist = new_dict['country_str'] # Bisa jadi Indonesia bisa jadi ID klo ID dia error
        state_exist = new_dict['state_str']
        city_exist = new_dict['city_str']

        for param in ['name', 'country_str', 'state_str', 'city_str']:
            if new_dict.get(param):
                params.append((param, '=ilike', new_dict[param]))

        similar_rec = self.env['tt.hotel.destination'].search(params, limit=1)

        if similar_rec:
            is_exact = country_exist and city_exist
            return is_exact, similar_rec
        else:
            # Create
            if force_create:
                similar_rec = self.env['tt.hotel.destination'].create({
                'name': new_dict.get('name'),
                'country_str': new_dict.get('country_str'),
                'state_str': new_dict.get('state_str'),
                'city_str': new_dict.get('city_str'),
            })
            return True, similar_rec

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
        return True

    def copy_value_if_empty(self, target_id):
        target_obj = self.sudo().browse(target_id)
        need_to_check = ['city_str', 'state_str', 'country_str', 'city_id', 'state_id', 'country_id']
        x = {}
        for data in need_to_check:
            if not getattr(self, data):
                x[data] = getattr(target_obj, data)
        self.update(x)
        return True

    def prepare_destination_for_cache(self, curr_obj):
        return {
            'id': curr_obj.id,
            'name': curr_obj.name,
        }

    def save_this_destination_as_alias_city_name(self):
        if self.city_id:
            #Cek apakah alias dengan nama destinasi ini telah ada?
            if self.env['tt.destination.alias'].search([('name','=ilike',self.name), ('city_id','=',self.city_id.id)]):
                # Jika iya notif
                raise UserError('Alias Name Already Exist')
            else:
                # Jika Tidak Create
                self.env['tt.destination.alias'].create({
                    'name': self.name,
                    'city_id': self.city_id.id,
                })
                # self.city_id.city_search_name()

        else:
            raise UserError('You must set city First')

    def write(self, vals):
        # Jika Ganti nama Destinasi cek City nya
        if 'name' in vals:
            # Jika destinasi ini digunakan sebagai data alias maka ganti juga nama nya
            for rec in self.env['tt.destination.alias'].search([('name', '=ilike', self.name), ('city_id', '=', self.city_id.id)]):
                rec.name = vals['name']
        # Jika ada Alias dengan exact name as this destination Ganti City_ID ne
        if 'city_id' in vals:
            for rec in self.env['tt.destination.alias'].search([('name', '=ilike', self.name), ('city_id', '=', self.city_id.id)]):
                rec.city_id = vals['city_id']
        return super(HotelDestination, self).write(vals)

    # View Function Start
    def action_confirm(self):
        self.update({
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })

    def action_set_to_draft(self):
        if self.state == 'confirm':
            self.update({
                'state': 'draft',
                'confirm_uid': self.env.user.id,
                'confirm_date': datetime.now(),
            })
        else:
            self.state = 'draft'

    # View Function END
