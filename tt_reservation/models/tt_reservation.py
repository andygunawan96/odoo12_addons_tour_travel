from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools import variables, util, ERR
import json
from ...tools.ERR import RequestException
import logging, traceback
from datetime import datetime, timedelta
import time
import odoo.tools as tools
import base64
import copy

_logger = logging.getLogger(__name__)


PROVIDER_TYPE_SELECTION = {
    'AL': 'airline',
    'VS': 'visa',
    'PS': 'passport',
    'TN': 'train',
    'AT': 'activity',
    'TR': 'tour',
    'RESV': 'hotel',
    'RO': 'issued_offline',
    'BT': 'ppob',
    'EV': 'event',
    'PK': 'periksain',
    'PH': 'phc',
    'MK': 'mitrakeluarga',
    'LP': 'labpintar',
    'SE': 'swabexpress',
    'IR': 'insurance',
    'BU': 'bus',
    'SM': 'sentramedika'
}

class TtReservation(models.Model):
    _name = 'tt.reservation'
    _inherit = 'tt.history'
    _description = 'Reservation Model'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})
    provider_name = fields.Char('List of Provider', readonly=True)
    carrier_name = fields.Char('List of Carriers', readonly=True)
    voucher_code = fields.Char('Voucher', readonly=True)
    payment_method = fields.Char('Payment Method', readonly=True)
    is_member = fields.Boolean('Payment member', readonly=True)
    va_number = fields.Char('VA Number', readonly=True)

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Timelimit', readonly=True)  # fixme terpakai?
    hold_date = fields.Datetime('Price Guarantee Timelimit', readonly=True, states={'draft': [('readonly',False)]})

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Updated by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancel by', readonly=False)
    cancel_date = fields.Datetime('Cancel Date', readonly=True)
    refund_uid = fields.Many2one('res.users', 'Refund by', readonly=False)
    refund_date = fields.Datetime('Refund Date', readonly=True)
    payment_date = fields.Datetime('Payment Date', readonly=True)

    user_id = fields.Many2one('res.users', 'Booked by', readonly=True)  # create_uid
    sync_reservation = fields.Boolean('Sync Reservation', default=False) ## QUOTA PNR BTBO2
    #utk adjustment
    res_model = fields.Char('Res Model', invisible=1, readonly=True)

    sid_booked = fields.Char('SID Booked', readonly=True)  # Signature generate sendiri

    booker_id = fields.Many2one('tt.customer','Booker', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    booker_insentif = fields.Monetary('Insentif Booker')

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
    student = fields.Integer('Student', default=0, readonly=True, states={'draft': [('readonly', False)]})
    labour = fields.Integer('Labour', default=0, readonly=True, states={'draft': [('readonly', False)]})
    seaman = fields.Integer('Seaman', default=0, readonly=True, states={'draft': [('readonly', False)]})

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
    issued_request_ids = fields.One2many('tt.reservation.request', 'res_id', 'Issued Requests', readonly=True,domain=_get_res_model_domain)
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

    sale_service_charge_ids = fields.Char('Agent View Service Charge')

    total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_fare",store=True)
    total_tax = fields.Monetary(string='Total Tax', default=0, compute='_compute_total_tax',store=True)
    total = fields.Monetary(string='Grand Total', default=0, compute='_compute_grand_total',store=True)
    total_discount = fields.Monetary(string='Total Discount', default=0, compute='_compute_total_discount', store=True)
    total_commission = fields.Monetary(string='Total Commission', default=0, compute='_compute_total_commission',store=True)
    total_nta = fields.Monetary(string='NTA Amount',compute='_compute_total_nta',store=True)
    agent_nta = fields.Monetary(string='Agent NTA Amount',compute='_compute_agent_nta',store=True)
    parent_agent_commission = fields.Monetary(string='Parent Agent Commission', default=0, compute='_compute_parent_agent_commission',store=True)
    ho_commission = fields.Monetary(string='HO Commission', default=0, compute='_compute_ho_commission',store=True)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True,
                               default=lambda self: self.env.user.ho_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',readonly=True,
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]},
                                         help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id',
                                              store=True, readonly=True)

    # Jngn lup tmbhkn untuk delete printout
    printout_ticket_id = fields.Many2one('tt.upload.center', 'Ticket', readonly=True)
    printout_ticket_price_id = fields.Many2one('tt.upload.center', 'Ticket (Price)', readonly=True)
    printout_itinerary_id = fields.Many2one('tt.upload.center', 'Itinerary', readonly=True)
    printout_itinerary_price_id = fields.Many2one('tt.upload.center', 'Itinerary (Price)', readonly=True)
    printout_voucher_id = fields.Many2one('tt.upload.center', 'Voucher', readonly=True)
    printout_ho_invoice_id = fields.Many2one('tt.upload.center', 'Voucher', readonly=True)
    printout_vendor_invoice_id = fields.Many2one('tt.upload.center', 'Vendor Invoice', readonly=True)

    payment_acquirer_number_id = fields.Many2one('payment.acquirer.number','Payment Acquier Number')
    unique_amount_id = fields.Many2one('unique.amount','Unique Amount')

    # April 21, 2020 - SAM
    is_force_issued = fields.Boolean('Force Issued', default=False)
    is_halt_process = fields.Boolean('Halt Process', default=False)
    # END

    is_invoice_created = fields.Boolean('Is Invoice Created', default=False)
    reconcile_state = fields.Selection(variables.RESV_RECONCILE_STATE, 'Reconcile State',default='not_reconciled',
                                       compute='_compute_reconcile_state', store=True )

    is_using_point_reward = fields.Boolean('Is Using Point Reward', default=False)
    is_get_point_reward = fields.Boolean('Is Get Point Reward', default=False)

    payment_method_to_ho = fields.Selection([('balance','Balance'), ('credit_limit','Credit Limit')], 'Payment Method to HO', default='balance')

    is_upsell_in_service_charge = fields.Boolean('Is Upsell in service charges', default=False) ## for report old reservation

    total_pax = fields.Integer('Total Pax', readonly=True, compute='_compute_total_pax')

    estimated_currency = fields.Char('Estimated Currency')

    @api.model
    def create(self, vals_list):
        try:
            vals_list['name'] = self.env['ir.sequence'].next_by_code(self._name)
            vals_list['res_model'] = self._name
            if not vals_list.get('ho_id') and vals_list.get('agent_id'):
                agent_id = self.env['tt.agent'].browse(vals_list['agent_id'])
                if agent_id:
                    vals_list['ho_id'] = agent_id.ho_id.id
        except:
            pass
        return super(TtReservation, self).create(vals_list)

    def write(self, vals):
        if vals.get('hold_date'):
            if self.agent_id.is_btc_agent:
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

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError('Reservation data cannot be deleted. Please contact your system administrator if you need assistance on modifying or deleting this record.')
        return super(TtReservation, self).unlink()

    @api.depends('adult', 'child', 'infant', 'student', 'labour', 'seaman')
    def _compute_total_pax(self):
        for rec in self:
            rec.total_pax = rec.adult + rec.child + rec.infant + rec.elder + rec.student + rec.labour + rec.seaman

    def check_approve_refund_eligibility(self):
        return True

    def create_booker_api(self, vals, context):
        booker_obj = self.env['tt.customer'].sudo()
        get_booker_seq_id = util.get_without_empty(vals,'booker_seq_id')

        if get_booker_seq_id:
            booker_seq_id = vals['booker_seq_id']
            booker_rec = booker_obj.search([('seq_id','=',booker_seq_id)])
            update_value = {}
            if booker_rec:
                if vals.get('mobile'):
                    number_entered = False
                    vals_phone_number = '%s%s' % (vals.get('calling_code', ''), vals['mobile'])
                    for phone in booker_rec.phone_ids:
                        if phone.phone_number == vals_phone_number:
                            phone.last_updated_time = time.time()
                            number_entered = True
                            break

                    if not number_entered:
                        new_phone=[(0,0,{
                            'ho_id': context['co_ho_id'],
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

        vals.update({
            'ho_id': context['co_ho_id'],
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'ho_id': context['co_ho_id'],
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

    def get_booking_b2c_api(self, req, context):
        try:
            res = {}
            if req['product'] == 'airline':
                if req['forget_booking']:
                    origin = self.env['tt.destinations'].search([('code','=',req['origin']),('provider_type_id.code','=','airline')],limit=1)
                    destination = self.env['tt.destinations'].search([('code','=',req['destination']),('provider_type_id.code','=','airline')],limit=1)
                    if origin and destination:
                        book_objs = self.env['tt.reservation.%s' % req['product']].search([('origin_id','=',origin.id), ('destination_id','=',destination.id), ('contact_phone','=',req['phone_number']), ('departure_date','=',req['date'])])
                        res = []
                        for rec in book_objs:
                            book = self.env['tt.reservation.%s' % req['product']].get_booking_airline_api({'order_number':rec.name}, context)
                            if book['error_code'] == 0:
                                res.append(book['response'])
                        if len(res) == 0:
                            return ERR.get_error(1013)
                        res = ERR.get_no_error(res)
                    else:
                        return ERR.get_error(1013)
                else:
                    book_obj = self.env['tt.reservation.%s' % req['product']].get_booking_airline_api(req, context)
                    # check res
                    # kalau lupa booking origin, destination, tanggal, phone number
                    if book_obj['error_code'] == 0:
                        if req['date'] == book_obj['response']['departure_date'] and req['phone_number'] == book_obj['response']['contact']['phone']:
                            res = book_obj
                        else:
                            return ERR.get_error(1013)
                    else:
                        return ERR.get_error(1013)

            elif req['product'] == 'train':
                if req['forget_booking']:
                    origin = self.env['tt.destinations'].search([('code','=',req['origin']),('provider_type_id.code','=','train')],limit=1)
                    destination = self.env['tt.destinations'].search([('code','=',req['destination']),('provider_type_id.code','=','train')],limit=1)
                    if origin and destination:
                        book_objs = self.env['tt.reservation.%s' % req['product']].search([('origin_id','=',origin.id), ('destination_id','=',destination.id), ('contact_phone','=',req['phone_number']), ('departure_date','=',req['date'])])
                        res = []
                        for rec in book_objs:
                            book = self.env['tt.reservation.%s' % req['product']].get_booking_train_api({'order_number':rec.name}, context)
                            if book['error_code'] == 0:
                                res.append(book['response'])
                        if len(res) == 0:
                            return ERR.get_error(1013)
                        res = ERR.get_no_error(res)
                    else:
                        return ERR.get_error(1013)
                else:
                    book_obj = self.env['tt.reservation.%s' % req['product']].get_booking_train_api(req, context)
                    # check res
                    # kalau lupa booking origin, destination, tanggal, phone number
                    if book_obj['error_code'] == 0:
                        if req['date'] == book_obj['response']['departure_date'] and req['phone_number'] == book_obj['response']['contact']['phone']:
                            res = book_obj
                        else:
                            return ERR.get_error(1013)
                    else:
                        return ERR.get_error(1013)
            elif req['product'] == 'hotel':
                if req['forget_booking']:
                    book_objs = self.env['tt.reservation.%s' % req['product']].search([('hotel_city', '=', req['city']), ('checkin_date', '=', req['date']),('contact_phone', '=', req['phone_number'])])
                    # book_objs = self.env['tt.reservation.%s' % req['product']].search([('hotel_city', 'ilike', ''), ('checkin_date', '=', req['date']),('contact_phone', '=', False)]) # testing
                    res = []
                    for rec in book_objs:
                        res.append(self.env['test.search'].get_booking_result(rec.name, context))
                    if len(res) == 0:
                        return ERR.get_error(1013)
                    res = ERR.get_no_error(res)
                else:
                    book_obj = self.env['test.search'].get_booking_result(req['order_number'], context)
                    if book_obj:
                        if req['date'] == book_obj['checkin_date'] and req['phone_number'] == book_obj['contact']['phone']:
                            res = book_obj
                        # if True: #testing
                        #     res = book_obj #testing
                        else:
                            return ERR.get_error(1013)
                        res = ERR.get_no_error(res)
                    else:
                        return ERR.get_error(1013)
                # kalau lupa booking nama hotel, checkin, phone number
            elif req['product'] == 'activity':
                res = self.env['tt.reservation.%s' % req['product']].get_booking_by_api(req, context)
                # kalau lupa booking nama activity, tanggal, phone number
            elif req['product'] == 'tour':
                res = self.env['tt.reservation.%s' % req['product']].get_booking_api(req, context)
                # kalau lupa booking nama tour, tanggal, phone number
            elif req['product'] == 'ppob':
                res = self.env['tt.reservation.%s' % req['product']].get_inquiry_api(req, context)
                # kalau lupa booking nomor pelanggan, bulan, phone number
            elif req['product'] == 'visa':
                res = self.env['tt.reservation.%s' % req['product']].get_booking_visa_api(req, context)
            elif req['product'] == 'passport':
                res = self.env['tt.reservation.%s' % req['product']].get_booking_passport_api(req, context)
            elif req['product'] == 'event':
                res = self.env['tt.reservation.%s' % req['product']].get_booking_from_backend(req, context)
            elif req['product'] == 'phc':
                if req['forget_booking']:
                    book_objs = self.env['tt.reservation.%s' % req['product']].search([('hotel_city', '=', req['city']), ('checkin_date', '=', req['date']),('contact_phone', '=', req['phone_number'])])
                    # book_objs = self.env['tt.reservation.%s' % req['product']].search([('hotel_city', 'ilike', ''), ('checkin_date', '=', req['date']),('contact_phone', '=', False)]) # testing
                    res = []
                    for rec in book_objs:
                        res.append(self.env['test.search'].get_booking_result(rec.name, context))
                    if len(res) == 0:
                        return ERR.get_error(1013)
                    res = ERR.get_no_error(res)
                else:
                    res = self.env['tt.reservation.%s' % req['product']].get_booking_phc_api(req, context)
            elif req['product'] == 'medical':
                book_obj = self.env['tt.reservation.medical'].get_booking_medical_api({"order_number": req['order_number']}, context)
                if book_obj:
                    if book_obj['response']['contact_id']['name'].lower() == req['booker_name'].lower():
                        res = book_obj['response']
                    else:
                        return ERR.get_error(1013)
                    res = ERR.get_no_error(res)
                else:
                    return ERR.get_error(1013)
            elif req['product'] == 'mitrakeluarga':
                book_obj = self.env['tt.reservation.mitrakeluarga'].get_booking_mitrakeluarga_api({"order_number": req['order_number']}, context)
                if book_obj:
                    if book_obj['response']['contact_id']['name'].lower() == req['booker_name'].lower():
                        res = book_obj['response']
                    else:
                        return ERR.get_error(1013)
                    res = ERR.get_no_error(res)
                else:
                    return ERR.get_error(1013)
            return res
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)


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
                            phone.last_updated_time = time.time()
                            number_entered = True
                            break
                    if not number_entered:
                        new_phone = [(0, 0, {
                            'ho_id': context['co_ho_id'],
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

        vals.update({
            'ho_id': context['co_ho_id'],
            'agent_id': context['co_agent_id'],
            'nationality_id': country and country[0].id or False,
            'email': vals.get('email'),
            'phone_ids': [(0,0,{
                'ho_id': context['co_ho_id'],
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
        # ini perlu, karena kalau jadi pax dan dia contact. create di call dluan, jadi bukan di create waktu create pax objectnya.
        if context.get('co_customer_parent_id'):
            vals.update({
                'customer_parent_ids': [(4, context['co_customer_parent_id'])]
            })

        return contact_obj.create(vals)

    def create_customer_api(self,passengers,context,booker_seq_id=False,contact_seq_id=False):
        country_obj = self.env['res.country'].sudo()
        passenger_obj = self.env['tt.customer'].sudo()

        res_ids = []
        # identity_req = ['identity_number','identity_country_of_issued_id','identity_expdate','identity_type']
        ho_agent_obj = self.env['tt.agent'].browse(context['co_ho_id'])
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
                    if ho_agent_obj:
                        vals_for_update.update({
                            'ho_id': ho_agent_obj.id
                        })

                    #manual aja
                    # [vals_for_update.update({
                    #     key: psg[key]
                    # }) for key in update_list if psg.get(key) != getattr(current_passenger, key)]

                    if vals_for_update:
                        current_passenger.update(vals_for_update)

                    ## update customer behavior 1 maret 2023 IVAN
                    if psg.get('behaviors'):
                        for provider_type in psg['behaviors']:
                            current_passenger.add_behavior(provider_type.lower(), psg['behaviors'][provider_type])

                    if psg.get('identity'):
                        current_passenger.add_or_update_identity(psg['identity'])
                    if psg.get('ff_numbers'):
                        current_passenger.add_or_ff_number(psg['ff_numbers'])
                    res_ids.append(current_passenger)
                    continue

            psg['ho_id'] = context['co_ho_id']
            psg['agent_id'] = context['co_agent_id']

            psg.update({
                'marital_status': 'married' if psg.get('title') == 'MRS' else '',
                'is_get_booking_from_vendor': psg.get('is_get_booking_from_vendor', False),
                'register_uid': context['co_uid'],
                'ho_id': ho_agent_obj.id
            })
            # sepertinya tidak terpakai
            # #if ada phone, kalau dari frontend cache passenger
            # if psg.get('phone'):
            #     psg.update({
            #         'phone_ids': [(0, 0, {
            #             'calling_code': psg.get('phone_id', ''),
            #             'calling_number': psg.get('phone', ''),
            #             'phone_number': '%s%s' % (psg.get('phone_id', ''), psg.get('phone', '')),
            #             'country_id': country and country[0].id or False,
            #         })]
            #     })

            ##ngelink kan customer yg baru di create ke corporate login user, seharusnya hanya terjadi kalau corpnya login sendiri
            if context.get('co_customer_parent_id'):
                psg.update({
                    'customer_parent_ids': [(4,context['co_customer_parent_id'])]
                })

            psg_obj = passenger_obj.create(psg)

            ## update customer behavior 1 maret 2023 IVAN
            if psg.get('behaviors'):
                for provider_type in psg['behaviors']:
                    psg_obj.add_behavior(provider_type.lower(), psg['behaviors'][provider_type])

            if psg.get('identity'):
                if not psg['identity'].get('identity_first_name'):
                    psg['identity'].update({
                        'identity_first_name': psg['first_name'],
                        'identity_last_name': psg.get('last_name', '')
                    })
                psg_obj.add_or_update_identity(psg['identity'])
            if psg.get('identity_passport'):
                if not psg['identity_passport'].get('identity_first_name'):
                    psg['identity_passport'].update({
                        'identity_first_name': psg['first_name'],
                        'identity_last_name': psg.get('last_name', '')
                    })
                psg_obj.add_or_update_identity(psg['identity_passport'])
            if psg.get('ff_numbers'):
                psg_obj.add_or_ff_number(psg['ff_numbers'])
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

    def create_passenger_value_api(self,passenger):
        list_passenger_value = []
        country_obj = self.env['res.country'].sudo()
        for rec in passenger:
            nationality_id = country_obj.search([('code','=ilike',rec['nationality_code'])],limit=1).id
            identity = rec.get('identity')
            is_valid_identity = identity and identity.get('is_valid_identity', True) or True
            idt_first_name = ''
            idt_last_name = ''
            if identity:
                idt_first_name = identity.get('identity_first_name') and identity['identity_first_name'] or ''
                idt_last_name = identity.get('identity_last_name') and identity['identity_last_name'] or ''
            if idt_first_name:
                name_tuple = (idt_first_name, idt_last_name)
            else:
                name_tuple = (rec['first_name'],rec['last_name'])
            pax_data = (0,0,{
                'name': "%s %s" % name_tuple,
                'first_name': idt_first_name if idt_first_name else rec['first_name'],
                'last_name': idt_last_name if idt_first_name else rec['last_name'],
                'gender': rec['gender'],
                'title': rec['title'],
                'birth_date': rec.get('birth_date',False),
                'nationality_id': nationality_id,
                'identity_type': identity and identity['identity_type'] or '',
                'identity_number': identity and identity['identity_number'] or '',
                'identity_expdate': identity and identity['identity_expdate'] or False,
                'identity_country_of_issued_id': identity and country_obj.search([('code','=ilike',identity['identity_country_of_issued_code'])],limit=1).id or False,
                'sequence': rec['sequence'],
                'is_valid_identity': is_valid_identity
            })
            identity_passport = rec.get('identity_passport')
            if identity_passport:
                pax_data[2].update({
                    'passport_type': identity_passport['identity_type'],
                    'passport_number': identity_passport['identity_number'],
                    'passport_expdate': identity_passport['identity_expdate'],
                    'passport_country_of_issued_id': country_obj.search([('code','=ilike',identity_passport['identity_country_of_issued_code'])],limit=1).id,
                })
            list_passenger_value.append(pax_data)

        return list_passenger_value

    def _compute_reconcile_state(self):
        for rec in self:
            if not rec.reconcile_state:
                rec.reconcile_state = 'not_reconciled'

    @api.depends("refund_ids", "state")
    @api.onchange("refund_ids", "state")
    def _compute_refundable(self):
        for rec in self:
            if rec.state in ['issued','rescheduled']:
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

    def multi_recalculate_service_charges(self):
        for rec in self:
            _logger.info(rec.name)
            rec.calculate_service_charge()
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
                if sale.charge_type in ['ROC', 'TAX','ADMIN_FEE_MEDICAL'] and sale.charge_code != 'csc':
                    tax_total += sale.total
            rec.total_tax = tax_total

    @api.depends("sale_service_charge_ids")
    def _compute_grand_total(self):
        for rec in self:
            grand_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type not in ['RAC', 'DISC']:
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
                if sale.charge_type != 'DISC' and sale.charge_code != 'csc': # don't count channel upsell
                    nta_total += sale.total
            rec.total_nta = nta_total

    @api.depends("sale_service_charge_ids")
    def _compute_total_discount(self):
        for rec in self:
            total_discount = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type in ['DISC']:
                    total_discount += abs(sale.total)
            rec.total_discount = total_discount

    @api.depends("sale_service_charge_ids")
    def _compute_agent_nta(self):
        for rec in self:
            agent_nta_total = 0
            for sale in rec.sale_service_charge_ids:
                if (sale.charge_code != 'rac' and sale.charge_type == 'RAC') and sale.charge_code != 'csc':
                    agent_nta_total += sale.total * -1
            rec.agent_nta = agent_nta_total + rec.total_nta

    @api.depends("sale_service_charge_ids")
    def _compute_parent_agent_commission(self):
        for rec in self:
            commission_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'RAC' and sale.charge_code != 'rac' and sale.commission_agent_id and not sale.commission_agent_id.is_ho_agent:
                    commission_total += abs(sale.total)
            rec.parent_agent_commission = commission_total

    @api.depends("sale_service_charge_ids")
    def _compute_ho_commission(self):
        for rec in self:
            commission_total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'RAC' and sale.commission_agent_id and sale.commission_agent_id.is_ho_agent:
                    commission_total += abs(sale.total)
            rec.ho_commission = commission_total

    def cancel_payment(self, req, context): # cancel di gabung karena sama semua kalau create payment beda" per reservasi karena di panggil waktu issued
        book_obj = self.env['tt.reservation.%s' % PROVIDER_TYPE_SELECTION[req['order_number'].split('.')[0]]].search([('name', '=', req['order_number'])])
        try:
            book_obj.create_date
        except:
            raise RequestException(1001)

        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)

        if book_obj.agent_id.id == context.get('co_agent_id', -1) or self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids or book_obj.agent_id.is_btc_agent or book_obj.user_id.agent_id.is_btc_agent:
            payment_acq_number = ''
            bank_code = ''
            url = ''
            amount = 0
            phone_number = ''
            name = ''
            email = ''
            bank_name = ''
            provider = ''
            if book_obj.payment_acquirer_number_id:
                if book_obj.payment_acquirer_number_id.payment_acquirer_id.account_number == '' or book_obj.payment_acquirer_number_id.payment_acquirer_id.account_number == False: # ESPAY
                    payment_acq_number = book_obj.payment_acquirer_number_id.number
                    url = book_obj.payment_acquirer_number_id.url
                    amount = book_obj.payment_acquirer_number_id.amount
                    bank_code = book_obj.payment_acquirer_number_id.payment_acquirer_id.bank_id.code
                    bank_name = book_obj.payment_acquirer_number_id.payment_acquirer_id.name
                    name = book_obj.contact_title
                    phone_number = book_obj.contact_phone
                    email = book_obj.contact_email
                    if book_obj.payment_acquirer_number_id.provider_id:
                        provider = book_obj.payment_acquirer_number_id.provider_id.code
                book_obj.payment_acquirer_number_id.state = 'cancel2'
                book_obj.payment_acquirer_number_id = False
            return ERR.get_no_error({
                "order_number": book_obj.name,
                "payment_acq_number": payment_acq_number,
                "provider": provider,
                "bank_code": bank_code,
                "bank_name": bank_name,
                'url': url,
                "amount": amount,
                "name": name,
                "phone_number": phone_number,
                "email": email,

            })
        else:
            return ERR.get_error(1001)

    def to_dict(self, context=False):
        # invoice_list = []
        # if hasattr(self, 'invoice_line_ids'):
        #     for rec in self.invoice_line_ids:
        #         invoice_list.append({
        #             'name': rec.name,
        #             'state': rec.state
        #         })
        include_total_nta = False
        if context and context.get('co_agent_id'):
            include_total_nta = context['co_agent_id'] == context['co_ho_id']
        payment_acquirer_number = {}
        if self.payment_acquirer_number_id:
            if self.payment_acquirer_number_id.state in ['close']: ## hanya state close yg di check timelimit
                if not self.payment_acquirer_number_id.time_limit:
                    self.cancel_payment_method()
                different_time = self.payment_acquirer_number_id.time_limit - datetime.now()
                if different_time > timedelta(seconds=0):  ## LEBIH DARI 1 JAM TIMELIMIT 55 MENIT
                    payment_acquirer_number = {
                        'create_date': self.payment_acquirer_number_id.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                        'time_limit': self.payment_acquirer_number_id.time_limit and self.payment_acquirer_number_id.time_limit.strftime("%Y-%m-%d %H:%M:%S") or (self.payment_acquirer_number_id.create_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                        'nomor_rekening': self.payment_acquirer_number_id.payment_acquirer_id.account_number,
                        'account_name': self.payment_acquirer_number_id.payment_acquirer_id.account_name,
                        'va_number': self.payment_acquirer_number_id.va_number,
                        'url': self.payment_acquirer_number_id.url,
                        'amount': self.payment_acquirer_number_id.get_total_amount(),
                        'order_number': self.payment_acquirer_number_id.number,
                        'currency': self.payment_acquirer_number_id.currency_id.name,
                        'state': self.payment_acquirer_number_id.state
                    }
                else:
                    self.cancel_payment_method()
        if self.voucher_code and self.state in ['booked']: ##SETIAP GETBOOKING STATUS BOOKED CHECK VOUCHER VALID/TIDAK, YG EXPIRED DI LEPAS LEWAT CRON
            self.check_voucher_valid(self.voucher_code, context)
        is_agent = False
        if context and context.get('co_agent_id'):
            if context['co_agent_id'] == self.agent_id.id:
                is_agent = True

        if len(self.issued_request_ids.ids) <= 0:
            issued_request_status = 'none'
        else:
            if any(rec.state == 'approved' for rec in self.issued_request_ids):
                issued_request_status = 'approved'
            elif any(rec.state in ['draft', 'on_process'] for rec in self.issued_request_ids):
                issued_request_status = 'on_process'
            else:
                issued_request_status = 'none'

        res = {
            'order_number': self.name,
            'book_id': self.id,
            'ho_id': self.ho_id.id if self.ho_id else '',
            'agent_id': self.agent_id.id if self.agent_id else '',
            'agent_name': self.agent_id.name if self.agent_id else '',
            'customer_parent_name': self.customer_parent_id.name if self.customer_parent_id else '',
            'customer_parent_type_name': self.customer_parent_type_id.name if self.customer_parent_type_id else '',
            'pnr': self.pnr and self.pnr or '',
            'state': self.state,
            'state_description': variables.BOOKING_STATE_STR[self.state],
            'hold_date': self.hold_date and self.hold_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'YCD': self.elder,
            'ADT': self.adult,
            'CHD': self.child,
            'INF': self.infant,
            'is_agent': is_agent,
            'contact': {
                'title': self.contact_title,
                'name': self.contact_name,
                'email': self.contact_email,
                'phone': self.contact_phone
            },
            'voucher_reference': self.voucher_code,
            'voucher_discount': self.get_total_voucher() if self.voucher_code else 0,
            'contact_id': self.contact_id.to_dict(),
            'booker': self.booker_id.to_dict(),
            'departure_date': self.departure_date and self.departure_date or '',
            'arrival_date': self.arrival_date and self.arrival_date or '',
            'provider_type': self.provider_type_id.code,
            'payment_acquirer_number': payment_acquirer_number,
            'issued_request_status': issued_request_status,
            # May 19, 2020 - SAM
            'is_force_issued': self.is_force_issued,
            'is_halt_process': self.is_halt_process,
            'agent_nta': self.agent_nta,
            'create_date': self.create_date and self.create_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'booked_date': self.booked_date and self.booked_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'booked_by': self.user_id.name,
            'issued_by': self.issued_uid.name,
            'issued_date': self.issued_date and self.issued_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'use_point': self.is_using_point_reward,
            'signature_booked': self.sid_booked,
            'currency': self.currency_id.name,
            'estimated_currency': json.loads(self.estimated_currency) if self.estimated_currency else {}
            # END
        }
        if self.booker_insentif:
            res['booker_insentif'] = self.booker_insentif
        if include_total_nta:
            res['total_nta'] = self.total_nta

        # March 28, 2022 - SAM
        # Menambahkan data info user context (user yang booking)
        user_context = {}
        if self.user_id:
            user_context = self.user_id.get_credential(prefix='co_')
            co_user_info = self.env['tt.agent'].sudo().get_agent_level(user_context['co_agent_id'])
            co_customer_parent_type_code = self.customer_parent_type_id.code if self.customer_parent_type_id else ''
            co_customer_parent_id = self.customer_parent_id.id if self.customer_parent_id else ''
            user_context.update({
                'co_customer_parent_type_code': co_customer_parent_type_code,
                'co_customer_parent_id': co_customer_parent_id,
                'co_user_info': co_user_info,
            })
        res.update({
            'user_context': user_context,
        })
        # END
        return res

    def cancel_payment_method(self):
        if self.payment_acquirer_number_id:
            self.payment_acquirer_number_id.state = 'cancel'
            self.payment_acquirer_number_id = False

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

    def get_transaction_additional_info(self): #placeholder function please don't delete
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

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                return ERR.get_error(1008)

            if book_obj.agent_id.id == context['co_agent_id'] or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
                for psg in req['passengers']:
                    for psg_obj in book_obj.passenger_ids:
                        if psg['sequence'] == psg_obj.sequence:
                            psg_obj.create_channel_pricing(psg['pricing'], req.get('type', ''))
                            break
                book_obj.create_svc_upsell()
            else:
                return ERR.get_error(1001)
        except Exception as e:
            _logger.error(str(e) + traceback.format_exc())
            return ERR.get_error(500, additional_message=str(e))
        return ERR.get_no_error()

    def recompute_svc_upsell(self):
        types = variables.PROVIDER_TYPE
        dom = []
        dom.append(('total_channel_upsell', '!=', 0))
        for type in types:
            list_obj = self.env['tt.reservation.%s' % (type)].search(dom, order='create_date desc')
            for rec in list_obj:
                _logger.info('check upsell for %s' % rec.name)
                try:
                    rec.create_svc_upsell()
                except Exception as e:
                    _logger.error('%s, %s' % (str(e), traceback.format_exc()))

    def create_svc_upsell(self):
        # if self.state in ['booked', 'halt_booked','halt', 'draft']: ## check reservasi terluar
        #     svc_list = []
        #     total_pax = {
        #         "ADT": {
        #             "total": 0,
        #             "id": []
        #         },
        #         "CHD": {
        #             "total": 0,
        #             "id": []
        #         },
        #         "INF": {
        #             "total": 0,
        #             "id": []
        #         },
        #     }
        #
        #     for idx, rec in enumerate(self.provider_booking_ids):
        #         total_provider = len(self.provider_booking_ids)
        #         for pax in self.passenger_ids:
        #             pax_type = ''
        #             if idx == 0:
        #                 if hasattr(rec, 'ticket_ids'):
        #                     for ticket in rec.ticket_ids:
        #                         if pax.id == ticket.passenger_id.id:
        #                             pax_type = ticket.pax_type
        #                             total_pax[pax_type]['total'] += 1
        #                             total_pax[pax_type]['id'].append(pax.id)
        #                             break
        #                 else:
        #                     # tidak ada ticket upsell per reservasi asumsi adult 1
        #                     ## hotel, ppob
        #                     pax_type = 'ADT'
        #                     total_pax[pax_type]['total'] = 1
        #                     total_pax[pax_type]['id'].append(pax.id)
        #
        #             for sc in pax.channel_service_charge_ids:
        #                 sc_pax = copy.deepcopy(sc.to_dict())
        #
        #                 if pax_type != '' and total_pax[pax_type]['total'] == 1 or '.' in sc_pax['charge_code']:
        #                     sc_pax.update({
        #                         "charge_type": 'ROC',
        #                         "amount": sc_pax['amount'] / total_provider,
        #                         "pax_type": pax_type,
        #                         "pax_count": 0,
        #                         "foreign_amount": sc_pax['amount'] / total_provider,
        #                     })
        #                     if '.' in sc_pax['charge_code']: ## untuk upsell after sales per orang
        #                         sc_pax.update({
        #                             "pax_count": 1,
        #                             "passenger_%s_ids" % self.provider_type_id.code: [(6, 0, [pax.id])]
        #                         })
        #                     svc_list.append(sc_pax)
        #
        #                     sc_pax = copy.deepcopy(sc_pax)
        #                     ## jika harga lebih dari 0 bikin rac upsell, jika kurang dari 0 discount tidak bikin rac
        #                     ## FIXME DOWNSELL UPSELL TETAP BIKIN RAC 16 MARET 2023
        #                     # if sc['amount'] > 0:
        #                     sc_pax.update({
        #                         "charge_type": 'RAC',
        #                         "amount": sc_pax['amount'] * -1,
        #                     })
        #                     svc_list.append(sc_pax)
        #     if svc_list:
        #         for rec in self.provider_booking_ids:
        #             svc_list_to_save_backend = []
        #             for svc in svc_list:
        #                 svc.update({
        #                     "description": rec.pnr if rec.pnr != False else '',
        #                     'total': svc['amount'] * svc.get('pax_count', 0),
        #                     'currency_id': rec.currency_id.id,
        #                     'foreign_currency_id': rec.currency_id.id,
        #                 })
        #                 if svc['total'] == 0:
        #                     svc.update({
        #                         "passenger_%s_ids" % self.provider_type_id.code: [(6, 0, total_pax[svc['pax_type']]['id'])],
        #                         'pax_count': total_pax[svc['pax_type']]['total'],
        #                         'total': svc['amount'] * total_pax[svc['pax_type']]['total'],
        #                     })
        #                 svc_list_to_save_backend.append((4, self.env['tt.service.charge'].create(svc).id))
        #             ##update cost service charges passenger
        #             for svc in rec.cost_service_charge_ids:
        #                 if 'csc' in svc.charge_code and svc.charge_type in ['RAC', 'ROC']:
        #                     svc_list_to_save_backend.append((2, svc.id))
        #             rec.write({
        #                 'cost_service_charge_ids': svc_list_to_save_backend
        #             })
        #         self.calculate_service_charge()
        #         self.is_upsell_in_service_charge = True
        #         _logger.info('update upsell for %s' % self.name)
        #     else:
        #         _logger.info('upsell not found for %s' % self.name)
        ho_obj = False
        if self.ho_id:
            ho_obj = self.ho_id
        elif self.agent_id:
            ho_obj = self.agent_id.ho_id

        svc_list = []
        total_pax = {
            "ADT": {
                "total": 0,
                "id": []
            },
            "CHD": {
                "total": 0,
                "id": []
            },
            "INF": {
                "total": 0,
                "id": []
            },
            "YCD": {
                "total": 0,
                "id": []
            }
        }

        for idx, rec in enumerate(self.provider_booking_ids):
            total_provider = len(self.provider_booking_ids)
            if rec.state in ['booked', 'halt_booked','halt', 'draft']:
                for pax in self.passenger_ids:
                    pax_type = ''
                    if idx == 0:
                        if hasattr(rec, 'ticket_ids'):
                            for ticket in rec.ticket_ids:
                                if pax.id == ticket.passenger_id.id:
                                    pax_type = ticket.pax_type
                                    total_pax[pax_type]['total'] += 1
                                    total_pax[pax_type]['id'].append(pax.id)
                                    break
                        else:
                            # tidak ada ticket upsell per reservasi asumsi adult 1
                            ## hotel, ppob
                            pax_type = 'ADT'
                            total_pax[pax_type]['total'] = 1
                            total_pax[pax_type]['id'].append(pax.id)

                    for sc in pax.channel_service_charge_ids:
                        sc_pax = copy.deepcopy(sc.to_dict())

                        if pax_type != '' and total_pax[pax_type]['total'] == 1 or '.' in sc_pax['charge_code']:
                            sc_pax.update({
                                "charge_type": 'ROC',
                                "amount": sc_pax['amount'] / total_provider,
                                "pax_type": pax_type,
                                "pax_count": 0,
                                "foreign_amount": sc_pax['amount'] / total_provider,
                            })
                            if '.' in sc_pax['charge_code']: ## untuk upsell after sales per orang
                                sc_pax.update({
                                    "pax_count": 1,
                                    "passenger_%s_ids" % self.provider_type_id.code: [(6, 0, [pax.id])]
                                })
                            svc_list.append(sc_pax)

                            sc_pax = copy.deepcopy(sc_pax)
                            ## jika harga lebih dari 0 bikin rac upsell, jika kurang dari 0 discount tidak bikin rac
                            ## FIXME DOWNSELL UPSELL TETAP BIKIN RAC 16 MARET 2023
                            # if sc['amount'] > 0:
                            sc_pax.update({
                                "charge_type": 'RAC',
                                "amount": sc_pax['amount'] * -1,
                            })
                            svc_list.append(sc_pax)
        if svc_list:
            for rec in self.provider_booking_ids:
                svc_list_to_save_backend = []
                for svc in svc_list:
                    svc.update({
                        "description": rec.pnr if rec.pnr != False else '',
                        'total': svc['amount'] * svc.get('pax_count', 0),
                        'currency_id': rec.currency_id.id,
                        'foreign_currency_id': rec.currency_id.id,
                        'ho_id': ho_obj and ho_obj.id or False
                    })
                    if svc['total'] == 0:
                        svc.update({
                            "passenger_%s_ids" % self.provider_type_id.code: [(6, 0, total_pax[svc['pax_type']]['id'])],
                            'pax_count': total_pax[svc['pax_type']]['total'],
                            'total': svc['amount'] * total_pax[svc['pax_type']]['total'],
                        })
                    svc_list_to_save_backend.append((4, self.env['tt.service.charge'].create(svc).id))
                ##update cost service charges passenger
                for svc in rec.cost_service_charge_ids:
                    if 'csc' in svc.charge_code and svc.charge_type in ['RAC', 'ROC']:
                        svc_list_to_save_backend.append((2, svc.id))
                rec.write({
                    'cost_service_charge_ids': svc_list_to_save_backend
                })
            self.calculate_service_charge()
            self.is_upsell_in_service_charge = True
            _logger.info('update upsell for %s' % self.name)
        else:
            _logger.info('upsell not found for %s' % self.name)

    ##butuh field
    def booker_insentif_api(self, req, context):
        try:
            resv_obj = self.env['tt.reservation.%s' % (req['provider_type'])]
            book_obj = resv_obj.get_book_obj(req.get('book_id'), req.get('order_number'))
            try:
                book_obj.create_date
            except:
                return ERR.get_error(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                return ERR.get_error(1008)

            if book_obj.agent_id.id == context['co_agent_id'] or self.env.ref('tt_base.group_tt_process_channel_bookings').id in user_obj.groups_id.ids:
                book_obj.booker_insentif = req['booker']['amount']
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
            for rec in self.issued_request_ids:
                rec.action_cancel()
            self.delete_voucher()
        except:
            _logger.error("provider type %s failed to expire vendor" % (self._name))

    def action_cancel(self, context=False, gateway_context=False):
        self.cancel_date = fields.Datetime.now()
        if gateway_context:
            self.cancel_uid = gateway_context['co_uid']
        else:
            self.cancel_uid = self.env.user.id
        self.state = 'cancel'

    # def get_installment_dp_amount(self):
    ##overwrite this method for installment
    def get_nta_amount(self,method='full'):
        return self.agent_nta

    # June 2, 2020 - SAM
    def get_unpaid_nta_amount(self, method='full'):
        unpaid_nta_amount = 0.0
        for provider_obj in self.provider_booking_ids:
            # if provider_obj.state == 'issued':
            #     continue
            ## 19 JUN 2023 IVAN fail_booked tidak dihitung
            if provider_obj.state in ['fail_booked']:
                continue
            for sc in provider_obj.cost_service_charge_ids:
                if sc.is_ledger_created or (sc.charge_type == 'RAC' and sc.charge_code not in ['rac', 'csc']):
                    continue
                unpaid_nta_amount += sc.total
        return unpaid_nta_amount
    # END

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

    def set_sync_reservation_api(self, req, context):
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.%s' % (req['table_name'])].browse(req.get('book_id'))
            else:
                book_obj = self.env['tt.reservation.%s' % (req['table_name'])].search([('name', '=', req.get('order_number'))],
                                                                               limit=1)
            book_obj.sync_reservation = req['is_sync_reservation']
            return ERR.get_no_error()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)

    def create_reservation_issued_request_api(self, req, context):
        if req.get('book_id'):
            book_obj = self.env['tt.reservation.%s' % (req['table_name'])].browse(req['book_id'])
        else:
            book_obj = self.env['tt.reservation.%s' % (req['table_name'])].search(
                [('name', '=', req['order_number'])], limit=1)
        if not book_obj:
            return ERR.get_error(1001)

        try:
            if context.get('co_customer_seq_id'):
                booker_obj = self.env['tt.customer'].search([('seq_id', '=', context['co_customer_seq_id'])], limit=1)
            else:
                booker_obj = book_obj.booker_id
            booking_booker_obj = self.env['tt.customer.parent.booker.rel'].search([('customer_parent_id', '=', context.get('co_customer_parent_id', book_obj.customer_parent_id.id)), ('customer_id', '=', booker_obj.id)], limit=1)
            upline_user_list_id = []
            if booking_booker_obj:
                booker_hierarchy = booking_booker_obj.job_position_id and booking_booker_obj.job_position_id.hierarchy_id.sequence or 10
                upline_user_list_id = book_obj.customer_parent_id.get_upline_user_customer_parent(booker_hierarchy)
            else:
                booker_hierarchy = 10
            request_obj = self.env['tt.reservation.request'].create({
                'res_model': book_obj._name,
                'res_id': book_obj.id,
                'booker_id': booker_obj.id,
                'user_id': context['co_uid'],
                'ho_id': context.get('co_ho_id', book_obj.ho_id.id),
                'agent_id': context.get('co_agent_id', book_obj.agent_id.id),
                'customer_parent_id': context.get('co_customer_parent_id', book_obj.customer_parent_id.id),
                'cur_approval_seq': context.get('co_hierarchy_sequence', booker_hierarchy),
                # 'upline_ids': [(6,0,upline_user_list_id)]
            })
            for rec in upline_user_list_id:
                self.env['tt.reservation.request.res.users.rel'].create({
                    "reservation_request_id": request_obj.id,
                    "user_id": rec
                })

            request_obj.send_email_to_upline()
            response = {
                'request_id': request_obj.id,
                'request_number': request_obj.name
            }
            return ERR.get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1005)

    def get_discount(self, voucher_reference, context):
        voucher = {
            'order_number': self.name,
            'voucher_reference': voucher_reference,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'provider_type': self._name.split('.')[len(self._name.split('.')) - 1],
            'provider': self.provider_name.split(',')
        }
        return voucher, self.env['tt.voucher.detail'].new_simulate_voucher(voucher, context)

    def check_voucher_valid(self, voucher_reference, context={}):
        if voucher_reference:
            voucher_dict, discount = self.get_discount(voucher_reference, context)
            is_same_voucher_value = self.is_same_total_discount_voucher(discount)
            if discount['error_code'] != 0 or not is_same_voucher_value:
                self.delete_voucher()

    def is_same_total_discount_voucher(self, discount_list):
        total_discount_voucher = 0
        total_discount_in_reservation = 0
        for rec_discount in discount_list['response']:
            total_discount_voucher += rec_discount['provider_total_discount'] * -1
        for svc_discount in self.env['tt.service.charge'].search([('res_voucher_model', '=', self._name), ('res_voucher_id', '=', self.id), ('is_voucher', '=', True)]):
            total_discount_in_reservation += svc_discount.total
        if total_discount_in_reservation == total_discount_voucher:
            return True
        return False

    def get_total_voucher(self):
        total_discount_in_reservation = 0
        for svc_discount in self.env['tt.service.charge'].search([('res_voucher_model', '=', self._name), ('res_voucher_id', '=', self.id), ('is_voucher', '=', True)]):
            total_discount_in_reservation += svc_discount.total * -1
        return total_discount_in_reservation

    def add_voucher(self, voucher_reference, context={}, type='apply'): ##type apply --> pasang, use --> pakai
        if self.state in ['draft', 'booked', 'issued', 'halt_booked']: ## DRAFT UNTUK VOUCHER BOOK / FORCE ISSUED
            if voucher_reference:
                voucher_dict, discount = self.get_discount(voucher_reference, context)
                is_same_voucher_value = True
                if discount['error_code'] == 0: ##kalau voucher bisa di pakai baru di check
                    self.voucher_code = voucher_reference
                    is_same_voucher_value = self.is_same_total_discount_voucher(discount)

                if not is_same_voucher_value and discount['error_code'] == 0: ## kalau ada beda discount
                    self.delete_voucher()
                    for idx, rec in enumerate(discount['response']):  ##DISKON PER PROVIDER
                        pax_type_dict = {}
                        total_pax = 0
                        passenger_list_id = []
                        for pax_obj in self.passenger_ids:
                            pax_type = ''
                            passenger_list_id.append(pax_obj.id)
                            if pax_obj.cost_service_charge_ids:
                                pax_type = pax_obj.cost_service_charge_ids[0].pax_type
                                if not pax_type_dict.get(pax_obj.cost_service_charge_ids[0].pax_type):
                                    pax_type_dict[pax_obj.cost_service_charge_ids[0].pax_type] = 0
                            if pax_type != '':
                                pax_type_dict[pax_type] += 1
                                total_pax += 1
                        if pax_type_dict == {} and self._name == 'tt.reservation.hotel':
                            pax_type_dict[''] = 1
                            total_pax += 1
                            passenger_list_id = [self.passenger_ids[0].id]
                        service_charge = []
                        for pax_type in pax_type_dict:
                            service_charge.append({
                                "charge_code": "disc_voucher",
                                "charge_type": "DISC",
                                "currency": "IDR",
                                "pax_type": pax_type,
                                "pax_count": pax_type_dict[pax_type],
                                "amount": rec['provider_total_discount'] / total_pax * -1,
                                "foreign_currency": "IDR",
                                "foreign_amount": rec['provider_total_discount'] / total_pax * -1,
                                "total": (pax_type_dict[pax_type] * rec['provider_total_discount'] / total_pax) * -1,
                                "sequence": idx,
                                "res_voucher_model": self._name,
                                "res_voucher_id": self.id,
                                "description": self.provider_booking_ids[idx].pnr if len(self.provider_booking_ids) > idx else '',
                                "is_voucher": True,
                                "passenger_%s_ids" % self.provider_type_id.code: [(6, 0, passenger_list_id)],
                            })
                        if service_charge:
                            self.provider_booking_ids[idx].create_service_charge(service_charge)
                    self.calculate_service_charge()

                if type == 'use':  ##CATAT DI VOUCHER DETAIL
                    discount = self.env['tt.voucher.detail'].use_voucher_new(voucher_dict, context, type)

    def delete_voucher(self):
        for svc_discount in self.env['tt.service.charge'].search([('res_voucher_model','=',self._name), ('res_voucher_id','=',self.id), ('is_voucher','=',True)]):
            svc_discount.unlink() ##unlink service charge
        for voucher_use in self.env['tt.voucher.detail.used'].search([('order_number','=',self.name)]):
            voucher_use.unlink() ##unlink voucher use
        self.voucher_code = ''
        self.calculate_service_charge()

    ##ini potong ledger
    def payment_reservation_api(self,table_name,req,context):
        _logger.info("Payment\n" + json.dumps(req))
        try:
            if req.get('book_id'):
                book_obj = self.env['tt.reservation.%s' % (table_name)].browse(req.get('book_id'))
            else:
                book_obj = self.env['tt.reservation.%s' % (table_name)].search([('name','=',req.get('order_number'))],limit=1)

            if context.get('co_job_position_is_request_required'):
                resv_req_obj = self.env['tt.reservation.request'].search([
                    ('res_model', '=', book_obj._name), ('res_id', '=', book_obj.id), ('state', '=', 'approved')])
                if not resv_req_obj:
                    raise RequestException(1038)

            voucher = None
            discount = {'error_code': -1}
            total_discount = 0
            try:
                book_obj.create_date
                agent_obj = book_obj.agent_id
            except:
                raise RequestException(1001)

            user_obj = self.env['res.users'].browse(context['co_uid'])
            try:
                user_obj.create_date
            except:
                raise RequestException(1008)

            ## 2 tab bayar pakai payment gateway, lalu tab ke 2 bayar pakai cash/transfer
            if book_obj.payment_acquirer_number_id and book_obj.payment_acquirer_number_id.state not in ['process', 'waiting'] or not book_obj.payment_acquirer_number_id:
                ## FIXME BTBO 2 SKIP CHECK OTP & PIN
                if context:
                    is_need_check_required = True
                    if context.get('co_user_login') and context.get('user_login'):
                        if context['co_user_login'] == context['user_login']:
                            is_need_check_required = False
                    if is_need_check_required:
                        # tambah sudo karena kalo offline / visa bukan gateway user yang akses
                        if user_obj.ho_id.sudo().is_agent_required_otp == 'required' and not user_obj.is_using_otp and user_obj.ho_id.sudo().is_agent_required_pin == 'required' and not user_obj.is_using_pin:
                            raise RequestException(1046)
                        elif user_obj.ho_id.sudo().is_agent_required_otp == 'required' and not user_obj.is_using_otp:
                            raise RequestException(1043)
                        elif user_obj.ho_id.sudo().is_agent_required_pin == 'required' and not user_obj.is_using_pin:
                            raise RequestException(1045)
                #### CHECK PIN HERE ####
                if user_obj.is_using_pin:
                    # if table_name not in ['visa', 'offline']:
                    ### ASUMSI KLO DI SET TIDAK MUNGKIN KOSONG
                    user_obj.check_pin_api('check', req.get('pin', ''))

            if agent_obj.id == context.get('co_agent_id',-1) or self.env.ref('tt_base.group_tt_process_channel_bookings_medical_only').id in user_obj.groups_id.ids:
                book_obj.write({
                    'is_member': req.get('member', False),
                    'payment_method': req.get('acquirer_seq_id', False),
                    'payment_date': datetime.now().strftime('%Y-%m-%d %H:%M')
                })

                #cek balance due book di sini, mungkin suatu saat yang akan datang
                if book_obj.state == 'issued':
                    _logger.error('Transaction Has been paid.')
                    raise RequestException(1009,additional_message="Please re-check your booking status first.")
                # May 13, 2020 - SAM
                # if book_obj.state not in ['booked']:
                #     # _logger.error('Cannot issue not [Booked] State.')
                #     _logger.error('Cannot issue state, %s' % book_obj.state)
                #     raise RequestException(1020)
                # END

                payment_method = req.get('payment_method', 'full')

                # agent_check_amount = book_obj.get_nta_amount(payment_method)
                agent_check_amount = book_obj.get_unpaid_nta_amount(payment_method)

                # June 2, 2020 - SAM
                if book_obj.get_nta_amount(payment_method) <= 0:
                    raise Exception("Cannot Payment 0 or lower.")
                # END
                voucher_reference = ''
                ### voucher agent here##
                if req.get('voucher'): ## WAKTU ISSUED INPUT VOUCHER
                    voucher_reference = req['voucher']['voucher_reference']
                elif book_obj.voucher_code: ## INPUT VOUCHER TAPI TIDAK LANGSUNG ISSUED
                    voucher_reference = book_obj.voucher_code
                if voucher_reference: ##USE VOUCHER
                    book_obj.add_voucher(voucher_reference, context, 'use')
                    agent_check_amount = book_obj.get_unpaid_nta_amount(payment_method)

                is_use_point = False
                website_use_point_reward = book_obj.agent_id.ho_id.sudo().get_is_use_point_reward()
                if website_use_point_reward:
                    is_use_point = req.get('use_point')

                total_use_point = 0
                if is_use_point:
                    payment_method_obj = self.env['payment.acquirer'].search([('seq_id','=',book_obj.payment_method)])
                    if payment_method_obj.type == 'cash':
                        point_reward = book_obj.agent_id.actual_point_reward
                        if point_reward > agent_check_amount:
                            total_use_point = agent_check_amount - 1
                        else:
                            total_use_point = point_reward
                    elif payment_method_obj.type == 'payment_gateway':  ## minimal bayar 10 rb dari transfer bank
                        point_reward = book_obj.agent_id.actual_point_reward
                        if point_reward - payment_method_obj.minimum_amount > agent_check_amount:
                            total_use_point = agent_check_amount - payment_method_obj.minimum_amount
                        else:
                            total_use_point = point_reward
                    if total_use_point:
                        ### check agent amount minimal saldo yg di punya oleh agent yg setelah di kurang point
                        agent_check_amount -= total_use_point
                can_use_credit_limit = False
                if agent_obj.credit_limit > 0:
                    try:
                        can_use_credit_limit = False
                        ## asumsi kalau all provider_type & provider pasti True
                        is_provider_type = True
                        is_provider = True
                        if book_obj.provider_type_id.code in ['groupbooking', 'tour']: ## if untuk product yg bisa installment, dibuat tidak bisa karena jika di pakai akan bug di payment harus rombak total
                            is_provider_type = False
                        if agent_obj.agent_credit_limit_provider_type_access_type == 'allow' and book_obj.provider_type_id not in agent_obj.agent_credit_limit_provider_type_eligibility_ids or \
                                agent_obj.agent_credit_limit_provider_type_access_type == 'restrict' and book_obj.provider_type_id in agent_obj.agent_credit_limit_provider_type_eligibility_ids:
                            is_provider_type = False
                        for provider_booking in book_obj.provider_booking_ids:
                            if agent_obj.agent_credit_limit_provider_access_type == 'allow' and provider_booking.provider_id not in agent_obj.agent_credit_limit_provider_eligibility_ids or \
                                    agent_obj.agent_credit_limit_provider_access_type == 'restrict' and provider_booking.provider_id in agent_obj.agent_credit_limit_provider_eligibility_ids:
                                is_provider = False
                                break
                        if is_provider_type and is_provider:
                            can_use_credit_limit = True
                    except Exception as e:
                        _logger.error('%s, %s' % (str(e), traceback.format_exc()))
                payment_method_to_ho_list = []
                ## hanya untuk yg check otomatis / pilih credit_limit
                if can_use_credit_limit and req.get('agent_payment_method', False) in [False, 'credit_limit', None]:
                    payment_method_to_ho_list.append('credit_limit')
                ## hanya untuk yg check otomatis / pilih balance
                if req.get('agent_payment_method', False) in [False, 'balance', None]: ## kalau dari bca agent payment method None
                    payment_method_to_ho_list.append('balance')
                payment_method_use_to_ho = ''
                balance_res = {
                    'error_code': 500
                }
                for payment_method_to_ho in payment_method_to_ho_list:
                    balance_res = self.env['tt.agent'].check_balance_limit_api(book_obj.agent_id.id,agent_check_amount, payment_method_to_ho)
                    if balance_res['error_code'] == 0:
                        payment_method_use_to_ho = payment_method_to_ho
                        book_obj.payment_method_to_ho = payment_method_to_ho
                        break
                if balance_res['error_code'] != 0:
                    if req.get('agent_payment_method', False) == 'credit_limit':
                        _logger.error('Agent Credit Limit not enough')
                        add_message = "agent credit limit %s" % (book_obj.agent_id.name)
                    else:
                        _logger.error('Agent Balance not enough')
                        add_message = "agent balance %s" % (book_obj.agent_id.name)
                    raise RequestException(1007,additional_message=add_message)

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

                for provider in book_obj.provider_booking_ids:
                    if provider.state not in ['fail_booked']:
                        ledger_created = provider.action_create_ledger(context['co_uid'], payment_method, is_use_point, payment_method_use_to_ho) ##payment method untuk bayar full / installment, payment method use to ho --> payment agent to HO (balance / credit limit)
                        # if agent_obj.is_using_pnr_quota: ##selalu potong quota setiap  attemp payment
                        if agent_obj.is_using_pnr_quota and ledger_created: #tidak potong quota jika tidak membuat ledger
                            _logger.info('create quota pnr')
                            ledger_obj = self.env['tt.ledger'].search([('res_model', '=', book_obj._name),('res_id','=',book_obj.id),('is_reversed','=',False),('agent_id.is_ho_agent','=',True)])
                            amount = 0
                            for ledger in ledger_obj:
                                amount += ledger.debit
                            carrier_code = []
                            carrier_str = ''
                            if hasattr(provider, 'journey_ids'):
                                for journey in provider.journey_ids:
                                    if hasattr(journey, 'segment_ids'):
                                        for segment in journey.segment_ids:
                                            if segment.carrier_code not in carrier_code:
                                                carrier_code.append(segment.carrier_code)
                                    else:
                                        if journey.carrier_code not in carrier_code:
                                            carrier_code.append(journey.carrier_code)
                            for carrier in carrier_code:
                                if carrier_str != '' and carrier != '':
                                    carrier += ', '
                                carrier_str += carrier
                            quota_usage_obj = self.env['tt.pnr.quota.usage'].search([('ref_name', '=', "%s" % book_obj.name), ('ref_pnrs', '=', provider.pnr)])
                            if not quota_usage_obj:
                                agent_obj.use_pnr_quota({
                                    'res_model_resv': book_obj._name,
                                    'res_id_resv': book_obj.id,
                                    'res_model_prov': provider._name,
                                    'res_id_prov': provider.id,
                                    'ref_pnrs': provider.pnr,
                                    'ref_carriers': carrier_str,
                                    'ref_provider': provider.provider_id.code,
                                    'ref_name': book_obj.name,
                                    'ref_provider_type': PROVIDER_TYPE_SELECTION[book_obj.name.split('.')[0]], #parser code al to provider type
                                    'ref_pax': hasattr(book_obj, 'passenger_ids') and len(book_obj.passenger_ids) or 0,  # total pax
                                    'ref_r_n': hasattr(book_obj, 'nights') and book_obj.nights or 0,  # room/night
                                    'inventory': 'internal',
                                    'amount': amount
                                })
                            # if not quota_used:
                            #     print("5k woi")

                ## add point reward for agent
                if website_use_point_reward and payment_method_use_to_ho != 'credit_limit':
                    ## ASUMSI point reward didapat dari total harga yg di bayar
                    ## karena kalau per pnr per pnr 55 rb & rules point reward kelipatan 10 rb agent rugi 1 point
                    self.env['tt.point.reward'].add_point_reward(book_obj, agent_check_amount, context['co_uid'])

                data = {
                    'order_number': book_obj.name,
                    'table_name': table_name,
                    'is_sync_reservation': True
                }
                self.set_sync_reservation_api(data, context)
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
            return ERR.get_error(1011,additional_message="Please refresh the page and sync status first.")

    def use_pnr_quota_api(self, req, context):
        user_obj = self.env['res.users'].browse(context['co_uid'])
        try:
            user_obj.create_date
        except:
            raise RequestException(1008)
        agent_obj = user_obj.agent_id
        try:
            quota_usage_obj = self.env['tt.pnr.quota.usage'].search([('ref_name','=', "EXT.%s" % req['order_number']),('ref_pnrs','=', req['pnr'])])
            if not quota_usage_obj:
                carrier_str = ''
                for carrier in req.get('carriers'):
                    if carrier_str != '' and carrier != '':
                        carrier += ', '
                    carrier_str += carrier
                agent_obj.use_pnr_quota({
                    'res_model_resv': '',
                    'res_id_resv': '',
                    'res_model_prov': '',
                    'res_id_prov': '',
                    'ref_pnrs': req['pnr'],
                    'ref_carriers': carrier_str,
                    'ref_provider': req['provider'],
                    'provider_type': req['provider_type'],
                    'ref_provider_type': req['provider_type'],
                    'ref_name': "EXT.%s" % req['order_number'],
                    'ref_pax': req.get('pax'), # total pax
                    'ref_r_n': req.get('r_n'), # room/night
                    'inventory': 'external'
                })
                res = ERR.get_no_error()
            else:
                res = ERR.get_error(4043) ## duplicate pnr
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = ERR.get_error(500)
        return res

    def get_email_reply_to(self):
        try:
            final_email = ''
            if self.agent_id:
                ho_agent_obj = self.agent_id.ho_id
                final_email = ho_agent_obj.email_server_id.smtp_user
        except Exception as e:
            _logger.info(str(e))
            final_email = ''
        return final_email

    def get_btc_hold_date(self, is_actual=False):
        if (self.booked_date + timedelta(hours=1)) >= self.hold_date or is_actual:
            final_time = (self.hold_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            final_time = (self.booked_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        return final_time + ' (GMT +7)'

    def get_btc_url(self):
        try:
            if self.ho_id:
                base_url = self.ho_id.redirect_url_signup
            else:
                base_url = self.agent_id.ho_id.redirect_url_signup
            final_url = base_url + '/' + str(self.provider_type_id.code) + '/booking/' + (base64.b64encode(str(self.name).encode())).decode()
        except Exception as e:
            _logger.info(str(e))
            final_url = '#'
        return final_url

    def get_btc_booked_date(self):
        return (self.booked_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') + ' (GMT +7)'

    def get_btc_issued_date(self):
        return (self.issued_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') + ' (GMT +7)'

    def compute_all_provider_total_price(self):
        provider_obj = self.env['tt.provider.%s' % self.provider_type_id.code]
        for rec in provider_obj.search([]):
            # if rec.total_price == 0 or rec.total_price == False:
            price = 0
            roc_found = False
            for sc in rec.cost_service_charge_ids:
                if sc.charge_type != 'ROC' and sc.charge_type != 'RAC':
                    price += sc.total
                if sc.charge_type == 'ROC':
                    roc_found = True
            if not roc_found:
                price = 0
                for sc in rec.cost_service_charge_ids:
                    price += sc.total
            rec.total_price = price


    def fixing_commission_agent_id_prices(self):
        try:
            for rec in self.search([]):
                _logger.info(rec.name)
                for prices in rec.sale_service_charge_ids:
                    if prices.charge_type == 'RAC':
                        if prices.charge_code in ['dif','fac','hoc']:
                            ho_obj = self.agent_id.ho_id
                            prices.commission_agent_id = ho_obj and ho_obj.id or False
                        elif prices.charge_code == 'rac':
                            prices.commission_agent_id = False
                        elif prices.charge_code != 'rac':
                            current_agent = self.agent_id
                            for loop in range(int(prices.charge_code and prices.charge_code[-1] or 0)):
                                current_agent = current_agent.parent_agent_id
                            if current_agent.id != self.agent_id.id:
                                prices.commission_agent_id = current_agent.id
        except Exception as e:
            _logger.info("FIXING PRICES CAUSE %s" % (prices.charge_code))
            _logger.error(traceback.format_exc())

    def unlink_all_printout(self, type='All'):
        # Untuk Unlink All Printout
        # Biasane Fungsi def print_, Nma fiel biasane: printout_"XXX"_id
        for rec in self:
            rec.printout_ticket_id.sudo().unlink()
            rec.printout_ticket_price_id.sudo().unlink()
            rec.printout_itinerary_id.sudo().unlink()
            rec.printout_itinerary_price_id.sudo().unlink()
            rec.printout_ho_invoice_id.sudo().unlink()
            # rec.printout_voucher_id.unlink()
            # rec.printout_vendor_invoice_id.unlink()
        return True

    def get_company_name(self):
        company_obj = self.env['res.company'].search([],limit=1)
        return company_obj.name

    def get_posted_acc_actions(self):
        return {}
