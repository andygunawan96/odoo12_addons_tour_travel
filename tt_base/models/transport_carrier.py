from odoo import api, fields, models, _
import re

class TransportCarrier(models.Model):
    _name = 'tt.transport.carrier'
    _description = "List of Carrier Code"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', help="for airline : 2-letter IATA")
    icao = fields.Char('ICAO Code', help="ICAO code for airline")
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type')
    call_sign = fields.Char('Call Sign')
    # cancellation_policy = fields.Html('Cancellation Policy')
    # general_policy = fields.Html('General Policy')

    # logo = fields.Binary('Logo', attachment=True,
    #     help='This field holds the image used as avatar for this contact, limited to 1024x1024px')

    active = fields.Boolean('Active', default='True')
    # country_id = fields.Many2one('res.country', 'Country') masihbutuh?

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()

    def get_id(self, code, type='airline'):
        res = self.sudo().search([('code','=',code), ('transport_type', '=', type)])
        return res and res[0].id or False

    def get_carrier_info(self, code):
        res = self.sudo().search([('code','=',code)], limit=1)
        if res:
            return {
                'name': res[0].name,
                'code': res[0].code,
                'display_name': res[0].display_name,
                'logo': res[0].logo,
            }
        return {
                'name': code,
                'code': code,
                'display_name': code,
                'logo': False,
            }

    def get_carrier_list(self, type='airline'):
        data_ids = self.sudo().search([('transport_type', '=', type)])
        res = {}
        [res.update({data.code: data.name}) for data in data_ids if data.code and re.match("^[A-Za-z0-9]*$", data.code)]
        return res

    def to_dict(self):
        return {
            'name': self.name,
            'code': self.code,
            'icao': self.icao,
            'provider_type_id': self.provider_type_id.to_dict(),
            'call_sign': self.transport_type,
            'active': self.active
        }
