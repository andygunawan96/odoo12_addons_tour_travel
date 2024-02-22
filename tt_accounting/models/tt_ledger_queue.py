from odoo import api, fields, models, _
from datetime import datetime
import json
class LedgerQueue(models.Model):
    _name = 'tt.ledger.queue'
    _order = 'id DESC'
    _description = 'Ledger Queue'

    name = fields.Char('Name', required=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    ledger_values_data = fields.Text('Value Data', required=True)
    res_model = fields.Char(
        'Related Ledger Owner Name', index=True)
    res_id = fields.Integer(
        'Related Ledger Owner ID', index=True, help='ID of the followed resource')
    active = fields.Boolean('Active', default=True)
    is_reverse_ledger_queue = fields.Boolean('Is Reverse', default=False)
    ledger_created_date = fields.Datetime('Ledger Created Date', readonly=True)

    def create_queued_ledger(self):
        self.env['tt.ledger'].create(json.loads(self.ledger_values_data))
        self.active = False
        self.ledger_created_date = datetime.now()

    #todo untuk kondisi queue belum created, tetapi reservasi sdh di reverse. coba find reference terus cancel queuenya.