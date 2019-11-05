from odoo import api,models,fields
import json

class TtSsrAirline(models.Model):
    _name = 'tt.fee.airline'
    _description = 'Feee Airline Model'

    name = fields.Char("Name")
    type = fields.Char("Type")
    code = fields.Char("Code")
    value = fields.Char("Value")
    description = fields.Text("Description")
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency","Currency")
    passenger_id = fields.Many2one("tt.reservation.passenger.airline","Currency")

    def to_dict(self):
        return {
            'fee_name': self.name,
            'fee_type': self.type,
            'fee_code': self.code,
            'fee_value': self.value,
            'description': json.loads(self.description),
            'amount': self.amount,
            'currency_id': self.currency_id.name
        }