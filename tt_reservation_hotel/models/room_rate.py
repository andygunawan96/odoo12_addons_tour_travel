from odoo import api, fields, models, _


class RoomRate(models.Model):
    _name = 'tt.room.rate'
    _description = 'Room Price per Night or Day(s)'

    room_info_id = fields.Many2one('tt.room.info', 'Room Info')
    spc_room_info_id = fields.Many2one('tt.room.info', 'Special Room Info')
    # date = fields.Date('Date')
    day = fields.Selection([
        (7, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ], 'Day', default=1)
    start_date = fields.Date('Start Date', default='')
    end_date = fields.Date('End Date', default='')
    nationality = fields.Selection([
        ('all', 'All'),
        ('wni', 'WNI'),
        ('wna', 'WNA'),
    ], 'Nationality', default='all')

    nta_price = fields.Monetary('NTA Price', default=0)
    cost_price = fields.Monetary('Channel Price', compute='_calc_cost_price')
    # sale_price = fields.Monetary('Sale Price', default=0)
    sale_price = fields.Monetary('Sale Price', compute='_calc_sale_price')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    availability = fields.Integer('Total Available Room')
    sequence = fields.Integer('Sequence')
    is_promo = fields.Boolean('Is Promo', default=False)
    active = fields.Boolean('Active', default=True)
    # MG Meal Type, digunakan untuk issued MG
    meal_type = fields.Char('Meal Type')
    cancel_policy = fields.Many2one('cancellation.policy','Cancel Policy', default=lambda self: self.env.ref('tt_reservation_hotel.hotel_no_refund_policy'))

    apply_on_sunday = fields.Boolean('Apply on Sunday', default=True)
    apply_on_monday = fields.Boolean('Apply on Monday', default=True)
    apply_on_tuesday = fields.Boolean('Apply on Tuesday', default=True)
    apply_on_wednesday = fields.Boolean('Apply on wednesday', default=True)
    apply_on_thursday = fields.Boolean('Apply on Thursday', default=True)
    apply_on_friday = fields.Boolean('Apply on Friday', default=True)
    apply_on_saturday = fields.Boolean('Apply on Saturday', default=True)

    @api.multi
    def _calc_cost_price(self):
        for my in self:
            my_room = my.room_info_id or my.spc_room_info_id
            charge_rule_id = self.env['tt.service.charge'].get_default_charge_rule(my_room)
            if not charge_rule_id:
                charge_rule_id = self.env['tt.service.charge'].get_default_charge_rule_partner(
                    my_room.hotel_id.hotel_partner_id)
            if not charge_rule_id:
                charge_rule_id = self.env['tt.service.charge'].get_provider_increment_charge_rule1(my_room.hotel_id.provider)
            if charge_rule_id:
                charge_rule_obj = self.env['tt.service.charge'].browse(charge_rule_id)
                my.sale_rule_id = charge_rule_obj.id
                my.cost_price = my.nta_price + charge_rule_obj.count_sale_nominal(my.nta_price)


    @api.multi
    def _calc_sale_price(self):
        for my in self:
            my_room = my.room_info_id or my.spc_room_info_id
            charge_rule_id = self.env['tt.service.charge'].get_default_charge_rule_2(my_room)
            if not charge_rule_id:
                charge_rule_id = self.env['tt.service.charge'].get_default_charge_rule_partner2(
                    my_room.hotel_id.hotel_partner_id)
            if not charge_rule_id:
                charge_rule_id = self.env['tt.service.charge'].get_provider_increment_charge_rule2(my_room.hotel_id.provider)
            if charge_rule_id:
                charge_rule_obj = self.env['tt.service.charge'].browse(charge_rule_id)
                my.sale_rule_id = charge_rule_obj.id
                my.sale_price = my.cost_price + charge_rule_obj.count_sale_nominal(my.cost_price)

    @api.onchange('nta_price')
    def calc_price(self):
        self._calc_cost_price()
        self._calc_sale_price()


class RoomInfo(models.Model):
    _inherit = 'tt.room.info'

    room_rate_ids = fields.One2many('tt.room.rate', 'room_info_id', 'Room Rate')
    spc_room_rate_ids = fields.One2many('tt.room.rate', 'spc_room_info_id', 'Special Room Rate')