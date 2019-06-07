from odoo import models, fields


class TourImages(models.Model):
    _name = 'tt.tour.images'

    url = fields.Char('URL', required=True)
    description = fields.Text('Description')
    pricelist_id = fields.Many2one('tt.tour.pricelist', 'Pricelist ID')
