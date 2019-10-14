from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy
import json
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
    ('done', 'Done')
]


class TtVisa(models.Model):
    _name = 'tt.reservation.visa'
    _inherit = 'tt.reservation'
    _order = 'name desc'
    _description = 'Rodex Model'

    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type',
                                       default=lambda self: self.env['tt.provider.type'].search([('code', '=', 'visa')],
                                                                                                limit=1))

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

    provider_booking_ids = fields.One2many('tt.provider.visa', 'booking_id', string='Provider Booking',
                                           readonly=True, states={'cancel2': [('readonly', False)]})

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    contact_ids = fields.One2many('tt.customer', 'visa_id', 'Contacts', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    acquirer_id = fields.Char('Payment Method', readonly=True)

    proof_of_consulate = fields.Many2many('ir.attachment', string="Proof of Consulate")

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

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
            'state': 'issued'
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
            'in_process_date': datetime.now()
        })
        for rec in self.passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        context = {
            'co_uid': self.env.user.id
        }
        self.action_booked_visa(context)
        self.action_issued_visa(context)
        self.message_post(body='Order IN PROCESS')

    def action_pay_now_visa(self):
        pass

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
        self.write({
            'state_visa': 'delivered'
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
            if self.sale_service_charge_ids:
                self._create_anti_ho_ledger_visa()
                self._create_anti_ledger_visa()
                self._create_anti_commission_ledger_visa()
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

    ######################################################################################################
    # CREATE
    ######################################################################################################

    param_sell_visa = {
        "total_cost": 25,
        "provider": "skytors_visa",
        "pax": {
            "adult": 1,
            "child": 0,
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
            "country_of_issued_code": "",
            "passport_expdate": "",
            "passport_number": "",
            "passenger_id": "",
            "is_booker": False,
            "is_contact": False,
            "number": 1,
            "master_visa_Id": "1",
            "required": [
                {
                    "is_original": False,
                    "is_copy": False,
                    "id": 1
                }
            ]
        }
    ]

    param_search = {
        "destination": "Albania",
        "consulate": "Jakarta",
        "departure_date": "2019-10-04",
        "provider": "skytors_visa"
    }

    param_context = {
        'co_uid': 2,
        'co_agent_id': 3
    }

    param_kwargs = {
        'force_issued': True
    }

    param_payment = {
        "member": False,
        "seq_id": "PQR.0429001"
    }

    def get_booking_visa_api(self, data):  #
        res = {}
        for rec in self.search([('name', '=', data['order_number'])]):  # self.name
            res_dict = rec.sudo().to_dict()
            print('Res Dict. : ' + str(res_dict))
            passenger = []
            # contact = []
            # sale = {}
            type = []
            for idx, pax in enumerate(rec.passenger_ids, 1):
                requirement = []
                # sale[pax.passenger_id.first_name + ' ' + pax.passenger_id.last_name] = []
                # for sale_price in passenger[len(passenger) - 1]['visa']['price']:
                #     if sale_price != 'currency':
                #         sale[pax.passenger_id.first_name + ' ' + pax.passenger_id.last_name].append({
                #             'charge_code': sale_price,
                #             'amount': passenger[len(passenger) - 1]['visa']['price'][sale_price],
                #             'currency': passenger[len(passenger) - 1]['visa']['price']['currency']
                #         })
                sale_obj = self.env['tt.service.charge'].sudo().search([('visa_id', '=', data['order_number']), ('passenger_visa_ids', '=', pax.id)])  # self.name
                sale = {}
                for ssc in sale_obj:
                    if ssc['charge_code'] == 'rac':
                        sale['RAC'] = {
                            'charge_code': 'rac',
                            'amount': ssc['amount'],
                            'currency': ssc['currency_id'].name
                        }
                    else:
                        sale[ssc['charge_code'].upper()] = {
                            'charge_code': ssc['charge_code'],
                            'amount': ssc['amount'],
                            'currency': ssc['currency_id'].name
                        }
                for require in pax.to_requirement_ids:
                    requirement.append({
                        'name': require.requirement_id.name,
                        # 'is_ori': require.is_ori,
                        # 'is_copy': require.is_copy,
                        # 'validate_HO': require.validate_HO,
                        # 'required': require.required,
                    })
                passenger.append({
                    # 'title': pax.passenger_id.title,
                    'title': pax.title,
                    'first_name': pax.first_name,
                    'last_name': pax.last_name,
                    'birth_date': str(pax.birth_date),
                    'gender': pax.gender,
                    # 'age': pax.passenger_id.age or '',
                    'passport_number': pax.passport_number or '',
                    'passport_expdate': pax.passport_expdate or '',
                    'visa': {
                        # 'sale_price': pax.pricelist_id.sale_price,
                        # 'commission': pax.pricelist_id.commission_price,
                        # 'currency': pax.pricelist_id.currency_id.name
                        'price': sale,
                        'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(pax.pricelist_id.entry_type),
                        'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(pax.pricelist_id.visa_type),
                        'process': dict(pax.pricelist_id._fields['process_type'].selection).get(pax.pricelist_id.process_type),
                        'pax_type': pax.pricelist_id.pax_type,
                        'duration': pax.pricelist_id.duration,
                        'immigration_consulate': pax.pricelist_id.immigration_consulate,
                        'requirement': requirement
                    },
                    'sequence': idx
                })
                type.append({
                    'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(pax.pricelist_id.entry_type),
                    'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(pax.pricelist_id.visa_type),
                    'process': dict(pax.pricelist_id._fields['process_type'].selection).get(pax.pricelist_id.process_type)
                })
            # for pax in rec.contact_ids:
            #     contact.append({
            #         'title': pax.title,
            #         'name': pax.name,
            #         'phone_number': pax.phone_ids[0].phone_number if len(pax.phone_ids) > 0 else '',
            #     })
            res = {
                'contact': {
                    'name': res_dict['contact']['name'],
                    'email': res_dict['contact']['email'],
                    'phone': res_dict['contact']['phone']
                },
                # {
                #     'first_name': rec.contact_id.first_name,
                #     'last_name': rec.contact_id.last_name,
                #     'email': rec.contact_id.email,
                #     'phone_number': rec.contact_id.phone_ids[0].phone_number if len(
                #         rec.contact_id.phone_ids) > 0 else '',
                # }
                # 'booker': rec.booker_id.to_dict(),
                # {
                #     # 'title': rec.booker_id.title,
                #     'first_name': rec.booker_id.first_name,
                #     'last_name': rec.booker_id.last_name,
                #     'email': rec.booker_id.email,
                #     'phone_number': rec.booker_id.phone_ids[0].phone_number if len(rec.booker_id.phone_ids) > 0 else '',
                # }
                'journey': {
                    'country': rec.country_id.name,
                    'departure_date': str(res_dict['departure_date']),
                    'name': res_dict['order_number'],
                    'payment_status': rec.commercial_state,
                    'state': res_dict['state'],
                    'state_visa': rec.state_visa
                },
                'passengers': passenger,
                # 'contact': contact,
                # 'sale_price': sale
            }
        if not res:
            res = Response().get_error(str('Visa Booking not found'), 500)
        print('Response : ' + str(json.dumps(res)))
        return Response().get_no_error(res)

    def create_booking_visa_api(self, data, context, kwargs):  #
        sell_visa = data['sell_visa'] # self.param_sell_visa
        booker = data['booker']  # self.param_booker
        contact = data['contact']  # self.param_contact
        passengers = data['passenger']  # self.param_passenger
        search = data['search']  # self.param_search
        payment = data['payment']  # self.param_payment
        context = context  # self.param_context
        kwargs = kwargs  # self.param_kwargs

        try:
            user_obj = self.env['res.users'].sudo().browse(context['co_uid'])

            header_val = self._visa_header_normalization(search, sell_visa)
            booker_id = self.create_booker_api(booker, context)
            # contact_ids = self._create_contact(context, contact)  # create contact
            contact_id = self.create_contact_api(contact[0], booker_id, context)
            # passenger_ids = self._create_passenger(context, passengers)  # create passenger
            passenger_ids = self.create_customer_api(passengers, context, booker_id, contact_id)  # create passenger
            to_psg_ids = self._create_visa_order(passengers, passenger_ids)  # create visa order
            ssc_vals = self.create_sale_service_charge_value(passengers, to_psg_ids)
            ssc_ids = self._create_sale_service_charge(ssc_vals)  # create pricing

            header_val.update({
                'country_id': self.env['res.country'].sudo().search([('name', '=', search['destination'])], limit=1).id,
                'booker_id': booker_id.id,
                # 'contact_ids': [(6, 0, contact_ids)],
                'contact_id': contact_id.id,
                'contact_name': contact_id.name,
                'contact_email': contact_id.email,
                'contact_phone': contact_id.phone_ids[0].phone_number,
                'passenger_ids': [(6, 0, passenger_ids)],
                'sale_service_charge_ids': [(6, 0, ssc_ids)],
                'passenger_ids': [(6, 0, to_psg_ids)],
                'adult': sell_visa['pax']['adult'],
                'child': sell_visa['pax']['child'],
                'infant': sell_visa['pax']['infant'],
                'state': 'booked',
                'agent_id': context['co_agent_id'],
                'user_id': context['co_uid'],
            })

            book_obj = self.sudo().create(header_val)

            if payment.get('member'):
                customer_parent_id = self.env['tt.customer.parent'].search([('seq_id', '=', payment['seq_id'])])
            else:
                customer_parent_id = book_obj.agent_id.customer_parent_walkin_id.id
            if payment.get('seq_id'):
                acquirer_id = self.env['payment.acquirer'].search([('seq_id', '=', payment['seq_id'])], limit=1).id
                if not acquirer_id:
                    raise RequestException(1017)

            book_obj.sudo().write({
                'customer_parent_id': customer_parent_id,
            })

            self._calc_grand_total()

            # book_obj.action_booked_visa(context)
            # book_obj.action_issued_visa(context)
            response = {
                'id': book_obj.name
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
        return res

    def _update_api_context(self, contact, context):
        # sementara comment dulu. tunggu sampai ada agent_id di contact
        # for con in contact:
        #     sub_agent_id = int(con['agent_id'])
        #     context['co_uid'] = int(context['co_uid'])
        #     user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
        #
        #     # jika tidak ada is_company_website di context
        #     if 'is_company_website' not in context:
        #         context.update({
        #             'agent_id': user_obj.agent_id.id,
        #             'sub_agent_id': user_obj.agent_id.id,
        #             'booker_type': 'FPO',
        #         })
        #     # jika is_company_website ada isinya
        #     elif context['is_company_website']:
        #         if user_obj.agent_id.agent_type_id.id == 3 or 9:  # 3 : COP | 9 : POR
        #             # ===== COR/POR User ===== CORPOR LOGIN SENDIRI
        #             context.update({
        #                 'agent_id': user_obj.agent_id.parent_agent_id.id,
        #                 'sub_agent_id': user_obj.agent_id.id,
        #                 'booker_type': 'COR/POR',
        #             })
        #         elif sub_agent_id:
        #             # ===== COR/POR in Contact ===== DARMO YANG LOGIN
        #             context.update({
        #                 'agent_id': user_obj.agent_id.id,
        #                 'sub_agent_id': sub_agent_id,
        #                 'booker_type': 'COR/POR',
        #             })
        #         else:
        #             # ===== FPO in Contact =====
        #             context.update({
        #                 'agent_id': user_obj.agent_id.id,
        #                 'sub_agent_id': user_obj.agent_id.id,
        #                 'booker_type': 'FPO',
        #             })
        #     # jika is_company_website tidak ada isinya / kosong
        #     else:
        #         context.update({
        #             'agent_id': user_obj.agent_id.id,
        #             'sub_agent_id': user_obj.agent_id.id,
        #             'booker_type': 'FPO',
        #         })
        #     return context
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

    def _create_booker(self, context, booker):
        country_env = self.env['res.country'].sudo()
        booker_env = self.env['tt.customer'].sudo()
        if booker.get('booker_id'):
            booker['booker_id'] = int(booker['booker_id'])
            booker_rec = booker_env.browse(booker['booker_id'])
            if booker_rec:
                booker_rec.update({
                    'email': booker.get('email', booker_rec.email),
                    # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                })
            return booker_rec.id
        else:
            country = country_env.search([('code', '=', booker.pop('nationality_code'))])
            booker.update({
                'commercial_agent_id': context['co_agent_id'],
                'agent_id': context['co_agent_id'],
                'nationality_id': country and country[0].id or False,
                'email': booker.get('email', booker['email']),
                'mobile': booker.get('mobile', booker['mobile']),
            })
            booker_obj = booker_env.create(booker)
            booker_obj.update({
                'phone_ids': booker_obj.phone_ids.create({
                    'phone_number': booker.get('mobile', booker['mobile']),
                    'type': 'work'
                }),
            })
            return booker_obj.id

    def _create_contact(self, context, contact):  # odoo10 : hanya 1 contact | odoo12 : bisa lebih dari 1 contact
        contact_env = self.env['tt.customer'].sudo()
        country_env = self.env['res.country'].sudo()
        contact_list = []
        contact_count = 0
        for con in contact:
            contact_count += 1
            # cek jika sudah ada contact
            if con['contact_id']:
                con['contact_id'] = int(con['contact_id'])
                contact_rec = contact_env.browse(con['contact_id'])
                if contact_rec:
                    contact_rec.update({
                        'email': con.get('email', contact_rec.email),
                        # 'mobile': vals.get('mobile', contact_rec.phone_ids[0]),
                    })
                # return contact_rec
                contact_list.append(con['contact_id'])
            # jika tidak ada, buat customer baru
            else:
                country = country_env.search([('code', '=', con.pop('nationality_code'))])  # diubah ke country_code
                con.update({
                    'commercial_agent_id': context['co_agent_id'],
                    'agent_id': context['co_agent_id'],
                    'nationality_id': country and country[0].id or False,
                    # 'passenger_type': 'ADT',
                    'email': con.get('email', con['email'])
                })
                contact_obj = contact_env.create(con)
                contact_obj.update({
                    'phone_ids': contact_obj.phone_ids.create({
                        'phone_number': con.get('mobile', con['mobile']),
                        'type': 'work'
                    }),
                })
                contact_list.append(contact_obj.id)
        return contact_list

    def _create_passenger(self, context, passengers):
        passenger_list = []
        country_env = self.env['res.country'].sudo()
        passenger_env = self.env['tt.customer'].sudo()
        passenger_count = 0
        for psg in passengers:
            passenger_count += 1
            p_id = psg.get('passenger_id')
            if p_id:
                p_object = passenger_env.browse(int(p_id))
                if p_object:
                    passenger_list.append(p_id)
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
                # buat nationality_id dan country_of_issued_id
                country = country_env.search([('code', '=', psg.pop('nationality_code'))])
                psg['nationality_id'] = country and country[0].id or False
                if psg['country_of_issued_code']:
                    country = country_env.search([('code', '=', psg.pop('country_of_issued_code'))])
                    psg['country_of_issued_id'] = country and country[0].id or False
                if not psg.get('passport_expdate'):
                    psg.pop('passport_expdate')

                psg.update({
                    'passenger_id': False,
                    'agent_id': context['co_agent_id']
                })
                psg_res = passenger_env.create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                passenger_list.append(psg_res.id)
        return passenger_list

    def create_sale_service_charge_value(self, passenger, passenger_ids):
        ssc_list = []
        ssc_list_final = []
        pricelist_env = self.env['tt.reservation.visa.pricelist'].sudo()
        passenger_env = self.env['tt.reservation.visa.order.passengers']
        for idx, psg in enumerate(passenger):
            ssc = []
            pricelist_id = int(psg['master_visa_Id'])
            pricelist_obj = pricelist_env.browse(pricelist_id)
            passenger_obj = passenger_env.browse(passenger_ids[idx])
            vals = {
                'amount': pricelist_obj.sale_price,
                'charge_code': 'fare',
                'charge_type': 'FARE',
                'passenger_visa_id': passenger_ids[idx],
                'description': pricelist_obj.description,
                'pax_type': pricelist_obj.pax_type,
                'currency_id': pricelist_obj.currency_id.id,
                'pax_count': 1,
                'total': pricelist_obj.sale_price,
                'pricelist_id': pricelist_id,
                'sequence': passenger_obj.sequence
            }
            ssc_list.append(vals)
            # passenger_env.search([('id', '=', 'passenger_ids[idx])].limit=1).cost_service_charge_ids.create(ssc_list))
            ssc_obj = passenger_obj.cost_service_charge_ids.create(vals)
            ssc.append(ssc_obj.id)
            vals2 = vals.copy()
            vals2.update({
                'total': int(pricelist_obj.commission_price) * -1,
                'amount': int(pricelist_obj.commission_price) * -1,
                'charge_code': 'rac',
                'charge_type': 'RAC'
            })
            ssc_list.append(vals2)
            ssc_obj2 = passenger_obj.cost_service_charge_ids.create(vals2)
            ssc.append(ssc_obj2.id)
            passenger_obj.write({
                'cost_service_charge_ids': [(6, 0, ssc)]
            })

        for ssc in ssc_list:
            # compare with ssc_list
            ssc_same = False
            for ssc_final in ssc_list_final:
                if ssc['pricelist_id'] == ssc_final['pricelist_id']:
                    if ssc['charge_code'] == ssc_final['charge_code']:
                        if ssc['pax_type'] == ssc_final['pax_type']:
                            ssc_same = True
                            # update ssc_final
                            ssc_final['pax_count'] = ssc_final['pax_count'] + 1,
                            ssc_final['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                            ssc_final['total'] += ssc.get('amount')
                            ssc_final['pax_count'] = ssc_final['pax_count'][0]
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
                vals['passenger_visa_ids'].append(ssc['passenger_visa_id'])
                ssc_list_final.append(vals)
        print('Final : ' + str(ssc_list_final))
        return ssc_list_final

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
                # Pada state request, pax akan diberi expired date dg durasi tergantung dari paket visa yang diambil
                'expired_date': fields.Date.today() + timedelta(days=pricelist_obj.duration),
                'sequence': int(idx+1)
            })
            to_psg_obj = to_psg_env.create(psg_vals)

            to_req_list = []

            if psg['required']:
                for req in psg['required']:  # pricelist_obj.requirement_ids
                    req_vals = {
                        'to_passenger_id': to_psg_obj.id,
                        'requirement_id': req['id'],
                        'is_ori': req['is_original'],
                        'is_copy': req['is_copy']
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
        self.write(vals)

    ######################################################################################################
    # LEDGER
    ######################################################################################################

    @api.one
    def action_issued_visa(self, api_context=None):
        for rec in self:
            if not api_context:  # Jika dari call from backend
                api_context = {
                    'co_uid': rec.env.user.id
                }
            if not api_context.get('co_uid'):
                api_context.update({
                    'co_uid': rec.env.user.id
                })

            vals = {}

            if rec.name == 'New':
                vals.update({
                    'state': 'partial_booked',
                })

            vals.update({
                'state': 'issued',
                'issued_uid': api_context['co_uid'],
                'issued_date': datetime.now(),
                'confirmed_uid': api_context['co_uid'],
                'confirmed_date': datetime.now(),
            })

            self.write(vals)

            self._compute_commercial_state()
            self._create_ledger_visa()
            self._create_ho_ledger_visa()
            self._create_commission_ledger_visa()

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

            vals = ledger.prepare_vals('Profit HO ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       3, rec.currency_id.id, ho_profit, 0)
            vals = ledger.prepare_vals_for_resv(self, vals)
            vals.update({
                'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id
            })

            new_aml = ledger.create(vals)

    def _create_ledger_visa(self):
        # pass
        print(self.sale_service_charge_ids.read())
        ledger = self.env['tt.ledger']
        total_order = 0
        for rec in self:
            doc_type = []
            desc = ''

            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                if sc.charge_code == 'FARE':
                    total_order += sc.total
                if sc.pricelist_id.display_name:
                    desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       2, rec.currency_id.id, 0, total_order)
            vals = ledger.prepare_vals_for_resv(self, vals)

            new_aml = ledger.create(vals)

    def _create_commission_ledger_visa(self):
        # pass
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)

            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 3,
                                               rec.currency_id.id, agent_commission, 0)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'description': 'Agent Commission'
                })
                commission_aml = ledger_obj.create(vals)
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, parent_commission, 0)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                    'description': 'Parent Agent Commission'
                })
                commission_aml = ledger_obj.create(vals)
            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, ho_commission, 0)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                    'description': 'HO Commission'
                })
                commission_aml = ledger_obj.create(vals)
        print('Total Fare : ' + str(self.total_fare))

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

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
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
        return self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_ho').report_action(self, data=data)

    def do_print_out_visa_cust(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_reservation_visa.action_report_printout_tt_visa_cust').report_action(self, data=data)

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

    @api.multi
    @api.depends('passenger_ids')
    def _compute_immigration_consulate(self):
        for rec in self:
            if rec.passenger_ids:
                rec.immigration_consulate = rec.passenger_ids[0].pricelist_id.immigration_consulate

    def _calc_grand_total(self):
        for rec in self:
            rec.total = 0
            rec.total_tax = 0
            rec.total_disc = 0
            rec.total_commission = 0
            rec.total_fare = 0

            for line in rec.sale_service_charge_ids:
                if line.charge_type == 'FARE':
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
