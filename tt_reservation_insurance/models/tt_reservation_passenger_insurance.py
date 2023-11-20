from dateutil.relativedelta import relativedelta
from odoo import api,models,fields
import json
from ...tools import variables,util
from datetime import datetime

class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.passenger.insurance'
    _inherit = 'tt.reservation.passenger'
    _description = 'Reservation Passenger Insurance'

    seq_id = fields.Char('Sequence ID', index=True, readonly=True)
    cost_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_insurance_cost_charge_rel', 'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge','tt_reservation_insurance_channel_charge_rel', 'passenger_id', 'service_charge_id', 'Channel Service Charges')
    booking_id = fields.Many2one('tt.reservation.insurance')
    is_ticketed = fields.Boolean('Ticketed')
    account_number = fields.Char('Passenger Account Number')
    account_name = fields.Char('Passenger Account Name')
    email = fields.Char('Email')
    phone_number = fields.Char('Phone Number')
    passport_type = fields.Selection(variables.IDENTITY_TYPE, 'Passport Type')
    passport_number = fields.Char('Passport Number')
    passport_expdate = fields.Date('Passport Expire Date')
    passport_country_of_issued_id = fields.Many2one('res.country', 'Passport Issued Country')
    insurance_data = fields.Text('Insurance Data')
    fee_ids = fields.One2many('tt.fee.insurance', 'passenger_id', 'Additional Fee')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.reservation.passenger.insurance')
        return super(TtReservationCustomer, self).create(vals_list)

    def to_dict(self):
        res = super(TtReservationCustomer, self).to_dict()

        insurance_data = self.insurance_data and json.loads(self.insurance_data) or {}

        if 'addons' in insurance_data:
            for idx,rec in enumerate(insurance_data['addons']):
                for idy, child in enumerate(rec['child']):
                    for idz, detail in enumerate(child['detail']):
                        if detail == None:
                            insurance_data['addons'][idx]['child'][idy]['detail'][idz] = ''
                for idy, detail in enumerate(rec['detail']):
                    if detail == None:
                        insurance_data['addons'][idx]['detail'][idy] = ''
                if rec['timelimitdisplay'] == None:
                    insurance_data['addons'][idx]['timelimitdisplay'] = ''
        sale_service_charges = self.get_service_charges()
        service_charge_details = self.get_service_charge_details()
        pax_type = ''
        for pnr in sale_service_charges:
            for svc in sale_service_charges[pnr]:
                pax_type = sale_service_charges[pnr][svc]['pax_type']
                break
            break
        res.update({
            'sale_service_charges': sale_service_charges,
            'service_charge_details': service_charge_details,
            'passport_type': self.passport_type and self.passport_type or '',
            'passport_number': self.passport_number and self.passport_number or '',
            'passport_expdate': self.passport_expdate and self.passport_expdate.strftime('%Y-%m-%d'),
            'passport_country_of_issued_id': self.passport_country_of_issued_id and self.passport_country_of_issued_id.code or '',
            'insurance_data': insurance_data,
            'email': self.email,
            'phone_number': self.phone_number,
            'seq_id': self.seq_id,
            'pax_type': pax_type
        })
        if len(self.channel_service_charge_ids.ids)>0:
            res['channel_service_charges'] = self.get_channel_service_charges()
        return res

    def fill_seq_id(self):
        for idx,rec in enumerate(self.search([('seq_id','=',False)])):
            rec.seq_id = "PGI.O%s%s" % (idx,datetime.now().second)

    def create_ssr(self,ssr_param,pnr,provider_id, is_create_service_charge=True):
        service_chg_obj = self.env['tt.service.charge']
        currency_obj = self.env['res.currency']
        ssr_list = []
        for ssr in ssr_param:
            amount = 0
            currency_id = False
            # September 10, 2021 - SAM
            # Fix amount 0 apabila booking telah terissued.
            for sc in ssr['service_charges']:
                currency_id = currency_obj.search([('name', '=', sc.pop('currency'))], limit=1).id
                sc['currency_id'] = currency_id
                sc['foreign_currency_id'] = currency_obj.search([('name','=',sc.pop('foreign_currency'))],limit=1).id
                sc['description'] = pnr
                sc['passenger_insurance_ids'] = [(4,self.id)]
                sc['provider_insurance_booking_id'] = provider_id
                sc['is_extra_fees'] = True
                amount += sc['amount']
                if is_create_service_charge:
                    service_chg_obj.create(sc)

            ssr_values = {
                'name': ssr['name'],
                'description': ssr['description'],
                'amount': amount,
                'passenger_id': self.id,
                'pnr': pnr,
                'provider_id': provider_id,
            }
            if currency_id:
                ssr_values['currency_id'] = currency_id
            ssr_list.append((0,0,ssr_values))

        self.write({'fee_ids': ssr_list})