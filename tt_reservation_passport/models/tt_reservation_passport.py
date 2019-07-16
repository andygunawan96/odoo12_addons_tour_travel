from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError
import logging
import traceback
import copy

_logger = logging.getLogger(__name__)

STATE_PASSPORT = [
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


class TtPassport(models.Model):
    _name = 'tt.reservation.passport'
    _inherit = ['tt.reservation', 'tt.history']

    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type',
                                       default=lambda self: self.env['tt.provider.type']
                                       .search([('code', '=', 'passport')], limit=1))

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True)

    state_passport = fields.Selection(STATE_PASSPORT, 'State', default='draft', help='''draft = requested
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
                                readonly=True)  # estimasi tanggal selesainya paspor
    payment_date = fields.Date('Payment Date', help='Date when accounting must pay the vendor')
    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)
    vendor = fields.Char('Vendor Name')
    receipt_number = fields.Char('Reference Number')
    vendor_ids = fields.One2many('tt.reservation.passport.vendor.lines', 'passport_id', 'Expenses')

    to_passenger_ids = fields.One2many('tt.reservation.passport.order.passengers', 'passport_id',
                                       'Travel Document Order Passengers')
    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'passport_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger', readonly=True,
                                 domain=[('res_model', '=', 'tt.reservation.passport')])

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'passport_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)
    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    contact_ids = fields.One2many('tt.customer', 'passport_id', 'Contacts', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)

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

    def action_draft_passport(self):
        self.write({
            'state_passport': 'draft',
            'state': 'issued'
        })
        # saat mengubah state ke draft, akan mengubah semua state passenger ke draft
        for rec in self.to_passenger_ids:
            rec.action_draft()
        self.message_post(body='Order DRAFT')

    def action_confirm_passport(self):
        is_confirmed = True
        for rec in self.to_passenger_ids:
            if rec.state not in ['confirm', 'cancel', 'validate']:
                is_confirmed = False

        if not is_confirmed:
            raise UserError(
                _('You have to Confirmed all The passengers document first.'))

        self.write({
            'state_passport': 'confirm',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })

    def action_validate_passport(self):
        is_validated = True
        for rec in self.to_passenger_ids:
            if rec.state not in ['validate', 'cancel']:
                is_validated = False

        if not is_validated:
            raise UserError(
                _('You have to Validated all The passengers document first.'))

        self.write({
            'state_passport': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })

    def action_in_process_passport(self):
        self.write({
            'state_passport': 'in_process',
            'in_process_date': datetime.now()
        })
        for rec in self.to_passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        self.message_post(body='Order IN PROCESS')

    # very low chance untuk pake vendor
    def action_to_vendor_passport(self):
        self.write({
            'use_vendor': True,
            'state_passport': 'to_vendor',
            'to_vendor_date': datetime.now()
        })
        self.message_post(body='Order SENT TO VENDOR')

    def action_vendor_process_passport(self):
        self.write({
            'state_passport': 'vendor_process',
            'vendor_process_date': datetime.now()
        })
        self.message_post(body='Order VENDOR PROCESS')

    def action_payment_passport(self):
        self.write({
            'state_passport': 'payment'
        })
        self.message_post(body='Order PAYMENT')

    def action_in_process_immigration_passport(self):
        is_payment = True
        for rec in self.to_passenger_ids:
            if rec.state not in ['confirm_payment']:
                is_payment = False

        if not is_payment:
            raise UserError(
                _('You have to pay all the passengers first.'))

        self.write({
            'state_passport': 'in_process',
            'in_process_date': datetime.now()
        })

    def action_partial_proceed_passport(self):
        self.write({
            'state_passport': 'partial_proceed'
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_proceed_passport(self):
        self.write({
            'state_passport': 'proceed'
        })

    def action_delivered_passport(self):
        self.write({
            'state_passport': 'delivered'
        })

    def action_cancel_passport(self):
        # set semua state passenger ke cancel
        for rec in self.to_passenger_ids:
            rec.action_cancel()
        self.write({
            'state_passport': 'cancel',
        })

    def action_ready_passport(self):
        self.write({
            'state_passport': 'ready',
            'ready_date': datetime.now()
        })

    def action_done_passport(self):
        self.write({
            'state_passport': 'done',
            'done_date': datetime.now()
        })

    ######################################################################################################
    # LEDGER
    ######################################################################################################

    @api.one
    def action_issued_passport(self, api_context=None):
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
                'name': self.env['ir.sequence'].next_by_code('passport.number'),
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
        self._create_ledger_passport()
        self._create_ho_ledger_passport()

    def _create_ledger_passport(self):
        ledger = self.env['tt.ledger']
        total_order = 0
        for rec in self:
            doc_type = []
            desc = ''

            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.passport_type not in doc_type:
                    doc_type.append(sc.pricelist_id.passport_type)
                if sc.charge_code == 'fare':
                    total_order += sc.total
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

    def _create_ho_ledger_passport(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''
            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.passport_type not in doc_type:
                    doc_type.append(sc.pricelist_id.passport_type)
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

            vals.update({
                'res_id': rec.id,
                'res_model': rec._name,
                'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id,
                'pnr': rec.pnr,
                'description': desc,
                'provider_type_id': rec.provider_type_id.id
            })

            new_aml = ledger.sudo().create(vals)

    def _create_commission_ledger_passport(self):
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

    def _create_anti_ledger_passport(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''

            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.passport_type not in doc_type:
                    doc_type.append(sc.pricelist_id.passport_type)
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

    def _create_anti_ho_ledger_passport(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            desc = ''
            for sc in rec.sale_service_charge_ids:
                if not sc.pricelist_id.passport_type in doc_type:
                    doc_type.append(sc.pricelist_id.passport_type)
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
                'description': 'REVERSAL ' + desc
            })

            new_aml = ledger.sudo().create(vals)
            # new_aml.action_done()
            # rec.ledger_id = new_aml

    def _create_anti_commission_ledger_passport(self):
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
    # CREATE
    ######################################################################################################

    def create_booking(self):
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
