from odoo import api, fields, models, _

BOOKING_STATE_TO_STR = {
    'draft': 'New',
    'confirm': 'Confirmed',
    'cancel': 'Cancelled',
    'cancel2': 'Expired',
    'fail_booking': 'Failed (Book)',
    'booked': 'Booked',
    'partial_booked': 'Partial Booked',
    'fail_issue': 'Failed (Issue)',
    'partial_issued': 'Partial Issued',
    'issued': 'Issued',
    'done': 'Done',
    'refund': 'Refund',
    'reroute': 'Reroute',
    'error': 'Connection Loss',
    'in_progress': 'In Progress',
    'fail_refunded': 'Failed (REFUNDED)',
}

BOOKING_STATE = [
    ('draft', 'New'),
    ('confirm', 'Confirmed'),
    ('cancel', 'Cancelled'),
    ('cancel2', 'Expired'),
    ('error', 'Connection Loss'),
    ('fail_booking', 'Failed (Book)'),
    ('booked', 'Booked'), ('partial_booked', 'Partial Booked'),
    ('in_progress', 'In Progress'),
    ('fail_issue', 'Failed (Issue)'),
    ('partial_issued', 'Partial Issued'),
    ('issued', 'Issued'),
    ('done', 'Done'),
    ('fail_refunded', 'Failed (REFUNDED)'),
    ('refund', 'Refund'),
    ('reroute', 'Reroute'),
]

JOURNEY_DIRECTION = [
    ('OW', 'One Way'),
    ('RT', 'Return')
]

STATE = [
    ('draft', 'Draft'),
    ('book', 'Book'),
    ('fail_book', 'Fail Book'),
    ('partial_issued', 'Partial Issued'),
    ('issued', 'Issued'),
    ('fail_issued', 'Fail Issued'),
    ('refund', 'Refund'),
    ('book', 'Book')
]

RESERVATION_TYPE = [
    ('airline', 'Airline'),
    ('train', 'Train'),
    ('ship', 'Ship'),
    ('cruise', 'Cruise'),
    ('car', 'Car/Rent'),
    ('bus', 'Bus')
]


# class tt_ledger(models.Model):
#     _inherit = 'tt.ledger'
#
#     resv_id = fields.Many2one('tt.reservation', 'Reservation', readonly=True)


# class tt_adjustment(models.Model):
#     _inherit = 'tt.adjustment'
#
#     resv_id = fields.Many2one('tt.reservation', 'Reservation', readonly=True)


# class tt_agent_invoice(models.Model):
#     _inherit = 'tt.agent.invoice'
#
#     resv_id = fields.Many2one('tt.reservation', 'Reservation', readonly=True)



class TtReservation(models.Model):
    _name = 'tt.reservation'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True)##fixme terpakai?
    hold_date = fields.Datetime('Hold Date', readonly=True)

    state = fields.Selection(BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Booked by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Create by', readonly=True) #create_uid

    sid = fields.Char('SID')
    issued_sid = fields.Char('Issued SID')

    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})
    contact_name = fields.Char('Contact Name')##fixme oncreate later
    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})


    elder = fields.Integer('Elder', readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult', default=1, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child', readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant', readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger')

    departure_date = fields.Date('Journey Date', readonly=True, states={'draft': [('readonly', False)]})  # , required=True
    return_date = fields.Date('Return Date', readonly=True, states={'draft': [('readonly', False)]})

    # agent_invoice_ids = fields.One2many('tt.agent.invoice', '', 'Agent Invoice')  # One2Many -> tt.agent.invoice
    # agent_invoice_ids = fields.Char('Agent Invoice')##fixme invoice here

    provider_type = fields.Many2one('tt.provider.type','Provider Type')

    adjustment_ids = fields.Char('Adjustment')  # One2Many -> tt.adjustment
    error_msg = fields.Char('Error Message')
    notes = fields.Char('Notes')

    ##fixme tambahkan compute field nanti
    # display_provider_name = fields.Char(string='Provider', compute='_action_display_provider', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)


    # total_fare = fields.Monetary(string='Total Fare', default=0, compute="_compute_total_booking", store=True)
    # total_tax = fields.Monetary(string='Total Tax', default=0, compute="_compute_total_booking", store=True)
    # total = fields.Monetary(string='Grand Total', default=0, compute="_compute_total_booking", store=True)
    # total_discount = fields.Monetary(string='Total Discount', default=0, compute="_compute_total_booking", store=True)
    # total_commission = fields.Monetary(string='Total Commission', default=0, compute="_compute_total_booking", store=True)
    # total_nta = fields.Monetary(string='NTA Amount', compute="_compute_total_booking", store=True)

    total_fare = fields.Char(string='Total Fare', default=0)
    total_tax = fields.Char(string='Total Tax', default=0)
    total = fields.Char(string='Grand Total', default=0)
    total_discount = fields.Char(string='Total Discount', default=0)
    total_commission = fields.Char(string='Total Commission', default=0)
    total_nta = fields.Char(string='NTA Amount')

    #yang jual
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id or self.env.user.company_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    store=True)

    #yang beli, kalau FPO sama dengan agent_id
    sub_agent_id = fields.Many2one('tt.agent', 'Sub-Agent', readonly=True, states={'draft': [('readonly', False)]},
                                   help='COR / POR')
    sub_agent_type_id = fields.Many2one('tt.agent.type', 'Sub Agent Type', related='sub_agent_id.agent_type_id',
                                        store=True, readonly=True)

    @api.model
    def create(self, vals_list):
        vals_list['res_model'] = self._name
        return super(TtReservation, self).create(vals_list)