from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
from ...tools import variables
from datetime import datetime
from decimal import Decimal


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
            'cust_first_name': self.customer_id.first_name,
            'cust_last_name': self.customer_id.last_name,
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
        # jangan pakai .rs. lagi karena ada pengecekan if rs in charge_code.split('.') untuk csc reschedule post-issued
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
                if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
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

    def get_service_charge_details(self):
        sc_value = {}
        for p_sc in self.cost_service_charge_ids:
            p_charge_type = p_sc.charge_type
            pnr = p_sc.description
            commission_agent_id = p_sc.commission_agent_id

            # if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
            #     if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
            #         continue

            if p_charge_type == 'RAC' and commission_agent_id:
                continue

            if not sc_value.get(pnr):
                sc_value[pnr] = {}
            if not sc_value[pnr].get(p_charge_type):
                sc_value[pnr][p_charge_type] = []

            sc_value[pnr][p_charge_type].append({
                'charge_code': p_sc.charge_code,
                'currency': p_sc.currency_id.name,
                'foreign_currency': p_sc.foreign_currency_id.name,
                'amount': p_sc.amount,
                'pax_type': p_sc.pax_type,
                'foreign_amount': p_sc.foreign_amount,
            })

        result = []
        for pnr, pnr_data in sc_value.items():
            base_fare = Decimal("0.0")
            base_tax = Decimal("0.0")
            base_roc = Decimal("0.0")
            base_commission = Decimal("0.0")
            base_commission_charge = Decimal("0.0")
            base_discount = Decimal("0.0")
            base_commission_upline = Decimal("0.0")
            base_commission_provider_ho = Decimal("0.0")
            base_commission_provider_vat = Decimal("0.0")
            base_commission_ho = Decimal("0.0")
            base_fee_ho = Decimal("0.0")
            base_vat_ho = Decimal("0.0")
            base_vat_provider = Decimal("0.0")
            pax_type = ''

            for charge_type, service_charges in pnr_data.items():
                for sc in service_charges:
                    sc_amount = Decimal(str(sc['amount']))
                    '''
                        FARE, TAX, ROC, RAC, DISC, RACUA, ROCUA,
                        RACHSP, RACHVP, RACAVP, ROCHSP, ROCHVP, ROCAVP,
                        RACHSA, RACHVA, RACAVA, ROCHSA, ROCHVA, ROCAVA,
                        RACHSC, RACHVC, RACAVC, ROCHSC, ROCHVC, ROCAVC,
                    '''
                    if charge_type == 'FARE':
                        base_fare += sc_amount
                    elif charge_type == 'TAX':
                        base_tax += sc_amount
                    elif charge_type == 'ROC':
                        base_roc += sc_amount
                    elif charge_type == 'RAC':
                        base_commission += sc_amount
                    elif charge_type == 'DISC':
                        base_discount += sc_amount
                    elif charge_type == 'RACUA':
                        base_commission_upline += sc_amount
                    elif charge_type == 'ROCUA':
                        pass
                    elif charge_type == 'RACHSP':
                        base_commission_provider_ho += sc_amount
                        base_commission_ho += sc_amount
                    elif charge_type == 'RACHVP':
                        base_commission_ho += sc_amount
                    elif charge_type == 'RACAVP':
                        base_commission_provider_vat += sc_amount
                    elif charge_type == 'ROCHSP':
                        base_fee_ho += sc_amount
                    elif charge_type == 'ROCHVP':
                        base_vat_ho += sc_amount
                    elif charge_type == 'ROCAVP':
                        base_vat_provider += sc_amount
                    elif charge_type == 'ROCCHG':
                        pass
                    elif charge_type == 'RACCHG':
                        base_commission_charge += sc_amount
                    elif charge_type in ['RACHSA', 'RACHVA', 'RACAVA', 'RACHSC', 'RACHVC', 'RACAVC']:
                        base_commission_ho += sc_amount
                    elif charge_type in ['ROCHSA', 'ROCHSC']:
                        base_fee_ho += sc_amount
                    elif charge_type in ['ROCHVA', 'ROCAVA', 'ROCHVC', 'ROCAVC']:
                        base_vat_ho += sc_amount
                    else:
                        base_roc += sc_amount
                    if not pax_type:
                        pax_type = sc['pax_type']

            # base_tax_total = base_tax + base_roc + base_vat_ho
            base_tax_total = base_tax + base_roc
            base_price_ori = base_fare + base_tax
            # base_price = base_fare + base_tax + base_roc + base_discount + base_vat_ho
            base_price = base_fare + base_tax + base_roc + base_discount
            base_commission_airline = base_commission + base_commission_upline + base_commission_provider_ho + base_commission_provider_vat + base_commission_charge
            base_nta = base_price + base_commission
            base_nta_airline = base_price_ori + base_commission_airline

            pax_values = {
                'pnr': pnr,
                'service_charges': pnr_data,
                'pax_type': pax_type,
                'pax_count': 1,
                'base_fare': float(base_fare),
                'base_tax': float(base_tax_total),
                'base_discount': float(base_discount),
                'base_fare_ori': float(base_fare),
                'base_tax_ori': float(base_tax),
                'base_commission': float(base_commission),
                'base_commission_ho': float(base_commission_ho),
                'base_commission_upline': float(base_commission_upline),
                'base_commission_provider_vat': float(base_commission_provider_vat),
                'base_commission_charge': float(base_commission_charge),
                'base_commission_vendor': float(base_commission_airline),
                'base_fee_ho': float(base_fee_ho),
                'base_vat_ho': float(base_vat_ho),
                'base_vat_provider': float(base_vat_provider),
                'base_price': float(base_price),
                'base_price_ori': float(base_price_ori),
                'base_nta': float(base_nta),
                'base_nta_vendor': float(base_nta_airline),
            }
            result.append(pax_values)
        return result

    #butuh field channel_service_charge_ids
    def get_channel_service_charges(self):
        total = 0
        total_addons = 0
        amt_rs_dict = {}
        currency_code = 'IDR'

        for rec in self.channel_service_charge_ids:
            if rec.charge_code == 'csc':
                total += rec.amount
            elif rec.charge_code == 'csc.addons':
                total_addons += rec.amount
            else:
                if rec.description:
                    if amt_rs_dict.get(rec.description):
                        amt_rs_dict[rec.description] += rec.amount
                    else:
                        amt_rs_dict.update({
                            rec.description: rec.amount
                        })
            currency_code = rec.currency_id.name

        return {
            'amount': total,
            'amount_addons': total_addons,
            'amount_rs': amt_rs_dict,
            'currency_code': currency_code
        }
