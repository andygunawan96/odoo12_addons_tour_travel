from odoo import api, fields, models, _


class TourChecklist(models.Model):
    _name = 'tt.reservation.tour.checklist'
    _description = 'Rodex Model'

    item = fields.Char('Item')
    description = fields.Char('Description')
    quantity = fields.Integer('Quantity')
    is_checked = fields.Boolean('Is Checked')
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Pricelist ID', readonly=True)
