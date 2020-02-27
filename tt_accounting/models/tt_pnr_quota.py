from odoo import models, fields, api, _

class TtPnrQuota(models.Model):
    _inherit = 'tt.pnr.quota'

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger(s)', domain=[('res_model','=','tt.pnr.quota')])