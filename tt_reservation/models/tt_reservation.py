from odoo import api, fields, models, _
from ...tools import variables


class TtReservation(models.Model):
    _name = 'tt.reservation'

    name = fields.Char('Order Number', index=True, default='New', readonly=True)
    pnr = fields.Char('PNR', readonly=True, states={'draft': [('readonly', False)]})

    date = fields.Datetime('Booking Date', default=lambda self: fields.Datetime.now(), readonly=True, states={'draft': [('readonly', False)]})
    expired_date = fields.Datetime('Expired Date', readonly=True)  # fixme terpakai?
    hold_date = fields.Datetime('Hold Date', readonly=True)

    state = fields.Selection(variables.BOOKING_STATE, 'State', default='draft')

    booked_uid = fields.Many2one('res.users', 'Booked by', readonly=True)
    booked_date = fields.Datetime('Booked Date', readonly=True)
    issued_uid = fields.Many2one('res.users', 'Issued by', readonly=True)
    issued_date = fields.Datetime('Issued Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Create by', readonly=True)  # create_uid

    sid_booked = fields.Char('SID Booked')  # Signature generate sendiri

    booker_id = fields.Many2one('tt.customer','Booker', ondelete='restrict', readonly=True, states={'draft':[('readonly',False)]})
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})

    contact_name = fields.Char('Contact Name')  # fixme oncreate later
    contact_email = fields.Char('Contact Email')
    contact_phone = fields.Char('Contact Phone')

    display_mobile = fields.Char('Contact Person for Urgent Situation',
                                 readonly=True, states={'draft': [('readonly', False)]})

    elder = fields.Integer('Elder', default=0, readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult', default=1, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child', default=0, readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant', default=0, readonly=True, states={'draft': [('readonly', False)]})

    ledger_ids = fields.One2many('tt.ledger', 'res_id', 'Ledger')

    departure_date = fields.Date('Journey Date', readonly=True, states={'draft': [('readonly', False)]})  # , required=True
    return_date = fields.Date('Return Date', readonly=True, states={'draft': [('readonly', False)]})

    provider_type_id = fields.Many2one('tt.provider.type','Provider Type')

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

    total_fare = fields.Monetary(string='Total Fare', default=0)
    total_tax = fields.Monetary(string='Total Tax', default=0)
    total = fields.Monetary(string='Grand Total', default=0)
    total_discount = fields.Monetary(string='Total Discount', default=0)
    total_commission = fields.Monetary(string='Total Commission', default=0)
    total_nta = fields.Monetary(string='NTA Amount')

    # yang jual
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True,
                               default=lambda self: self.env.user.agent_id,
                               readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id',
                                    store=True)

    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer Parent', readonly=True,
                                         states={'draft': [('readonly', False)]}, help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type',
                                              related='customer_parent_id.customer_parent_type_id', store=True,
                                              readonly=True)
