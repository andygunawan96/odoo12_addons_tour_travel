from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
from ...tools import variables
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger'

    name = fields.Char(string='Name')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')
    title = fields.Selection(variables.TITLE, string='Title')
    birth_date = fields.Date('Birth Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    identity_type = fields.Selection(variables.IDENTITY_TYPE, 'Identity Type')
    identity_number = fields.Char('Identity Number')
    country_of_issued_id = fields.Many2one('res.country', 'Country of Issued')  # for passport
    customer_id = fields.Many2one('tt.customer','Customer Reference')
    sequence = fields.Integer('Sequence')

    def to_dict(self):
        res = {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name and self.last_name or '',
            'gender': self.gender,
            'title': self.title,
            'birth_date': self.birth_date.strftime('%Y-%m-%d'),
            'nationality_code': self.nationality_id.code and self.nationality_id.code or '',
            'country_of_issued_code': self.country_of_issued_id.code and self.country_of_issued_id.code or '',
            'identity_type': self.identity_type and self.identity_type or '',
            'identity_number': self.identity_number and self.identity_number or '',
            'sequence': self.sequence
        }
        return res

    def create_channel_pricing(self,channel_prices):
        for rec in self.channel_service_charge_ids:
            rec.unlink()
        currency_obj = self.env['res.currency']
        for sc in channel_prices:
            sc['currency_id'] = currency_obj.search([('name','=',sc.pop('currency_code'))]).id
            sc['charge_code'] = 'csc'
            sc['charge_type'] = 'CSC'
            self.write({
                'channel_service_charge_ids': [(0,0,sc)]
            })