from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools import variables
from datetime import datetime
from ...tools.repricing_tools import RepricingTools, RepricingToolsV2

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
    _description = 'Provider Offline'

    _rec_name = 'pnr'
    # _order = 'sequence'
    # _order = 'departure_date'

    pnr = fields.Char('PNR')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.offline', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    state_offline = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state_offline')
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

    is_lg_required = fields.Boolean('Is LG Required', readonly=True, compute='compute_is_lg_required')
    is_po_required = fields.Boolean('Is PO Required', readonly=True, compute='compute_is_po_required')
    letter_of_guarantee_ids = fields.One2many('tt.letter.guarantee', 'res_id', 'Letter of Guarantees / Purchase Orders', readonly=True)

    @api.onchange('provider_id')
    def compute_is_lg_required(self):
        for rec in self:
            if rec.provider_id.is_using_lg:
                rec.is_lg_required = True
            else:
                rec.is_lg_required = False

    @api.onchange('provider_id')
    def compute_is_po_required(self):
        for rec in self:
            if rec.provider_id.is_using_po:
                rec.is_po_required = True
            else:
                rec.is_po_required = False

    def generate_lg_or_po(self, lg_type):
        if self.booking_id.state_offline == 'validate':
            if not self.env.user.has_group('tt_base.group_lg_po_level_5'):
                hour_passed = (datetime.now() - self.booking_id.validate_date).seconds / 3600
                if hour_passed > 1:
                    raise UserError('Failed to generate Letter of Guarantee. It has been more than 1 hour after this reservation was validated, please contact Accounting Manager to generate Letter of Guarantee.')

            lg_exist = self.env['tt.letter.guarantee'].search([('res_model', '=', self._name), ('res_id', '=', self.id), ('type', '=', lg_type)])
            if lg_exist:
                if lg_type == 'po':
                    type_str = 'Purchase Order'
                else:
                    type_str = 'Letter of Guarantee'
                raise UserError('%s for this provider is already exist.' % (type_str, ))
            else:
                multiplier = ''
                mult_amount = 0
                quantity = ''
                qty_amount = 0
                pax_desc_str = ''

                desc_dict = {}
                for rec in self.booking_id.line_ids:
                    if rec.provider_id.id == self.provider_id.id:
                        if not desc_dict.get(rec.pnr):
                            desc_dict[rec.pnr] = ''

                        if self.booking_id.offline_provider_type == 'airline':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            dept_date_str = datetime.strptime('%s %s:%s' % (rec.departure_date, rec.departure_hour, rec.departure_minute), '%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            ret_date_str = datetime.strptime('%s %s:%s' % (rec.arrival_date, rec.return_hour, rec.return_minute), '%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            desc_dict[rec.pnr] += '%s %s %s (%s) %s - %s (%s) %s<br/>' % (rec.carrier_code, rec.carrier_number, rec.origin_id.city, rec.origin_id.code, dept_date_str, rec.destination_id.city, rec.destination_id.code, ret_date_str)
                        elif self.booking_id.offline_provider_type == 'train':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            dept_date_str = datetime.strptime('%s %s:%s' % (rec.departure_date, rec.departure_hour, rec.departure_minute),'%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            ret_date_str = datetime.strptime('%s %s:%s' % (rec.arrival_date, rec.return_hour, rec.return_minute),'%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            desc_dict[rec.pnr] += '%s %s %s (%s) %s - %s (%s) %s<br/>' % (rec.carrier_code, rec.carrier_number, rec.origin_id.city, rec.origin_id.code, dept_date_str, rec.destination_id.city, rec.destination_id.code, ret_date_str)
                        elif self.booking_id.offline_provider_type == 'hotel':
                            multiplier = 'Room'
                            quantity = 'Night'
                            mult_amount = rec.obj_qty
                            qty_amount = (datetime.strptime(rec.check_out, '%Y-%m-%d') - datetime.strptime(rec.check_in, '%Y-%m-%d')).days
                            desc_dict[rec.pnr] += '%s<br/>' % (rec.hotel_name and rec.hotel_name or '-')
                            desc_dict[rec.pnr] += 'Room : %s<br/>' % (rec.room and rec.room or '-')
                            desc_dict[rec.pnr] += 'Meal Type : %s<br/>' % (rec.meal_type and rec.meal_type or '-')
                            desc_dict[rec.pnr] += 'Check In Date : %s<br/>' % (rec.check_in and datetime.strptime(rec.check_in, '%Y-%m-%d').strftime('%d %B %Y') or '-')
                            desc_dict[rec.pnr] += 'Check Out Date : %s<br/>' % (rec.check_out and datetime.strptime(rec.check_out, '%Y-%m-%d').strftime('%d %B %Y') or '-')
                            desc_dict[rec.pnr] += '<br/>'
                        elif self.booking_id.offline_provider_type == 'tour':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.offline_provider_type == 'activity':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            visit_date_str = datetime.strptime(rec.visit_date, '%Y-%m-%d').strftime('%d %B %Y')
                            desc_dict[rec.pnr] += '%s (%s) - %s<br/>' % (rec.activity_name, rec.activity_package, visit_date_str)
                        elif self.booking_id.offline_provider_type == 'visa':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.offline_provider_type == 'passport':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.offline_provider_type == 'ppob':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.offline_provider_type == 'event':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        else:
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description

                for rec in self.booking_id.passenger_ids:
                    pax_desc_str += '%s. %s %s<br/>' % (rec.title, rec.first_name, rec.last_name)
                    if multiplier == 'Pax':
                        mult_amount += 1

                price_per_mul = self.total_price / mult_amount / qty_amount

                lg_vals = {
                    'res_model': self._name,
                    'res_id': self.id,
                    'provider_id': self.provider_id.id,
                    'type': lg_type,
                    'parent_ref': self.booking_id.name,
                    'pax_description': pax_desc_str,
                    'multiplier': multiplier,
                    'multiplier_amount': mult_amount,
                    'quantity': quantity,
                    'quantity_amount': qty_amount,
                    'currency_id': self.currency_id.id,
                    'price_per_mult': price_per_mul,
                    'price': self.total_price,
                }
                new_lg_obj = self.env['tt.letter.guarantee'].create(lg_vals)
                for key, val in desc_dict.items():
                    line_vals = {
                        'lg_id': new_lg_obj.id,
                        'ref_number': key,
                        'description': val
                    }
                    self.env['tt.letter.guarantee.lines'].create(line_vals)
        else:
            raise UserError('You can only generate Letter of Guarantee if this reservation state is "Validated".')

    def generate_lg(self):
        self.generate_lg_or_po('lg')

    def generate_po(self):
        self.generate_lg_or_po('po')

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def generate_sc_repricing(self):
        scs_list = []
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
        segment_count = len(self.booking_id.line_ids)
        route_count = 1
        adt_count = 0
        chd_count = 0
        inf_count = 0
        total_pax_count = 0
        # Get all pricing per pax
        adt_id_list = []
        chd_id_list = []
        inf_id_list = []
        for psg in self.booking_id.passenger_ids:
            if psg.pax_type == 'INF':
                inf_count += 1
                inf_id_list.append(psg.id)
            elif psg.pax_type == 'CHD':
                chd_count += 1
                chd_id_list.append(psg.id)
            else:
                adt_count += 1
                adt_id_list.append(psg.id)
            total_pax_count += 1

        adt_scs_list = []
        chd_scs_list = []
        inf_scs_list = []
        user_info = self.env['tt.agent'].sudo().get_agent_level(self.booking_id.agent_id.id)
        if adt_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'ADT',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': adt_id_list,
                'pax_count': adt_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * adt_count,
            })
            adt_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': adt_count,
                'pax_type': 'ADT',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })

        if chd_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'CHD',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': chd_id_list,
                'pax_count': chd_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * chd_count,
            })
            chd_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': chd_count,
                'pax_type': 'CHD',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })

        if inf_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'INF',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': inf_id_list,
                'pax_count': inf_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * inf_count,
            })
            inf_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': inf_count,
                'pax_type': 'INF',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })
        commission_list = adt_scs_list + chd_scs_list + inf_scs_list

        for comm in commission_list:
            if comm['pax_type'] == 'INF':
                psg_id_list = inf_id_list
            elif comm['pax_type'] == 'CHD':
                psg_id_list = chd_id_list
            else:
                psg_id_list = adt_id_list
            if comm['amount'] != 0:
                comm.update({
                    'passenger_offline_ids': psg_id_list,
                    'description': '',
                    'currency_id': self.currency_id.id,
                    'provider_offline_booking_id': self.id
                })
                scs_list.append(comm)

        if self.booking_id.admin_fee_ho != 0:
            currency_obj = self.env['res.currency'].sudo().search([('name', '=', 'IDR')], limit=1)
            scs_list.append({
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
        return scs_list

    def generate_sc_repricing_v2(self):
        context = self.env['tt.api.credential'].get_userid_credential({
            'user_id': self.booking_id.user_id.id
        })
        if not context.get('error_code'):
            context = context['response']
        else:
            raise UserError('Failed to generate service charge, context user not found.')
        repr_tool = RepricingToolsV2('offline', context)
        scs_dict = {
            'service_charges': []
        }
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
            else:
                sale_price = self.booking_id.input_total

        total_commission_amount = self.booking_id.total_commission_amount
        segment_count = len(self.booking_id.line_ids)
        route_count = 1
        adt_count = 0
        chd_count = 0
        inf_count = 0
        total_pax_count = 0
        # Get all pricing per pax
        adt_id_list = []
        chd_id_list = []
        inf_id_list = []
        for psg in self.booking_id.passenger_ids:
            if psg.pax_type == 'INF':
                inf_count += 1
                inf_id_list.append(psg.id)
            elif psg.pax_type == 'CHD':
                chd_count += 1
                chd_id_list.append(psg.id)
            else:
                adt_count += 1
                adt_id_list.append(psg.id)
            total_pax_count += 1

        if adt_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'currency_id': self.currency_id.id,
                'pax_type': 'ADT',
                'pax_count': adt_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * adt_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'ADT',
                'pax_count': adt_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * adt_count,
            })
        if chd_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'currency_id': self.currency_id.id,
                'pax_type': 'CHD',
                'pax_count': chd_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * chd_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'CHD',
                'pax_count': chd_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * chd_count,
            })

        if inf_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'currency_id': self.currency_id.id,
                'pax_type': 'INF',
                'pax_count': inf_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * inf_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'INF',
                'pax_count': inf_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * inf_count,
            })

        if self.booking_id.admin_fee_ho:
            scs_dict['service_charges'].append({
                'currency_id': self.currency_id.id,
                'charge_code': 'adm',
                'charge_type': 'ROC',
                'pax_type': 'ADT',
                'pax_count': len(self.booking_id.passenger_ids),
                'amount': self.booking_id.admin_fee_ho / len(self.booking_id.line_ids) / len(self.booking_id.passenger_ids),
                'total': self.booking_id.admin_fee_ho / len(self.booking_id.line_ids)
            })

        repr_tool.add_ticket_fare(scs_dict)
        carrier_code = ''
        for line in self.booking_id.line_ids:
            if line.pnr == self.pnr and line.carrier_id:
                carrier_code = line.carrier_id.code
        rule_param = {
            'provider': self.provider_id.code,
            'carrier_code': carrier_code,
            'route_count': route_count,
            'segment_count': segment_count,
            'show_commission': True,
            'pricing_datetime': '',
        }
        repr_tool.calculate_pricing(**rule_param)

        for scs in scs_dict['service_charges']:
            if scs['amount'] != 0:
                if scs['pax_type'] == 'INF':
                    psg_id_list = inf_id_list
                elif scs['pax_type'] == 'CHD':
                    psg_id_list = chd_id_list
                else:
                    psg_id_list = adt_id_list
                scs.update({
                    'passenger_offline_ids': psg_id_list,
                    'description': '',
                    'provider_offline_booking_id': self.id
                })

        return scs_dict['service_charges']

    def create_service_charge(self):
        self.delete_service_charge()
        scs_list = self.generate_sc_repricing()
        # scs_list = self.generate_sc_repricing_v2()

        # Insert into cost service charge
        service_chg_obj = self.env['tt.service.charge']
        for scs in scs_list:
            scs['passenger_offline_ids'] = [(6, 0, scs['passenger_offline_ids'])]
            if abs(scs['total']) != 0:
                service_chg_obj.create(scs)

    def generate_sc_repricing_hotel(self, index):
        book_obj = self.booking_id
        scs_list = []

        provider_line_count = 0
        for line in self.booking_id.line_ids:
            if line.provider_id.id == self.provider_id.id:
                if line.pnr == self.pnr:
                    provider_line_count += 1

        total_amount = book_obj.total_commission_amount
        segment_count = 1
        route_count = 1
        adt_count = 0
        chd_count = 0
        inf_count = 0
        total_pax_count = 0
        # Get all pricing per pax
        adt_id_list = []
        chd_id_list = []
        inf_id_list = []
        for psg in self.booking_id.passenger_ids:
            if psg.pax_type == 'INF':
                inf_count += 1
                inf_id_list.append(psg.id)
            elif psg.pax_type == 'CHD':
                chd_count += 1
                chd_id_list.append(psg.id)
            else:
                adt_count += 1
                adt_id_list.append(psg.id)
            total_pax_count += 1

        line_obj = book_obj.line_ids[index]

        check_in_current = datetime.strptime(line_obj.check_in, '%Y-%m-%d')
        check_out_current = datetime.strptime(line_obj.check_out, '%Y-%m-%d')
        days_current = check_out_current - check_in_current
        days_int_current = int(days_current.days)

        total_line_qty = 0
        for line in book_obj.line_ids:
            check_in = datetime.strptime(line.check_in, '%Y-%m-%d')
            check_out = datetime.strptime(line.check_out, '%Y-%m-%d')
            days = check_out - check_in
            days_int = int(days.days)
            route_count = days_int
            segment_count = line.obj_qty

            total_line_qty += days_int * line.obj_qty

        sale_price = book_obj.input_total / total_line_qty * line_obj.obj_qty * days_int_current

        adt_scs_list = []
        chd_scs_list = []
        inf_scs_list = []
        user_info = self.env['tt.agent'].sudo().get_agent_level(self.booking_id.agent_id.id)
        if adt_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'ADT',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': adt_id_list,
                'pax_count': adt_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * adt_count,
            })
            adt_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(
                    self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': adt_count,
                'pax_type': 'ADT',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })

        if chd_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'CHD',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': chd_id_list,
                'pax_count': chd_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * chd_count,
            })
            chd_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(
                    self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': chd_count,
                'pax_type': 'CHD',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })

        if inf_count > 0:
            scs_list.append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'description': '',
                'pax_type': 'INF',
                'currency_id': self.currency_id.id,
                'provider_offline_booking_id': self.id,
                'passenger_offline_ids': inf_id_list,
                'pax_count': inf_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * inf_count,
            })
            inf_scs_list = self.booking_id.calculate_offline_pricing({
                'fare_amount': 0,
                'tax_amount': 0,
                'roc_amount': 0,
                'rac_amount': (total_amount / len(
                    self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'currency': 'IDR',
                'provider': self.provider_id.code,
                'origin': '',
                'destination': '',
                'carrier_code': '',
                'class_of_service': '',
                'route_count': route_count,
                'segment_count': segment_count,
                'pax_count': inf_count,
                'pax_type': 'INF',
                'agent_type_code': self.booking_id.agent_type_id.code,
                'agent_id': self.booking_id.agent_id.id,
                'user_info': user_info,
                'is_pricing': False,
                'is_commission': True,
                'is_retrieved': False,
                'pricing_date': '',
                'show_upline_commission': True
            })
        commission_list = adt_scs_list + chd_scs_list + inf_scs_list

        for comm in commission_list:
            if comm['pax_type'] == 'INF':
                psg_id_list = inf_id_list
            elif comm['pax_type'] == 'CHD':
                psg_id_list = chd_id_list
            else:
                psg_id_list = adt_id_list
            if comm['amount'] != 0:
                comm.update({
                    'passenger_offline_ids': psg_id_list,
                    'description': '',
                    'currency_id': self.currency_id.id,
                    'provider_offline_booking_id': self.id
                })
                scs_list.append(comm)

        basic_admin_fee = 0

        if book_obj.admin_fee_id:
            for line in book_obj.admin_fee_id.admin_fee_line_ids:
                basic_admin_fee += line.amount
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
        return scs_list

    def generate_sc_repricing_hotel_v2(self, index):
        context = self.env['tt.api.credential'].get_userid_credential({
            'user_id': self.booking_id.user_id.id
        })
        if not context.get('error_code'):
            context = context['response']
        else:
            raise UserError('Failed to generate service charge, context user not found.')
        repr_tool = RepricingToolsV2('offline', context)
        scs_dict = {
            'service_charges': []
        }

        book_obj = self.booking_id

        carrier_code = ''
        provider_line_count = 0
        for line in self.booking_id.line_ids:
            if line.provider_id.id == self.provider_id.id:
                if line.pnr == self.pnr:
                    if line.carrier_id:
                        carrier_code = line.carrier_id.code
                    provider_line_count += 1

        total_commission_amount = book_obj.total_commission_amount
        segment_count = 1
        route_count = 1
        adt_count = 0
        chd_count = 0
        inf_count = 0
        total_pax_count = 0
        # Get all pricing per pax
        adt_id_list = []
        chd_id_list = []
        inf_id_list = []
        for psg in self.booking_id.passenger_ids:
            if psg.pax_type == 'INF':
                inf_count += 1
                inf_id_list.append(psg.id)
            elif psg.pax_type == 'CHD':
                chd_count += 1
                chd_id_list.append(psg.id)
            else:
                adt_count += 1
                adt_id_list.append(psg.id)
            total_pax_count += 1

        line_obj = book_obj.line_ids[index]

        check_in_current = datetime.strptime(line_obj.check_in, '%Y-%m-%d')
        check_out_current = datetime.strptime(line_obj.check_out, '%Y-%m-%d')
        days_current = check_out_current - check_in_current
        days_int_current = int(days_current.days)

        total_line_qty = 0
        for line in book_obj.line_ids:
            check_in = datetime.strptime(line.check_in, '%Y-%m-%d')
            check_out = datetime.strptime(line.check_out, '%Y-%m-%d')
            days = check_out - check_in
            days_int = int(days.days)
            route_count = days_int
            segment_count = line.obj_qty

            total_line_qty += days_int * line.obj_qty

        sale_price = book_obj.input_total / total_line_qty * line_obj.obj_qty * days_int_current

        if adt_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'pax_type': 'ADT',
                'currency_id': self.currency_id.id,
                'pax_count': adt_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * adt_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'ADT',
                'pax_count': adt_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * adt_count,
            })

        if chd_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'pax_type': 'CHD',
                'currency_id': self.currency_id.id,
                'pax_count': chd_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * chd_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'CHD',
                'pax_count': chd_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * chd_count,
            })

        if inf_count > 0:
            scs_dict['service_charges'].append({
                'amount': sale_price / len(self.booking_id.passenger_ids),
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'pax_type': 'INF',
                'currency_id': self.currency_id.id,
                'pax_count': inf_count,
                'total': (sale_price / len(self.booking_id.passenger_ids)) * inf_count,
            })
            scs_dict['service_charges'].append({
                'amount': (total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC',
                'currency_id': self.currency_id.id,
                'pax_type': 'INF',
                'pax_count': inf_count,
                'total': ((total_commission_amount / len(self.booking_id.line_ids) * provider_line_count / total_pax_count) * -1) * inf_count,
            })

        basic_admin_fee = 0
        if book_obj.admin_fee_id:
            for line in book_obj.admin_fee_id.admin_fee_line_ids:
                basic_admin_fee += line.amount
        if self.booking_id.admin_fee_ho:
            scs_dict['service_charges'].append({
                'amount': basic_admin_fee * line_obj.obj_qty * days_int_current,
                'charge_code': 'adm',
                'charge_type': 'ROC',
                'pax_type': 'ADT',
                'currency_id': self.currency_id.id,
                'pax_count': 1,
                'total': basic_admin_fee * line_obj.obj_qty * days_int_current,
            })

            ho_agent = self.env['tt.agent'].sudo().search(
                [('agent_type_id.id', '=', self.env.ref('tt_base.agent_type_ho').id)], limit=1)
            scs_dict['service_charges'].append({
                'commission_agent_id': ho_agent and ho_agent[0].id or False,
                'amount': -basic_admin_fee * line_obj.obj_qty * days_int_current,
                'charge_code': 'hsc',
                'charge_type': 'RAC',
                'pax_type': 'ADT',
                'currency_id': self.currency_id.id,
                'pax_count': 1,
                'total': -basic_admin_fee * line_obj.obj_qty * days_int_current,
            })
        repr_tool.add_ticket_fare(scs_dict)

        rule_param = {
            'provider': self.provider_id.code,
            'carrier_code': carrier_code,
            'route_count': route_count,
            'segment_count': segment_count,
            'show_commission': True,
            'pricing_datetime': '',
        }
        repr_tool.calculate_pricing(**rule_param)

        for scs in scs_dict['service_charges']:
            if scs['amount'] != 0:
                if scs['pax_type'] == 'INF':
                    psg_id_list = inf_id_list
                elif scs['pax_type'] == 'CHD':
                    psg_id_list = chd_id_list
                else:
                    psg_id_list = adt_id_list
                scs.update({
                    'passenger_offline_ids': psg_id_list,
                    'description': '',
                    'provider_offline_booking_id': self.id
                })

        return scs_dict['service_charges']

    def create_service_charge_hotel(self, index):
        self.delete_service_charge()
        scs_list = self.generate_sc_repricing_hotel(index)
        # scs_list = self.generate_sc_repricing_hotel_v2(index)

        # Insert into cost service charge
        service_chg_obj = self.env['tt.service.charge']
        for scs_2 in scs_list:
            scs_2['passenger_offline_ids'] = [(6, 0, scs_2['passenger_offline_ids'])]
            if abs(scs_2['total']) != 0:
                service_chg_obj.create(scs_2)

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
