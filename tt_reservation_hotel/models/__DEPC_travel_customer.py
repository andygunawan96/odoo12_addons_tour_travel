from odoo import api, fields, models, _

class TravelCustomer(models.Model):
    _inherit = 'tt.customer.details'

    hotel_res_id = fields.Many2one('tt.reservation.hotel', 'Hotel Book ID')