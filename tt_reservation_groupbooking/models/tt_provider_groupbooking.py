from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools import variables, ERR
from datetime import datetime
from dateutil.relativedelta import relativedelta
import traceback, logging
from ...tools.repricing_tools import RepricingTools, RepricingToolsV2

_logger = logging.getLogger(__name__)

STATE_GROUP_BOOKING = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('sent', 'Sent'),
    ('validate', 'Validate'),
    ('done', 'Done'),
    ('refund', 'Refund'),
    ('expired', 'Expired'),
    ('cancel', 'Canceled')
]


class ProviderGroupBooking(models.Model):
    _name = 'tt.provider.groupbooking'
    _description = 'Provider Group Booking'

    _rec_name = 'pnr'
    # _order = 'sequence'
    # _order = 'departure_date'

    pnr = fields.Char('PNR')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.groupbooking', 'Order Number', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    state_groupbooking = fields.Selection(variables.BOOKING_STATE, string='State', default='draft', related='booking_id.state_groupbooking')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_groupbooking_booking_id', 'Cost Service Charges')

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
    refund_uid = fields.Many2one('res.users', 'Refund By')
    refund_date = fields.Datetime('Refund Date')
    hold_date = fields.Datetime('Hold Date')
    expired_date = fields.Datetime('Expired Date')
    sid_issued = fields.Char('SID Issued', readonly=True,states={'draft': [('readonly', False)]})  # signature generate sendiri
    sid_cancel = fields.Char('SID Cancel', readonly=True,states={'draft': [('readonly', False)]})  # signature generate sendiri

    promotion_code = fields.Char(string='Promotion Code', readonly=True, states={'draft': [('readonly', False)]})

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

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    letter_of_guarantee_ids = fields.One2many('tt.letter.guarantee', 'res_id', 'Letter of Guarantees / Purchase Orders', readonly=True, domain=_get_res_model_domain)

    fare_id = fields.Many2one('tt.fare.groupbooking', 'Fare Group Booking')
    rule_ids = fields.Many2many('tt.tnc.groupbooking', 'groupbooking_tnc_rel', 'tt_provider_id',
                                      'tnc_id', string='Rules')

    @api.onchange('provider_id')
    def compute_is_lg_required(self):
        for rec in self:
            temp_req = False
            temp_ho_id = rec.booking_id.agent_id.ho_id
            if temp_ho_id:
                prov_ho_obj = self.env['tt.provider.ho.data'].search(
                    [('ho_id', '=', temp_ho_id.id), ('provider_id', '=', rec.provider_id.id)], limit=1)
                if prov_ho_obj and prov_ho_obj[0].is_using_lg:
                    temp_req = True
            rec.is_lg_required = temp_req

    @api.onchange('provider_id')
    def compute_is_po_required(self):
        for rec in self:
            temp_req = False
            temp_ho_id = rec.booking_id.agent_id.ho_id
            if temp_ho_id:
                prov_ho_obj = self.env['tt.provider.ho.data'].search(
                    [('ho_id', '=', temp_ho_id.id), ('provider_id', '=', rec.provider_id.id)], limit=1)
                if prov_ho_obj and prov_ho_obj[0].is_using_po:
                    temp_req = True
            rec.is_po_required = temp_req

    def to_dict(self):
        rule_list = []
        for rec in self.rule_ids:
            rule_list.append(rec.to_dict())
        return {
            'pnr': self.pnr and self.pnr or '',
            'provider': self.provider_id.code,
            'provider_id': self.id,
            'agent_id': self.booking_id.agent_id.id if self.booking_id and self.booking_id.agent_id else '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'sequence': self.sequence,
            'currency': self.currency_id.name,
            'hold_date': self.hold_date and self.hold_date or '',
            # 'service_charges': service_charges,
            # April 29, 2020 - SAM
            'total_price': self.total_price,
            'ticket': self.fare_id.get_fare_detail(),
            'rules': rule_list
        }

    def action_issued_api_groupbooking(self, context):
        # current_wib_datetime = datetime.now(pytz.timezone('Asia/Jakarta'))
        # current_datetime = current_wib_datetime.astimezone(pytz.utc)
        # if '08:00' < str(current_wib_datetime.time())[:5] < '18:00':
        #     pending_date = current_datetime + timedelta(hours=1)
        # else:
        #     pending_date = current_datetime.replace(hour=3, minute=0) # UTC0, jam 10 pagi surabaya
        #     if current_datetime > pending_date:
        #         pending_date = pending_date+timedelta(days=1)

        for rec in self:
            rec.write({
                'state': 'issued',
                'sid_issued': context['signature'],
                'issued_date': datetime.now(),
                'issued_uid': context['co_uid'],
                'balance_due': 0
            })

    def generate_lg_or_po(self, lg_type):
        if self.booking_id.state_groupbooking == 'validate':
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

                        if self.booking_id.groupbooking_provider_type == 'airline':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            dept_date_str = datetime.strptime('%s %s:%s' % (rec.departure_date, rec.departure_hour, rec.departure_minute), '%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            ret_date_str = datetime.strptime('%s %s:%s' % (rec.arrival_date, rec.return_hour, rec.return_minute), '%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            desc_dict[rec.pnr] += '%s %s %s (%s) %s - %s (%s) %s<br/>' % (rec.carrier_code, rec.carrier_number, rec.origin_id.city, rec.origin_id.code, dept_date_str, rec.destination_id.city, rec.destination_id.code, ret_date_str)
                        elif self.booking_id.groupbooking_provider_type == 'train':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            dept_date_str = datetime.strptime('%s %s:%s' % (rec.departure_date, rec.departure_hour, rec.departure_minute),'%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            ret_date_str = datetime.strptime('%s %s:%s' % (rec.arrival_date, rec.return_hour, rec.return_minute),'%Y-%m-%d %H:%M').strftime('%d %b %Y %H:%M')
                            desc_dict[rec.pnr] += '%s %s %s (%s) %s - %s (%s) %s<br/>' % (rec.carrier_code, rec.carrier_number, rec.origin_id.city, rec.origin_id.code, dept_date_str, rec.destination_id.city, rec.destination_id.code, ret_date_str)
                        elif self.booking_id.groupbooking_provider_type == 'hotel':
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
                        elif self.booking_id.groupbooking_provider_type == 'tour':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.groupbooking_provider_type == 'activity':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            visit_date_str = datetime.strptime(rec.visit_date, '%Y-%m-%d').strftime('%d %B %Y')
                            desc_dict[rec.pnr] += '%s (%s) - %s<br/>' % (rec.activity_name, rec.activity_package, visit_date_str)
                        elif self.booking_id.groupbooking_provider_type == 'visa':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.groupbooking_provider_type == 'passport':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.groupbooking_provider_type == 'ppob':
                            multiplier = 'Pax'
                            quantity = 'Qty'
                            qty_amount = 1
                            desc_dict[rec.pnr] += '%s<br/>' % rec.description
                        elif self.booking_id.groupbooking_provider_type == 'event':
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
                if self.booking_id.ho_id:
                    ho_obj = self.booking_id.ho_id
                else:
                    ho_obj = self.booking_id.agent_id.ho_id
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
                    'ho_id': ho_obj and ho_obj.id or False
                }
                new_lg_obj = self.env['tt.letter.guarantee'].create(lg_vals)
                for key, val in desc_dict.items():
                    line_vals = {
                        'lg_id': new_lg_obj.id,
                        'ref_number': key,
                        'description': val,
                        'ho_id': ho_obj and ho_obj.id or False
                    }
                    self.env['tt.letter.guarantee.lines'].create(line_vals)
        else:
            raise UserError('You can only generate Letter of Guarantee if this reservation state is "Validated".')

    def generate_lg(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_lg_po_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 128')
        self.generate_lg_or_po('lg')

    def generate_po(self):
        if not ({self.env.ref('base.group_system').id, self.env.ref('tt_base.group_lg_po_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 129')
        self.generate_lg_or_po('po')

    def action_refund(self, check_provider_state=False):
        self.state = 'refund'
        if check_provider_state:
            self.booking_id.check_provider_state({'co_uid': self.env.user.id})


    def set_total_price(self):
        for rec in self:
            rec.total_price = 0
            for scs in rec.cost_service_charge_ids:
                    rec.total_price += scs.total

    def action_create_ledger(self, issued_uid, pay_method=None, use_point=False,payment_method_use_to_ho=False):
        for rec in self.booking_id.payment_rules_id.installment_ids:
            if rec.due_date == 0:
                total_amount = (rec.payment_percentage / 100) * self.booking_id.total

                res_model = self.booking_id._name
                res_id = self.booking_id.id
                name = 'Order %s: %s' % (rec.name, self.booking_id.name)
                ref = self.booking_id.name
                date = datetime.now()+relativedelta(hours=7)
                currency_id = self.booking_id.currency_id.id
                ledger_issued_uid = issued_uid
                agent_id = self.booking_id.agent_id.id
                customer_parent_id = self.booking_id.customer_parent_id.id
                description = 'Ledger for ' + str(self.booking_id.name)
                ledger_type = 2
                debit = 0
                credit = total_amount
                additional_vals = {
                    'pnr': self.booking_id.pnr,
                    'display_provider_name': self.provider_id.name,
                    'provider_type_id': self.provider_id.provider_type_id.id,
                }
                ##CHECK USE POINT IVAN
                return self.env['tt.ledger'].create_ledger_vanilla(res_model, res_id, name, ref, ledger_type, currency_id,
                                                            ledger_issued_uid, agent_id, customer_parent_id, debit, credit, description, **additional_vals)


    def action_create_installment_ledger(self, issued_uid, payment_rules_id, payment_rule_installment_index, total_amount, commission_ledger=False): #index installment dari belakang
        try:
            payment_rules_obj = self.env['tt.payment.rules.groupbooking'].sudo().browse(int(payment_rules_id))
            payment_rules_installment_obj = payment_rules_obj.installment_ids[payment_rule_installment_index]

            is_enough = self.env['tt.agent'].check_balance_limit_api(self.booking_id.agent_id.id, total_amount)
            if is_enough['error_code'] != 0:
                raise UserError(_('Not Enough Balance.'))

            res_model = self.booking_id._name
            res_id = self.booking_id.id
            name = 'Order ' + payment_rules_installment_obj.name + ': ' + self.booking_id.name
            ref = self.booking_id.name
            date = datetime.now()+relativedelta(hours=7)
            currency_id = self.booking_id.currency_id.id
            ledger_issued_uid = issued_uid
            agent_id = self.booking_id.agent_id.id
            customer_parent_id = False
            description = 'Ledger for ' + str(self.booking_id.name)
            ledger_type = 2
            debit = 0
            credit = total_amount
            additional_vals = {
                'pnr': self.booking_id.pnr,
                'display_provider_name': self.provider_id.name,
                'provider_type_id': self.provider_id.provider_type_id.id,
            }

            self.env['tt.ledger'].create_ledger_vanilla(res_model, res_id, name, ref, ledger_type, currency_id,
                                                        ledger_issued_uid, agent_id, customer_parent_id, debit, credit, description, **additional_vals)

            if commission_ledger:
                self.env['tt.ledger'].create_commission_ledger(self, issued_uid)
            return ERR.get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)