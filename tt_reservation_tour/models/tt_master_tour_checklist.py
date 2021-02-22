from odoo import api, fields, models, _


class TourChecklist(models.Model):
    _name = 'tt.master.tour.checklist'
    _description = 'Master Tour Checklist'

    item = fields.Char('Item')
    description = fields.Char('Description')
    quantity = fields.Integer('Quantity')
    is_checked = fields.Boolean('Is Checked')
    tour_pricelist_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
