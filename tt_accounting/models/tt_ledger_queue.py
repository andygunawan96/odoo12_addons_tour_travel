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
    active = fields.Boolean('Active', default=True)
    ledger_created_date = fields.Datetime('Ledger Created Date', readonly=True)

    def create_queued_ledger(self):
        self.env['tt.ledger'].create(json.loads(self.ledger_values_data))
        self.toggle_active()
        self.ledger_created_date = datetime.now()
        self.update_reversed_ledger_info()

    def update_reversed_ledger_info(self):
        ledger_values = json.loads(self.ledger_values_data)
        if ledger_values.get('reverse_id'):
            reversed_ledger_obj = self.env['tt.ledger'].browse(ledger_values['reverse_id'])
            self.update({
                'reverse_id': reversed_ledger_obj.id,
                'is_reversed': True,
            })