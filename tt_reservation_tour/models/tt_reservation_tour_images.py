from odoo import models, fields


class TourImages(models.Model):
    _name = 'tt.reservation.tour.images'
    _description = 'Rodex Model'

    url = fields.Char('URL', required=True)
    description = fields.Text('Description')
    pricelist_id = fields.Many2one('tt.master.tour', 'Pricelist ID')
