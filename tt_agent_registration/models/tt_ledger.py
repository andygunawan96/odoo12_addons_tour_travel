from odoo import api, fields, models, _


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    res_id = fields.Integer('Related Reservation ID', index=True, help='Id of the followed resource')
    # res_model = fields.Char('Related Document Model Name', required=True, index=True)
