from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy
from ...tools.api import Response
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

JOURNEY_DIRECTION = [
    ('OW', 'One Way'),
    ('RT', 'Return')
]


class TtVisa(models.Model):
    _name = 'tt.visa'
    _inherit = ['tt.reservation', 'tt.history']
    _order = 'issued_date desc'

    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type',
                                       default=lambda self: self.env['tt.provider.type'].search([('id', '=', 6)],
                                                                                                limit=1))

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True)

    state_visa = fields.Selection(STATE_VISA, 'State', default='confirm',
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
    # domain=[('res_model', '=', 'tt.visa')]

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'visa_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

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

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    ######################################################################################################
    # STATE
    ######################################################################################################

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


    def get_booking_visa_api(self, data):
        for rec in self.search([('name', '=', data['order_number'])]):
            passenger = []
            contact = []
            for pax in rec.to_passenger_ids:
                requirement = []
                for require in pax.to_requirement_ids:
                    requirement.append({
                        'name': require.requirement_id.name,
                        # 'required': require.required,
                    })
                passenger.append({
                    'title': pax.passenger_id.title,
                    'first_name': pax.passenger_id.first_name,
                    'last_name': pax.passenger_id.last_name,
                    'birth_date': pax.passenger_id.birth_date,
                    'age': pax.passenger_id.age,
                    'passport': pax.passenger_id.passport_number,
                    'visa': {
                        'price':
                        {
                            'sale_price': pax.pricelist_id.sale_price,
                            'commission': pax.pricelist_id.commission_price,
                            'currency': pax.pricelist_id.currency_id.name
                        },
                        'entry_type': dict(pax.pricelist_id._fields['entry_type'].selection).get(pax.pricelist_id.entry_type),
                        'visa_type': dict(pax.pricelist_id._fields['visa_type'].selection).get(pax.pricelist_id.visa_type),
                        'process': dict(pax.pricelist_id._fields['process_type'].selection).get(pax.pricelist_id.process_type),
                        'pax_type': pax.pricelist_id.pax_type,
                        'immigration_consulate': pax.pricelist_id.immigration_consulate,
                        'requirement': requirement
                    }
                })

            for pax in rec.contact_ids:
                contact.append({
                    'title': pax.title,
                    'name': pax.name,
                    'phone_number': pax.phone_ids[0].phone_number if len(pax.phone_ids) > 0 else '',
                })
            res = {
                'booker': {
                    'title': rec.booker_id.title,
                    'first_name': rec.booker_id.title,
                    'last_name': rec.booker_id.title,
                    'phone_number': rec.booker_id.phone_ids[0].phone_number if len(rec.booker_id.phone_ids) > 0 else '',
                },
                'journey': {
                    'country': rec.country_id.name,
                    'departure_date': rec.departure_date
                },
                'passenger': passenger,
                'contact': contact,

            }
        if not res:
            res = Response().get_error(str('Visa Booking not found'), 500)
        return res

    def create_booking_visa_api(self, data, context, kwargs):
        sell_visa = copy.deepcopy(data['sell_visa'])
        booker = copy.deepcopy(data['booker'])
        contact = copy.deepcopy(data['contact'])
        passengers = copy.deepcopy(data['passenger'])
        search = copy.deepcopy(data['search'])
        context = copy.deepcopy(context)
        kwargs = copy.deepcopy(kwargs)

        context.update({
            'co_uid': context['co_uid']
        })

        try:
            context = self._update_api_context(contact, context)  # update agent_id dan booker
            user_obj = self.env['res.users'].sudo().browse(context['co_uid'])
            for contact_data in contact:
                contact_data.update({
                    'agent_id': context['agent_id'],
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

            header_val = self._visa_header_normalization(search, sell_visa)
            booker_id = self._create_booker(context, booker)
            contact_ids = self._create_contact(context, contact)  # create contact
            passenger_ids = self._create_passenger(context, passengers)  # create passenger
            ssc_ids = self._create_sale_service_charge(passengers)  # create pricing
            to_psg_ids = self._create_visa_order(passengers)  # create visa order

            header_val.update({
                'country_id': self.env['res.country'].sudo().search([('name', '=', search['destination'])], limit=1).id,
                'booker_id': booker_id,
                'contact_ids': [(6, 0, contact_ids)],
                'passenger_ids': [(6, 0, passenger_ids)],
                'sale_service_charge_ids': [(6, 0, ssc_ids)],
                'to_passenger_ids': [(6, 0, to_psg_ids)],
                'adult': sell_visa['pax']['adult'],
                'child': sell_visa['pax']['child'],
                'infant': sell_visa['pax']['infant'],
                'state': 'booked',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
            })

            book_obj = self.sudo().create(header_val)
            book_obj.sub_agent_id = self.env.user.agent_id  # kedepannya mungkin dihapus | contact['agent_id']

            book_obj.action_booked_visa(context)  # ubah state ke booked sekaligus
            book_obj.action_issued_visa(context)
            response = {
                'id': book_obj.name
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
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
            'sub_agent_id': user_obj.agent_id.id,
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
                'commercial_agent_id': context['agent_id'],
                'agent_id': context['agent_id'],
                'nationality_id': country and country[0].id or False,
                'email': booker.get('email', booker['email']),
                'mobile': booker.get('mobile', booker['mobile']),
            })
            booker_obj = booker_env.create(booker)
            booker_obj.update({
                'phone_ids': booker_obj.phone_ids.create({
                    'phone_number': booker.get('mobile', booker['mobile']),
                    'type': 'custom'
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
                    'commercial_agent_id': context['agent_id'],
                    'agent_id': context['agent_id'],
                    'nationality_id': country and country[0].id or False,
                    # 'passenger_type': 'ADT',
                    'email': con.get('email', con['email'])
                })
                contact_obj = contact_env.create(con)
                contact_obj.update({
                    'phone_ids': contact_obj.phone_ids.create({
                        'phone_number': con.get('mobile', con['mobile']),
                        'type': 'custom'
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
                    'agent_id': context['agent_id']
                })
                psg_res = passenger_env.create(psg)
                psg.update({
                    'passenger_id': psg_res.id,
                })
                passenger_list.append(psg_res.id)
        return passenger_list

    def _create_sale_service_charge(self, passengers):
        pricing_list = []
        pricelist_list = []
        pricelist_env = self.env['tt.visa.pricelist'].sudo()
        pricing_env = self.env['tt.service.charge'].sudo()

        for psg in passengers:
            # check pricelist_id
            pricelist_found = False
            pricing_id = ''
            commission_pricing_id = ''

            for rec in pricelist_list:
                if pricelist_list is not [] and psg['master_visa_Id'] in str(rec['pricelist_id']):
                    pricelist_found = True
                    pricing_id = rec['pricing_id']
                    commission_pricing_id = rec['commission_pricing_id']

            if not pricelist_found:
                # create fare pricing
                pricelist_id = int(psg['master_visa_Id'])
                pricelist_obj = pricelist_env.browse(pricelist_id)
                service_charge_summary = {
                    'amount': pricelist_obj.sale_price,
                    'charge_code': 'fare',
                    'charge_type': 'fare',
                    'description': pricelist_obj.description,
                    'pax_type': pricelist_obj.pax_type,
                    'currency_id': pricelist_obj.currency_id.id,
                    'pax_amount': 1,
                    'total': pricelist_obj.sale_price,
                    'pricelist_id': pricelist_id
                }
                pricing_obj = pricing_env.create(service_charge_summary)
                pricing_list.append(pricing_obj.id)

                # create commission pricing
                service_charge_summary2 = service_charge_summary.copy()
                service_charge_summary2.update({
                    'total': int(pricelist_obj.commission_price) * -1,
                    'amount': int(pricelist_obj.commission_price) * -1,
                    'charge_code': 'r.ac',
                    'charge_type': 'r.ac'
                })
                commission_pricing_obj = pricing_obj.create(service_charge_summary2)

                # create pricelist_ids
                pricelist_dict = {
                    'pricelist_id': pricelist_id,
                    'pricing_id': pricing_obj.id,
                    'commission_pricing_id': commission_pricing_obj.id,
                }
                pricelist_list.append(pricelist_dict)
                pricing_list.append(commission_pricing_obj.id)
            else:
                prc_obj = pricing_env.browse(pricing_id)
                comm_prc_obj = pricing_env.browse(commission_pricing_id)
                prc_obj.update({
                    'pax_count': int(prc_obj.pax_count) + 1,
                    'total': int(prc_obj.total) + int(prc_obj.amount)
                })
                comm_prc_obj.update({
                    'pax_count': int(comm_prc_obj.pax_count) + 1,
                    'total': int(comm_prc_obj.total) - int(comm_prc_obj.amount)
                })

        return pricing_list

    def _create_visa_order(self, passengers):
        pricelist_env = self.env['tt.visa.pricelist'].sudo()
        to_psg_env = self.env['tt.visa.order.passengers'].sudo()
        to_req_env = self.env['tt.visa.order.requirements'].sudo()
        to_psg_list = []

        for psg in passengers:
            pricelist_id = int(psg['master_visa_Id'])
            pricelist_obj = pricelist_env.browse(pricelist_id)
            psg_vals = {
                'passenger_id': psg['passenger_id'],
                # 'passenger_type': psg['passenger_type'],
                'pricelist_id': pricelist_id,
            }
            to_psg_obj = to_psg_env.create(psg_vals)

            to_req_list = []
            for req in pricelist_obj.requirement_ids:
                req_vals = {
                    'to_passenger_id': to_psg_obj.id,
                    'requirement_id': req.id,
                }
                to_req_obj = to_req_env.create(req_vals)
                to_req_list.append(to_req_obj.id)  # akan dipindah ke edit requirements

            # jika ingin assign requirement_ids, edit disini
            # jika cara ini digunakan dan memiliki banyak requirements, mungkin akan menyebabkan performance drop
            # for req in psg['required']:
            #     to_req_obj = to_req_env.browse(req['id'])
            #     to_req_obj.update({
            #         'to_passenger_id': psg.id,
            #         'is_ori': req['is_ori'],
            #         'is_copy': req['is_copy'],
            #         'check_uid': req['check_uid'],
            #         'check_date': req['check_date']
            #     })
            #     to_req_list.append(to_req_obj.id)

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
    # LEDGER | create ledger akan dipindah ke tt_accounting
    ######################################################################################################

    @api.one
    def action_issued_visa(self, api_context=None):
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
            'issued_date': datetime.now(),
            'confirmed_uid': api_context['co_uid'],
            'confirmed_date': datetime.now(),
        })

        self.write(vals)
        self._compute_commercial_state()
        self._create_ledger_visa()
        self._create_ho_ledger_visa()
        # self._create_commission_ledger_visa()
        # self.create_agent_invoice_traveldoc()

    def _create_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''
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
                print('Cost Price : ' + str(pax.pricelist_id.cost_price))
                print('NTA Price : ' + str(pax.pricelist_id.nta_price))
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price

            vals = ledger.prepare_vals('Profit HO ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'commission', rec.currency_id.id, ho_profit, 0)

            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name
            print('id : ' + str(rec.id))
            vals.update({
                'res_id': rec.id,
                'res_model': rec._name,
                'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id,
                'pnr': rec.pnr,
                'description': desc,
                'provider_type_id': rec.provider_type_id.id
            })

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_ledger_visa(self):
        # pass
        print(self.sale_service_charge_ids.read())
        ledger = self.env['tt.ledger']
        total_order = 0
        for rec in self:
            doc_type = []
            desc = ''

            for sc in rec.sale_service_charge_ids:
                # if rec.transport_type == 'passport':
                #     if not sc.pricelist_id.apply_type in doc_type:
                #         doc_type.append(sc.pricelist_id.apply_type)
                #     desc = sc.pricelist_id.passport_type.upper() + ' ' + sc.pricelist_id.apply_type.upper()
                # else:
                if sc.pricelist_id.visa_type not in doc_type:
                    doc_type.append(sc.pricelist_id.visa_type)
                if sc.charge_code == 'fare':
                    total_order += sc.total
                print('Total fare : ' + str(sc.total))
                desc = sc.pricelist_id.display_name.upper() + ' ' + sc.pricelist_id.entry_type.upper()

            doc_type = ','.join(str(e) for e in doc_type)

            print('Total : ' + str(total_order))

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       'travel.doc', rec.currency_id.id, 0, total_order)
            vals.update({
                'res_id': rec.id,
                'res_model': rec._name,
                'agent_id': rec.agent_id.id,
                'pnr': rec.pnr,
                'provider_type_id': rec.provider_type_id.id,
                'description': desc
            })
            # vals['transport_type'] = rec.transport_type
            # vals['display_provider_name'] = rec.display_provider_name

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
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()
                # rec.commission_ledger_id = commission_aml.id
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, parent_commission, 0)
                vals.update({
                    'agent_id': rec.sub_agent_id.parent_agent_id.id,
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               'commission',
                                               rec.currency_id.id, ho_commission, 0)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                    'res_id': rec.id,
                })
                commission_aml = ledger_obj.create(vals)
                # commission_aml.action_done()

    # ANTI / REVERSE LEDGER

    def _create_anti_ho_ledger_visa(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''
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
            desc = ''

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
