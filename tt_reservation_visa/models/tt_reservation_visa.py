from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy
import json
import base64
from ...tools.api import Response
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException

_logger = logging.getLogger(__name__)


STATE_VISA = [
    ('draft', 'Open'),
    ('confirm', 'Confirm to HO'),
    ('validate', 'Validated by HO'),
    ('to_vendor', 'Send to Vendor'),
    ('vendor_process', 'Proceed by Vendor'),
    ('cancel', 'Canceled'),
    ('payment', 'Payment'),
    ('in_process', 'In Process'),
    ('partial_proceed', 'Partial Proceed'),
    ('proceed', 'Proceed'),
    ('delivered', 'Delivered'),
    ('ready', 'Sent'),
    ('done', 'Done'),
    ('expired', 'Expired')
]


class TtVisa(models.Model):
    _name = 'tt.reservation.visa'
    _inherit = 'tt.reservation'
    _order = 'name desc'
    _description = 'Rodex Model'

    provider_type_id = fields.Many2one('tt.provider.type', string='Provider Type',
                                       default=lambda self: self.env.ref('tt_reservation_visa.tt_provider_type_visa'))

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True, compute="_compute_total_price")

    state_visa = fields.Selection(STATE_VISA, 'State', default='confirm',
                                  help='''draft = requested
                                        confirm = HO accepted
                                        validate = if all required documents submitted and documents in progress
                                        cancel = request cancelled
                                        to_vendor = Documents sent to Vendor
                                        vendor_process = Documents proceed by Vendor
                                        in_process = process to consulate/immigration
                                        payment = payment to embassy
                                        partial proceed = partial proceed by consulate/immigration
                                        proceed = proceed by consulate/immigration
                                        delivered = Documents sent to agent
                                        ready = Documents ready at agent
                                        done = Documents given to customer''')

    ho_profit = fields.Monetary('HO Profit')

    estimate_date = fields.Date('Estimate Date', help='Estimate Process Done since the required documents submitted',
                                readonly=True)
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)
    vendor = fields.Char('Vendor Name')
    receipt_number = fields.Char('Reference Number')
    vendor_ids = fields.One2many('tt.reservation.visa.vendor.lines', 'visa_id', 'Expenses')

    document_to_ho_date = fields.Datetime('Document to HO Date', readonly=1)

    passenger_ids = fields.One2many('tt.reservation.visa.order.passengers', 'visa_id', 'Visa Order Passengers')
    commercial_state = fields.Char('Payment Status', readonly=1)  # , compute='_compute_commercial_state'
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,
                                 domain=[('res_model', '=', 'tt.reservation.visa')])

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'visa_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    provider_booking_ids = fields.One2many('tt.provider.visa', 'booking_id', string='Provider Booking')  # readonly=True, states={'cancel2': [('readonly', False)]}

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)
    delivered_date = fields.Datetime('Delivered Date', readonly=1)

    contact_ids = fields.One2many('tt.customer', 'visa_id', 'Contacts', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

    acquirer_id = fields.Many2one('payment.acquirer', 'Payment Method', readonly=True)

    proof_of_consulate = fields.Many2many('ir.attachment', string="Proof of Consulate")

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    agent_commission = fields.Monetary('Agent Commission', default=0, compute="_compute_agent_commission")

    printout_handling_ho_id = fields.Many2one('tt.upload.center', readonly=True)
    printout_handling_customer_id = fields.Many2one('tt.upload.center', readonly=True)

    ######################################################################################################
    # STATE
    ######################################################################################################

    @api.multi
    def _compute_commercial_state(self):
        for rec in self:
            if rec.state == 'issued':
                rec.commercial_state = 'Paid'
            else:
                rec.commercial_state = 'Unpaid'

    def action_draft_visa(self):
        self.write({
            'state_visa': 'draft',
            'state': 'booked'
        })
        # saat mengubah state ke draft, akan mengubah semua state passenger ke draft
        for rec in self.passenger_ids:
            rec.action_draft()
        self.message_post(body='Order DRAFT')

    def action_confirm_visa(self):
        is_confirmed = True
        for rec in self.passenger_ids:
            if rec.state not in ['confirm', 'cancel', 'validate']:
                is_confirmed = False

        if not is_confirmed:
            raise UserError(
                _('You have to Confirmed all The passengers document first.'))

        self.write({
            'state_visa': 'confirm',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })
        self.message_post(body='Order CONFIRMED')

    def action_validate_visa(self):
        is_validated = True
        for rec in self.passenger_ids:
            if rec.state not in ['validate', 'cancel']:
                is_validated = False

        if not is_validated:
            raise UserError(
                _('You have to Validated all The passengers document first.'))

        self.write({
            'state_visa': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })
        self.message_post(body='Order VALIDATED')

    def action_in_process_visa(self):
        self.write({
            'state_visa': 'in_process',
            # 'in_process_date': datetime.now()
        })
        # cek saldo
        # balance_res = self.env['tt.agent'].check_balance_limit_api(self.agent_id.id, self.total)
        # if balance_res['error_code'] != 0:
        #     raise UserError("Balance not enough.")

        for rec in self.passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        context = {
            'co_uid': self.env.user.id
        }
        # self.action_booked_visa(context)
        self.action_issued_visa(context)
        self.message_post(body='Order IN PROCESS')

    # kirim data dan dokumen ke vendor
    def action_to_vendor_visa(self):
        for provider in self.provider_booking_ids:
            provider.use_vendor = True
        self.write({
            'use_vendor': True,
            'state_visa': 'to_vendor',
            'to_vendor_date': datetime.now()
        })
        self.message_post(body='Order SENT TO VENDOR')

    def action_vendor_process_visa(self):
        self.write({
            'state_visa': 'vendor_process',
            'vendor_process_date': datetime.now()
        })
        self.message_post(body='Order VENDOR PROCESS')

    def action_payment_visa(self):
        self.write({
            'state_visa': 'payment'
        })
        self.message_post(body='Order PAYMENT')

    def action_in_process_consulate_visa(self):
        is_payment = True
        for rec in self.passenger_ids:
            if rec.state not in ['confirm_payment']:
                is_payment = False

        if not is_payment:
            raise UserError(
                _('You have to pay all the passengers first.'))

        self.write({
            'state_visa': 'in_process',
            'in_process_date': datetime.now()
        })
        self.message_post(body='Order IN PROCESS TO CONSULATE')
        for rec in self.passenger_ids:
            rec.action_in_process2()

    def action_partial_proceed_visa(self):
        self.write({
            'state_visa': 'partial_proceed'
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_delivered_visa(self):
        """ Expenses wajib di isi untuk mencatat pengeluaran HO """
        for provider in self.provider_booking_ids:
            if not provider.vendor_ids:
                raise UserError(
                    _('You have to Fill Expenses.'))
        if self.state_visa != 'delivered':
            self.calc_visa_vendor()

        self.write({
            'state_visa': 'delivered',
            'delivered_date': datetime.now()
        })
        self.message_post(body='Order DELIVERED')

    def action_proceed_visa(self):
        self.write({
            'state_visa': 'proceed'
        })
        self.message_post(body='Order PROCEED')

    def action_cancel_visa(self):
        # cek state visa.
        # jika state : in_process, partial_proceed, proceed, delivered, ready, done, create reverse ledger
        if self.state_visa not in ['in_process', 'partial_proceed', 'proceed', 'delivered', 'ready', 'done']:
            for rec in self.ledger_ids:
                rec.reverse_ledger()
                # self._create_anti_ho_ledger_visa()
                # self._create_anti_ledger_visa()
                # self._create_anti_commission_ledger_visa()
        # set semua state passenger ke cancel
        for rec in self.passenger_ids:
            rec.action_cancel()
        # set state agent invoice ke cancel
        # for rec2 in self.agent_invoice_ids:
        #     rec2.action_cancel()
        # unlink semua vendor
        for rec3 in self.vendor_ids:
            rec3.sudo().unlink()
        self.write({
            'state_visa': 'cancel',
        })

    def action_ready_visa(self):
        self.write({
            'state_visa': 'ready',
            'ready_date': datetime.now()
        })
        self.message_post(body='Order READY')

    def action_done_visa(self):
        self.write({
            'state_visa': 'done',
            'done_date': datetime.now()
        })
        self.message_post(body='Order DONE')

    def action_expired_visa(self):
        self.write({
            'state_visa': 'expired',
            'done_date': datetime.now()
        })
        self.message_post(body='Order EXPIRED')

    def calc_visa_vendor(self):
        """ Mencatat expenses ke dalam ledger visa """

        """ Hitung total expenses (pengeluaran) """
        total_expenses = 0
        for provider in self.provider_booking_ids:
            for rec in provider.vendor_ids:
                total_expenses += rec.amount

        """ Hitung total nta per pax """
        nta_price = 0
        for pax in self.passenger_ids:
            if pax.state != 'cancel':
                nta_price += pax.pricelist_id.nta_price

        """ hitung profit HO dg mengurangi harga NTA dg total pengeluaran """
        ho_profit = nta_price - total_expenses

        """ Jika profit HO > 0 (untung) """
        if ho_profit > 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.visa_type in doc_type:
                        doc_type.append(sc.pricelist_id.visa_type)

                doc_type = ','.join(str(e) for e in doc_type)

                vals = ledger.prepare_vals(self._name, self.id, 'Profit ' + doc_type + ' : ' + rec.name, rec.name,
                                           datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, ho_profit, 0)
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml
        """ Jika profit HO < 0 (rugi) """
        if ho_profit < 0:
            ledger = self.env['tt.ledger']
            for rec in self:
                doc_type = []
                for sc in rec.sale_service_charge_ids:
                    if not sc.pricelist_id.visa_type in doc_type:
                        doc_type.append(sc.pricelist_id.visa_type)

                doc_type = ','.join(str(e) for e in doc_type)

                vals = ledger.prepare_vals(self._name, self.id, 'Additional Charge ' + doc_type + ' : ' + rec.name,
                                           rec.name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 3,
                                           rec.currency_id.id, self.env.user.id, 0, ho_profit)
                vals['agent_id'] = rec.env.ref('tt_base.rodex_ho').id

                new_aml = ledger.create(vals)
                # new_aml.action_done()
                rec.ledger_id = new_aml

    ######################################################################################################
    # CREATE
    ######################################################################################################

    param_sell_visa = {
        "total_cost": 25,
        "provider": "visa_rodextrip",
        "pax": {
            "adult": 2,
            "child": 1,
            "infant": 0,
            "elder": 0
        }
    }

    param_booker = {
        "title": "MR",
        "first_name": "ivan",
        "last_name": "suryajaya",
        "email": "asd@gmail.com",
        "calling_code": "62",
        "mobile": "81823812832",
        "nationality_name": "Indonesia",
        "nationality_code": "ID",
        "booker_id": ""
    }

    param_contact = [
        {
            "title": "MR",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "email": "asd@gmail.com",
            "calling_code": "62",
            "mobile": "81823812832",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "contact_id": "",
            "is_booker": True
        }
    ]

    param_passenger = [
        {
            "pax_type": "ADT",
            "first_name": "ivan",
            "last_name": "suryajaya",
            "title": "MR",
            "birth_date": "2002-10-01",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "identity": {
                "identity_country_of_issued_code": "ID",
                "identity_expdate": "2022-11-10",
                "identity_number": "0938675340864",
                "identity_type": "passport"
            },
            "passenger_id": "",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "master_visa_Id": "19",
            "notes": "Pax Notes",
            "required": [
                {
                    "is_original": True,
                    "is_copy": False,
                    "id": 2
                }
            ]
        },
        {
            "pax_type": "ADT",
            "first_name": "andy",
            "last_name": "sanjaya",
            "title": "MR",
            "birth_date": "2000-02-15",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            "identity": {
                "identity_country_of_issued_code": "ID",
                "identity_expdate": "2022-11-10",
                "identity_number": "0938675340864",
                "identity_type": "passport"
            },
            "passenger_id": "",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "master_visa_Id": "19",
            "notes": "Pax Notes2",
            "required": [
                {
                    "is_original": True,
                    "is_copy": False,
                    "id": 2
                }
            ]
        },
        {
            "pax_type": "CHD",
            "first_name": "ricky",
            "last_name": "sanjaya",
            "title": "MR",
            "birth_date": "2017-02-15",
            "nationality_name": "Indonesia",
            "nationality_code": "ID",
            # "identity": {
            #     "identity_country_of_issued_code": "ID",
            #     "identity_expdate": "2022-11-10",
            #     "identity_number": "0938675340864",
            #     "identity_type": "passport"
            # },
            "passenger_id": "",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "master_visa_Id": "20",
            "notes": "Pax Notes3",
            "required": [
                {
                    "is_original": True,
                    "is_copy": False,
                    "id": 2
                }
            ]
        }
    ]

    param_search = {
        "destination": "Germany",
        "consulate": "Surabaya",
        "departure_date": "2019-10-04",
        "provider": "visa_rodextrip"
    }

    param_context = {
        'co_uid': 66,
        'co_agent_id': 3
    }

    param_kwargs = {
        'force_issued': True
    }

    param_payment = {
        "member": False,
        "seq_id": "PQR.0429001"
        # "seq_id": "PQR.9999999"
    }

    def get_booking_visa_api(self, data, context):  #
        res = {}
        for rec in self.search([('name', '=', data['order_number'])]):  # self.name
            res_dict = rec.sudo().to_dict()
            print('Res Dict. : ' + str(res_dict))
            passenger = []
            type = []
            for idx, pax in enumerate(rec.passenger_ids, 1):
                requirement = []
                interview = {
                    'needs': pax.interview
                }
                biometrics = {
                    'needs': pax.biometrics
                }
                # sale_obj = self.env['tt.service.charge'].sudo().search([('visa_id', '=', self.name)])  # data['order_number'] , ('passenger_visa_ids', 'in', pax.id)]
                # print(sale_obj.read())
                sale = {}
                for ssc in pax.cost_service_charge_ids:
                    if ssc.charge_code == 'rac':
                        sale['RAC'] = {
                            'charge_code': ssc.charge_code,
                            'amount': abs(ssc.amount)
                        }
                        if ssc.currency_id:
                            sale['RAC'].update({
                                'currency': ssc.currency_id.name
                            })
                    elif ssc.charge_code == 'total':
                        sale['TOTAL'] = {
                            'charge_code': ssc.charge_code,
                            'amount': ssc.amount
                        }
                        if ssc['currency_id']:
                            sale['TOTAL'].update({
                                'currency': ssc.currency_id.name
                            })
                """ Requirements """
                for require in pax.to_requirement_ids:
                    requirement.append({
                        'name': require.requirement_id.name,
                        'is_copy': require.is_copy,
                        'is_original': require.is_ori
                    })
                """ Interview """
                interview_list = []
                if pax.interview is True:
                    for intvw in pax.interview_ids:
                        interview_list.append({
                            'datetime': str(intvw.datetime),
                            'ho_employee': intvw.ho_employee.name,
                            'meeting_point': intvw.meeting_point,
                            'location': intvw.location_id.name
                        })
                interview['interview_list'] = interview_list
                """ Biometrics """
                biometrics_list = []
                if pax.biometrics is True:
                    for bio in pax.biometrics_ids:
                        biometrics_list.append({
                            'datetime': str(bio.datetime),
                            'ho_employee': bio.ho_employee.name,
                            'meeting_point': bio.meeting_point,
                            'location': bio.location_id.name
                        })
                biometrics['biometrics_list'] = biometrics_list
                passenger.append({
                    'title': pax.title,
                    'first_name': pax.first_name,
                    'last_name': pax.last_name,
                    'birth_date': str(pax.birth_date),
                    'gender': pax.gender,
                    # 'age': pax.passenger_id.age or '',
                    'passport_number': pax.passport_number or '',
                    'passport_expdate': str(pax.passport_expdate) or '',
                    'visa': {
                        'price': sale,
                        'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(pax.pricelist_id.entry_type),
                        'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(pax.pricelist_id.visa_type),
                        'process': dict(pax.pricelist_id._fields['process_type'].selection).get(pax.pricelist_id.process_type),
                        'pax_type': pax.pricelist_id.pax_type,
                        'duration': pax.pricelist_id.duration,
                        'immigration_consulate': pax.pricelist_id.immigration_consulate,
                        'requirement': requirement,
                        'interview': interview,
                        'biometrics': biometrics
                    },
                    'sequence': idx
                })
                type.append({
                    'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(pax.pricelist_id.entry_type),
                    'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(pax.pricelist_id.visa_type),
                    'process': dict(pax.pricelist_id._fields['process_type'].selection).get(pax.pricelist_id.process_type)
                })
            res = {
                'contact': {
                    'title': res_dict['contact']['title'],
                    'name': res_dict['contact']['name'],
                    'email': res_dict['contact']['email'],
                    'phone': res_dict['contact']['phone']
                },
                'journey': {
                    'country': rec.country_id.name,
                    'departure_date': str(res_dict['departure_date']),
                    'in_process_date': str(rec['in_process_date'].strftime("%Y-%m-%d")) if rec['in_process_date'] else '',
                    'name': res_dict['order_number'],
                    'payment_status': rec.commercial_state,
                    'state': res_dict['state'],
                    'state_visa': dict(rec._fields['state_visa'].selection).get(rec.state_visa)
                },
                'passengers': passenger
            }
        if not res:
            res = Response().get_error(str('Visa Booking not found'), 500)
        print('Response : ' + str(json.dumps(res)))
        return Response().get_no_error(res)

    def create_booking_visa_api(self, data, context):  #
        sell_visa = data['sell_visa']  # self.param_sell_visa
        booker = data['booker']  # self.param_booker
        contact = data['contact']  # self.param_contact
        passengers = copy.deepcopy(data['passenger'])  # self.param_passenger
        search = data['search']  # self.param_search
        payment = data['payment']  # self.param_payment
        context = context  # self.param_context
        try:
            # cek saldo
            total_price = 0
            for psg in passengers:
                visa_pricelist_obj = self.env['tt.reservation.visa.pricelist'].search([('id', '=', psg['master_visa_Id'])])
                if visa_pricelist_obj:
                    total_price += visa_pricelist_obj.sale_price
            balance_res = self.env['tt.agent'].check_balance_limit_api(context['co_agent_id'], total_price)
            if balance_res['error_code'] != 0:
                _logger.error('Agent Balance not enough')
                raise RequestException(1007, additional_message="agent balance")

            user_obj = self.env['res.users'].sudo().browse(context['co_uid'])

            header_val = self._visa_header_normalization(search, sell_visa)

            booker_id = self.create_booker_api(booker, context)
            contact_id = self.create_contact_api(contact[0], booker_id, context)
            passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
            to_psg_ids = self._create_visa_order(passengers, passenger_ids)  # create visa order data['passenger']
            pricing = self.create_sale_service_charge_value(passengers, to_psg_ids, context)  # create pricing dict

            header_val.update({
                'country_id': self.env['res.country'].sudo().search([('name', '=', search['destination'])], limit=1).id,
                'provider_name': self.env['tt.provider'].sudo().search([('code', '=', 'visa_rodextrip')], limit=1).name,
                'booker_id': booker_id.id,
                'contact_title': contact[0]['title'],
                'contact_id': contact_id.id,
                'contact_name': contact[0]['first_name'] + ' ' + contact[0]['last_name'],
                'contact_email': contact_id.email,
                'contact_phone': contact_id.phone_ids[0].phone_number,
                'passenger_ids': [(6, 0, to_psg_ids)],
                'adult': sell_visa['pax']['adult'],
                'child': sell_visa['pax']['child'],
                'infant': sell_visa['pax']['infant'],
                'state': 'booked',
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
            })

            book_obj = self.sudo().create(header_val)

            book_obj.document_to_ho_date = datetime.now() + timedelta(days=1)
            book_obj.hold_date = datetime.now() + timedelta(days=3)

            book_obj.pnr = book_obj.name

            book_obj.write({
                'state_visa': 'confirm',
                'confirmed_date': datetime.now(),
                'confirmed_uid': context['co_uid']
            })
            book_obj.message_post(body='Order CONFIRMED')

            if payment.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', payment['seq_id'])])
            else:
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id
            if payment.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', payment['seq_id'])], limit=1)
                if not acquirer_id:
                    raise RequestException(1017)
                else:
                    book_obj.acquirer_id = acquirer_id.id

            book_obj.sudo().write({
                'customer_parent_id': customer_parent_id,
            })

            self._calc_grand_total()

            country_obj = self.env['res.country']
            provider_obj = self.env['tt.provider']

            provider = provider_obj.env['tt.provider'].search([('code', '=', sell_visa['provider'])], limit=1)
            country = country_obj.search([('name', '=', search['destination'])], limit=1)

            vals = {
                'booking_id': book_obj.id,
                'pnr': book_obj.name,
                'provider_id': provider.id,
                'country_id': country.id,
                'departure_date': search['departure_date']
            }
            provider_visa_obj = book_obj.env['tt.provider.visa'].sudo().create(vals)

            book_obj.action_booked_visa(context)

            for psg in book_obj.passenger_ids:
                vals = {
                    'provider_id': provider_visa_obj.id,
                    'passenger_id': psg.id,
                    'pax_type': psg.passenger_type,
                    'pricelist_id': psg.pricelist_id.id
                }
                self.env['tt.provider.visa.passengers'].sudo().create(vals)

            provider_visa_obj.delete_service_charge()
            provider_visa_obj.create_service_charge(pricing)
            book_obj.calculate_service_charge()
            response = {
                'id': book_obj.name
            }
            res = Response().get_no_error(response)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            res = Response().get_error(str(e), 500)
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return res

    # to generate sale service charge
    def calculate_service_charge(self):
        for service_charge in self.sale_service_charge_ids:
            service_charge.unlink()

        for provider in self.provider_booking_ids:
            sc_value = {}
            for p_sc in provider.cost_service_charge_ids:
                p_charge_code = p_sc.charge_code  # get charge code
                p_charge_type = p_sc.charge_type  # get charge type
                p_pax_type = p_sc.pax_type  # get pax type
                p_pricelist_id = p_sc.pricelist_id.id
                if not sc_value.get(p_pricelist_id):  # if sc_value[pax type] not exists
                    sc_value[p_pricelist_id] = {}
                if p_charge_type != 'RAC':  # if charge type != RAC
                    if not sc_value[p_pricelist_id].get(p_charge_type):  # if charge type not exists
                        sc_value[p_pricelist_id][p_charge_type] = {}
                        sc_value[p_pricelist_id][p_charge_type].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_type
                    c_code = p_charge_type.lower()
                elif p_charge_type == 'RAC':  # elif charge type == RAC
                    if not sc_value[p_pricelist_id].get(p_charge_code):
                        sc_value[p_pricelist_id][p_charge_code] = {}
                        sc_value[p_pricelist_id][p_charge_code].update({
                            'amount': 0,
                            'foreign_amount': 0,
                            'total': 0
                        })
                    c_type = p_charge_code
                    c_code = p_charge_code
                sc_value[p_pricelist_id][c_type].update({
                    'charge_type': p_charge_type,
                    'charge_code': c_code,
                    'pax_type': p_pax_type,
                    'pax_count': p_sc.pax_count,
                    'currency_id': p_sc.currency_id.id,
                    'foreign_currency_id': p_sc.foreign_currency_id.id,
                    'amount': sc_value[p_pricelist_id][c_type]['amount'] + p_sc.amount,
                    'total': sc_value[p_pricelist_id][c_type]['total'] + p_sc.total,
                    'foreign_amount': sc_value[p_pricelist_id][c_type]['foreign_amount'] + p_sc.foreign_amount,
                })

            values = []
            for p_pricelist, p_val in sc_value.items():
                for c_type, c_val in p_val.items():
                    curr_dict = {
                        'pricelist_id': p_pricelist,
                        'booking_visa_id': self.id,
                        'description': provider.pnr
                    }
                    curr_dict.update(c_val)
                    values.append((0, 0, curr_dict))

            self.write({
                'sale_service_charge_ids': values
            })

    def _update_api_context(self, contact, context):
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        context.update({
            'agent_id': user_obj.agent_id.id,
            # 'sub_agent_id': user_obj.agent_id.id,
            'booker_type': 'FPO',
        })
        return context

    def _visa_header_normalization(self, search, sell_visa):
        res = {}
        str_sell_visa = ['provider']
        str_search = ['departure_date']

        for rec in str_search:
            res.update({
                rec: search[rec]
            })

        for rec in str_sell_visa:
            res.update({
                rec: sell_visa[rec]
            })

        return res

    def create_sale_service_charge_value(self, passenger, passenger_ids, context):
        ssc_list = []
        ssc_list_2 = []

        pricelist_env = self.env['tt.reservation.visa.pricelist'].sudo()
        passenger_env = self.env['tt.reservation.visa.order.passengers']
        pricing_obj = self.env['tt.pricing.agent'].sudo()
        provider_type_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa')
        agent_id = self.env['tt.agent'].search([('id', '=', context['co_agent_id'])], limit=1)

        for idx, psg in enumerate(passenger):
            ssc = []
            pricelist_id = int(psg['master_visa_Id'])
            pricelist_obj = pricelist_env.browse(pricelist_id)
            passenger_obj = passenger_env.browse(passenger_ids[idx])
            vals = {
                'amount': pricelist_obj.sale_price,
                'charge_code': 'total',
                'charge_type': 'TOTAL',
                'passenger_visa_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': pricelist_obj.pax_type,
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': pricelist_obj.sale_price,
                'pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence,
                # 'passenger_visa_ids': []
            }
            # vals['passenger_visa_ids'].append(vals['passenger_visa_id'])
            ssc_list.append(vals)
            # passenger_env.search([('id', '=', 'passenger_ids[idx])].limit=1).cost_service_charge_ids.create(ssc_list))
            ssc_obj = passenger_obj.cost_service_charge_ids.create(vals)
            ssc_obj.write({
                'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
            })
            ssc.append(ssc_obj.id)
            commission_list = pricing_obj.get_commission(pricelist_obj.commission_price, agent_id, provider_type_id)
            for comm in commission_list:
                if comm['amount'] > 0:
                    vals2 = vals.copy()
                    vals2.update({
                        'commission_agent_id': comm['commission_agent_id'],
                        'total': comm['amount'] * -1,
                        'amount': comm['amount'] * -1,
                        'charge_code': comm['code'],
                        'charge_type': 'RAC',
                    })
                    ssc_list.append(vals2)
                    ssc_obj2 = passenger_obj.cost_service_charge_ids.create(vals2)
                    ssc_obj2.write({
                        'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
                    })
                    ssc.append(ssc_obj2.id)
            passenger_obj.write({
                'cost_service_charge_ids': [(6, 0, ssc)]
            })
            vals_fixed = {
                'commission_agent_id': self.env.ref('tt_base.rodex_ho').id,
                'amount': pricelist_obj.cost_price - pricelist_obj.nta_price,
                'charge_code': 'fixed',
                'charge_type': 'RAC',
                'passenger_visa_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': pricelist_obj.pax_type,
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': pricelist_obj.sale_price,
                'pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence,
                # 'passenger_visa_ids': []
            }
            ssc_list.append(vals_fixed)
            ssc_obj3 = passenger_obj.cost_service_charge_ids.create(vals)
            ssc_obj3.write({
                'passenger_visa_ids': [(6, 0, passenger_obj.ids)]
            })
            ssc.append(ssc_obj3.id)

        # susun daftar ssc yang sudah dibuat
        for ssc in ssc_list:
            # compare with ssc_list
            ssc_same = False
            for ssc_2 in ssc_list_2:
                if ssc['pricelist_id'] == ssc_2['pricelist_id']:
                    if ssc['charge_code'] == ssc_2['charge_code']:
                        if ssc['pax_type'] == ssc_2['pax_type']:
                            ssc_same = True
                            # update ssc_final
                            ssc_2['pax_count'] = ssc_2['pax_count'] + 1,
                            ssc_2['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                            ssc_2['total'] += ssc.get('amount')
                            ssc_2['pax_count'] = ssc_2['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'passenger_visa_ids': [],
                    'description': ssc['description'],
                    'pax_type': ssc['pax_type'],
                    'currency_id': ssc['currency_id'],
                    'pax_count': 1,
                    'total': ssc['total'],
                    'pricelist_id': ssc['pricelist_id']
                }
                if 'commission_agent_id' in ssc:
                    vals.update({
                        'commission_agent_id': ssc['commission_agent_id']
                    })
                vals['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                ssc_list_2.append(vals)
        print('SSC 2 : ' + str(ssc_list_2))

        return ssc_list_2

    def _create_sale_service_charge(self, ssc_vals):
        service_chg_obj = self.env['tt.service.charge']
        ssc_ids = []
        for ssc in ssc_vals:
            ssc['passenger_visa_ids'] = [(6, 0, ssc['passenger_visa_ids'])]
            ssc_obj = service_chg_obj.create(ssc)
            print(ssc_obj.read())
            ssc_ids.append(ssc_obj.id)
        return ssc_ids

    def _create_visa_order(self, passengers, passenger_ids):
        pricelist_env = self.env['tt.reservation.visa.pricelist'].sudo()
        to_psg_env = self.env['tt.reservation.visa.order.passengers'].sudo()
        to_req_env = self.env['tt.reservation.visa.order.requirements'].sudo()
        to_psg_list = []

        for idx, psg in enumerate(passengers):
            pricelist_id = int(psg['master_visa_Id'])
            pricelist_obj = pricelist_env.browse(pricelist_id)
            psg_vals = passenger_ids[idx][0].copy_to_passenger()
            psg_vals.update({
                'name': psg_vals['first_name'] + ' ' + psg_vals['last_name'],
                'customer_id': passenger_ids[idx][0].id,
                'title': psg['title'],
                'pricelist_id': pricelist_id,
                'passenger_type': psg['pax_type'],
                'notes': psg.get('notes'),
                # Pada state request, pax akan diberi expired date dg durasi tergantung dari paket visa yang diambil
                'expired_date': fields.Date.today() + timedelta(days=pricelist_obj.duration),
                'sequence': int(idx+1)
            })
            if 'identity' in psg:
                psg_vals.update({
                    'passport_number': psg['identity'].get('identity_number'),
                    'passport_expdate': psg['identity'].get('identity_expdate')
                })
            to_psg_obj = to_psg_env.create(psg_vals)
            to_psg_obj.action_sync_handling()

            to_req_list = []

            if len(psg['required']) > 0:
                for req in psg['required']:  # pricelist_obj.requirement_ids
                    req_vals = {
                        'to_passenger_id': to_psg_obj.id,
                        'requirement_id': req['id'],
                        'is_ori': req['is_original'],
                        'is_copy': req['is_copy'],
                        'check_uid': self.env.user.id,
                        'check_date': datetime.now()
                    }
                    to_req_obj = to_req_env.create(req_vals)
                    to_req_list.append(to_req_obj.id)  # akan dipindah ke edit requirements

            to_psg_obj.write({
                'to_requirement_ids': [(6, 0, to_req_list)]
            })

            to_psg_list.append(to_psg_obj.id)
        return to_psg_list

    def action_booked_visa(self, api_context=None):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        vals = {}
        if self.name == 'New':
            vals.update({
                'state': 'partial_booked',
            })

        vals.update({
            'state': 'booked',
            'booked_uid': api_context and api_context['co_uid'],
            'booked_date': datetime.now(),
        })

        self._compute_commercial_state()
        for pvdr in self.provider_booking_ids:
            pvdr.action_booked_api_visa(pvdr.to_dict(), api_context, self.hold_date)
        self.write(vals)

    ######################################################################################################
    # LEDGER
    ######################################################################################################

    @api.one
    def action_issued_visa(self, api_context=None):
        for rec in self:
            if not api_context:  # Jika dari call from backend
                api_context = {
                    'co_uid': rec.env.user.id,

                }
            if not api_context.get('co_uid'):
                api_context.update({
                    'co_uid': rec.env.user.id,
                })

            api_context.update({
                'co_agent_id': rec.agent_id.id
            })

            req = {
                'book_id': rec.id,
                'order_number': rec.name,
                'acquirer_seq_id': rec.acquirer_id.seq_id,
                'member': False
            }
            if self.customer_parent_id.customer_parent_type_id.id != self.env.ref('tt_base.customer_type_fpo').id:
                req.update({
                    'member': True
                })

            self._compute_commercial_state()

            payment = self.payment_reservation_api('visa', req, api_context)
            if payment['error_code'] != 0:
                _logger.error(payment['error_msg'])
                raise UserError(_(payment['error_msg']))

            vals = {}

            vals.update({
                'state': 'issued',
                'issued_uid': api_context['co_uid'],
                'issued_date': datetime.now(),
                # 'confirmed_uid': api_context['co_uid'],
                # 'confirmed_date': datetime.now(),
            })

            self.write(vals)
            # for pvdr in rec.provider_booking_ids:
            #     pvdr.action_issued_api_visa(api_context)
            #     pvdr.action_create_ledger()
            # self._create_ho_ledger_visa()  # sementara diaktifkan

    def _create_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)

            doc_type = ','.join(str(e) for e in doc_type)

            ho_profit = 0
            for pax in self.passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price

            vals = ledger.prepare_vals(self._name, self.id, 'Commission HO : ' + rec.name, rec.name, rec.issued_date,
                                       3, rec.currency_id.id, self.env.user.id, ho_profit, 0)
            vals = ledger.prepare_vals_for_resv(self, rec.name, vals)
            vals.update({
                'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id
            })

            new_aml = ledger.create(vals)

    # ANTI / REVERSE LEDGER

    def _create_anti_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''
            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                if sc.pricelist_id.display_name:
                    desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            ho_profit = 0
            for pax in self.passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price

            vals = ledger.prepare_vals('Profit ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       3, rec.currency_id.id, 0, ho_profit)
            vals = ledger.prepare_vals_for_resv(self, vals)
            vals.update({
                'agent_id': self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False)], limit=1).id,
                'description': 'REVERSAL ' + desc,
                'is_reversed': True
            })

            new_aml = ledger.create(vals)
            new_aml.update({
                'reverse_id': new_aml.id,
            })
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_anti_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''

            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                if sc.pricelist_id.display_name:
                    desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            vals = ledger.prepare_vals(self._name, self.id, 'Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       2, rec.currency_id.id, rec.total, 0)
            vals = ledger.prepare_vals_for_resv(self, vals)
            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name
            vals.update({
                'description': 'REVERSAL ' + desc,
                'is_reversed': True
            })

            new_aml = ledger.create(vals)
            new_aml.update({
                'reverse_id': new_aml.id,
            })
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_anti_commission_ledger_visa(self):
        # pass
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)
            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 3,
                                               rec.currency_id.id, 0, agent_commission)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'description': 'REVERSAL - Agent Commission',
                    'is_reversed': True
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.update({
                    'reverse_id': commission_aml.id,
                })
                # commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml.id
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, 0, parent_commission)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                    'description': 'REVERSAL - Parent Agent Commission',
                    'is_reversed': True
                })
                commission_aml_parent = ledger_obj.create(vals)
                commission_aml_parent.update({
                    'reverse_id': commission_aml_parent.id,
                })
                # commission_aml.action_done()

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, 0, ho_commission)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                    'description': 'REVERSAL - HO Commission',
                    'is_reversed': True
                })
                commission_aml_ho = ledger_obj.create(vals)
                commission_aml_ho.update({
                    'reverse_id': commission_aml_ho.id,
                })

                # commission_aml.action_done()

    ######################################################################################################
    # PRINTOUT
    ######################################################################################################

    def do_print_out_visa_ho(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        visa_handling_ho_id = self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_ho')
        if not self.printout_handling_ho_id:
            pdf_report = visa_handling_ho_id.report_action(self, data=data)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report.update({
                'ids': self.ids,
                'model': self._name,
            })
            pdf_report_bytes = visa_handling_ho_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Visa HO %s.pdf' % self.name,
                    'file_reference': 'Visa HO Handling',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': self.env.user.agent_id.id,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_handling_ho_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_handling_ho_id.url,
        }
        return url
        # return self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_ho').report_action(self, data=data)

    def do_print_out_visa_cust(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        visa_handling_customer_id = self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_cust')
        if not self.printout_handling_customer_id:
            pdf_report = visa_handling_customer_id.report_action(self, data=data)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report.update({
                'ids': self.ids,
                'model': self._name,
            })
            pdf_report_bytes = visa_handling_customer_id.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Visa Customer %s.pdf' % self.name,
                    'file_reference': 'Visa Customer Handling',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': self.env.user.agent_id.id,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_handling_ho_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "ZZZ",
            'target': 'new',
            'url': self.printout_handling_ho_id.url,
        }
        return url
        # return self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_cust').report_action(self, data=data)

    def action_proforma_invoice_visa(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_reservation_visa.action_report_printout_proforma_invoice_visa').report_action(self, data=data)

    ######################################################################################################
    # CRON
    ######################################################################################################

    def cron_check_visa_pax_expired_date(self):
        visa_draft = self.search([('state_visa', '=', 'draft')])
        for rec in visa_draft:
            expired = False
            for psg in rec.passenger_ids:
                if psg.expired_date <= fields.Date.today():
                    expired = True
            if expired:
                rec.action_cancel_visa()

    ######################################################################################################
    # OTHERS
    ######################################################################################################

    param_channel_service_charge = {
        # "order_number": "VS.19080500053",
        "passengers": [{
            "sequence": 1,
            "pricing": [{
                "amount": 30000,
                "currency_code": "IDR"
            },
            {
                "amount": 10000,
                "currency_code": "IDR"
            },
            {
                "amount": -50000,
                "currency_code": "IDR"
            }]
        }]
    }

    def calc_channel_service_charge_visa(self):
        req = self.param_channel_service_charge
        req.update({
            "order_number": self.name,
            'provider_type': 'visa'
        })
        self.channel_pricing_api(req, self.param_context)
        csc_list = []
        for psg in self.passenger_ids:
            for channel in psg.channel_service_charge_ids:
                channel.write({
                    'total': channel.amount * channel.pax_count,
                    'pax_type': psg.passenger_type,
                    'description': 'Repricing'
                })
                self.write({  # hasil sementara : isi di prices di replace semuanya
                    'sale_service_charge_ids': [(4, channel.id)]
                })

    def update_service_charges(self):
        pricing_list = []
        for psg in self.passenger_ids:
            if psg.pricelist_id and (psg.booking_state == 'draft' or psg.booking_state == 'confirm' or psg.booking_state == 'validate'):
                for scs in psg.cost_service_charge_ids:
                    if scs.charge_type == 'TOTAL':
                        if scs.amount != psg.pricelist_id.sale_price:
                            scs.amount = psg.pricelist_id.sale_price
                    elif scs.charge_type == 'RAC':
                        if scs.amount != psg.pricelist_id.commission_price:
                            scs.amount = psg.pricelist_id.commission_price
            for scs in psg.cost_service_charge_ids:
                pricing_list.append({
                    'amount': scs.amount if scs.amount else 0,
                    'total': scs.total if scs.total else 0,
                    'charge_code': scs.charge_code,
                    'charge_type': scs.charge_type,
                    'pax_type': scs.pax_type,
                    'currency_id': scs.currency_id,
                    'sequence': scs.sequence,
                    'description': scs.description
                })

    def action_booked_api_visa(self, context, pnr_list, hold_date):
        self.write({
            'state': 'booked',
            'pnr': ', '.join(pnr_list),
            'hold_date': hold_date,
            'booked_uid': context['co_uid'],
            'booked_date': datetime.now()
        })

    def check_provider_state(self, context, pnr_list=[], hold_date=False, req={}):
        if all(rec.state == 'booked' for rec in self.provider_booking_ids):
            # booked
            self.calculate_service_charge()
            self.action_booked_api_visa(context, pnr_list, hold_date)
        elif all(rec.state == 'issued' for rec in self.provider_booking_ids):
            # issued
            ##get payment acquirer
            if req.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', req['seq_id'])])
                if not acquirer_id:
                    raise RequestException(1017)
            else:
                # raise RequestException(1017)
                acquirer_id = self.agent_id.default_acquirer_id

            if req.get('member'):
                customer_parent_id = acquirer_id.agent_id.id
            else:
                customer_parent_id = self.agent_id.customer_parent_walkin_id.id
        else:
            # entah status apa
            _logger.error('Entah status apa')
            raise RequestException(1006)

    @api.onchange('state')
    @api.depends('state')
    def _compute_expired_visa(self):
        for rec in self:
            if rec.state == 'expired':
                rec.state_visa = 'expired'

    def _compute_agent_commission(self):
        for rec in self:
            agent_comm = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_code == 'rac':
                    agent_comm += sale.total
            rec.agent_commission = abs(agent_comm)

    @api.multi
    @api.depends('passenger_ids')
    @api.onchange('passenger_ids')
    def _compute_immigration_consulate(self):
        for rec in self:
            if rec.passenger_ids:
                rec.immigration_consulate = rec.passenger_ids[0].pricelist_id.immigration_consulate

    def _compute_total_price(self):
        for rec in self:
            total = 0
            for sale in rec.sale_service_charge_ids:
                if sale.charge_type == 'TOTAL':
                    total += sale.total
            rec.total_fare = total

    def _calc_grand_total(self):
        for rec in self:
            rec.total = 0
            rec.total_tax = 0
            rec.total_disc = 0
            rec.total_commission = 0
            rec.total_fare = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_type == 'TOTAL':
                    rec.total_fare += line.total
                if line.charge_type == 'tax':
                    rec.total_tax += line.total
                if line.charge_type == 'disc':
                    rec.total_disc += line.total
                if line.charge_type == 'ROC':
                    rec.total_commission += line.total
                if line.charge_type == 'RAC':
                    rec.total_commission += line.total

            print('Total Fare : ' + str(rec.total_fare))
            rec.total = rec.total_fare + rec.total_tax + rec.total_discount
            rec.total_nta = rec.total - rec.total_commission

    def randomizer_rec(self):
        import random
        list_agent_id = self.env['tt.agent'].sudo().search([]).ids
        country_id = self.env['res.country'].sudo().search([]).ids
        for rec in self.sudo().search([], limit=1000):
            new_rec = rec.sudo().copy()
            new_rec.update({
                'agent_id': list_agent_id[random.randrange(0, len(list_agent_id) - 1, 1)],
                'adult': random.randrange(0, 5, 1),
                'child': random.randrange(0, 5, 1),
                'infant': random.randrange(0, 5, 1),
                'country_id': country_id[random.randrange(0, len(country_id) - 1, 1)],
            })
        return True
