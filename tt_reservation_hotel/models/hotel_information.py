from odoo import api, fields, models, _
from odoo.exceptions import UserError
import random, string


class HotelInformation(models.Model):
    _name = 'tt.hotel'
    _description = 'Master Data Hotel yg dikirim ke gateway atau merupakan data final dari system'
    _inherit = ['tt.history']

    name = fields.Char('Name', required="True")
    hotel_management_id = fields.Many2one('res.partner', 'Hotel Management', help='Presented by')
    # Digunakan untuk pengelompokan CMS jadi user A bisa edit hotel apa aja?
    # hotel_partner_id = fields.Many2one('res.partner', 'Hotel Partner', help='')
    # Dulu hotel_partner_city_id
    city_id = fields.Many2one('res.city', 'City')
    hotel_type_id = fields.Many2one('tt.hotel.type', 'Hotel Type', domain=[('usage', '=', 'hotel')])
    room_info_ids = fields.One2many('tt.room.info', 'hotel_id', 'Rooms')
    facility_ids = fields.Many2many('tt.hotel.facility', 'hotel_facility_rel', 'hotel_id', 'facility_id')
    tac = fields.Text('Terms & Conditions')
    description = fields.Text('Description')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('expired', 'Not Available'),
                              ('tobe_merge', 'To Be Merge'), ('merged', 'Merged')], default='draft')
    rating = fields.Selection([
        (0, 'No Star'),
        (1, 'One Star'),
        (2, 'Two Star'),
        (3, 'Three Star'),
        (4, 'Four Star'),
        (5, 'Five Star'),
        (6, 'Six Star'),
        (7, 'Seven Star'),
    ], 'Star', default=0)

    lat = fields.Char('Latitude')
    long = fields.Char('Longitude')
    cancel_policy_id = fields.Many2one('cancellation.policy','Cancel Policy', default=lambda self: self.env.ref('tt_reservation_hotel.hotel_no_refund_policy'))
    cancel_policy = fields.Char('Cancellation Policy')
    address = fields.Text('Address #1')
    address2 = fields.Text('Address #2')
    address3 = fields.Char('Address #3')
    email = fields.Char('Email')
    website = fields.Char('Website')
    phone = fields.Char('Phone')
    phone_2 = fields.Char('Phone #2')
    phone_3 = fields.Char('Phone #3')
    fax = fields.Char('Fax')
    # Pertimbangkan gabung dengan tt.master.image themespark
    image_ids = fields.One2many('tt.hotel.image', 'hotel_id', string='Images')
    provider = fields.Char('Provider', default='cms', help='Real Provider')

    zip = fields.Char()
    # district_id = fields.Many2one("res.country.district", string='District')
    destination_id = fields.Many2one("tt.hotel.destination", 'Destination', help='Destination Name or Searchable in Auto Complete')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    message = fields.Text('Message')
    ribbon = fields.Selection([
        ('no', 'No Ribbon'),
        ('bp', 'Best Price'),
        ('fb', 'Free Breakfast'),
        ('dc', 'Discount Today'),
    ], 'Ribbon', default='no', help='Using to give promo mark')
    file_number = fields.Text('File Number')

    @api.one
    def action_confirm(self):
        if not self.env.user.has_group('tt_base.group_master_data_hotel_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 138')
        self.state = 'confirm'

    @api.one
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def unlink(self):
        for rec in self:
            for prov_code in self.env['tt.provider.code'].search([('res_model','=','tt.hotel'),('res_id','=',rec.id)]):
                prov_code.unlink()
        return super(HotelInformation, self).unlink()

    def get_all_hotels(self):
        hotels = self.env['tt.hotel'].sudo().search([('state', '=', 'confirm')])
        data = []
        for rec in hotels:
            json = {
                'id': rec.id,
                'type': 'hotel',
                'name': rec.name,
                'city_id': rec.city_id.id,
                'city_name': rec.city_id.name,
                'state_name': rec.city_id.state_id and rec.city_id.state_id.name or rec.city_id.state_id,
                'country_id': rec.city_id.country_id and rec.city_id.country_id.id or rec.city_id.country_id,
                'country_name': rec.city_id.country_id and rec.city_id.country_id.name or rec.city_id.country_id,
                'provider': {},
            }
            for provider in rec.provider_hotel_ids:
                json['provider'].update({
                    str(provider.provider_id.provider_code and provider.provider_id.provider_code or provider.provider_id.name).lower(): provider.code,
                })
            data.append(json)
        return data

    def get_provider_name(self):
        x = 0
        # for rec in self.env['tt.hotel.master'].search([('id', '>=', self.id),('provider', '=', '')]):
        for rec in self:
            master_fac = []
            rec_provider = ''
            for provider in rec.info_ids:
                for prov_obj in provider.provider_hotel_ids:
                    rec_provider += prov_obj.provider_id.name + '; '
                # No vendor code

            rec.write({
                'provider': rec_provider,
            })

            # x += 1
            # if x % 20 == 0:
            #     self.env.cr.commit()
            # if x % 2000 == 0:
            #     return True

    def calc_get_provider_name(self):
        for rec in self.search([('city_id', '=', self.city_id.id)]):
            rec.get_provider_name()

    def render_cache_city(self):
        self.env['test.search'].update_cache_city()

    # result:
    # {'A1': '001', 'A2': '002', 'A3': '003'}
    # Misal 1 Hotel ada code same provider dia kereplace dengan nilai terakhir
    def get_provider_code_fmt(self):
        provider_fmt = {}
        for rec in self.provider_hotel_ids:
            # if is_alias:
            #     provider_fmt.update({rec.provider_id.alias: rec.code})
            # else:
            #     provider_fmt.update({rec.provider_id.code: rec.code})
            # Webbeds: SH12345
            provider_fmt.update({rec.provider_id.code: rec.code})
            # A6: SH12345
            # provider_fmt.update({rec.provider_id.alias: rec.code})
        return provider_fmt

    # result:
    # {'1~A1': '001', '1~A2': '002', '2~A2': '003', '1~A3': '004'}
    # def get_provider_code_fmt(self):
    def get_provider_code_fmt_ver1(self):
        provider_fmt = {}
        provider_counter = {}
        for rec in self.provider_hotel_ids:
            if not provider_counter.get(rec.provider_id.alias):
                provider_counter[rec.provider_id.alias] = 0
            provider_counter[rec.provider_id.alias] += 1
            provider_fmt.update({str(provider_counter[rec.provider_id.alias]) + '~' + rec.provider_id.alias: rec.code})
        return provider_fmt

    def get_hotel_image_fmt(self):
        hotel_fmt_list = []
        for rec in self.image_ids:
            hotel_fmt_list.append({
                'name': rec.name,
                'url': rec.url,
                'description': rec.description,
                'provider_id': self.provider,
            })
        return hotel_fmt_list

    def get_hotel_facility_fmt(self):
        hotel_fmt_list = []
        for rec in self.facility_ids:
            hotel_fmt_list.append({
                'facility_id': rec.id,
                'name': rec.name,
                'facility_name': rec.name,
                'description': rec.description,
            })
        return hotel_fmt_list

    def fmt_read(self, hotel_obj={}, city_idx=0):
        hotel = hotel_obj or self.read()[0]
        new_hotel = {
            'id': str(hotel['id']),
            'name': hotel.get('name') and hotel['name'].title(),
            'rating': hotel.get('rating', 0),
            'prices': [],
            'description': hotel.get('description'),
            'location': {
                'address': hotel.get('address') or hotel.get('street'),
                'city': hotel.get('city_id') and hotel['city_id'][1] or False,
                'city_code': hotel.get('city_id') and hotel['city_id'][0] or False,
                'state': hotel.get('state_id') and hotel['state_id'][1] or False,
                'state_code': hotel.get('state_id') and hotel['state_id'][0] or False,
                'country_code': hotel.get('country_id') and hotel['country_id'][0] or False,
                'country': hotel.get('country_id') and hotel['country_id'][1] or False,
                'zipcode': hotel.get('zip')
            },
            'telephone': hotel.get('phone'),
            'fax': hotel.get('fax'),
            'ribbon': '',
            'lat': hotel.get('lat'),
            'long': hotel.get('long'),
            'state': 'confirm',
            'external_code': self.get_provider_code_fmt(),
            'near_by_facility': [],
            'images': self.get_hotel_image_fmt(),
            'facilities': hotel.get('facilities') or self.get_hotel_facility_fmt(),
            'id2': city_idx,
        }
        if not isinstance(new_hotel['rating'], int):
            try:
                new_hotel['rating'] = int(new_hotel['rating'][0])
            except:
                new_hotel['rating'] = 0

        # fac_list = []
        # for img in new_hotel.get('image_ids') or []:
        #     if isinstance(img, str):
        #         new_img_url = 'http' in img and img or 'http://www.sunhotels.net/Sunhotels.net/HotelInfo/hotelImage.aspx' + img + '&full=1'
        #         provider_id = False
        #         fac_list.append({'name': '', 'url': new_img_url, 'description': '', 'provider_id': provider_id})
        #     else:
        #         # Digunakan hotel yg bisa dpet nama image nya
        #         # Sampai tgl 11-11-2019 yg kyak gini (miki_api) formate sdah bener jadi bisa langsung break
        #         # Lek misal formate beda mesti di format ulang
        #         fac_list = new_hotel['images']
        #         break
        # new_hotel['images'] = fac_list

        new_fac = []
        for fac in new_hotel.get('facilities') or []:
            if isinstance(fac, dict):
                if not fac.get('facility_name'):
                    fac['facility_name'] = fac.pop('name')
                # fac_name = fac['facility_name']
            else:
                # fac_name = fac
                fac = {
                    'facility_name': fac,
                    'facility_id': False,
                }
            new_fac.append(fac)
            # for fac_det in fac_name.split('/'):
            #     facility = self.env['tt.hotel.facility'].search([('name', '=ilike', fac_det)])
            #     if facility:
            #         fac['facility_id'] = facility[0].internal_code
            #         break
            #     else:
            #         facility = self.env['tt.provider.code'].search([('name', '=ilike', fac_det), ('facility_id', '!=', False)])
            #         if facility:
            #             fac['facility_id'] = facility[0].facility_id.internal_code
            #             break
            #
            #         # Rekap Facility Other Name
            #         with open('/var/log/cache_hotel/result log/master/new_facility.csv', 'a') as csvFile:
            #             writer = csv.writer(csvFile)
            #             writer.writerows([[provider, fac_det]])
            #         csvFile.close()
        new_hotel['facilities'] = new_fac
        return new_hotel

    def fill_country_city(self):
        # if self.destination_id.name == 'Lampung Province':
        #     self.destination_id = False
        #     self.country_id = False
        if not self.destination_id:
            is_exact, destination_obj = self.env['tt.hotel.destination'].find_similar_obj({
                'id': False,
                'name': self.address3,
                'city_str': self.address3,
                'city_id': self.city_id and self.city_id.id or False,
                'state_str': False,
                'country_id': self.country_id and self.country_id.id or False,
            })
            self.destination_id = destination_obj
        if not self.city_id and self.destination_id.city_id:
            self.city_id = self.destination_id.city_id.id
        if not self.country_id:
            self.country_id = self.city_id and self.city_id.country_id.id or self.destination_id.country_id.id
        if not self.state_id:
            self.state_id = self.destination_id.state_id.id
        if self.city_id and self.country_id and not self.destination_id.city_id:
            is_exact, destination_obj = self.env['tt.hotel.destination'].find_similar_obj({
                'id': False,
                'name': False,
                'city_str': self.city_id.name,
                'state_str': False,
                'country_str': self.country_id.name,
            })
            self.destination_id = destination_obj

    def mass_fill_country_city(self):
        for rec in self:
            rec.fill_country_city()

    def mass_re_mapp(self):
        for idx, rec in enumerate(self):
            # Re Mapping Hotel XXX
            comparer = [x for x in rec.compare_ids if x.state in ['draft', 'tobe_merged', 'merged']]
            if rec.compare_ids and comparer:
                # Skip Re Mapping Hotel XXX got some need process compare data
                continue
            rec.advance_find_similar_name_from_database_2()
            comparer = [x for x in rec.compare_ids if x.state in ['draft']]
            if comparer:
                for rec2 in comparer:
                    if rec2.score > 55 and 'stay later' not in rec2.hotel_id.name.lower():
                        # Merging compare Hotel XXX with Hotel YYY
                        rec2.merge_hotel()
                        break
            else:
                # Creating Empty compare record Hotel XXX
                comparing_id = self.env['tt.hotel.compare'].create({
                    'hotel_id': rec.id,
                    'comp_hotel_id': False
                })
                if rec.destination_id and rec.destination_id.country_id and rec.address:
                    comparing_id.merge_hotel()

            if idx % 5 == 0:
                self.env.cr.commit()

    def mass_recalc_state(self):
        for rec in self:
            create_new = True
            is_draft = 0
            for line_obj in rec.compare_ids:
                if line_obj.state in ['merge','tobe_merge']:
                    create_new = False
                    break
                if line_obj.state == 'draft' and not line_obj.comp_hotel_id:
                    compare_id = line_obj
                    is_draft += 1

            if is_draft == 1:
                compare_id.to_merge_hotel()
            if create_new:
                compare_id = self.env['tt.hotel.compare'].create({'hotel_id': rec.id,})
                compare_id.to_merge_hotel()

    # Temporary Function digunakan untuk feeling mass empty data
    def set_country_by_destination_and_city(self):
        idx = 0
        for rec in self.env['tt.hotel'].search([('country_id','=',False),'|',('city_id','!=',False),('destination_id','!=',False)]):
            rec.country_id = rec.city_id and rec.city_id.country_id.id or False
            if not rec.country_id:
                rec.country_id = rec.destination_id and rec.destination_id.country_id.id or False
            idx += 1

            if idx > 1001:
                self.env.cr.commit()
                idx = 0

    @api.onchange('city_id')
    @api.depends('city_id')
    def onchange_city(self):
        for rec in self:
            rec.country_id = rec.city_id and rec.city_id.country_id.id or False


class HotelImage(models.Model):
    _inherit = 'tt.hotel.image'

    hotel_id = fields.Many2one('tt.hotel', "Hotel")
    master_hotel_id = fields.Many2one('tt.hotel.master', "Master Hotel")


class HotelMaster(models.Model):
    _name = 'tt.hotel.master'
    _inherit = 'tt.hotel'
    _description = 'Hotel Comparer Data'

    info_ids = fields.Many2many('tt.hotel', 'hotel_compared_info_rel', 'compared_id', 'info_id', 'Hotel Info', help='Data Hotel setelah di merge dan akan di publish')
    compare_ids = fields.One2many('tt.hotel.compare', 'similar_id', 'Hotel Compare')
    image_ids = fields.One2many('tt.hotel.image', 'master_hotel_id', string='Images')
    facility_ids = fields.Many2many('tt.hotel.facility', 'master_hotel_facility_rel', 'master_hotel_id', 'facility_id')

    internal_code = fields.Char('Internal Code', help='Internal Code')

    def get_provider_code_fmt(self):
        alias_code = self.env.ref('tt_reservation_hotel.tt_hotel_provider_rodextrip_hotel').code
        provider_fmt = {alias_code: self.internal_code}
        for hotel in self.info_ids:
            for rec in hotel.provider_hotel_ids:
                provider_fmt.update({rec.provider_id.code: rec.code})
                # provider_fmt.update({rec.provider_id.alias: rec.code})
        return provider_fmt

    def get_hotel_info(self):
        for rec in self.compare_ids:
            self.info_ids = [(4, rec.hotel_id.id)]

    def calc_get_city(self):
        if not self.city_id:
            self.city_id = self.destination_id.city_id.id
        if not self.country_id:
            self.country_id = self.destination_id.country_id.id

    def calc_get_provider_name(self):
        for rec in self.search([('city_id', '=', self.city_id.id)]):
            rec.get_provider_name()
            rec.get_hotel_info()

    def comp_internal_code(self):
        for rec in self:
            if not rec.internal_code:
                rec.internal_code = str(rec['id']) + '_' + ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    def fmt_read(self, hotel_obj={}, city_idx=0):
        rec = super(HotelMaster, self).fmt_read(hotel_obj, city_idx)
        if not self.internal_code:
            self.comp_internal_code()
        rec.update({'id': self.internal_code,})
        return rec

    def get_provider_name(self):
        super(HotelMaster, self).get_provider_name()
        if not self.internal_code:
            self.comp_internal_code()



class TtTemporaryRecord(models.Model):
    _inherit = 'tt.temporary.record'

    def get_obj(self):
        new_obj = {
            'res.country': [('tt.hotel', 'country_id'), ('tt.hotel.master', 'country_id')],
            'res.country.state': [('tt.hotel', 'state_id'), ('tt.hotel.master', 'state_id')],
            'res.city': [('tt.hotel', 'city_id'), ('tt.hotel.master', 'city_id')],
            'tt.hotel.destination': [('tt.hotel', 'destination_id'), ('tt.hotel.master', 'destination_id')]
        }
        obj_list = super(TtTemporaryRecord, self).get_obj()
        for obj_key in new_obj.keys():
            if obj_list.get(obj_key):
                obj_list[obj_key] += new_obj[obj_key]
            else:
                obj_list[obj_key] = new_obj[obj_key]
        return obj_list

