from odoo import api, fields, models, _
from ...tools import variables
import json

class TtThirdPartyWebhook(models.Model):
    _name = 'tt.third.party.webhook'
    _description = 'Third Party Webhook Model'

    third_party_data = fields.Text('Third Party Data')
    third_party_provider = fields.Char('Third Party Provider')

    def to_dict(self):
        return {
            'third_party_data': json.loads(self.third_party_data) if self.third_party_data else {},
            'provider': self.third_party_provider
        }
