from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
from ...tools import variables
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger'
    _description = 'Reservation Passenger'

    name = fields.Char(string='Name')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    gender = fields.Selection(variables.GENDER, string='Gender')
    title = fields.Selection(variables.TITLE, string='Title')
    birth_date = fields.Date('Birth Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    identity_type = fields.Selection(variables.IDENTITY_TYPE,'Identity Type')
    identity_number = fields.Char('Identity Number')
    identity_expdate = fields.Date('Identity Expire Date')
    identity_country_of_issued_id = fields.Many2one('res.country','Identity Issued  Country')
    is_valid_identity = fields.Boolean('Is Valid Identity', default=True)
    customer_id = fields.Many2one('tt.customer','Customer Reference')
    sequence = fields.Integer('Sequence')

    def to_dict(self):
        res = {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name and self.last_name or '',
            'gender': self.gender,
            'title': self.title,
            'birth_date': self.birth_date and self.birth_date.strftime('%Y-%m-%d') or '',
            'nationality_code': self.nationality_id.code and self.nationality_id.code or '',
            'identity_country_of_issued_code': self.identity_country_of_issued_id and self.identity_country_of_issued_id.code or '',
            'identity_type': self.identity_type and self.identity_type or '',
            'identity_number': self.identity_number and self.identity_number or '',
            'identity_expdate': self.identity_expdate and self.identity_expdate.strftime('%Y-%m-%d'),
            'sequence': self.sequence,
            'is_valid_identity': self.is_valid_identity
        }
        return res

    def create_channel_pricing(self,channel_prices,type=''):
        is_post_issued = False
        if type == 'request_new':
            ch_code = 'csc.addons'
        elif len(type.split('~')) > 1:
            ch_code = 'csc.rs.%s' % (type.split('~')[1])
            is_post_issued = True
        else:
            ch_code = 'csc'

        if is_post_issued:
            rs_idx = 1
            for rec in self.channel_service_charge_ids.filtered(lambda x: 'rs' in x.charge_code.split('.')):
                rs_idx += 1
            ch_code = 'csc.rs.%s.%s' % (str(rs_idx), type.split('~')[1])
        else:
            for rec in self.channel_service_charge_ids.filtered(lambda x: x.charge_code == ch_code):
                rec.unlink()

        currency_obj = self.env['res.currency']
        for sc in channel_prices:
            sc['currency_id'] = currency_obj.search([('name','=',sc.pop('currency_code'))]).id
            sc['charge_code'] = ch_code
            sc['charge_type'] = 'CSC'
            self.write({
                'channel_service_charge_ids': [(0,0,sc)]
            })

    #butuh field cost_service_charge_ids
    def get_service_charges(self):
        sc_value = {}
        for p_sc in self.cost_service_charge_ids:
            p_charge_type = p_sc.charge_type
            pnr = p_sc.description

            if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
                continue

            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = {
                    'amount': 0,
                    'foreign_amount': 0,
                    'charge_code': '',
                    'currency': '',
                    'foreign_currency': '',
                }

            sc_value[pnr][p_charge_type].update({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': sc_value[pnr][p_charge_type]['amount'] + p_sc.amount,
                # 'amount': p_sc.amount,
                'foreign_amount': sc_value[pnr][p_charge_type]['foreign_amount'] + p_sc.foreign_amount,
                'pax_type': p_sc.pax_type #untuk ambil pax type di to_dict
                # 'foreign_amount': p_sc.foreign_amount,
            })

        return sc_value

    #butuh field channel_service_charge_ids
    def get_channel_service_charges(self):
        total = 0
        total_addons = 0
        total_rs = 0
        currency_code = 'IDR'
        for rec in self.channel_service_charge_ids:
            if rec.charge_code == 'csc':
                total += rec.amount
            elif rec.charge_code == 'csc.addons':
                total_addons += rec.amount
            else:
                total_rs += rec.amount
            currency_code = rec.currency_id.name

        return {
            'amount': total,
            'amount_addons': total_addons,
            'amount_rs': total_rs,
            'currency_code': currency_code
        }
