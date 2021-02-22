from odoo import api, fields, models, _

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('validate', 'Validate'),
    ('cancel', 'Cancel'),
]

PAX_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

EXTRA_TYPE = [
    ('variable_cost', 'Variable Cost'),
    ('merchandise', 'Merchandise'),
    ('others', 'Others')
]


class TourPackageQuotation(models.Model):
    _name = 'tt.master.tour.quotation'
    _description = 'Master Tour Quotation'

    state = fields.Selection(STATE, 'State', default='draft')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    tour_id = fields.Many2one('tt.master.tour', 'Tour')
    airport_tax = fields.Monetary('Airport Tax', readonly=True, related='')

    # PAX
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type', default='ADT', readonly=True, states={'draft': [('readonly', False)]})
    pax_amount = fields.Integer('Pax Amount', default=1, readonly=True, states={'draft': [('readonly', False)]})

    # PERIOD
    start_period = fields.Date('Start Period', readonly=True, states={'draft': [('readonly', False)]})
    end_period = fields.Date('End Period', readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Date', readonly=True, states={'draft': [('readonly', False)]})
    code = fields.Char('Code', readonly=True, states={'draft': [('readonly', False)]})

    # STATE UID & DATE
    confirm_uid = fields.Many2one('res.users', 'Confirmed By', readonly=True)
    confirm_date = fields.Datetime('Confirmed Date', readonly=True)

    validate_uid = fields.Many2one('res.users', 'Validated By', readonly=True)
    validate_date = fields.Datetime('Validated Date', readonly=True)

    canceled_uid = fields.Many2one('res.users', 'Canceled By', readonly=True)
    canceled_date = fields.Datetime('Canceled Date', readonly=True)

    # INTERNATIONAL FLIGHT
    international_flight = fields.Integer('International Flight', readonly=True,
                                          states={'draft': [('readonly', False)]}, default=0)
    international_flight_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    international_flight_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                                states={'draft': [('readonly', False)]})
    rupiah_international_flight = fields.Monetary('International Flight (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_international_flight')

    # DOMESTIC FLIGHT
    domestic_flight = fields.Integer('Domestic Flight', readonly=True,
                                     states={'draft': [('readonly', False)]}, default=0)
    domestic_flight_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    domestic_flight_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                           states={'draft': [('readonly', False)]})
    rupiah_domestic_flight = fields.Monetary('Domestic Flight (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_domestic_flight')

    # TRAIN
    train_cost = fields.Integer('Train', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    train_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    train_rate = fields.Monetary('Exchange Rate', default=1, readonly=True, states={'draft': [('readonly', False)]})
    rupiah_train_cost = fields.Monetary('Train (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_train_cost')

    # LAND PACKAGE
    land_package = fields.Integer('Land Package', readonly=True,
                                  states={'draft': [('readonly', False)]}, default=0)
    land_package_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    land_package_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                        states={'draft': [('readonly', False)]})
    rupiah_land_package = fields.Monetary('Land Package (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_land_package')

    # INSURANCE
    insurance_cost = fields.Integer('Insurance', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    insurance_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    insurance_rate = fields.Monetary('Exchange Rate', default=1, readonly=True, states={'draft': [('readonly', False)]})
    rupiah_insurance_cost = fields.Monetary('Insurance (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_insurance_cost')

    # VISA
    visa = fields.Monetary('Visa', readonly=True, states={'draft': [('readonly', False)]}, default=0)

    # PORTER
    porter_ids = fields.One2many('tt.master.tour.quotation.porter', 'tour_quotation_id', 'Porter(s)', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    total_porter_cost = fields.Monetary('Total Porter Cost', readonly=True, default=0, compute='_compute_total_porter_cost')

    # MERCHANDISE
    passport_wallet = fields.Monetary('Passport Wallet', readonly=True,
                                      states={'draft': [('readonly', False)]}, default=0)
    passport_cover = fields.Monetary('Passport Cover', readonly=True,
                                     states={'draft': [('readonly', False)]}, default=0)
    luggage_tag = fields.Monetary('Luggage Tag', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    pen = fields.Monetary('Pen', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    souvenir = fields.Monetary('Souvenir', readonly=True, states={'draft': [('readonly', False)]}, default=0)
    travel_bag = fields.Monetary('Travel/Trolley Bag', readonly=True,
                                 states={'draft': [('readonly', False)]}, default=0)
    snack = fields.Monetary('Snack', readonly=True, states={'draft': [('readonly', False)]}, default=0)

    total_merchandise = fields.Monetary('Total Merchandise', readonly=True, default=0, compute='_compute_total_merchandise')

    # TOUR LEADER FEE
    tour_leader_fee = fields.Integer('Tour Leader Fee', readonly=True,
                                     states={'draft': [('readonly', False)]}, default=0)
    tour_leader_fee_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    tour_leader_fee_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                           states={'draft': [('readonly', False)]})
    rupiah_tour_leader_fee = fields.Monetary('Tour Leader Fee (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_tour_leader_fee')
    tour_leader_fee_days = fields.Integer('Days', default=1, readonly=True, states={'draft': [('readonly', False)]})

    # TICKET FOR TOUR LEADER
    ticket_for_tour_leader = fields.Integer('Ticket for Tour Leader', readonly=True,
                                            states={'draft': [('readonly', False)]}, default=0)
    ticket_for_tour_leader_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    ticket_for_tour_leader_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                                  states={'draft': [('readonly', False)]})
    rupiah_ticket_for_tour_leader = fields.Monetary('Ticket for Tour Leader (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_ticket_for_tour_leader')
    ticket_for_tour_leader_days = fields.Integer('Number of Tour Leader(s)', default=1, readonly=True,
                                                 states={'draft': [('readonly', False)]})

    # LAND TOUR FOR TOUR LEADER
    land_tour_for_tour_leader = fields.Monetary('Land Tour for Tour Leader (Rupiah)', readonly=True,
                                                states={'draft': [('readonly', False)]})

    # SINGLE SUPPORT FOR TOUR LEADER
    single_supp_for_tour_leader = fields.Integer('Single Supp for Tour Leader', readonly=True,
                                                 states={'draft': [('readonly', False)]}, default=0)
    single_supp_for_tour_leader_currency = fields.Char('Currency', readonly=True,
                                                       states={'draft': [('readonly', False)]})
    single_supp_for_tour_leader_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                                       states={'draft': [('readonly', False)]})
    rupiah_single_supp_for_tour_leader = fields.Monetary('Single Supp for Tour Leader (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_single_supp_for_tour_leader')

    # VISA FOR TOUR LEADER
    visa_for_tour_leader = fields.Monetary('Visa for Tour Leader (Rupiah)', readonly=True,
                                           states={'draft': [('readonly', False)]})

    # AIRPORT TAX FOR TOUR LEADER
    airport_tax_for_tour_leader = fields.Monetary('Airport Tax for Tour Leader', readonly=True,
                                                  states={'draft': [('readonly', False)]}, default=0)

    # TRAVEL EXPENSE FOR TOUR LEADER
    expense_for_tour_leader = fields.Integer('Travel Expense for Tour Leader', readonly=True,
                                             states={'draft': [('readonly', False)]}, default=0)
    expense_for_tour_leader_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    expense_for_tour_leader_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                                   states={'draft': [('readonly', False)]})
    rupiah_expense_for_tour_leader = fields.Monetary('Travel Expense for Tour Leader (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_expense_for_tour_leader')
    expense_for_tour_leader_days = fields.Integer('Number of Tour Leader(s)', default=1, readonly=True,
                                                  states={'draft': [('readonly', False)]})

    # INSURANCE FOR TOUR LEADER
    insurance_for_tour_leader_cost = fields.Integer('Insurance for Tour Leader', readonly=True,
                                                    states={'draft': [('readonly', False)]}, default=0)
    insurance_for_tour_leader_currency = fields.Char('Currency', readonly=True, states={'draft': [('readonly', False)]})
    insurance_for_tour_leader_rate = fields.Monetary('Exchange Rate', default=1, readonly=True,
                                                     states={'draft': [('readonly', False)]})
    rupiah_insurance_for_tour_leader_cost = fields.Monetary('Insurance for Tour Leader (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_insurance_for_tour_leader_cost')

    # TRAVEL ALLOWANCE
    travel_allowance = fields.Monetary('Travel Allowance (Rupiah)', readonly=True,
                                       states={'draft': [('readonly', False)]})

    # TOTAL VARIABLE COST
    total_variable_cost = fields.Monetary('Total Variable Cost', readonly=True, default=0, compute='_compute_total_variable_cost')

    # BASED ON PAX
    based_on_pax = fields.Monetary('Based on Pax', readonly=True, default=0, compute='_compute_based_on_pax')

    # TOTALS
    total_exclude = fields.Monetary('Grand Total (EXC. Tipping, Airport Tax, Visa)', readonly=True, default=0, compute='_compute_total_exclude')

    service_charge = fields.Monetary('Service Charge', readonly=True,
                                     states={'draft': [('readonly', False)]}, default=0)
    omzet = fields.Monetary('Tax 1% (omzet)', readonly=True, states={'draft': [('readonly', False)]}, default=0)

    retail_price_exclude = fields.Monetary('Retail Price (EXC. Tipping, Airport Tax, Visa)', readonly=True, default=0, compute='_compute_retail_price_exclude')

    retail_price_include = fields.Monetary('Retail Price (INC. Tipping, Airport Tax, Visa)', readonly=True, default=0, compute='_compute_retail_price_include')

    # EXTRA
    extra_ids = fields.One2many('tt.master.tour.quotation.extra', 'tour_quotation_id', 'Extra(s)', readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    total_extra_cost = fields.Monetary('Total Extra Cost', readonly=True, default=0, compute='_compute_total_extra_cost')

    # TIPPING
    tipping_guide = fields.Monetary('Tipping Guide', readonly=True, related='tour_id.tipping_guide')
    tipping_tour_leader = fields.Monetary('Tipping Tour Leader', readonly=True, related='tour_id.tipping_tour_leader')
    tipping_driver = fields.Monetary('Tipping Driver', readonly=True, related='tour_id.tipping_driver')
    total_tipping = fields.Monetary('Total Tipping', readonly=True, default=0, compute='_compute_total_tipping')

    @api.depends('tour_id')
    @api.onchange('tour_id')
    def _compute_total_tipping(self):
        self.total_tipping = (self.tour_id.tipping_guide * self.tour_id.guiding_days) + (
                    self.tour_id.tipping_tour_leader * self.tour_id.duration) + (
                    self.tour_id.tipping_driver * self.tour_id.driving_times)

    @api.depends('porter_ids')
    @api.onchange('porter_ids')
    def _compute_total_porter_cost(self):
        tot = 0
        for rec in self.porter_ids:
            tot += rec.rupiah_porter_cost
        self.total_porter_cost = tot

    @api.depends('passport_wallet', 'passport_cover', 'luggage_tag', 'pen', 'souvenir', 'travel_bag', 'snack',
                 'extra_ids')
    @api.onchange('passport_wallet', 'passport_cover', 'luggage_tag', 'pen', 'souvenir', 'travel_bag', 'snack',
                  'extra_ids')
    def _compute_total_merchandise(self):
        tot = self.passport_wallet + self.passport_cover + self.luggage_tag + self.pen + self.souvenir + self.travel_bag + self.snack
        self.total_merchandise = tot

    @api.depends('rupiah_tour_leader_fee', 'rupiah_ticket_for_tour_leader', 'land_tour_for_tour_leader', 'rupiah_single_supp_for_tour_leader',
                 'visa_for_tour_leader', 'airport_tax_for_tour_leader', 'rupiah_expense_for_tour_leader',
                 'rupiah_insurance_for_tour_leader_cost', 'travel_allowance')
    @api.onchange('rupiah_tour_leader_fee', 'rupiah_ticket_for_tour_leader', 'land_tour_for_tour_leader', 'rupiah_single_supp_for_tour_leader',
                  'visa_for_tour_leader', 'airport_tax_for_tour_leader', 'rupiah_expense_for_tour_leader',
                  'rupiah_insurance_for_tour_leader_cost', 'travel_allowance')
    def _compute_total_variable_cost(self):
        tot = self.rupiah_tour_leader_fee + self.rupiah_ticket_for_tour_leader + self.land_tour_for_tour_leader + self.rupiah_single_supp_for_tour_leader + self.visa_for_tour_leader + self.airport_tax_for_tour_leader + self.rupiah_expense_for_tour_leader + self.rupiah_insurance_for_tour_leader_cost + self.travel_allowance
        self.total_variable_cost = tot

    @api.depends('total_variable_cost', 'pax_amount')
    @api.onchange('total_variable_cost', 'pax_amount')
    def _compute_based_on_pax(self):
        if self.total_variable_cost > 0 and self.pax_amount > 0:
            self.based_on_pax = self.total_variable_cost / self.pax_amount
        else:
            self.based_on_pax = 0

    @api.depends('extra_ids')
    @api.onchange('extra_ids')
    def _compute_total_extra_cost(self):
        tot = 0
        for rec in self.extra_ids:
            tot += rec.rupiah_extra_cost
        self.total_extra_cost = tot

    @api.depends('rupiah_international_flight', 'rupiah_domestic_flight', 'rupiah_train_cost', 'rupiah_land_package',
                 'rupiah_insurance_cost', 'total_porter_cost', 'total_extra_cost', 'total_merchandise', 'based_on_pax')
    @api.onchange('rupiah_international_flight', 'rupiah_domestic_flight', 'rupiah_train_cost', 'rupiah_land_package',
                  'rupiah_insurance_cost', 'total_porter_cost', 'total_extra_cost', 'total_merchandise', 'based_on_pax')
    def _compute_total_exclude(self):
        self.total_exclude = self.rupiah_international_flight + self.rupiah_domestic_flight + self.rupiah_train_cost + \
                             self.rupiah_land_package + self.rupiah_insurance_cost + self.total_porter_cost + \
                             self.total_extra_cost + self.total_merchandise + self.based_on_pax

    @api.depends('total_exclude', 'service_charge', 'pax_type')
    @api.onchange('total_exclude', 'service_charge', 'pax_type')
    def _compute_retail_price_exclude(self):
        if self.pax_type != 'inf':
            self.retail_price_exclude = self.total_exclude + self.service_charge
        else:
            self.retail_price_exclude = self.total_exclude

    @api.depends('retail_price_exclude', 'total_tipping', 'tour_id', 'visa', 'pax_type')
    @api.onchange('retail_price_exclude', 'total_tipping', 'tour_id', 'visa', 'pax_type')
    def _compute_retail_price_include(self):
        if self.pax_type != 'inf':
            self.retail_price_include = self.retail_price_exclude + self.total_tipping + self.tour_id.airport_tax + self.visa
        else:
            self.retail_price_include = self.retail_price_exclude

    @api.depends('international_flight', 'international_flight_rate')
    @api.onchange('international_flight', 'international_flight_rate')
    def _compute_rupiah_international_flight(self):
        self.rupiah_international_flight = self.international_flight * self.international_flight_rate

    @api.depends('domestic_flight', 'domestic_flight_rate')
    @api.onchange('domestic_flight', 'domestic_flight_rate')
    def _compute_rupiah_domestic_flight(self):
        self.rupiah_domestic_flight = self.domestic_flight * self.domestic_flight_rate

    @api.depends('train_cost', 'train_rate')
    @api.onchange('train_cost', 'train_rate')
    def _compute_rupiah_train_cost(self):
        self.rupiah_train_cost = self.train_cost * self.train_rate

    @api.depends('land_package', 'land_package_rate')
    @api.onchange('land_package', 'land_package_rate')
    def _compute_rupiah_land_package(self):
        self.rupiah_land_package = self.land_package * self.land_package_rate

    @api.depends('insurance_cost', 'insurance_rate')
    @api.onchange('insurance_cost', 'insurance_rate')
    def _compute_rupiah_insurance_cost(self):
        self.rupiah_insurance_cost = self.insurance_cost * self.insurance_rate

    @api.depends('tour_leader_fee', 'tour_leader_fee_rate', 'tour_leader_fee_days')
    @api.onchange('tour_leader_fee', 'tour_leader_fee_rate', 'tour_leader_fee_days')
    def _compute_rupiah_tour_leader_fee(self):
        self.rupiah_tour_leader_fee = self.tour_leader_fee * self.tour_leader_fee_rate * self.tour_leader_fee_days

    @api.depends('ticket_for_tour_leader', 'ticket_for_tour_leader_rate', 'ticket_for_tour_leader_days')
    @api.onchange('ticket_for_tour_leader', 'ticket_for_tour_leader_rate', 'ticket_for_tour_leader_days')
    def _compute_rupiah_ticket_for_tour_leader(self):
        self.rupiah_ticket_for_tour_leader = self.ticket_for_tour_leader * self.ticket_for_tour_leader_rate * self.ticket_for_tour_leader_days

    @api.depends('single_supp_for_tour_leader', 'single_supp_for_tour_leader_rate')
    @api.onchange('single_supp_for_tour_leader', 'single_supp_for_tour_leader_rate')
    def _compute_rupiah_single_supp_for_tour_leader(self):
        self.rupiah_single_supp_for_tour_leader = self.single_supp_for_tour_leader * self.single_supp_for_tour_leader_rate

    @api.depends('expense_for_tour_leader', 'expense_for_tour_leader_rate', 'expense_for_tour_leader_days')
    @api.onchange('expense_for_tour_leader', 'expense_for_tour_leader_rate', 'expense_for_tour_leader_days')
    def _compute_rupiah_expense_for_tour_leader(self):
        self.rupiah_expense_for_tour_leader = self.expense_for_tour_leader * self.expense_for_tour_leader_rate * self.expense_for_tour_leader_days

    @api.depends('insurance_for_tour_leader_cost', 'insurance_for_tour_leader_rate')
    @api.onchange('insurance_for_tour_leader_cost', 'insurance_for_tour_leader_rate')
    def _compute_rupiah_insurance_for_tour_leader_cost(self):
        self.rupiah_insurance_for_tour_leader_cost = self.insurance_for_tour_leader_cost * self.insurance_for_tour_leader_rate

    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.confirm_uid = self.env.user.id
            rec.confirm_date = fields.Datetime.now()

    @api.multi
    def action_validate(self):
        for rec in self:
            rec.state = 'validate'
            rec.validate_uid = self.env.user.id
            rec.validate_date = fields.Datetime.now()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            rec.cancel_uid = self.env.user.id
            rec.cancel_date = fields.Datetime.now()

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_duplicate(self):
        res = self.copy()
        if not res.tour_id:
            res.update({
                'tour_id': self.tour_id,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class TourQuotationExtra(models.Model):
    _name = 'tt.master.tour.quotation.extra'
    _description = 'Master Tour Quotation Extra'

    tour_quotation_id = fields.Many2one('tt.master.tour.quotation', 'Tour Quotation')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    description = fields.Text('Description')

    extra_cost = fields.Integer('Cost', default=0)
    extra_currency = fields.Char('Currency')
    extra_rate = fields.Monetary('Exchange Rate', default=1)
    extra_type = fields.Selection(EXTRA_TYPE, 'Type')
    rupiah_extra_cost = fields.Monetary('Cost (Rupiah)', readonly=True, default=0, compute='_compute_rupiah_extra_cost')
    extra_days = fields.Integer('Days', default=1)

    @api.depends('extra_cost', 'extra_rate', 'extra_days')
    @api.onchange('extra_cost', 'extra_rate', 'extra_days')
    def _compute_rupiah_extra_cost(self):
        self.rupiah_extra_cost = self.extra_cost * self.extra_rate * self.extra_days


class TourQuotationPorter(models.Model):
    _name = 'tt.master.tour.quotation.porter'
    _description = 'Master Tour Quotation Porter'

    tour_quotation_id = fields.Many2one('tt.master.tour.quotation', 'Tour Quotation')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    porter_cost = fields.Monetary('Porter Cost', default=0)
    porter_currency = fields.Char('Porter Currency')
    porter_rate = fields.Monetary('Porter Rate', default=1)
    rupiah_porter_cost = fields.Monetary('Rupiah Porter Cost', readonly=True, default=0, compute='_compute_rupiah_porter_cost')
    porter_days = fields.Integer('Porter Days', default=1)

    @api.depends('porter_cost', 'porter_rate', 'porter_days')
    @api.onchange('porter_cost', 'porter_rate', 'porter_days')
    def _compute_rupiah_porter_cost(self):
        self.rupiah_porter_cost = self.porter_cost * self.porter_rate * self.porter_days
