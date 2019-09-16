from odoo import api,fields,models

class TtTopUpInh(models.Model):
    _inherit = 'tt.top.up'

    payment_id = fields.Many2one('tt.payment','Payment')