from odoo import models, fields


class TourImages(models.Model):
    _name = 'tt.reservation.tour.images'

    url = fields.Char('URL', required=True)
    description = fields.Text('Description')
    pricelist_id = fields.Many2one('tt.reservation.tour.pricelist', 'Pricelist ID')
