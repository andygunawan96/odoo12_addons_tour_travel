from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


def getfield(model, field_name):
    value = model
    for part in field_name.split('.'):
        value = getattr(value, part)
    if isinstance(value, (str, bool, int)):
        return value
    else:
        return value.id


class HotelFindSimilar(models.Model):
    _name = 'tt.hotel.find.similar'
    _description = 'Finding Similar record for selected hotel'

    hotel_id = fields.Many2one('tt.hotel', 'Hotel #1', required="True")
    compare_uid = fields.Many2one('res.users', 'Compare by')
    compare_date = fields.Datetime('Compare Date')
    end_date = fields.Datetime('End Date')

    similar_ids = fields.One2many('tt.hotel.compare', 'similar_id', 'Similar(s)')
    hotel_name = fields.Char('Name')
    similar_length = fields.Integer('Similar(s)')

    @api.multi
    def clear_similar(self):
        for rec in self.similar_ids:
            rec.comp_hotel_id.state = 'draft'
            rec.sudo().unlink()
        self.hotel_name = ''
        self.compare_uid = False
        self.compare_date = False
        self.end_date = False

    @api.multi
    def selected_string_removal(self, hotel_name=""):
        if self.hotel_name:
            return self.hotel_name

        if hotel_name == '':
            hotel_name = self.hotel_id.name
        # Change Mark to Space " "
        hotel_name = hotel_name.replace("-", " ").replace("&", "and").replace(" - ", " ")

        # Todo: Pertimbangkan Remove Nama Kota pada bagian ini
        # Remove selected String for hotel name
        str_list = []
        remove_str = self.env['hotel.image.settings'].sudo().search([], limit=1).remove_str
        remove_str = remove_str and remove_str.split(";") or []
        for rec in hotel_name.split(' '):
            if rec.lower() not in remove_str:
                str_list.append(rec)
        self.hotel_name = ' '.join(str(e) for e in str_list)
        return str_list

    @api.multi
    def find_similar(self):
        self.compare_uid = self.env.user.id
        self.compare_date = fields.Datetime.now()
        str_list = self.selected_string_removal()
        # Todo: Pertimbangkan untuk optimasi cari dari similar kota saja
        # Todo: Pertimbangkan 1. Hotel Name = "Hotel Tunjungan Plaza Surabaya"
        # Todo: list pencarian nama ['tunjungan plaza surabaya', 'tunjungan plaza', 'tunjungan surabaya', 'plaza surabaya']
        query = []
        for rec in str_list:
            query.append( ('name','ilike', str(rec)) )
        query += [('id', '!=', self.hotel_id.id), ('state', 'in', ['draft', 'confirm'])]

        list_id = self.env['tt.hotel'].sudo().search(query)
        for rec in list_id:
            a = self.env['tt.hotel.compare'].sudo().create({
                'hotel_id': self.hotel_id.id,
                'comp_hotel_id': rec.id,
                'similar_id': self.id
            })
            a.compare_hotel()
        if len(str_list) > 2:
            query = []
            for rec in str_list[1:len(str_list)]:
                query.append(('name', 'ilike', str(rec)))
            query += [('id', '!=', self.hotel_id.id), ('state', 'in', ['draft', 'confirm'])]

            list2_id = self.env['tt.hotel'].sudo().search(query)

            query = []
            for rec in str_list[:len(str_list)-1]:
                query.append(('name', 'ilike', str(rec)))
            query += [('id', '!=', self.hotel_id.id), ('state', 'in', ['draft', 'confirm'])]

            list2_id += self.env['tt.hotel'].sudo().search(query)

            for rec in list2_id:
                if list2_id not in list_id:
                    a = self.env['tt.hotel.compare'].sudo().create({
                        'hotel_id': self.hotel_id.id,
                        'comp_hotel_id': rec.id,
                        'similar_id': self.id
                    })
                    a.compare_hotel()
        self.end_date = fields.Datetime.now()
        self.similar_length = len(self.similar_ids)


class HotelInformationCompare(models.Model):
    _name = 'tt.hotel.compare'
    _description = 'Merging between 2 hotel that being considered have similarities'

    hotel_id = fields.Many2one('tt.hotel', 'Hotel #1', required="True")
    comp_hotel_id = fields.Many2one('tt.hotel', 'Hotel #2', required=0)

    line_ids = fields.One2many('tt.hotel.compare.line', 'compare_id', 'Line(s)')

    compare_uid = fields.Many2one('res.users', 'Compare by')
    compare_date = fields.Datetime('Compare Date')
    merge_uid = fields.Many2one('res.users', 'Merge by')
    merge_date = fields.Datetime('Merge Date')

    score = fields.Integer('Score')
    similar_id = fields.Many2one('tt.hotel.master', 'Master Hotel', help='Final Product after merged')
    state = fields.Selection([('draft', 'Draft'), ('merge', 'Merged'), ('cancel', 'Cancel')], string='State', default='draft')

    def get_compared_param(self):
        return ['name','rating','address','address2','address3','lat','long','email','city_id','phone','state_id','country_id','provider']

    def collect_hotel(self, params):
        for param in params:
            self.env['tt.hotel.compare.line'].create({
                'compare_id': self.id,
                'params': param,
                'value_1': getfield(self.hotel_id, param),
                'value_2': getfield(self.comp_hotel_id, param),
                'is_value_1': getfield(self.hotel_id, param) != False,
            })

    def compute_score(self):
        score = 0
        for rec in self.line_ids:
            if rec.value_1 and rec.value_2:
                if rec.value_1 == rec.value_2:
                    score += 1
                elif rec.value_1 in rec.value_2:
                    score += 0.5
                elif rec.value_2 in rec.value_1:
                    score += 0.5

        self.score = score and score * 100 / len(self.line_ids) or 0

    # Fungsi digunakan untuk compare 2 data hotel jika mirip maka akan di merge
    def compare_hotel(self):
        if not self.comp_hotel_id:
            raise UserError(_('Fill Compared Hotel First.'))
        params = self.get_compared_param()
        self.collect_hotel(params)
        self.compute_score()

        self.compare_uid = self.env.uid
        self.compare_date = fields.Datetime.now()
        self.comp_hotel_id.state = 'tobe_merge'

    def merge_image(self):
        for img in self.comp_hotel_id.image_ids:
            new_img_id = img.copy()
            new_img_id.hotel_id = self.similar_id.id

    def merge_provider_code(self):
        for provider in self.comp_hotel_id.provider_hotel_ids:
            provider.hotel_id = self.similar_id.id

    # Merge di Hotel #1 & Hotel #2 di non-aktifkan
    # Provider Code di Hotel #2 di pindah ke Hotel #1
    def merge_hotel(self):
        vals = {}
        if not self.similar_id:
            hotel_dict = self.hotel_id.read()[0]
            pop_list = []
            for key in hotel_dict.keys():
                if isinstance(hotel_dict[key], list):
                    pop_list.append(key)
                elif isinstance(hotel_dict[key], tuple):
                    hotel_dict[key] = hotel_dict[key][0]
            for key in pop_list:
                hotel_dict.pop(key)
            self.similar_id = self.env['tt.hotel.master'].create(hotel_dict)
        for rec in self.line_ids:
            if rec.params == 'rating':
                vals[rec.params] = rec.is_value_1 and int(rec.value_1) or int(rec.value_2)
            else:
                vals[rec.params] = rec.is_value_1 and rec.value_1 or rec.value_2
        self.similar_id.update(vals)
        self.merge_image()
        self.merge_provider_code()
        self.similar_id.get_provider_name()

        self.merge_uid = self.env.uid
        self.merge_date = fields.Datetime.now()

        self.comp_hotel_id.state = 'merged'
        self.state = 'merge'

    def cancel_merge_hotel(self):
        if self.comp_hotel_id.state == 'merged':
            self.comp_hotel_id.state = 'draft'
            self.state = 'cancel'

    def set_to_draft(self):
        if self.comp_hotel_id.state == 'draft':
            self.comp_hotel_id.state = 'tobe_merge'
            self.state = 'draft'
        else:
            raise UserError(_('Cannot set to draft because hotel #2 already confirmed. Set Hotel #2 to re compare'))

    def clear_compare_list(self):
        for rec in self.line_ids:
            rec.sudo().unlink()


class HotelInformationCompareLine(models.Model):
    _name = 'tt.hotel.compare.line'
    _description = 'Value Compared'

    compare_id = fields.Many2one('tt.hotel.compare', 'Hotel Compare', ondelete='cascade')
    params = fields.Char('Param(s)', required=1)
    value_1 = fields.Char('Hotel #1')
    value_2 = fields.Char('Hotel #2')
    is_value_1 = fields.Boolean('Hotel 1 Value', help='Using Hotel 1 Value for Hotel Record')


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    def compare_hotel(self):
        compare_id = self.env['tt.hotel.compare'].create({'hotel_id': self.id,})

        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')
        client_action = {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': base_url + "/web#id=" + str(compare_id.id) + "&view_type=form&model=tt.hotel.compare&action=4250",
        }
        return client_action