from odoo import api,models,fields
import json

class TtFeeInsurance(models.Model):
    _name = 'tt.fee.insurance'
    _description = 'Fee Insurance Model'

    name = fields.Char("Name")
    description = fields.Text("Description")
    amount = fields.Monetary("Amount")
    currency_id = fields.Many2one("res.currency","Currency",default=lambda self:self.env.user.company_id.currency_id)
    passenger_id = fields.Many2one("tt.reservation.passenger.insurance","Passenger")
    provider_id = fields.Many2one('tt.provider.insurance', 'Provider', default=None)
    pnr = fields.Char('PNR', default='')
    # May 18, 2020 - SAM
    # END

    def to_dict(self):
        return {
            'fee_name': self.name,
            'description': json.loads(self.description),
            'amount': self.amount,
            'currency': self.currency_id.name,
            'pnr': self.provider_id and self.provider_id.pnr or '',
        }

    def convert_json_to_str(self, json_data):
        return json_data