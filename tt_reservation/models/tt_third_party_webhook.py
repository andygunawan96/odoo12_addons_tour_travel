from odoo import api, fields, models, _
from ...tools import variables
import json

class TtThirdPartyWebhook(models.Model):
    _name = 'tt.third.party.webhook'
    _description = 'Third Party Webhook Model'

    third_party_data = fields.Text('Third Party Data')
    third_party_provider = fields.Char('Third Party Provider')
    res_model = fields.Char('Related Reservation Name', index=True, readonly=False)
    res_id = fields.Integer('Related Reservation ID', index=True, help='ID of the followed resource', readonly=False)

    def to_dict(self):
        third_party_data = {}
        if self.third_party_data:
            book_obj = self.env[self.res_model].browse(self.res_id)
            third_party_data = json.loads(self.third_party_data)
            if third_party_data.get('urlredirectbook'):
                if third_party_data.get('urlredirectbook')[len(third_party_data['urlredirectbook'])-1] != '/':
                    third_party_data['urlredirectbook'] += '/'
                third_party_data['urlredirectbook'] += '%s' % book_obj.name
            elif third_party_data.get('urlredirectissued'):
                if third_party_data.get('urlredirectissued')[len(third_party_data['urlredirectissued'])-1] != '/':
                    third_party_data['urlredirectissued'] += '/'
                third_party_data['urlredirectissued'] += '%s' % book_obj.name
        return {
            'third_party_data': third_party_data,
            'provider': self.third_party_provider
        }
