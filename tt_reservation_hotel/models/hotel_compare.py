from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from ...tools.timer import Timer


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
        self.write({
            'hotel_name': '',
            'compare_uid': False,
            'compare_date': False,
            'end_date': False,
        })

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

    hotel_id = fields.Many2one('tt.hotel', 'Hotel #1', required="True", description='Raw Data')
    comp_hotel_id = fields.Many2one('tt.hotel.master', 'Hotel #2', required=0, description='Master Data(Record Merged into this record)')

    line_ids = fields.One2many('tt.hotel.compare.line', 'compare_id', 'Line(s)')

    compare_uid = fields.Many2one('res.users', 'Compare by')
    compare_date = fields.Datetime('Compare Date')
    merge_uid = fields.Many2one('res.users', 'Merge by')
    merge_date = fields.Datetime('Merge Date')

    score = fields.Integer('Score')
    similar_id = fields.Many2one('tt.hotel.master', 'Master Hotel', help='Final Product after merged')
    state = fields.Selection([('draft', 'Draft'), ('tobe_merge', 'To Be Merged'), ('merge', 'Merged'), ('cancel', 'Cancel')], string='State', default='draft')

    hotel_state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('expired', 'Not Available'),
                              ('tobe_merge', 'To Be Merge'), ('merged', 'Merged')], related='hotel_id.state', string="Hotel #1 Current State")

    def get_compared_param(self):
        return ['name','rating','address','address2','address3','lat','long','email','destination_id','city_id','phone','state_id','country_id','provider']

    def get_length(self, target_obj, param):
        if getfield(target_obj, param):
            try:
                # Itank kadang return lat long 0.000000
                return len(str(float(getfield(target_obj, param))))
            except:
                return len(str(getfield(target_obj, param)))
        else:
            return 0

    def collect_hotel(self, params):
        for param in params:
            self.env['tt.hotel.compare.line'].create({
                'compare_id': self.id,
                'params': param,
                'value_1': getfield(self.hotel_id, param),
                'value_2': getfield(self.comp_hotel_id, param),
                'is_value_1': self.get_length(self.hotel_id, param) > self.get_length(self.comp_hotel_id, param)
            })

    def empty_compare_line(self):
        for rec in self.line_ids:
            rec.sudo().unlink()

    def remove_prefix_value(self, val_str, src_str_list=[]):
        for idx in range(len(val_str)):
            if val_str[idx] not in src_str_list:
                return val_str[idx:]
        return val_str

    def count_simple_string(self, value_1, value_2):
        split_value_1 = [a for a in value_1.split(' ') if a != ''] # Grande Bay 124
        split_value_2 = [a for a in value_2.split(' ') if a != ''] # Grande Bay South West
        if len(split_value_1) > 1 or len(split_value_2) > 1:
            exist = 0
            for val in split_value_1:
                if val in split_value_2:
                    exist += 1
            return exist / max(len(split_value_1), len(split_value_2))
        else:
            if value_1 == value_2:
                return 1
            elif value_1 in value_2:
                return len(value_1) / len(value_2)
            elif value_2 in value_1:
                return len(value_2) / len(value_1)
        return 0

    def count_similarity_string(self, record):
        rmv_param = []
        rmv_str = []
        temp_rec_1 = record.value_1.lower()
        temp_rec_2 = record.value_2.lower()
        const = 5

        if record.params in ['name']:
            rmv_param += ['-','"',"'",'!','@',':']
            rmv_str += ['hotel', 'motel', 'cottage', '&', 'and', '@', 'at']
            if record.compare_id.hotel_id.city_id.name == record.compare_id.comp_hotel_id.city_id.name and record.compare_id.comp_hotel_id.city_id.name != False:
                rmv_str += [record.compare_id.hotel_id.city_id.name.lower()]
            if record.compare_id.hotel_id.destination_id.name == record.compare_id.comp_hotel_id.destination_id.name and record.compare_id.comp_hotel_id.destination_id.name != False:
                rmv_str += [record.compare_id.hotel_id.destination_id.name.lower()]
        elif record.params in ['address']:
            rmv_param += ['-', '+', '.', ',', '/', '(', ')', ';', '–'] # Pertimbangkan pengunaan '(' , ')'
            # Contoh: Jl. P. Mangkubumi 57/59 vs Jl. Margoutomo (P. Mangkubumi)
            rmv_str = ['jalan', 'jl', 'jln', 'no', 'street']
            if record.compare_id.hotel_id.city_id.name == record.compare_id.comp_hotel_id.city_id.name and record.compare_id.comp_hotel_id.city_id.name != False:
                rmv_str += [record.compare_id.hotel_id.city_id.name.lower()]
            if record.compare_id.hotel_id.destination_id.name == record.compare_id.comp_hotel_id.destination_id.name and record.compare_id.comp_hotel_id.destination_id.name != False:
                rmv_str += [record.compare_id.hotel_id.destination_id.name.lower()]
        elif record.params in ['phone']:
            const = 3
            rmv_param += ['+',' ','-','.','(',')','/'] # '/' pertmbangkan nmbah char ini
            temp_rec_1 = ''.join([e for e in temp_rec_1 if e not in rmv_param])
            temp_rec_2 = ''.join([e for e in temp_rec_2 if e not in rmv_param])
            # TODO mekanisme hitung nomor telp dengan kode wilayah

            # TODO pertimbangkan '/', sebagai separator nomor misal 8661511/12
            # ';', sebagai separator nomor misal +62 21 7664922;(0967) 522345
            temp_result = 0
            for split_temp_rec_1 in temp_rec_1.split(';'):
                for split_temp_rec_2 in temp_rec_2.split(';'):
                    # TODO recheck this Methods START
                    # Remove '0' di paling depan
                    # CTH case: 0318661512 vs 62318661512 result 0
                    split_temp_rec_1 = self.remove_prefix_value(split_temp_rec_1, ['0'])
                    split_temp_rec_2 = self.remove_prefix_value(split_temp_rec_2, ['0'])
                    # TODO recheck this Methods END
                    temp_result = max(self.count_simple_string(split_temp_rec_1, split_temp_rec_2),temp_result)
            return const - 1, temp_result * const
        elif record.params in ['lat', 'long']:
            const = 1
            temp_rec_1 = temp_rec_1.replace("'", '').replace('"', '')
            temp_rec_2 = temp_rec_2.replace("'", '').replace('"', '')
            try:
                temp_rec_1 = float(temp_rec_1)
                temp_rec_2 = float(temp_rec_2)
                temp_result = 0
                x = 8
                while temp_result == 0:
                    temp_result = self.count_simple_string(str(round(temp_rec_1, x)), str(round(temp_rec_2, x)))
                    if x == 2:
                        return const - 1, 0
                    if temp_result != 1:
                        x -= 1
                return const - 1, (x / 8) * const
            except:
                return const - 1, 0

        if rmv_param:
            for x in [temp_rec_1, temp_rec_2]:
                new_x = []
                for idx, a in enumerate(x):
                    if a in rmv_param:
                        # Cek apakah 1 di depan / dibelakang ada ' '/(spasi)
                        # Cek apakah dia awal kata / akhir kata
                        if idx in [0, len(x)-1] or (x[idx-1] == ' ' or x[idx+1] == ' '):
                            # jika iya hapus contoh: jalan mawar, kabupaten SDA => jalan mawar kabupaten SDA
                            new_x += ''
                        else:
                            # jika tidak replace contoh: ruko 123-125 => ruko 123 125
                            new_x += ' '
                    else:
                        new_x += x[idx]
                if x == temp_rec_1:
                    temp_rec_1 = ''.join(new_x)
                else:
                    temp_rec_2 = ''.join(new_x)

        temp_rec_1 = ' '.join([e for e in temp_rec_1.split(' ') if e not in rmv_str])
        temp_rec_2 = ' '.join([e for e in temp_rec_2.split(' ') if e not in rmv_str])
        return const - 1, self.count_simple_string(temp_rec_1, temp_rec_2) * const

    def compute_score(self):
        score = 0
        max_score = 0
        for rec in self.line_ids:
            if rec.value_1 and rec.value_2 and rec.params not in ['address2', 'provider']:
                if rec.params in ['name', 'address', 'phone', 'lat', 'long']:
                    max_score_cou, score_cou = self.count_similarity_string(rec)
                    score += score_cou
                    max_score += max_score_cou
                    rec.write({
                        'similarity_value': score_cou,
                        'max_value': max_score_cou + 1
                    })
                else:
                    score_cou = self.count_simple_string(rec.value_1, rec.value_2)
                    score += score_cou
                    rec.write({
                        'similarity_value': score_cou,
                        'max_value': 1
                    })
                max_score += 1
            # Part ini untuk field yg mesti ada (bisa jadi name mirip tpi yg 1 alamate kosong sehingga angkane tinggi)
            # Name 1: Grand Kamala Lagoon By Veeroom, Name 2: Superior @ Grand Kamala Lagoon By Eha Room
            # Almat 1 kosong total score: 73
            elif rec.params in ['name', 'address']:
                max_score += 5
                rec.write({
                    'similarity_value': 0,
                    'max_value': 5
                })


        self.score = score and score * 100 / max_score or 0

    # Fungsi digunakan untuk compare 2 data hotel jika mirip maka akan di merge
    def compare_hotel(self):
        if not self.comp_hotel_id:
            raise UserError(_('Fill Compared Hotel First.'))
        if self.hotel_id == self.comp_hotel_id:
            raise UserError(_('Hotel#1 and Hotel#2 cannot be same object'))

        params = self.get_compared_param()
        self.empty_compare_line()
        self.collect_hotel(params)
        self.compute_score()

        self.write({
            'compare_uid': self.env.uid,
            'compare_date': fields.Datetime.now()
        })
        self.comp_hotel_id.state = 'tobe_merge'

    # ======= Part Rubah State blum merge trigger Start=======
    def to_merge_hotel(self):
        self.hotel_id.state = 'tobe_merge'
        self.state = 'tobe_merge'

    def to_merge_hotel_checker(self):
        # TODO: Cek tiap mau merge apa hotel yg yg mau di bandingkan masih ready?
        # TODO: Jika Hotel status tobe_Merge kita kluarkan Notif user untuk pilih hotel raw tersebut
        # ingin di merge Hotel Master yg mana
        if self.hotel_id.state == 'tobe_merge':
            # Find Comparer ambil(Nama Comparer, Nama Master, Total Score)
            similar_str = []
            for rec in self.search([('state', 'in', ['tobe_merge','merge']), ('hotel_id', '=', self.hotel_id.id)]):
                similar_str.append('{}: {} score:{} ({})'.format(rec.id, (rec.comp_hotel_id and rec.comp_hotel_id.name or 'New Record'), rec.score, rec.state))
            raise UserError('Hotel #1 Already Merged in other Comparer with ID: ' + ', '.join(similar_str))
        self.to_merge_hotel()

    def decline_merge_hotel(self):
        if self.state != 'draft':
            raise UserError('Hotel #1 state Must Draft')
        self.state = 'cancel'
        self.similar_id = False

    def set_to_draft(self):
        if self.state == 'cancel':
            self.state = 'draft'
        elif self.hotel_id.state == 'merged':
            any_merged = False
            for comp_id in self.hotel_id.compare_ids:
                if comp_id.state == 'merge':
                    any_merged = True
                    break
            if not any_merged:
                self.hotel_id.state = 'draft'
            self.state = 'draft'
        elif self.state != 'tobe_merge':
            if self.state == 'merge':
                raise UserError('Cannot Cancelling Merge Document already Merged')
            else:
                raise UserError('Cannot Cancelling Merge')
        else:
            self.hotel_id.state = 'draft'
            self.state = 'draft'

    def merge_image(self):
        # Note: Dulu kita copy ulang gmbare skrg cman tmbahin value sja
        if hasattr(self.hotel_id, 'image_ids'):
            for img in self.hotel_id.image_ids:
                img.master_hotel_id = self.similar_id.id

    def merge_facility(self):
        # Note: Dulu kita copy ulang gmbare skrg cman tmbahin value sja
        if hasattr(self.hotel_id, 'facility_ids'):
            self.similar_id.facility_ids = [(4, fac.id) for fac in self.hotel_id.facility_ids]

    # Temporary function karena ada rbah strukture DB
    def re_calc_facility(self):
        for hotel_comp in self.similar_id.compare_ids:
            hotel_comp.merge_facility()

    def unmerge_image(self):
        # Note: Dulu kita copy ulang gmbare skrg cman tmbahin value sja
        for img in self.hotel_id.image_ids:
            img.master_hotel_id = False

    def unmerge_facility(self):
        # Ini resiko klo misal vendor A dan Vendor B pny facility yg sama (Swimming pool) nanti bakal kedelet
        # for fac in self.hotel_id.facility_ids:
        #     self.similar_id.facility_ids = [(3,fac.id)]
        # TODO Mekanisme Paling Bagus:
        # 1. Delete ulang
        self.similar_id.facility_ids = [(5)]
        # 2. Ambil Facility dari current Provider
        for hotel_comp in self.similar_id.compare_ids:
            hotel_comp.merge_facility()

    # Cancel klo dah ke merge
    def cancel_merge_hotel(self):
        if self.state == 'merge':
            # Update Value ke value sebelum merge
            for rec in self.line_ids:
                if rec.is_value_1:
                    self.comp_hotel_id.write({
                        rec.params: rec.params == 'rating' and int(rec.value_2) or rec.value_2
                    })
            self.similar_id.info_ids = [(3, self.hotel_id.id)]

            hotel_state = 'draft'
            for rec in self.hotel_id.compare_ids:
                if rec['state'] == 'merge':
                    hotel_state = 'merged'
                    break
                elif rec['state'] == 'tobe_merge':
                    hotel_state = 'tobe_merge'
                    break

            self.hotel_id.state = hotel_state
            self.state = 'cancel'
            self.unmerge_image()
            self.unmerge_facility()

            if all(rec.state == 'cancel' for rec in self.comp_hotel_id.compare_ids):
                self.similar_id.sudo().unlink()
            self.similar_id = False
        else:
            raise UserError('Cannot UnMerge this comparing process')

    # ======= Part Rubah State blum merge trigger END  =======

    def merge_provider_code(self):
        for provider in self.comp_hotel_id.provider_hotel_ids:
            provider.hotel_id = self.similar_id.id

    def merge_hotel(self):
        vals = {}
        if not self.comp_hotel_id:
            hotel_dict = self.hotel_id.read()[0]
            pop_list = []
            for key in hotel_dict.keys():
                if isinstance(hotel_dict[key], list):
                    pop_list.append(key)
                elif isinstance(hotel_dict[key], tuple):
                    hotel_dict[key] = hotel_dict[key][0]
            for key in pop_list:
                hotel_dict.pop(key)
            hotel_dict['info_ids'] = [(4, self.hotel_id.id)]
            self.similar_id = self.env['tt.hotel.master'].create(hotel_dict)
            self.similar_id.state = 'draft'
        else:
            if not self.hotel_id.provider_hotel_ids:
                # Logger g bis proses soaale hotel yg mau di mapping g ada provider e
                return False
            self.similar_id = self.comp_hotel_id
            # _TIMER2 = Timer('Render Line')
            for rec in self.line_ids:
                if rec.params == 'rating':
                    vals[rec.params] = rec.is_value_1 and int(rec.value_1) or int(rec.value_2)
                else:
                    vals[rec.params] = rec.is_value_1 and rec.value_1 or rec.value_2
            vals['info_ids'] = [(4, self.hotel_id.id)]
            self.similar_id.write(vals)
            # _TIMER2.stop()
            # _TIMER3 = Timer('Merge Provider Code')
            self.merge_provider_code()
            # _TIMER3.stop()

        # _TIMER4 = Timer('Facility')
        # if not self.comp_hotel_id.facility_ids:
        #     self.merge_facility()
        # _TIMER4.stop()

        # _TIMER5 = Timer('Merge Image')
        self.merge_image()
        # _TIMER5.stop()
        # _TIMER6 = Timer('Adding similar')
        self.similar_id.get_provider_name()
        # _TIMER6.stop()

        # _TIMER7 = Timer('Merge Time')
        self.update({
            'merge_uid': self.env.uid,
            'merge_date': fields.Datetime.now(),
            'state': 'merge'
        })
        self.hotel_id.state = 'merged'
        # _TIMER7.stop()

    # ======= Part Extra tool(s) =======
    def multi_merge_hotel(self):
        for idx, rec in enumerate(self):
            try:
                rec.merge_hotel()
            except:
                # Logger yg error yg mna
                continue

            if idx % 10 == 0:
                self.env.cr.commit()

    def multi_decline_hotel(self):
        for rec in self:
            rec.decline_merge_hotel()

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
    similarity_value = fields.Char('Similarity')
    max_value = fields.Char('Max')
    is_value_1 = fields.Boolean('Hotel 1 Value', help='Using Hotel 1 Value for Hotel Record')


class HotelInformation(models.Model):
    _inherit = 'tt.hotel'

    compare_ids = fields.One2many('tt.hotel.compare', 'hotel_id', 'Compared', ondelete="cascade")

    def compare_hotel(self):
        compare_id = self.env['tt.hotel.compare'].create({'hotel_id': self.id,})

        base_url = self.sudo().env['ir.config_parameter'].get_param('web.base.url')
        client_action = {
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': base_url + "/web#id=" + str(compare_id.id) + "&view_type=form&model=tt.hotel.compare",
        }
        return client_action