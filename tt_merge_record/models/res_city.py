from odoo import api, fields, models, _
import csv


class ResCity(models.Model):
    _inherit = 'res.city'

    # Internal use only Start
    # Master data dari Inet
    def reader_city_list(self):
        with open('/home/rodex-it-05/Downloads/simplemaps_worldcities_basicv1.5/worldcities.csv', 'r') as f:
            rows = csv.reader(f)
            for rec in rows:
                country_id = self.env['res.country'].search([('code', '=', rec[5])], limit=1)
                if not country_id:
                    country_id = self.env['res.country'].create({'name': rec[4], 'code': rec[5], })
                else:
                    country_id = country_id[0]
                city_id = self.env['res.city'].search(['|', ('name', '=', rec[0]), ('name', '=', rec[1])], limit=1)
                if not city_id:
                    city_id = self.env['res.city'].create({
                        'name': rec[0],
                        'latitude': rec[2],
                        'longitude': rec[3],
                        'country_id': country_id.id,
                    })
                else:
                    city_id = city_id[0]
                if not self.env['tt.destination.alias'].search([('name', '=', rec[1]), ('city_id', '=', city_id.id)]):
                    self.env['tt.destination.alias'].create({'name': rec[1], 'city_id': city_id.id,})
                self.env.cr.commit()

    # Master data dari Andy
    def reader_city_list1(self):
        with open('/home/rodex-it-05/Downloads/simplemaps_worldcities_basicv1.5/res.country.city.csv', 'r') as f:
            rows = csv.reader(f)
            for rec in rows:
                country_id = self.env['res.country'].search([('code', '=', rec[5])], limit=1)
                if not country_id:
                    country_id = self.env['res.country'].create({'name': rec[4], 'code': rec[5], })
                else:
                    country_id = country_id[0]
                city_id = self.env['res.city'].search(['|', ('name', '=', rec[0]), ('name', '=', rec[1])], limit=1)
                if not city_id:
                    city_id = self.env['res.city'].create({
                        'name': rec[0],
                        'latitude': rec[2],
                        'longitude': rec[3],
                        'country_id': country_id.id,
                    })
                else:
                    city_id = city_id[0]
                if not self.env['tt.destination.alias'].search([('name', '=', rec[1]), ('city_id', '=', city_id.id)]):
                    self.env['tt.destination.alias'].create({'name': rec[1], 'city_id': city_id.id,})
                self.env.cr.commit()
    # Internal use only End

    @api.model
    def create(self, vals_list):
        new_obj = super(ResCity, self).create(vals_list)
        self.env['tt.temporary.record'].sudo().create({
            'name': new_obj.name,
            'remove_rec_id': new_obj.id,
            'rec_model': self._name,
        })
        return new_obj


class ResCountry(models.Model):
    _inherit = 'res.country'

    @api.model
    def create(self, vals_list):
        new_obj = super(ResCountry, self).create(vals_list)
        self.env['tt.temporary.record'].sudo().create({
            'name': new_obj.name,
            'remove_rec_id': new_obj.id,
            'rec_model': self._name,
        })
        return new_obj