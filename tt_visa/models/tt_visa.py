from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


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

    state_visa = fields.Selection(STATE_VISA, 'State', help='''draft = requested
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
    # vendor_ids = fields.One2many('tt.traveldoc.vendor.lines', 'booking_id', 'Expenses')

    to_passenger_ids = fields.One2many('tt.visa.order.passengers', 'visa_id', 'Visa Order Passengers')
    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

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

    def action_draft_visa(self):
        self.write({
            'state_visa': 'draft',
            'state': 'issued'
        })

    def action_confirm_visa(self):
        is_confirmed = True
        self.write({
            'state_visa': 'confirm',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })

    def action_validate_visa(self):
        is_validated = True
        self.write({
            'state_visa': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })

    def action_proceed_visa(self):
        self.write({
            'state_visa': 'proceed'
        })

    def action_cancel_visa(self):
        self.write({
            'state_visa': 'cancel',
        })

    def action_ready_visa(self):
        self.write({
            'state_visa': 'ready',
            'ready_date': datetime.now()
        })

    def action_done_visa(self):
        self.write({
            'state_visa': 'done',
            'done_date': datetime.now()
        })

    ######################################################################################################
    # CREATE
    ######################################################################################################

    def create_booking_traveldoc(self, contact_data, passengers, service_charge_summary, search_req, context, kwargs={}):
        try:
            self._validate_traveldoc(context, 'context')
            self._validate_traveldoc(search_req, 'header')
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
            if user_obj.agent_id.agent_type_id.id == self.env.ref('tt_base_rodex.agent_type_cor').id:
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'COR',
                    })

            if user_obj.agent_id.agent_type_id.id == self.env.ref('tt_base_rodex.agent_type_por').id:
                if user_obj.agent_id.parent_agent_id:
                    contact_data.update({
                        'commercial_agent_id': user_obj.agent_id.parent_agent_id.id,
                        'booker_type': 'POR',
                    })

            # if not context['agent_id']:
            #     raise Exception('ERROR Create booking, Customer or User, not have Agent (Agent ID)\n'
            #                     'Please contact Administrator, to complete the data !')

            header_val = self._traveldoc_header_normalization(search_req)
            contact_obj = self._create_contact(contact_data, context)

            psg_ids = self._evaluate_passenger_info(passengers, contact_obj.id, context['agent_id'])
            ssc_ids = self._create_service_charge_sale_traveldoc(service_charge_summary)

            to_psg_ids = self._create_traveldoc_order(passengers)

            header_val.update({
                'contact_id': contact_obj.id,
                'passenger_ids': [(6, 0, psg_ids)],
                'sale_service_charge_ids': [(6, 0, ssc_ids)],
                'to_passenger_ids': [(6, 0, to_psg_ids)],
                'state': 'booked',
                'agent_id': context['agent_id'],
                'user_id': context['co_uid'],
            })

            doc_type = header_val.get('transport_type')

            # create header & Update SUB_AGENT_ID
            book_obj = self.sudo().create(header_val)
            book_obj.sub_agent_id = contact_data['agent_id']

            book_obj.action_booked_traveldoc(context, doc_type)
            if kwargs.get('force_issued'):
                book_obj.action_issued_traveldoc(context, doc_type)

            self.env.cr.commit()
            return {
                'error_code': 0,
                'error_msg': 'Success',
                'response': {
                    'order_id': book_obj.id,
                    'order_number': book_obj.name,
                    'status': book_obj.state,
                    'state_traveldoc': book_obj.state_traveldoc,
                }
            }
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(msg=str(e) + '\n' + traceback.format_exc())
            return {
                'error_code': 1,
                'error_msg': str(e)
            }