from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime

STATE_OFFLINE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('refund', 'Refund'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
]


class ProviderOffline(models.Model):
    _name = 'tt.provider.offline'
    _description = 'Rodex Model'

    _rec_name = 'pnr'
    # _order = 'sequence'
    # _order = 'departure_date'

    pnr = fields.Char('PNR')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.offline', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_offline_booking_id', 'Cost Service Charges')

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)

    # total = fields.Monetary(string='Total', readonly=True)
    # total_fare = fields.Monetary(string='Total Fare', compute=False, readonly=True)
    # total_orig = fields.Monetary(string='Total (Original)', readonly=True)
    # promotion_code = fields.Char(string='Promotion Code')

    confirm_uid = fields.Many2one('res.users', 'Confirmed By')
    confirm_date = fields.Datetime('Confirm Date')
    sent_uid = fields.Many2one('res.users', 'Sent By')
    sent_date = fields.Datetime('Sent Date')
    issued_uid = fields.Many2one('res.users', 'Issued By')
    issued_date = fields.Datetime('Issued Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')

    error_msg = fields.Text('Message Error', readonly=True, states={'draft': [('readonly', False)]})

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})

    total_price = fields.Float('Total Price', readonly=True, default=0)

    #reconcile purpose#
    reconcile_line_id = fields.Many2one('tt.reconcile.transaction.lines','Reconciled')
    reconcile_time = fields.Datetime('Reconcile Time')
    ##

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def create_service_charge(self):
        self.delete_service_charge()

        if self.booking_id.offline_provider_type != 'other':
            provider_type_id = self.env['tt.provider.type'].search(
                [('code', '=', self.booking_id.offline_provider_type)], limit=1)
        else:
            provider_type_id = self.env['tt.provider.type'].search(
                [('code', '=', self.env.ref('tt_reservation_offline.tt_provider_type_offline').code)], limit=1)
        scs_list = []
        scs_list_2 = []
        pricing_obj = self.env['tt.pricing.agent'].sudo()
        sale_price = 0
        provider_line_count = 0
        if self.booking_id.provider_type_id_name not in ['activity']:
            line_count = 0
            for line in self.booking_id.line_ids:
                line_count += 1
                if line.provider_id.id == self.provider_id.id:
                    if line.pnr == self.pnr:
                        provider_line_count += 1
            sale_price = self.booking_id.input_total / line_count * provider_line_count
        else:
            if self.booking_id.line_ids:
                sale_price = self.booking_id.input_total / len(self.booking_id.line_ids)
                provider_line_count = 1
            else:
                sale_price = self.booking_id.input_total
                provider_line_count = 1

        total_amount = self.booking_id.total_commission_amount
        fee_amount_val = self.booking_id.get_fee_amount(self.booking_id.agent_id, provider_type_id,
                                                        self.booking_id.total_commission_amount)
        real_comm_amount = total_amount - (fee_amount_val['amount'] * (len(self.booking_id.provider_booking_ids) * len(self.booking_id.passenger_ids)))

        """ Hitung fee amount """
        for psg in self.booking_id.passenger_ids:
            fee_amount_vals = self.booking_id.sudo().get_fee_amount(self.booking_id.agent_id, provider_type_id,
                                                                    self.booking_id.total_commission_amount,
                                                                    psg)
            total_amount -= fee_amount_vals.get('amount')
            fee_amount_vals['provider_offline_booking_id'] = self.id
            fee_amount_vals['amount'] = -(fee_amount_vals['amount'])
            fee_amount_vals['total'] = -(fee_amount_vals['total'])
            scs_list.append(fee_amount_vals)

        # Get all pricing per pax
        for psg in self.booking_id.passenger_ids:
            scs = []
            vals = {
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': psg.pax_type,
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': [],
                'pax_count': 1,
                'total': sale_price / len(self.booking_id.passenger_ids),
            }
            vals['passenger_offline_ids'].append(psg.id)
            scs_list.append(vals)
            commission_list = pricing_obj.get_commission(real_comm_amount / len(self.booking_id.passenger_ids),
                                                         self.booking_id.agent_id, provider_type_id)
            for comm in commission_list:
                if comm['amount'] > 0:
                    vals2 = vals.copy()
                    vals2.update({
                        'commission_agent_id': comm['commission_agent_id'],
                        'total': comm['amount'] * -1 / len(self.booking_id.line_ids) * provider_line_count,
                        'amount': comm['amount'] * -1 / len(self.booking_id.line_ids) * provider_line_count,
                        'charge_code': comm['code'],
                        'charge_type': 'RAC',
                        'passenger_offline_ids': [],
                    })
                    vals2['passenger_offline_ids'].append(psg.id)
                    scs_list.append(vals2)

        # Gather pricing based on pax type
        for scs in scs_list:
            # compare with ssc_list
            scs_same = False
            for scs_2 in scs_list_2:
                if scs['charge_code'] == scs_2['charge_code']:
                    if scs['pax_type'] == scs_2['pax_type']:
                        scs_same = True
                        # update ssc_final
                        scs_2['pax_count'] = scs_2['pax_count'] + 1,
                        scs_2['total'] += scs.get('amount')
                        scs_2['pax_count'] = scs_2['pax_count'][0]
                        scs_2['passenger_offline_ids'].append(scs['passenger_offline_ids'][0])
                        break
            if scs_same is False:
                vals = {
                    'commission_agent_id': scs.get('commission_agent_id') if scs.get('charge_code') != 'rac' else False,
                    'amount': scs['amount'],
                    'charge_code': scs['charge_code'],
                    'charge_type': scs['charge_type'],
                    'description': scs['description'],
                    'pax_type': scs['pax_type'],
                    'currency_id': scs['currency_id'],
                    'passenger_offline_ids': scs['passenger_offline_ids'],
                    'provider_offline_booking_id': scs['provider_offline_booking_id'],
                    'pax_count': 1,
                    'total': scs['total'],
                }
                scs_list_2.append(vals)

        if self.booking_id.admin_fee_ho != 0:
            currency_obj = self.env['res.currency'].sudo().search([('name', '=', 'IDR')], limit=1)
            scs_list_2.append({
                'commission_agent_id': False,
                'currency_id': currency_obj and currency_obj[0].id or self.booking_id.agent_id.currency_id.id,
                'charge_code': 'adm',
                'charge_type': 'ROC',
                'description': '',
                'pax_type': 'ADT',
                'passenger_offline_ids': scs_list[0]['passenger_offline_ids'],
                'provider_offline_booking_id': self.id,
                'pax_count': len(self.booking_id.passenger_ids),
                'amount': self.booking_id.admin_fee_ho / len(self.booking_id.line_ids) / len(self.booking_id.passenger_ids),
                'total': self.booking_id.admin_fee_ho / len(self.booking_id.line_ids)
            })

            ho_agent = self.env['tt.agent'].sudo().search([('agent_type_id.id', '=', self.env.ref('tt_base.agent_type_ho').id)], limit=1)
            scs_list_2.append({
                'commission_agent_id': ho_agent and ho_agent[0].id or False,
                'currency_id': currency_obj and currency_obj[0].id or self.booking_id.agent_id.currency_id.id,
                'charge_code': 'hsc',
                'charge_type': 'RAC',
                'description': '',
                'pax_type': 'ADT',
                'passenger_offline_ids': scs_list[0]['passenger_offline_ids'],
                'provider_offline_booking_id': self.id,
                'pax_count': len(self.booking_id.passenger_ids),
                'amount': -self.booking_id.admin_fee_ho / len(self.booking_id.line_ids) / len(self.booking_id.passenger_ids),
                'total': -self.booking_id.admin_fee_ho / len(self.booking_id.line_ids)
            })

        # Insert into cost service charge
        scs_list_3 = []
        service_chg_obj = self.env['tt.service.charge']
        for scs_2 in scs_list_2:
            scs_2['passenger_offline_ids'] = [(6, 0, scs_2['passenger_offline_ids'])]
            if abs(scs_2['total']) != 0:
                scs_obj = service_chg_obj.create(scs_2)
                scs_list_3.append(scs_obj.id)

    def create_service_charge_hotel(self, index):
        self.delete_service_charge()

        provider_type_id = self.env['tt.provider.type'].search([('code', '=', self.booking_id.offline_provider_type)], limit=1)

        book_obj = self.booking_id

        pax_count = 0

        scs_list = []
        scs_list_2 = []
        pricing_obj = self.env['tt.pricing.agent'].sudo()

        """ Get provider fee amount """
        total_fee_amount = 0
        line_obj = book_obj.line_ids[index]

        check_in_current = datetime.strptime(line_obj.check_in, '%Y-%m-%d')
        check_out_current = datetime.strptime(line_obj.check_out, '%Y-%m-%d')
        days_current = check_out_current - check_in_current
        days_int_current = int(days_current.days)

        pax_count = days_int_current * (int(line_obj.obj_qty) if line_obj.obj_qty else 1)
        basic_admin_fee = 0

        if book_obj.admin_fee_id:
            for line in book_obj.admin_fee_id.admin_fee_line_ids:
                basic_admin_fee += line.amount

        total_line_qty = 0

        """ Get total fee amount """
        for line in book_obj.line_ids:
            check_in = datetime.strptime(line.check_in, '%Y-%m-%d')
            check_out = datetime.strptime(line.check_out, '%Y-%m-%d')
            days = check_out - check_in
            days_int = int(days.days)

            fee_amount_vals = book_obj.get_fee_amount(book_obj.agent_id, provider_type_id,
                                                      book_obj.total_commission_amount, )
            fee_amount_vals['provider_offline_booking_id'] = self.id
            fee_amount_vals['amount'] = fee_amount_vals.get('amount')
            fee_amount_vals['total'] = fee_amount_vals.get('total') * line.obj_qty * days_int
            total_fee_amount += fee_amount_vals.get('total')

            total_line_qty += days_int * line.obj_qty

        if total_fee_amount > book_obj.ho_commission:
            real_comm_amount = book_obj.ho_commission
            fee_amount_remaining = book_obj.ho_commission
        else:
            real_comm_amount = book_obj.total_commission_amount - total_fee_amount
            fee_amount_remaining = total_fee_amount

        fee_amount_vals = book_obj.get_fee_amount(book_obj.agent_id, provider_type_id,
                                                  book_obj.total_commission_amount, self.booking_id.passenger_ids[0])
        fee_amount_vals['provider_offline_booking_id'] = self.id
        for line_idx, line in enumerate(book_obj.line_ids):
            check_in = datetime.strptime(line.check_in, '%Y-%m-%d')
            check_out = datetime.strptime(line.check_out, '%Y-%m-%d')
            days = check_out - check_in
            days_int = int(days.days)

            if line_idx == index:
                if fee_amount_remaining >= 0:
                    if fee_amount_remaining < fee_amount_vals.get('amount') * line.obj_qty * days_int:
                        fee_amount_vals['amount'] = -fee_amount_remaining
                        fee_amount_vals['total'] = -fee_amount_remaining
                        fee_amount_vals['pax_count'] = 1
                        scs_list.append(fee_amount_vals)
                        fee_amount_remaining -= fee_amount_remaining
                    else:
                        fee_amount_vals['amount'] = -fee_amount_vals.get('amount') * line.obj_qty * days_int
                        fee_amount_vals['total'] = -fee_amount_vals.get('total') * line.obj_qty * days_int
                        fee_amount_vals['pax_count'] = 1
                        scs_list.append(fee_amount_vals)
                        fee_amount_remaining -= fee_amount_vals.get('amount') * line.obj_qty * days_int
            else:
                if fee_amount_remaining >= 0:
                    if fee_amount_remaining < fee_amount_vals.get('amount') * line.obj_qty * days_int:
                        fee_amount_remaining -= fee_amount_remaining
                    else:
                        fee_amount_remaining -= fee_amount_vals.get('amount') * line.obj_qty * days_int

        sale_price = book_obj.input_total / total_line_qty * line_obj.obj_qty * days_int_current

        # Get all pricing per pax
        vals = {
            'amount': sale_price,
            'charge_code': 'fare',
            'charge_type': 'FARE',
            'description': '',
            'pax_type': 'ADT',
            'currency_id': self.currency_id.id,
            'provider_offline_booking_id': self.id,
            'passenger_offline_ids': [],
            'pax_count': 1,
            'total': sale_price,
        }
        vals['passenger_offline_ids'].append(self.booking_id.passenger_ids[0].id)
        scs_list.append(vals)
        if total_fee_amount <= book_obj.ho_commission:
            commission_list = pricing_obj.get_commission(real_comm_amount, book_obj.agent_id, provider_type_id)
            for comm in commission_list:
                if comm['amount'] > 0:
                    vals2 = vals.copy()
                    vals2.update({
                        'commission_agent_id': comm['commission_agent_id'],
                        'total': comm['amount'] * -1 / total_line_qty * line_obj.obj_qty * days_int_current,
                        'amount': comm['amount'] * -1 / total_line_qty * line_obj.obj_qty * days_int_current,
                        'charge_code': comm['code'],
                        'charge_type': 'RAC',
                        'passenger_offline_ids': [],
                    })
                    vals2['passenger_offline_ids'].append(self.booking_id.passenger_ids[0].id)
                    scs_list.append(vals2)

        if self.booking_id.admin_fee_ho != 0:
            currency_obj = self.env['res.currency'].sudo().search([('name', '=', 'IDR')], limit=1)
            scs_list.append({
                'commission_agent_id': False,
                'amount': basic_admin_fee * line_obj.obj_qty * days_int_current,
                'charge_code': 'adm',
                'charge_type': 'ROC',
                'description': '',
                'pax_type': 'ADT',
                'currency_id': currency_obj and currency_obj[0].id or self.booking_id.agent_id.currency_id.id,
                'passenger_offline_ids': scs_list[0]['passenger_offline_ids'],
                'provider_offline_booking_id': self.id,
                'pax_count': 1,
                'total': basic_admin_fee * line_obj.obj_qty * days_int_current,
            })

            ho_agent = self.env['tt.agent'].sudo().search(
                [('agent_type_id.id', '=', self.env.ref('tt_base.agent_type_ho').id)], limit=1)
            scs_list.append({
                'commission_agent_id': ho_agent and ho_agent[0].id or False,
                'amount': -basic_admin_fee * line_obj.obj_qty * days_int_current,
                'charge_code': 'hsc',
                'charge_type': 'RAC',
                'description': '',
                'pax_type': 'ADT',
                'currency_id': currency_obj and currency_obj[0].id or self.booking_id.agent_id.currency_id.id,
                'passenger_offline_ids': scs_list[0]['passenger_offline_ids'],
                'provider_offline_booking_id': self.id,
                'pax_count': 1,
                'total': -basic_admin_fee * line_obj.obj_qty * days_int_current,
            })

        # Insert into cost service charge
        scs_list_3 = []
        service_chg_obj = self.env['tt.service.charge']
        for scs_2 in scs_list:
            scs_2['passenger_offline_ids'] = [(6, 0, scs_2['passenger_offline_ids'])]
            if abs(scs_2['total']) != 0:
                scs_obj = service_chg_obj.create(scs_2)
                scs_list_3.append(scs_obj.id)

    def delete_service_charge(self):
        ledger_created = False
        for rec in self.cost_service_charge_ids.filtered(lambda x: x.is_extra_fees == False):
            if rec.is_ledger_created:
                ledger_created = True
            else:
                rec.unlink()
        return ledger_created

    def action_create_ledger(self, issued_uid, pay_method=None):
        return self.env['tt.ledger'].action_create_ledger(self, issued_uid)

    def set_total_price(self):
        for rec in self:
            rec.total_price = 0
            for scs in rec.cost_service_charge_ids:
                    rec.total_price += scs.total
