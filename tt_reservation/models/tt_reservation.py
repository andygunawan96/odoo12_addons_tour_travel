from odoo import api, fields, models, _
from ...tools import variables, util, ERR
import json
from ...tools.ERR import RequestException
import logging, traceback
from datetime import datetime, timedelta
import time
import odoo.tools as tools
import base64

_logger = logging.getLogger(__name__)


class TtReservation(models.Model):
    _name = 'tt.reservation'
    _inherit = 'tt.history'
    _description = 'Rodex Model'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    provider_name = fields.Char('List of Provider', readonly=True)
    carrier_name = fields.Char('List of Carriers', readonly=True)
    voucher_code = fields.Char('Voucher', readonly=True)
    payment_method = fields.Char('Payment Method', readonly=True)
    is_member = fields.Boolean('Payment member', readonly=True)
    va_number = fields.Char('VA Number', readonly=True)

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True)  # fixme terpakai?
    hold_date = fields.Datetime('Hold Date', readonly=True, states={'draft': [('readonly',False)]})

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Booked by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel by', readonly=False)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    refund_uid = fields.Many2one('res.users', 'Refund by', readonly=False)
    refund_date = fields.Datetime('Refund Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Create by', readonly=True)  # create_uid

    #utk adjustment
    res_model = fields.Char('Res Model', invisible=1, readonly=True)

    sid_booked = fields.Char('SID Booked', readonly=True)  # Signature generate sendiri

    booker_id = fields.Many2one('tt.customer','Booker', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    contact_name = fields.Char('Contact Name',readonly=True)  # fixme oncreate later
    contact_title = fields.Char('Contact Title',readonly=True)
    contact_email = fields.Char('Contact Email',readonly=True)
    contact_phone = fields.Char('Contact Phone',readonly=True)

    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})

    elder = fields.Integer('Elder', default=0, readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult', default=1, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child', default=0, readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant', default=0, readonly=True, states={'draft': [('readonly', False)]})

    departure_date = fields.Char('Journey Date', readonly=True, states={'draft': [('readonly', False)]})  # , required=True
    return_date = fields.Char('Return Date', readonly=True, states={'draft': [('readonly', False)]})
    arrival_date = fields.Char('Arrival Date', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type',readonly=True)

    # April 24, 2020 - SAM
    penalty_amount = fields.Float('Penalty Amount', default=0)
    reschedule_uid = fields.Many2one('res.users', 'Rescheduled By')
    reschedule_date = fields.Datetime('Rescheduled Date')
    # END

    def _get_res_model_domain(self):
        return [('res_model', '=', self._name)]

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,domain=_get_res_model_domain)
    adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',readonly=True,domain=_get_res_model_domain)  # domain=[('res_model','=',lambda self: self._name)]
    # adjustment_ids = fields.One2many('tt.adjustment','res_id','Adjustment',readonly=True)  # domain=[('res_model','=',lambda self: self._name)]
    refund_ids = fields.One2many('tt.refund','res_id','Refund',readonly=True,domain=_get_res_model_domain)  # domain=[('res_model','=',lambda self: self._name)]
    error_msg = fields.Char('Error Message')
    notes = fields.Text('Notes for IT',default='')
    refundable = fields.Boolean('Refundable', default=True, readonly=True, compute='_compute_refundable')

    ##fixme tambahkan compute field nanti
    # display_provider_name = fields.Char(string='Provider', compute='_action_display_provider', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)


    # total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_booking", store=True)
    # total_tax = fields.Monetary(string='Total Tax', default=0, compute="_compute_total_booking", store=True)
    # total = fields.Monetary(string='Grand Total', default=0, compute="_compute_total_booking", store=True)
    # total_discount = fields.Monetary(string='Total Discount', default=0, compute="_compute_total_booking", store=True)
    # total_commission = fields.Monetary(string='Total Commission', default=0, compute="_compute_total_booking", store=True)
    # total_nta = fields.Monetary(string='NTA Amount', compute="_compute_total_booking", store=True)

    sale_service_charge_ids = fields.Char('dummy sale')

    total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_fare",store=True)
    total_tax = fields.Monetary(string='Total Tax', default=0, compute='_compute_total_tax',store=True)
    total = fields.Monetary(string='Grand Total', default=0, compute='_compute_grand_total',store=True)
    total_discount = fields.Monetary(string='Total Discount', default=0, readonly=True,store=True)
    total_commission = fields.Monetary(string='Total Commission', default=0, compute='_compute_total_commission',store=True)
    total_nta = fields.Monetary(string='NTA Amount',compute='_compute_total_nta',store=True)
    agent_nta = fields.Monetary(string='NTA Amount',compute='_compute_agent_nta',store=True)

    # yang jual
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',readonly=True,
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]},
                                         help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id',
                                              store=True, readonly=True)

    printout_ticket_id = fields.Many2one('tt.upload.center', 'Ticket', readonly=True)
    printout_ticket_price_id = fields.Many2one('tt.upload.center', 'Ticket (Price)', readonly=True)
    printout_itinerary_id = fields.Many2one('tt.upload.center', 'Itinerary', readonly=True)
    printout_voucher_id = fields.Many2one('tt.upload.center', 'Voucher', readonly=True)
    printout_ho_invoice_id = fields.Many2one('tt.upload.center', 'Voucher', readonly=True)

    payment_acquirer_number_id = fields.Many2one('payment.acquirer.number','Payment Acquier Number')

    # April 21, 2020 - SAM
    is_force_issued = fields.Boolean('Force Issued', default=False)
    is_halt_process = fields.Boolean('Halt Process', default=False)
    # END

    @api.model
    def create(self, vals_list):
        try:
            vals_list['name'] = self.env['ir.sequence'].next_by_code(self._name)
            vals_list['res_model'] = self._name
        except:
            pass
        return super(TtReservation, self).create(vals_list)

    def write(self, vals):
        if vals.get('hold_date'):
            if self.agent_type_id.id == self.env.ref('tt_base.agent_type_btc').id:
                vals.pop('hold_date')
                if not self.hold_date:
                    if vals.get('booked_date'):
                        vals['hold_date'] = vals['booked_date'] + timedelta(minutes=45)
                    elif self.booked_date:
                        vals['hold_date'] = self.booked_date + timedelta(minutes=45)
                    elif self.create_date:
                        vals['hold_date'] = self.create_date + timedelta(minutes=45)
                    else:
                        vals['hold_date'] = datetime.now() + timedelta(minutes=45)
        super(TtReservation, self).write(vals)

    def create_booker_api(self, vals, context):
        booker_obj = self.env['tt.customer'].sudo()
        get_booker_seq_id = util.get_without_empty(vals,'booker_seq_id')

        if get_booker_seq_id:
            booker_seq_id = vals['booker_seq_id']
            booker_rec = booker_obj.search([('seq_id','=',booker_seq_id)])
            update_value = {}
            if booker_rec:
                if vals.get('mobile'):
                    number_entered  = False
                    vals_phone_number = '%s%s' % (vals.get('calling_code', ''), vals['mobile'])
                    for phone in booker_rec.phone_ids:
                        if phone.phone_number == vals_phone_number:
                            number_entered = True
                            break

                    if not number_entered:
                        new_phone=[(0,0,{
                            'calling_code': vals.get('calling_code', ''),
                            'calling_number': vals.get('mobile', ''),
                            'phone_number': vals_phone_number
                        })]
                        update_value['phone_ids'] = new_phone
                if vals.get('email'):
                    if vals['email'] != booker_rec.email:
                        update_value['email'] = vals.get('email', booker_rec.email)
                if update_value:
                    booker_rec.update(update_value)
                return booker_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])

        vals.update({
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'calling_code': vals.get('calling_code',''),
                'calling_number': vals.get('mobile',''),
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'gender': vals.get('gender'),
            'marital_status': 'married' if vals.get('title') == 'MRS' else '',
            'is_get_booking_from_vendor': vals.get('is_get_booking_from_vendor',False),
            'register_uid': context['co_uid']
        })
        return booker_obj.create(vals)

    def create_contact_api(self, vals, booker, context):
        contact_obj = self.env['tt.customer'].sudo()
        get_contact_seq_id = util.get_without_empty(vals,'contact_seq_id',False)

        if get_contact_seq_id or vals.get('is_also_booker'):
            if get_contact_seq_id:
                contact_seq_id = get_contact_seq_id
            else:
                contact_seq_id = booker.seq_id

            contact_rec = contact_obj.search([('seq_id','=',contact_seq_id)])
            update_value = {}

            if contact_rec:
                if vals.get('mobile'):
                    number_entered = False
                    vals_phone_number = '%s%s' % (vals.get('calling_code', ''), vals['mobile'])
                    for phone in contact_rec.phone_ids:
                        if phone.phone_number == vals_phone_number:
                            number_entered = True
                            break
                    if not number_entered:
                        new_phone = [(0, 0, {
                            'calling_code': vals.get('calling_code', ''),
                            'calling_number': vals.get('mobile', ''),
                            'phone_number': vals_phone_number
                        })]
                        update_value['phone_ids'] = new_phone
                if vals.get('email'):
                    if vals['email'] != contact_rec.email:
                        update_value['email'] = vals.get('email', contact_rec.email)
                if update_value:
                    contact_rec.update(update_value)
                return contact_rec

        country = self.env['res.country'].sudo().search([('code', '=', vals.pop('nationality_code'))])
        agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])

        vals.update({
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'calling_code': vals.get('calling_code', ''),
                'calling_number': vals.get('mobile', ''),
                'phone_number': '%s%s' % (vals.get('calling_code',''),vals.get('mobile','')),
                'country_id': country and country[0].id or False,
            })],
            'first_name': vals.get('first_name'),
            'last_name': vals.get('last_name'),
            'marital_status': 'married' if vals.get('title') == 'MRS' else '',
            'gender': vals.get('gender'),
            'is_get_booking_from_vendor': vals.get('is_get_booking_from_vendor', False),
            'register_uid': context['co_uid']
        })

        return contact_obj.create(vals)

    def create_customer_api(self,passengers,context,booker_seq_id=False,contact_seq_id=False):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()

        res_ids = []
        # identity_req = ['identity_number','identity_country_of_issued_id','identity_expdate','identity_type']

        for psg in passengers:
            country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
            psg['nationality_id'] = country and country[0].id or False

            booker_contact_seq_id = ''
            if psg.get('is_also_booker'):
                booker_contact_seq_id = booker_seq_id
            elif psg.get('is_also_contact'):
                booker_contact_seq_id = contact_seq_id

            get_psg_seq_id = util.get_without_empty(psg, 'passenger_seq_id')

            if (get_psg_seq_id or booker_contact_seq_id) != '':
                current_passenger = passenger_obj.search([('seq_id','=',get_psg_seq_id or booker_contact_seq_id)])
                if current_passenger:
                    vals_for_update = {}
                    # update_list = ['nationality_id', 'birth_date']

                    if psg.get('nationality_id') != (current_passenger.nationality_id and current_passenger.nationality_id.id or False):
                        vals_for_update.update({
                            'nationality_id': psg['nationality_id']
                        })
                    if psg.get('birth_date') != (current_passenger.birth_date and datetime.strftime(current_passenger.birth_date,"%Y-%m-%d") or False):
                        vals_for_update.update({
                            'birth_date': psg['birth_date']
                        })

                    #manual aja
                    # [vals_for_update.update({
                    #     key: psg[key]
                    # }) for key in update_list if psg.get(key) != getattr(current_passenger, key)]

                    if vals_for_update:
                        current_passenger.update(vals_for_update)

                    if psg.get('identity'):
                        current_passenger.add_or_update_identity(psg['identity'])
                    res_ids.append(current_passenger)
                    continue

            psg['agent_id'] = context['co_agent_id']
            agent_obj = self.env['tt.agent'].sudo().browse(context['co_agent_id'])
            psg.update({
                'marital_status': 'married' if psg.get('title') == 'MRS' else '',
                'is_get_booking_from_vendor': psg.get('is_get_booking_from_vendor', False),
                'register_uid': context['co_uid']
            })
            #if ada phone, kalau dari frontend cache passenger
            if psg.get('phone'):
                psg.update({
                    'phone_ids': [(0, 0, {
                        'calling_code': psg.get('phone_id', ''),
                        'calling_number': psg.get('phone', ''),
                        'phone_number': '%s%s' % (psg.get('phone_id', ''), psg.get('phone', '')),
                        'country_id': country and country[0].id or False,
                    })]
                })
            psg_obj = passenger_obj.create(psg)
            if psg.get('identity'):
                psg_obj.add_or_update_identity(psg['identity'])
            res_ids.append(psg_obj)

        return res_ids

    # passenger_obj di isi oleh self.env['']
    def create_passenger_api(self,list_customer,passenger_obj):
        list_passenger = []
        for rec in list_customer:
            vals = rec[0].copy_to_passenger()
            if rec[1]:
                vals.update(rec[1])
            list_passenger.append(passenger_obj.create(vals).id)
        return list_passenger

    def create_passenger_value_api_test(self,passenger):
        list_passenger_value = []
        country_obj = self.env['res.country'].sudo()
        for rec in passenger:
            nationality_id = country_obj.search([('code','=ilike',rec['nationality_code'])],limit=1).id
            identity = rec.get('identity')
            list_passenger_value.append((0,0,{
                'name': "%s %s" % (rec['first_name'],rec['last_name']),
                'first_name': rec['first_name'],
                'last_name': rec['last_name'],
                'gender': rec['gender'],
                'title': rec['title'],
                'birth_date': rec['birth_date'],
                'nationality_id': nationality_id,
                'identity_type': identity and identity['identity_type'] or '',
                'identity_number': identity and identity['identity_number'] or '',
                'identity_expdate': identity and identity['identity_expdate'] or False,
                'identity_country_of_issued_id': identity and country_obj.search([('code','=ilike',identity['identity_country_of_issued_code'])],limit=1).id or False,
                'sequence': rec['sequence']
            }))

        return list_passenger_value

    @api.depends("refund_ids", "state")
    @api.onchange("refund_ids", "state")
    def _compute_refundable(self):
        for rec in self:
            if rec.state == 'issued':
                state_list = []
                for rec2 in rec.refund_ids:
                    state_list.append(rec2.state)
                if len(state_list) > 0:
                    if all(temp_state in ['cancel', 'expired'] for temp_state in state_list):
                        rec.refundable = True
                    else:
                        rec.refundable = False
                else:
                    rec.refundable = True
            else:
                rec.refundable = False

    def compute_all(self):
        for rec in self.search([]):
            _logger.info(rec.name)
            rec._compute_total_fare()
            rec._compute_total_tax()
            rec._compute_grand_total()
            rec._compute_total_commission()
            rec._compute_total_nta()
            rec._compute_agent_nta()

    @api.depends("sale_service_charge_ids")
    def _compute_total_fare(self):
        for rec in self:
            fare_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'FARE':
                    fare_total += sale.total
            rec.total_fare = fare_total

    @api.depends("sale_service_charge_ids")
    def _compute_total_tax(self):
        for rec in self:
            tax_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type in ['ROC', 'TAX']:
                    tax_total += sale.total
            rec.total_tax = tax_total

    @api.depends("sale_service_charge_ids")
    def _compute_grand_total(self):
        for rec in self:
            grand_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type != 'RAC':
                    grand_total += sale.total
            rec.total = grand_total

    @api.depends("sale_service_charge_ids")
    def _compute_total_commission(self):
        for rec in self:
            commission_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'RAC':
                    commission_total += abs(sale.total)
            rec.total_commission = commission_total

    @api.depends("sale_service_charge_ids")
    def _compute_total_nta(self):
        for rec in self:
            nta_total = 0
            for sale in rec.sale_service_charge_ids:
                nta_total += sale.total
            rec.total_nta = nta_total

    @api.depends("sale_service_charge_ids")
    def _compute_agent_nta(self):
        for rec in self:
            agent_nta_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_code == 'rac':
                    agent_nta_total += sale.total
            rec.agent_nta = agent_nta_total + rec.total

    def to_dict(self):
        # invoice_list = []
        # if hasattr(self, 'invoice_line_ids'):
        #     for rec in self.invoice_line_ids:
        #         invoice_list.append({
        #             'name': rec.name,
        #             'state': rec.state
        #         })

        payment_acquirer_number = {}
        if self.payment_acquirer_number_id:
            date_now = datetime.now()
            time_delta = date_now - self.payment_acquirer_number_id.create_date
            if divmod(time_delta.seconds, 3600)[0] == 0:
                payment_acquirer_number = {
                    'create_date': self.payment_acquirer_number_id.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'time_limit': (self.payment_acquirer_number_id.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    'nomor_rekening': self.payment_acquirer_number_id.payment_acquirer_id.account_number,
                    'account_name': self.payment_acquirer_number_id.payment_acquirer_id.account_name,
                    'amount': self.payment_acquirer_number_id.amount - self.payment_acquirer_number_id.unique_amount,
                    'order_number': self.payment_acquirer_number_id.number
                }
            else:
                self.payment_acquirer_number_id.state = 'cancel'
                self.payment_acquirer_number_id = False

        res = {
            'order_number': self.name,
            'book_id': self.id,
            'pnr': self.pnr and self.pnr or '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'hold_date': self.hold_date and self.hold_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'YCD': self.elder,
            'ADT': self.adult,
            'CHD': self.child,
            'INF': self.infant,
            'contact': {
                'title': self.contact_title,
                'name': self.contact_name,
                'email': self.contact_email,
                'phone': self.contact_phone
            },
            'contact_id': self.contact_id.to_dict(),
            'booker': self.booker_id.to_dict(),
            'departure_date': self.departure_date and self.departure_date or '',
            'arrival_date': self.arrival_date and self.arrival_date or '',
            'provider_type': self.provider_type_id.code,
            'payment_acquirer_number': payment_acquirer_number,
            # May 19, 2020 - SAM
            'is_force_issued': self.is_force_issued,
            'is_halt_process': self.is_halt_process,
            # END
        }

        return res

    def get_book_obj(self, book_id, order_number):
        if book_id:
            book_obj = self.browse(book_id)
        elif order_number:
            book_obj = self.search([('name', '=', order_number)], limit=1)

        if book_obj:
            return book_obj
        else:
            return False

    def get_aftersales_desc(self):
        return ''

    def get_acquirer_n_c_parent_id(self,req):
        acquirer_id = False
        #credit limit
        if req.get('member'):
            customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', req['acquirer_seq_id'])],
                                                                       limit=1).id
        ##cash / transfer
        else:
            if self.payment_method:
                payment_method = self.payment_method
            else:
                payment_method = req.get('acquirer_seq_id',False)

            if self.is_member:
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', payment_method)],
                                                                           limit=1).id
            ##get payment acquirer
            else:
                if payment_method:
                    acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', payment_method)], limit=1)
                    if not acquirer_id.create_date:
                        raise RequestException(1017)
                else:
                    acquirer_id = self.agent_id.default_acquirer_id
                customer_parent_id = self.agent_id.customer_parent_walkin_id.id  ##fpo
        return acquirer_id,customer_parent_id

    ##butuh field passenger_ids
    def channel_pricing_api(self,req,context):
        try:
            resv_obj = self.env['tt.reservation.%s' % (req['provider_type'])]
            book_obj = resv_obj.get_book_obj(req.get('book_id'), req.get('order_number'))
            try:
                book_obj.create_date
            except:
                return ERR.get_error(1001)
            if book_obj.agent_id.id == context['co_agent_id']:
                for psg in req['passengers']:
                    book_obj.passenger_ids[psg['sequence']-1].create_channel_pricing(psg['pricing'])
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500, additional_message=str(e))
        return ERR.get_no_error()

    def action_failed_book(self):
        self.write({
            'state': 'fail_booked'
        })

    def action_failed_issue(self):
        self.write({
            'state': 'fail_issued'
        })

    def action_failed_paid(self):
        self.write({
            'state': 'fail_paid'
        })

    ##override fungsi ini untuk melakukan action extra jika expired
    def action_expired(self):
        self.state = 'cancel2'
        try:
            for rec in self.provider_booking_ids.filtered(lambda x: x.state != 'cancel2'):
                rec.action_expired()
        except:
            _logger.error("provider type %s failed to expire vendor" % (self._name))

    def action_cancel(self):
        self.cancel_date = fields.Datetime.now()
        self.cancel_uid = self.env.user.id
        self.state = 'cancel'

    # def get_installment_dp_amount(self):
    ##overwrite this method for installment
    def get_nta_amount(self,method='full'):
        return self.agent_nta

    # def get_installment_dp_amount_cor(self):
    ##overwrite this method for installment
    def get_total_amount(self,method='full'):
        return self.total

    # May 28, 2020 - SAM
    def get_balance_due(self):
        return self.agent_nta - self.get_ledger_amount()

    def get_ledger_amount(self):
        total_debit = 0.0
        total_credit = 0.0
        for ledger in self.ledger_ids:
            if ledger.debit != 0:
                total_debit += ledger.debit
            if ledger.credit != 0:
                total_credit += ledger.credit
        result = total_credit - total_debit
        return result
    # END

    ## Digunakan untuk mengupdate PNR seluruh ledger untuk resv ini
    # Digunakan di hotel dan activity
    def update_ledger_pnr(self, new_pnr):
        for rec in self.ledger_ids:
            rec.update({'pnr': new_pnr})

    ##ini potong ledger
    def payment_reservation_api(self,table_name,req,context):
        _logger.info("Payment\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.%s' % (table_name)].browse(req.get('book_id'))
            else:
                book_obj = self.env['tt.reservation.%s' % (table_name)].search([('name','=',req.get('order_number'))],limit=1)
            voucher = None
            discount = {'error_code': -1}
            total_discount = 0
            try:
                book_obj.create_date
                agent_obj = book_obj.agent_id
            except:
                raise RequestException(1001)
            if agent_obj.id == context.get('co_agent_id',-1):
                book_obj.write({
                    'is_member': req.get('member', False),
                    'payment_method': req.get('acquirer_seq_id', False)
                })

                #cek balance due book di sini, mungkin suatu saat yang akan datang
                if book_obj.state == 'issued':
                    _logger.error('Transaction Has been paid.')
                    raise RequestException(1009)
                # May 13, 2020 - SAM
                # if book_obj.state not in ['booked']:
                #     # _logger.error('Cannot issue not [Booked] State.')
                #     _logger.error('Cannot issue state, %s' % book_obj.state)
                #     raise RequestException(1020)
                # END

                payment_method = req.get('payment_method', 'full')

                agent_check_amount = book_obj.get_nta_amount(payment_method)

                # May 28, 2020 - SAM
                # Sementara ditambahkan untuk pengecekkan state apabila ditemukan agent check amount <= 0
                if agent_check_amount <= 0 and book_obj.state in ['issued', 'partial_issued']:
                    raise Exception("Cannot Payment 0 or lower.")
                # END

                voucher = ''
                ### voucher agent here##
                if req.get('voucher'):
                    voucher = req['voucher']
                if voucher == '' and book_obj.voucher_code:
                    voucher = {
                        'voucher_reference': book_obj.voucher_code,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'provider_type': book_obj._name.split('.')[len(book_obj._name.split('.'))-1],
                        'provider': book_obj.provider_name.split(','),
                    }

                if voucher:
                    voucher.update({
                        'order_number': book_obj.name
                    })
                    discount = self.env['tt.voucher.detail'].simulate_voucher(voucher, context)
                    if discount['error_code'] == 0:
                        for rec in discount['response']:
                            total_discount = total_discount + rec['provider_total_discount']
                    agent_check_amount-=total_discount

                balance_res = self.env['tt.agent'].check_balance_limit_api(context['co_agent_id'],agent_check_amount)
                if balance_res['error_code'] != 0:
                    _logger.error('Agent Balance not enough')
                    raise RequestException(1007,additional_message="agent balance")

                if req.get("member"):
                    acquirer_seq_id = req.get('acquirer_seq_id')
                    if acquirer_seq_id:
                        cor_check_amount = book_obj.get_total_amount(payment_method)
                        cor_check_amount -= total_discount
                        ### voucher cor here

                        balance_res = self.env['tt.customer.parent'].check_balance_limit_api(acquirer_seq_id,cor_check_amount)
                        if balance_res['error_code'] != 0:
                            _logger.error('Customer Parent credit limit not enough')
                            raise RequestException(1007,additional_message="customer credit limit")
                    else:
                        raise RequestException(1017,additional_message=", Customer.")

                if discount['error_code'] == 0:
                    discount = self.env['tt.voucher.detail'].use_voucher_new(voucher, context)
                    if discount['error_code'] == 0:
                        for idx, rec in enumerate(discount['response']):
                            service_charge = [{
                                "charge_code": "disc",
                                "charge_type": "DISC",
                                "currency": "IDR",
                                "pax_type": "ADT",
                                "pax_count": 1,
                                "amount": rec['provider_total_discount'] / len(book_obj.passenger_ids) * -1,
                                "foreign_currency": "IDR",
                                "foreign_amount": rec['provider_total_discount'] / len(book_obj.passenger_ids) * -1,
                                "total": rec['provider_total_discount'] / len(book_obj.passenger_ids) * -1,
                                "sequence": idx
                            }]
                            book_obj.provider_booking_ids[idx].create_service_charge(service_charge)
                    book_obj.calculate_service_charge()

                for provider in book_obj.provider_booking_ids:
                    ledger_created = provider.action_create_ledger(context['co_uid'], payment_method)
                    # if agent_obj.is_using_pnr_quota: ##selalu potong quota setiap  attemp payment
                    if agent_obj.is_using_pnr_quota and ledger_created: #tidak potong quota jika tidak membuat ledger
                        agent_obj.use_pnr_quota({
                            'res_model_resv': book_obj._name,
                            'res_id_resv': book_obj.id,
                            'res_model_prov': provider._name,
                            'res_id_prov': provider.id
                        })
                        # if not quota_used:
                        #     print("5k woi")

                return ERR.get_no_error()
            else:
                raise RequestException(1001)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            try:
                book_obj.notes += str(datetime.now()) + '\n' + traceback.format_exc() + '\n'
            except:
                _logger.error('Creating Notes Error')
            return ERR.get_error(1011)

    def get_btc_hold_date(self):
        if (self.booked_date + timedelta(hours=1)) >= self.hold_date:
            final_time = (self.hold_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            final_time = (self.booked_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        return final_time + ' (GMT +7)'

    def get_btc_url(self):
        try:
            base_url = tools.config.get('frontend_url', '')
            final_url = base_url + '/' + str(self.provider_type_id.code) + '/booking/' + (base64.b64encode(str(self.name).encode())).decode()
        except Exception as e:
            _logger.info(str(e))
            final_url = '#'
        return final_url

    def get_btc_booked_date(self):
        return (self.booked_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') + ' (GMT +7)'

    def get_btc_issued_date(self):
        return (self.issued_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') + ' (GMT +7)'
