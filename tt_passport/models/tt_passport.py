from odoo import api, fields, models, _
from datetime import datetime, timedelta

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
    _name = 'tt.passport'
    _inherit = 'tt.reservation'

    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    duration = fields.Char('Duration', readonly=True, states={'draft': [('readonly', False)]})
    total_cost_price = fields.Monetary('Total Cost Price', default=0, readonly=True)
    state_passport = fields.Selection(STATE_PASSPORT, 'State', help='''draft = requested
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
    # use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)
    # vendor = fields.Char('Vendor Name')
    receipt_number = fields.Char('Reference Number')
    # vendor_ids = fields.One2many('tt.traveldoc.vendor.lines', 'booking_id', 'Expenses')

    to_passenger_ids = fields.One2many('tt.passport.order.passengers', 'passport_id',
                                       'Travel Document Order Passengers')
    commercial_state = fields.Char('Payment Status', readonly=1, compute='_compute_commercial_state')
    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    sale_service_charge_ids = fields.One2many('tt.service.charge', 'passport_id', 'Service Charge',
                                              readonly=True, states={'draft': [('readonly', False)]})

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)
    recipient_name = fields.Char('Recipient Name')
    recipient_address = fields.Char('Recipient Address')
    recipient_phone = fields.Char('Recipient Phone')

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    immigration_consulate = fields.Char('Immigration Consulate', readonly=1, compute="_compute_immigration_consulate")

    def action_draft_passport(self):
        self.write({
            'state_passport': 'draft',
            'state': 'issued'
        })

    def action_confirm_passport(self):
        is_confirmed = True
        self.write({
            'state_passport': 'confirm',
            'confirmed_date': datetime.now(),
            'confirmed_uid': self.env.user.id
        })

    def action_validate_passport(self):
        is_validated = True
        self.write({
            'state_passport': 'validate',
            'validate_date': datetime.now(),
            'validate_uid': self.env.user.id
        })

    def action_proceed_passport(self):
        self.write({
            'state_passport': 'proceed'
        })

    def action_cancel_passport(self):
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
