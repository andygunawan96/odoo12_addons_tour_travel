from odoo import api, fields, models, _

STATE_OFFLINE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('paid', 'Validate'),
    ('posted', 'Done'),
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
    state = fields.Selection(STATE_OFFLINE, 'Status', default='draft', related="booking_id.state")
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

    def action_refund(self):
        self.state = 'refund'
        self.booking_id.check_provider_state({'co_uid': self.env.user.id})

    def action_confirm(self):
        for rec in self:
            rec.write({
                'state': 'confirm',
                'confirm_date': fields.Datetime.now(),
            })
        self.env.cr.commit()

    @api.depends('sale_service_charge_ids')
    def _compute_total(self):
        for rec in self:
            total = 0
            total_orig = 0
            for sc in self.sale_service_charge_ids:
                if sc.charge_code.find('r.ac') < 0:
                    total += sc.total
                    # total_orig adalah NTA
                    total_orig += sc.total
                rec.write({
                    'total': total,
                    'total_orig': total_orig
                })

    def get_provider_pnr(self):
        pnr = []
        for line in self.booking_id.line_ids:
            if line.provider_id.id == self.provider_id.id:
                if line.pnr not in pnr:
                    pnr.append(line.pnr)
        return pnr

    def create_service_charge(self):
        self.delete_service_charge()

        scs_list = []
        scs_list_2 = []
        pricing_obj = self.env['tt.pricing.agent'].sudo()
        sale_price = 0
        provider_line_count = 0
        if self.booking_id.provider_type_id_name in ['airline', 'train']:
            line_count = 0
            for line in self.booking_id.line_ids:
                line_count += 1
                if line.provider_id.id == self.provider_id.id:
                    if line.pnr == self.pnr:
                        provider_line_count += 1
            sale_price = self.booking_id.total / line_count * provider_line_count
        else:
            sale_price = self.booking_id.total / len(self.booking_id.line_ids)
            provider_line_count = 1

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
                'pax_count': 1,
                'total': sale_price / len(self.booking_id.passenger_ids),
            }
            scs_list.append(vals)
            commission_list = pricing_obj.get_commission(self.booking_id.agent_commission / len(self.booking_id.passenger_ids),
                                                         self.booking_id.agent_id, self.booking_id.provider_type_id)
            for comm in commission_list:
                if comm['amount'] > 0:
                    vals2 = vals.copy()
                    vals2.update({
                        'commission_agent_id': comm['commission_agent_id'],
                        'total': comm['amount'] * -1 / len(self.booking_id.line_ids) * provider_line_count,
                        'amount': comm['amount'] * -1 / len(self.booking_id.line_ids) * provider_line_count,
                        'charge_code': comm['code'],
                        'charge_type': 'RAC',
                    })
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
                        break
            if scs_same is False:
                vals = {
                    'commission_agent_id': scs.get('commission_agent_id') if 'commission_agent_id' in scs else '',
                    'amount': scs['amount'],
                    'charge_code': scs['charge_code'],
                    'charge_type': scs['charge_type'],
                    'description': scs['description'],
                    'pax_type': scs['pax_type'],
                    'currency_id': scs['currency_id'],
                    'provider_offline_booking_id': scs['provider_offline_booking_id'],
                    'pax_count': 1,
                    'total': scs['total'],
                }
                scs_list_2.append(vals)

        # Insert into cost service charge
        scs_list_3 = []
        service_chg_obj = self.env['tt.service.charge']
        for scs_2 in scs_list_2:
            scs_obj = service_chg_obj.create(scs_2)
            scs_list_3.append(scs_obj.id)

    def create_service_charge_hotel(self):
        self.delete_service_charge()

        scs_list = []
        scs_list_2 = []
        pricing_obj = self.env['tt.pricing.agent'].sudo()
        sale_price = self.booking_id.total / len(self.booking_id.line_ids)

        # Get all pricing per pax
        vals = {
            'amount': sale_price,
            'charge_code': 'fare',
            'charge_type': 'FARE',
            'description': '',
            'pax_type': 'ADT',
            'currency_id': self.currency_id.id,
            'provider_offline_booking_id': self.id,
            'pax_count': 1,
            'total': sale_price,
        }
        scs_list.append(vals)
        commission_list = pricing_obj.get_commission(
            self.booking_id.agent_commission,
            self.booking_id.agent_id, self.booking_id.provider_type_id)
        for comm in commission_list:
            if comm['amount'] > 0:
                vals2 = vals.copy()
                vals2.update({
                    'commission_agent_id': comm['commission_agent_id'],
                    'total': comm['amount'] * -1 / len(self.booking_id.line_ids),
                    'amount': comm['amount'] * -1 / len(self.booking_id.line_ids),
                    'charge_code': comm['code'],
                    'charge_type': 'RAC',
                })
                scs_list.append(vals2)

        # Insert into cost service charge
        scs_list_3 = []
        service_chg_obj = self.env['tt.service.charge']
        for scs_2 in scs_list:
            scs_obj = service_chg_obj.create(scs_2)
            scs_list_3.append(scs_obj.id)

    def delete_service_charge(self):
        for rec in self.cost_service_charge_ids:
            rec.unlink()

    def action_create_ledger(self):
        if not self.is_ledger_created:
            self.write({'is_ledger_created': True})
            self.env['tt.ledger'].action_create_ledger(self, self.env.user.id)
