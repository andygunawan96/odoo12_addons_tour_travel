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
    _inherit = ['tt.reservation']
    _description = 'Rodex Model'

    provider_type_id = fields.Many2one('tt.provider.type', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}, string='Transaction Type',
                                       default=lambda self: self.env['tt.provider.type']
                                       .search([('code', '=', 'passport')], limit=1))

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.default_country_id())
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

    passenger_ids = fields.One2many('tt.reservation.passport.order.passengers', 'passport_id',
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

    # Jika pax belum menentukan tujuan negara, default country di isi singapore
    def default_country_id(self):
        return self.env['res.country'].search([('name', '=', 'Singapore')], limit=1).id

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
        for rec in self.passenger_ids:
            rec.action_draft()
        self.message_post(body='Order DRAFT')

    def action_confirm_passport(self):
        is_confirmed = True
        for rec in self.passenger_ids:
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
        self.message_post(body='Order CONFIRMED')

    def action_validate_passport(self):
        is_validated = True
        for rec in self.passenger_ids:
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
        self.message_post(body='Order VALIDATED')

    def action_in_process_passport(self):
        self.write({
            'state_passport': 'in_process',
            'in_process_date': datetime.now()
        })
        for rec in self.passenger_ids:
            if rec.state in ['validate', 'cancel']:
                rec.action_in_process()
        context = {
            'co_uid': self.env.user.id
        }
        self.action_booked_passport(context)
        self.action_issued_passport(context)
        self.message_post(body='Order IN PROCESS')

    def action_pay_now_passport(self):
        pass

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
        for rec in self.passenger_ids:
            if rec.state not in ['confirm_payment']:
                is_payment = False

        if not is_payment:
            raise UserError(
                _('You have to pay all the passengers first.'))

        self.write({
            'state_passport': 'in_process',
            'in_process_date': datetime.now()
        })
        self.message_post(body='Order IN PROCESS TO IMMIGRATION')
        for rec in self.passenger_ids:
            rec.action_in_process2()

    def action_partial_proceed_passport(self):
        self.write({
            'state_passport': 'partial_proceed'
        })
        self.message_post(body='Order PARTIAL PROCEED')

    def action_proceed_passport(self):
        self.write({
            'state_passport': 'proceed'
        })
        self.message_post(body='Order PROCEED')

    def action_delivered_passport(self):
        self.write({
            'state_passport': 'delivered'
        })
        self.message_post(body='Order DELIVERED')

    def action_cancel_passport(self):
        # set semua state passenger ke cancel
        if self.state_passport not in ['in_process', 'partial_proceed', 'proceed', 'delivered', 'ready', 'done']:
            if self.sale_service_charge_ids:
                self._create_anti_ho_ledger_passport()
                self._create_anti_ledger_passport()
                self._create_anti_commission_ledger_passport()
        for rec in self.passenger_ids:
            rec.action_cancel()
        self.write({
            'state_passport': 'cancel',
        })
        for rec3 in self.vendor_ids:
            rec3.sudo().unlink()
        self.message_post(body='Order CANCELED')

    def action_ready_passport(self):
        self.write({
            'state_passport': 'ready',
            'ready_date': datetime.now()
        })
        self.message_post(body='Order READY')

    def action_done_passport(self):
        self.write({
            'state_passport': 'done',
            'done_date': datetime.now()
        })
        self.message_post(body='Order DONE')

    def action_booked_passport(self, api_context=None):
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
        self._create_ledger_passport()
        self._create_ho_ledger_passport()
        # self._create_commission_ledger_passport()
        # self._calc_grand_total()

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

            vals = ledger.prepare_vals('Order ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date, 2,
                                       rec.currency_id.id, 0, total_order)
            vals = ledger.prepare_vals_for_resv(self, vals)

            new_aml = ledger.create(vals)

    def _create_ho_ledger_passport(self):
        ledger = self.env['tt.ledger']
        for rec in self:
            doc_type = []
            for sc in rec.sale_service_charge_ids:
                if sc.pricelist_id.passport_type not in doc_type:
                    doc_type.append(sc.pricelist_id.passport_type)

            doc_type = ','.join(str(e) for e in doc_type)

            ho_profit = 0
            for pax in self.passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price

            vals = ledger.prepare_vals('Profit HO ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date, 3,
                                       rec.currency_id.id, ho_profit, 0)
            vals = ledger.prepare_vals_for_resv(self, vals)
            vals.update({
                'agent_id': self.env['tt.agent'].sudo().search([('agent_type_id.name', '=', 'HO')], limit=1).id
            })

            new_aml = ledger.create(vals)

    def _create_commission_ledger_passport(self):
        # pass
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.sub_agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)

            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 3,
                                               rec.currency_id.id, agent_commission, 0)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)

                commission_aml = ledger_obj.create(vals)
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, parent_commission, 0)
                vals.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                })
                commission_aml = ledger_obj.create(vals)

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, ho_commission, 0)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                })
                commission_aml = ledger_obj.create(vals)

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
                                       2, rec.currency_id.id, rec.total, 0)
            vals = ledger.prepare_vals_for_resv(self, vals)
            vals.update({
                'description': 'REVERSAL ' + desc,
            })

            new_aml = ledger.sudo().create(vals)
            new_aml.update({
                'reversal_id': new_aml.id
            })

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
            for pax in self.passenger_ids:
                ho_profit += pax.pricelist_id.cost_price - pax.pricelist_id.nta_price
                print('HO Profit : ' + str(ho_profit))

            vals = ledger.prepare_vals('Profit ' + doc_type + ' : ' + rec.name, rec.name, rec.issued_date,
                                       3, rec.currency_id.id, 0, ho_profit)
            vals = ledger.prepare_vals_for_resv(self, vals)
            vals.update({
                'agent_id': self.env['tt.agent'].sudo().search([('parent_agent_id', '=', False)], limit=1).id,
                'description': 'REVERSAL ' + desc
            })

            new_aml = ledger.create(vals)
            new_aml.update({
                'reverse_id': new_aml.id,
            })

    def _create_anti_commission_ledger_passport(self):
        for rec in self:
            ledger_obj = rec.env['tt.ledger']
            agent_commission, parent_commission, ho_commission = rec.sub_agent_id.agent_type_id.calc_commission(
                rec.total_commission, 1)
            if agent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, rec.name, rec.issued_date, 3,
                                               rec.currency_id.id, 0, agent_commission)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                commission_aml = ledger_obj.create(vals)
                commission_aml.update({
                    'reverse_id': commission_aml.id,
                })
            if parent_commission > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'PA: ' + rec.name, rec.issued_date, 3,
                                               rec.currency_id.id, 0, parent_commission)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'agent_id': rec.agent_id.parent_agent_id.id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.update({
                    'reverse_id': commission_aml.id,
                })

            if int(ho_commission) > 0:
                vals = ledger_obj.prepare_vals('Commission : ' + rec.name, 'HO: ' + rec.name, rec.issued_date,
                                               3, rec.currency_id.id, 0, ho_commission)
                vals = ledger_obj.prepare_vals_for_resv(self, vals)
                vals.update({
                    'agent_id': rec.env['tt.agent'].sudo().search(
                        [('parent_agent_id', '=', False)], limit=1).id,
                })
                commission_aml = ledger_obj.create(vals)
                commission_aml.update({
                    'reverse_id': commission_aml.id,
                })

    ######################################################################################################
    # PRINTOUT
    ######################################################################################################

    def do_print_out_passport_ho(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_reservation_passport.action_report_printout_passport_ho').report_action(self, data=data)

    def do_print_out_passport_cust(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
        }
        return self.env.ref('tt_reservation_passport.action_report_printout_passport_cust').report_action(self, data=data)

    ######################################################################################################
    # CREATE
    ######################################################################################################

    def create_booking(self):
        pass

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
                'charge_type': 'fare',
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
                'charge_type': 'rac'
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
                            ssc_final['passenger_passport_ids'].append(ssc['passenger_passport_id'])
                            ssc_final['total'] += ssc.get('amount')
                            ssc_final['pax_count'] = ssc_final['pax_count'][0]
                            break
            if ssc_same is False:
                vals = {
                    'amount': ssc['amount'],
                    'charge_code': ssc['charge_code'],
                    'charge_type': ssc['charge_type'],
                    'description': ssc['description'],
                    'pax_type': ssc['pax_type'],
                    'currency_id': ssc['currency_id'],
                    'pax_count': 1,
                    'total': ssc['total'],
                    'pricelist_id': ssc['pricelist_id']
                }
                vals['passenger_passport_ids'].append(ssc['passenger_passport_id'])
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

    ######################################################################################################
    # OTHERS
    ######################################################################################################

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
                if line.charge_code == 'fare':
                    rec.total_fare += line.total
                if line.charge_code == 'tax':
                    rec.total_tax += line.total
                if line.charge_code == 'disc':
                    rec.total_disc += line.total
                if line.charge_code == 'r.oc':
                    rec.total_commission += line.total
                if line.charge_code == 'rac':
                    rec.total_commission += line.total

            print('Total Fare : ' + str(rec.total_fare))
            rec.total = rec.total_fare + rec.total_tax + rec.total_disc
            rec.total_nta = rec.total - rec.total_commission
