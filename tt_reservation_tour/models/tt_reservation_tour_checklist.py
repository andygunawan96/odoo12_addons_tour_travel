from odoo import api, fields, models, _


class TourChecklist(models.Model):
    _name = 'tt.reservation.tour.checklist'

    item = fields.Char('Item')
    description = fields.Char('Description')
    quantity = fields.Integer('Quantity')
    is_checked = fields.Boolean('Is Checked')
    tour_pricelist_id = fields.Many2one('tt.reservation.tour.pricelist', 'Pricelist ID', readonly=True)
