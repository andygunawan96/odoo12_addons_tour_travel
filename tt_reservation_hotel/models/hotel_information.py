from odoo import api, fields, models, _


class HotelInformation(models.Model):
    _name = 'tt.hotel'
    _description = 'Master Data Hotel'
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
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('expired', 'Not Avaliable'),
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
        self.state = 'confirm'

    @api.one
    def action_draft(self):
        self.state = 'draft'

    def get_all_hotels(self):
        hotels = self.env['tt.hotel'].sudo().search([('state', '=', 'confirm')])
        data = []
        for rec in hotels:
            json = {
                'id': rec.id,
                'type': 'hotel',
                'name': rec.name,
                'display_name': rec.name,
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
        self.provider = ''
        self.provider_ext_code = ''
        for provider in self.provider_hotel_ids:
            self.provider += provider.provider_id.name
            self.provider += '; '
            self.provider_ext_code += provider.code
            self.provider_ext_code += '; '

    def calc_get_provider_name(self):
        for rec in self.search([('city_id', '=', self.city_id.id)]):
            rec.get_provider_name()

    def render_cache_city(self):
        self.env['test.search'].update_cache_city()


class HotelImage(models.Model):
    _inherit = 'tt.hotel.image'

    hotel_id = fields.Many2one('tt.hotel', "Hotel")


class TtTemporaryRecord(models.Model):
    _inherit = 'tt.temporary.record'

    def get_obj(self):
        obj_list = super(TtTemporaryRecord, self).get_obj()
        obj_list += [('tt.hotel', 'city_id')]
        return obj_list
