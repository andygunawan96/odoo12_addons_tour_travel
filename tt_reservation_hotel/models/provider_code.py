from odoo import models, fields, api
from datetime import date, datetime, timedelta

# TODO remove this part
class ProviderCode(models.Model):
    _inherit = 'tt.provider.code'

    hotel_id = fields.Many2one('tt.hotel', 'Hotel')
    facility_id = fields.Many2one('tt.hotel.facility', 'Facility')
    type_id = fields.Many2one('tt.hotel.type', 'Type')


class Hotel(models.Model):
    _inherit = "tt.hotel"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    provider_hotel_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, hotel_id, provider_id):
        a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelFacility(models.Model):
    _inherit = "tt.hotel.facility"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, facility_id, provider_id):
        a = self.env['tt.provider.code'].search([('facility_id', '=', facility_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelType(models.Model):
    _inherit = "tt.hotel.type"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code


class HotelDestination(models.Model):
    _inherit = "tt.hotel.destination"

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]
    provider_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)

    def get_provider_code(self, type_id, provider_id):
        a = self.env['tt.provider.code'].search([('type_id', '=', type_id), ('provider_id', '=', provider_id)], limit= 1)
        return a.code

    def multi_merge_destination(self):
        max_len = 0
        max_obj = False
        # Cari provider ids terpanjang
        for rec in self:
            if max_len < len(rec.provider_ids.ids) + len(rec.hotel_ids.ids):
                max_len = len(rec.provider_ids.ids)
                max_obj = rec

        # Buat Merge Record
        for rec in self:
            if rec.id != max_obj.id:
                # Ambil data slave jika data dari master kosong
                max_obj.copy_value_if_empty(rec.id)
                new_temp_obj = self.env['tt.temporary.record'].sudo().create({
                    'name': rec.name,
                    'parent_rec_id': max_obj.id,
                    'remove_rec_id': rec.id,
                    'rec_model': self._name,
                })
                new_temp_obj.action_merge()

# class HotelMaster(models.Model):
#     _inherit = "tt.hotel.master"

    # def _get_res_model_domain(self):
    #     return [('res_model', '=', self._name)]
    #
    # provider_hotel_ids = fields.One2many('tt.provider.code', 'res_id', 'Provider External Code', domain=_get_res_model_domain)
    #
    # def get_provider_code(self, hotel_id, provider_id):
    #     a = self.env['tt.provider.code'].search([('hotel_id', '=', hotel_id), ('provider_id', '=', provider_id)], limit= 1)
    #     return a.code


class TtTemporaryRecord(models.Model):
    _inherit = 'tt.temporary.record'

    @api.multi
    def action_merge(self):
        result = super(TtTemporaryRecord, self).action_merge()
        # Move Provider Code e juga
        update_obj = []
        for rec in self.env['tt.provider.code'].search([('res_model','=',self.rec_model),('res_id','=',self.remove_rec_id)]):
            rec.res_id = self.parent_rec_id
            update_obj.append(rec.id)

        data = self.get_field_in_prov_code()
        if data.get(self.rec_model):
            for rec in self.env['tt.provider.code'].search([(data[self.rec_model], '=', self.remove_rec_id)]):
                rec.update({data[self.rec_model]: self.parent_rec_id})
                update_obj.append(rec.id)

        for rec in list( dict.fromkeys(update_obj) ):
            self.env['tt.record.move.line'].create({
                'temp_rec_id': self.id,
                'rec_id': rec,
                'rec_model': 'tt.provider.code',
            })
        return result

    @api.multi
    def action_revert(self):
        result = super(TtTemporaryRecord, self).action_revert()
        for rec in self.env['tt.record.move.line'].search([('temp_rec_id', '=', self.id)]):
            if rec.rec_model == 'tt.provider.code':
                code_obj = self.env[rec.rec_model].browse(rec.rec_id)
                code_obj.res_id = self.remove_rec_id
                code_obj.format_old()
                rec.sudo().unlink()
        return result