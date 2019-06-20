from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy

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
    ('ready', 'Ready'),
    ('done', 'Done')
]

JOURNEY_DIRECTION = [
    ('OW', 'One Way'),
    ('RT', 'Return')
]


class TtVisa(models.Model):
    _name = 'tt.visa'
    _inherit = ['tt.reservation', 'tt.history']

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True)

    state_visa = fields.Selection(STATE_VISA, 'State', default='draft',
                                  help='''draft = requested
                                        confirm = HO accepted
                                        validate = if all required documents submitted and documents in progress
                                        cancel = request cancelled
                                        to_vendor = Documents sent to Vendor
                                        vendor_process = Documents proceed by Vendor
                                        in_process = before payment
                                        payment = payment
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
    vendor_ids = fields.One2many('tt.visa.vendor.lines', 'visa_id', 'Expenses')

    to_passenger_ids = fields.One2many('tt.visa.order.passengers', 'visa_id', 'Visa Order Passengers')
    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'visa_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)
    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    ######################################################################################################
    # STATE
    ######################################################################################################

    @api.multi
    @api.onchange('state')
    def _compute_commercial_state(self):
        for rec in self:
            if rec.state == 'issued':
                rec.commercial_state = 'Paid'
            else:
                rec.commercial_state = 'Unpaid'

    def action_draft_visa(self):
        self.write({
            'state_visa': 'draft',
            'state': 'issued'
        })
        # saat mengubah state ke draft, akan mengubah semua state passenger ke draft
        for rec in self.to_passenger_ids:
            rec.action_draft()
        self.message_post(body='Order DRAFT')

    def action_confirm_visa(self):
        is_confirmed = True
        # cek semua state passanger.
        # jika ada state passenger yang masih diluar confirm, cancel atau validate, batalkan action confirm
        for rec in self.to_passenger_ids:
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
        # cek semua state passanger.
        # jika ada state passenger yang masih diluar cancel atau validate, batalkan action validate
        for rec in self.to_passenger_ids:
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
            'state_visa': 'in_process'
        })
        for rec in self.to_passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        self.message_post(body='Order IN PROCESS')

    # kirim data dan dokumen ke vendor
    def action_to_vendor_visa(self):
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
        for rec in self.to_passenger_ids:
            if rec.state not in ['confirm_payment']:
                is_payment = False

        if not is_payment:
            raise UserError(
                _('You have to pay all the passengers first.'))

        self.write({
            'state_visa': 'in_process',
            'in_process_date': datetime.now()
        })
        self.message_post(body='Order IN PROCESS TO CONSULATE/IMMIGRATION')
        for rec in self.to_passenger_ids:
            rec.action_in_process2()

    def action_partial_proceed_visa(self):
        self.write({
            'state_visa': 'partial_proceed'
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_delivered_visa(self):
        # if not self.vendor_ids:
        #     raise UserError(_('You have to Fill Expenses.'))
        # if self.statxisa_vendor()
        self.write({
            'state_visa': 'delivered'
        })
        self.message_post(body='Order DELIVERED')

    def action_proceed_visa(self):
        self.write({
            'state_visa': 'proceed'
        })

    def action_cancel_visa(self):
        # cek state visa.
        # jika state : in_process, partial_proceed, proceed, delivered, ready, done, create reverse ledger
        if self.state_visa not in ['in_process', 'partial_proceed', 'proceed', 'delivered', 'ready', 'done']:
            self._create_anti_ho_ledger_visa()
            self._create_anti_ledger_visa()
            self._create_anti_commission_ledger_visa()
        # set semua state passenger ke cancel
        for rec in self.to_passenger_ids:
            rec.action_cancel()
        # set state agent invoice ke cancel
        # for rec2 in self.agent_invoice_ids:
        #     rec2.action_cancel()
        # unlink semua vendor
        # for rec3 in self.vendor_ids:
        #     rec3.sudo().unlink()
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

    ######################################################################################################
    # CREATE
    ######################################################################################################

    param_contact_data = {
        "city": "Surabaya",
        "first_name": "Edy",
        "last_name": "Kend",
        "home_phone": "8123574874",
        "nationality_code": "ID--62",
        "title": "MR",
        "mobile": "8123574874",
        "province_state": "Jawa Timur",
        "contact_id": "2",
        "work_phone": "6231-5662000",
        "postal_code": 0,
        "agent_id": "4",
        "country_code": "ID",
        "address": "Jl. Raya Darmo 177B",
        "other_phone": "6231-5662000",
        "email": "paleleh@gmail.com"
    }

    param_passengers = [
        {
            "first_name": "Edy",
            "last_name": "Kend",
            "passenger_type": "ADT",
            "nationality_code": "ID",
            "title": "MR",
            "domicile": "ffsdfsdf",
            "visa_id": 869,
            "birth_date": "2000-03-04",
            "pricelist_id": 1,
            "passenger_id": "5"
        },
        {
            "first_name": "Edy",
            "last_name": "Kend",
            "passenger_type": "ADT",
            "nationality_code": "ID",
            "title": "MR",
            "domicile": "asdasd",
            "visa_id": 870,
            "birth_date": "2000-03-04",
            "pricelist_id": 1,
            "passenger_id": "5"
        }
    ]

    param_service_charge_summary = [
        {
            "charge_type": "fare",
            "description": "Visa Japan",
            "charge_code": "fare",
            "amount": 1900000.0,
            "currency": "IDR",
            "foreign_currency": "IDR",
            "pax_count": 1,
            "passenger_type": "ADT",
            "pricelist_id": 1,
            "foreign_amount": 0
        },
        {
            "charge_type": "fare",
            "description": "Visa Japan",
            "charge_code": "fare",
            "amount": 1910000.0,
            "currency": "IDR",
            "foreign_currency": "IDR",
            "pax_count": 1,
            "passenger_type": "ADT",
            "pricelist_id": 1,
            "foreign_amount": 0,
            "visa_type": "Tourist",
            "entry_type": "Single",
        }
    ]

    param_search_req = {
        "origin": "",
        "infant": 0,
        "uid": 1,
        "visa_ids": "869,870,",
        "departure_date": "2017-12-09",
        "destination": "",
        "country_id": "113",
        "direction": "OW",
        "search_type": "",
        "state": "draft",
        "transport_type": "visa",
        "adult": 1,
        "child": 0,
        "sid": "909a3a2f19050775964845ed83ce6a074b53a92c",
        "loaded": False,
        "class_of_service": "Y",
        "provider": "ALL",
        "return_date": False,
        "pax_count": "1,1,"
    }

    param_context = {
        "co_uid": 7  # co_uid akan menentukan agent yang membuat order visa
    }

    param_kwargs = {
        "force_issued": True
    }

    def create_booking_visa(self):
        contact_data = copy.deepcopy(self.param_contact_data)
        passengers = copy.deepcopy(self.param_passengers)
        service_charge_summary = copy.deepcopy(self.param_service_charge_summary)
        search_req = copy.deepcopy(self.param_search_req)
        context = copy.deepcopy(self.param_context)
        kwargs = copy.deepcopy(self.param_kwargs)

        try:
            self._validate_visa(context, 'context')
            self._validate_visa(search_req, 'header')
            context = self.update_api_context(int(contact_data.get('agent_id')), context)

            # ========= Validasi agent_id ===========
            # TODO : Security Issue VERY HIGH LEVEL
            # 1. Jika BUKAN is_company_website, maka contact.contact_id DIABAIKAN
            # 2. Jika ADA contact.contact_id MAKA agent_id = contact.contact_id.agent_id
            # 3. Jika TIDAK ADA contact.contact_id MAKA agent_id = co_uid.agent_id

            # PRODUCTION - SV
            # self._validate_booking(context)
            user_obj = self.env['res.users'].sudo().browse(int(context['co_uid']))
            contact_data.update({
                'agent_id': user_obj.agent_id.id,
                'commercial_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
            if user_obj.agent_id.agent_type_id.id == 3:  # 3 : COR
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'COR',
                    })

            if user_obj.agent_id.agent_type_id.id == 9:  # 9 : POR
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'POR',
                    })

            # if not context['agent_id']:
            #     raise Exception('ERROR Create booking, Customer or User, not have Agent (Agent ID)\n'
            #                     'Please contact Administrator, to complete the data !')

            header_val = self._visa_header_normalization(search_req)
            contact_obj = self._create_contact(contact_data, context)

            print('Agent Context : ' + str(context['agent_id']))

            psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
            ssc_ids = self._create_service_charge_sale_visa(service_charge_summary)

            to_psg_ids = self._create_visa_order(passengers)

            header_val.update({
                'contact_id': contact_obj.id,
                'passenger_ids': [(6, 0, psg_ids)],
                'sale_service_charge_ids': [(6, 0, ssc_ids)],
                'to_passenger_ids': [(6, 0, to_psg_ids)],
                'state': 'booked',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
            })

            print('Agent Header : ' + str(header_val['agent_id']))

            doc_type = header_val.get('transport_type')

            # create header & Update SUB_AGENT_ID
            book_obj = self.sudo().create(header_val)
            book_obj.sub_agent_id = contact_data['agent_id']

            book_obj.action_booked_visa(context, doc_type)
            if kwargs.get('force_issued'):
                book_obj.action_issued_visa(context, doc_type)

            self.env.cr.commit()
            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': {
                    'order_id': book_obj.id,
                    'order_number': book_obj.name,
                    'status': book_obj.state,
                    'state_visa': book_obj.state_visa,
                }
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }

    def _validate_visa(self, data, type):
        list_data = []
        if type == 'context':
            list_data = ['co_uid']
        elif type == 'header':
            list_data = ['transport_type', 'departure_date', 'adult', 'child', 'infant', 'country_id']

        # masukkan semua data context / header dalam keys_data
        keys_data = []
        for rec in data.keys():
            keys_data.append(str(rec))

        # cek apabila key pada list_data ada pada keys_data
        for ls in list_data:
            if not ls in keys_data:
                raise Exception('ERROR Validate %s, key : %s' % (type, ls))
        return True

    def update_api_context(self, sub_agent_id, context):
        context['co_uid'] = int(context['co_uid'])  # co_uid = 1
        user_obj = self.env['res.users'].sudo().browse(context['co_uid'])  # get res.users where co_uid = 1
        #if int(context['co_uid']) == 744:
        #    _logger.error('JUST Test : "Anta Utama" ' +  str(context))

        if 'is_company_website' not in context:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        elif context['is_company_website']:
            #============================================
            #====== Context dari WEBSITE/FRONTEND =======
            #============================================
            if user_obj.agent_id.agent_type_id.id == 3 or 9:
                # ===== COR/POR User ===== CORPOR LOGIN SENDIRI
                context.update({
                    'agent_id': user_obj.agent_id.parent_agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'COR/POR',
                })
            elif sub_agent_id:
                # ===== COR/POR in Contact ===== DARMO YANG LOGIN
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': sub_agent_id,
                    'booker_type': 'COR/POR',
                })
            else:
                # ===== FPO in Contact =====
                context.update({
                    'agent_id': user_obj.agent_id.id,
                    'sub_agent_id': user_obj.agent_id.id,
                    'booker_type': 'FPO',
                })
        else:
            # ===============================================
            # ====== Context dari API Client ( BTBO ) =======
            # ===============================================
            context.update({
                'agent_id': user_obj.agent_id.id,
                'sub_agent_id': user_obj.agent_id.id,
                'booker_type': 'FPO',
            })
        return context

    # memisahkan antara variabel integer dan char
    def _visa_header_normalization(self, data):
        res = {}
        str_key_att = ['transport_type', 'departure_date']
        int_key_att = ['adult', 'child', 'infant', 'country_id']

        for rec in str_key_att:
            res.update({
                rec: data[rec]
            })

        for rec in int_key_att:
            res.update({
                rec: int(data[rec])
            })

        return res

    def _create_contact(self, vals, context):
        country_obj = self.env['res.country'].sudo()
        contact_obj = self.env['tt.customer'].sudo()
        if vals.get('contact_id'):
            vals['contact_id'] = int(vals['contact_id'])
            contact_rec = contact_obj.browse(vals['contact_id'])
            if contact_rec:
                contact_rec.update({
                    'email': vals.get('email', contact_rec.email),
                    # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                })
            return contact_rec

        # country = country_obj.search([('code', '=', vals.pop('nationality_code'))])
        # vals['nationality_id'] = country and country[0].id or False

        if context['booker_type'] in ['COR', 'POR']:
            vals['passenger_on_partner_ids'] = [(4, context['sub_agent_id'])]

        country = country_obj.search([('code', '=', vals.pop('country_code'))])
        vals.update({
            'booker_mobile': vals.get('mobile', ''),
            'commercial_agent_id': context['agent_id'],
            'agent_id': context['agent_id'],
            'country_id': country and country[0].id or False,
            'passenger_type': 'ADT',
            'bill_to': '<span><b>{title} {first_name} {last_name}</b> <br>Phone: {mobile}</span>'.format(**vals),
            'mobile_orig': vals.get('mobile', ''),
            'email': vals.get('email', vals['email']),
            'mobile': vals.get('mobile', vals['mobile']),
        })
        return contact_obj.create(vals)

    def _evaluate_passenger_info(self, passengers, contact_id, agent_id):
        res = []
        country_obj = self.env['res.country'].sudo()
        psg_obj = self.env['tt.customer'].sudo()
        passenger_count = 0
        for psg in passengers:
            passenger_count += 1
            print('Passenger Count : ' + str(passenger_count))
            p_id = psg.get('passenger_id')
            if p_id:
                p_object = psg_obj.browse(int(p_id))
                if p_object:
                    res.append(int(p_id))
                    if psg.get('passport_number'):
                        p_object['passport_number'] = psg['passport_number']
                    if psg.get('passport_expdate'):
                        p_object['passport_expdate'] = psg['passport_expdate']
                    if psg.get('country_of_issued_id'):
                        p_object['country_of_issued_id'] = psg['country_of_issued_id']
                    print('Passenger Type : ' + str(psg['passenger_type']))
                    p_object.write({
                        'domicile': psg.get('domicile'),
                        # 'mobile': psg.get('mobile')
                    })
            else:
                country = country_obj.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
                if psg.get('country_of_issued_code'):
                    country = country_obj.search([('code', '=', psg.pop('country_of_issued_code'))])
                    psg['country_of_issued_id'] = country and country[0].id or False
                if not psg.get('passport_expdate'):
                    psg.pop('passport_expdate')

                psg.update({
                    'contact_id': contact_id,
                    'passenger_id': False,
                    'agent_id': agent_id
                })
                psg_res = psg_obj.create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                res.append(psg_res.id)
        return res

    def _create_service_charge_sale_visa(self, service_charge_summary):
        pricelist_env = self.env['tt.visa.pricelist'].sudo()
        res = []
        ssc_obj = self.env['tt.service.charge'].sudo()
        for rec in service_charge_summary:
            pricelist_obj = pricelist_env.browse(rec['pricelist_id'])
            sc_obj_fare = ssc_obj.create(rec)
            sc_obj_fare.update({
                'pax_type': rec['passenger_type']
            })
            res.append(sc_obj_fare.id)
            rec2 = rec.copy()
            rec2.update({
                'charge_code': 'r.ac',
                'pax_type': rec['passenger_type'],
                'amount': pricelist_obj.commission_price * -1,
            })
            sc_obj_commission = ssc_obj.create(rec2)
            res.append(sc_obj_commission.id)
        return res

    def _create_visa_order(self, passengers):
        pl_env = self.env['tt.visa.pricelist'].sudo()
        # to_env = self.env['tt.traveldoc.order'].sudo()
        to_psg_env = self.env['tt.visa.order.passengers'].sudo()
        to_req_env = self.env['tt.visa.order.requirements'].sudo()

        # to_obj = to_env.create({})
        to_psg_res = []
        for psg in passengers:
            pl_obj = pl_env.browse(psg['pricelist_id'])
            psg_vals = {
                'passenger_id': psg['passenger_id'],
                'passenger_type': psg['passenger_type'],
                'pricelist_id': psg['pricelist_id'],
            }
            to_psg_obj = to_psg_env.create(psg_vals)

            to_req_res = []
            for req in pl_obj.requirement_ids:
                req_vals = {
                    'to_passenger_id': to_psg_obj.id,
                    'requirement_id': req.id,
                }
                to_req_obj = to_req_env.create(req_vals)
                to_req_res.append(to_req_obj.id)

            to_psg_obj.write({
                'to_requirement_ids': [(6, 0, to_req_res)]
            })
            to_psg_res.append(to_psg_obj.id)
        # to_obj.write({
        #     'to_passenger_ids': [(6, 0, to_psg_res)]
        # })
        return to_psg_res

    def _get_pricelist_ids(self, service_charge_summary):
        res = []
        for rec in service_charge_summary:
            res.append(rec['pricelist_id'])
        return res

    def action_booked_visa(self, api_context=None, doc_type=''):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        vals = {}
        if self.name == 'New':
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('visa.number'),
                # .with_context(ir_sequence_date=self.date[:10])
                'state': 'partial_booked',
            })

        vals.update({
            'state': 'booked',
            'booked_uid': api_context and api_context['co_uid'],
            # 'pnr': False,
            'booked_date': datetime.now(),
            # 'hold_date': False,
            # 'expired_date': False,
        })
        self.write(vals)

    ######################################################################################################
    # LEDGER
    ######################################################################################################

    @api.one
    def action_issued_visa(self, api_context=None, doc_type=''):
        if not api_context:  # Jika dari call from backend
            api_context = {
                'co_uid': self.env.user.id
            }
        if not api_context.get('co_uid'):
            api_context.update({
                'co_uid': self.env.user.id
            })

        vals = {}

        if self.name == 'New':
            vals.update({
                'name': self.env['ir.sequence'].next_by_code('visa.number'),
                # .with_context(ir_sequence_date=self.date[:10])
                'state': 'partial_booked',
            })

        # self._validate_issue(api_context=api_context)

        vals.update({
            'state': 'issued',
            'issued_uid': api_context['co_uid'],
            'issued_date': datetime.now()
        })

        self.write(vals)

        self._create_ledger_visa()
        self._create_ho_ledger_visa()
        # self._create_commission_ledger_visa()
        # self.create_agent_invoice_traveldoc()

    def _create_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            for sc in rec.sale_service_charge_ids:
                # if rec.transport_type == 'passport':
                #     if not sc.pricelist_id.apply_type in doc_type:
                #         doc_type.append(sc.pricelist_id.apply_type)
                #     desc = sc.pricelist_id.passport_type.upper() + ' ' + sc.pricelist_id.apply_type.upper()
                # else:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            ho_profit = 0
            for pax in self.to_passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price

            vals = ledger.prepare_vals('Profit ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'commission', rec.currency_id.id, ho_profit, 0)

            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name
            print('id : ' + str(rec.id))
            vals.update({
                'res_id': rec.id,
                'agent_id': self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False)], limit=1).id,
                'pnr': rec.pnr,
                'description': desc
            })

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_ledger_visa(self):
        # pass
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            for sc in rec.sale_service_charge_ids:
                # if rec.transport_type == 'passport':
                #     if not sc.pricelist_id.apply_type in doc_type:
                #         doc_type.append(sc.pricelist_id.apply_type)
                #     desc = sc.pricelist_id.passport_type.upper() + ' ' + sc.pricelist_id.apply_type.upper()
                # else:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            print('Total : ' + str(rec.total))

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'travel.doc',
                                       rec.currency_id.id,
                                       0, rec.total)
            vals['res_id'] = rec.id
            vals['agent_id'] = rec.agent_id.id
            vals['pnr'] = rec.pnr
            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name
            vals['description'] = desc

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_commission_ledger_visa(self):
        # pass
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.sub_agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)
            print('Agent Comm : ' + str(agent_commission))
            print('Parent Comm : ' + str(parent_commission))
            print('HO Comm : ' + str(ho_commission))

            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 'commission',
                                               rec.currency_id.id, agent_commission, 0)
                vals.update({
                    'agent_id': rec.sub_agent_id.id,
                    'transport_booking_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()
                rec.commission_ledger_id = commission_aml.id
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, parent_commission, 0)
                vals.update({
                    'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    'transport_booking_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, ho_commission, 0)
                vals.update({
                    'agent_id': rec.env['res.partner'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                    'transport_booking_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.action_done()

    # ANTI / REVERSE LEDGER

    def _create_anti_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            for sc in rec.sale_service_charge_ids:
                # if rec.transport_type == 'passport':
                #     if not sc.pricelist_id.apply_type in doc_type:
                #         doc_type.append(sc.pricelist_id.apply_type)
                #     desc = sc.pricelist_id.passport_type.upper() + ' ' + sc.pricelist_id.apply_type.upper()
                # else:
                if not sc.pricelist_id.visa_type in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            ho_profit = 0
            for pax in self.to_passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price
                print('HO Profit : ' + str(ho_profit))

            vals = ledger.prepare_vals('Profit ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'commission',
                                       rec.currency_id.id, 0, ho_profit)

            vals.update({
                'res_id': rec.id,
                'agent_id': self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False)], limit=1).id,
                'pnr': rec.pnr,
                'description': 'REVERSAL ' +  desc
            })

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_anti_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []

            for sc in rec.sale_service_charge_ids:
                # if rec.transport_type == 'passport':
                #     if not sc.pricelist_id.apply_type in doc_type:
                #         doc_type.append(sc.pricelist_id.apply_type)
                #     desc = sc.pricelist_id.passport_type.upper() + ' ' + sc.pricelist_id.apply_type.upper()
                # else:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'travel.doc',
                                       rec.currency_id.id, rec.total, 0)
            vals['res_id'] = rec.id
            vals['agent_id'] = rec.agent_id.id
            vals['pnr'] = rec.pnr
            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name
            vals['description'] = 'REVERSAL ' + desc

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_anti_commission_ledger_visa(self):
        # pass
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.sub_agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)
            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 'commission',
                                               rec.currency_id.id, 0, agent_commission)
                vals.update({
                    'agent_id': rec.sub_agent_id.id,
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml.id
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, 0, parent_commission)
                vals.update({
                    'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, 0, ho_commission)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()

    ######################################################################################################
    # INVOICE
    ######################################################################################################

    def create_agent_invoice(self):
        pass

    ######################################################################################################
    # OTHERS
    ######################################################################################################

    @api.multi
    @api.depends('to_passenger_ids')
    def _compute_immigration_consulate(self):
        for rec in self:
            if rec.to_passenger_ids:
                rec.immigration_consulate = rec.to_passenger_ids[0].pricelist_id.immigration_consulate
