from odoo import api, fields, models, _


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    res_model = fields.Char(
        'Related Reservation Name', index=True)
    res_id = fields.Integer(
        'Related Reservation ID', index=True, help='Id of the followed resource')
