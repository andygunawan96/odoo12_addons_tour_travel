from odoo import api, fields, models, _


class ServiceCharge(models.Model):
    _name = 'tt.service.charge'
    _order = 'sequence, id'

    name = fields.Char('Name', default=True)
    # Used By
    provider = fields.Selection([
        ('cms', 'CMS'),
    ], 'Provider')
    hotel_id = fields.Many2one('tt.hotel', 'Hotel Info')
    room_info_id = fields.Many2one('tt.room.info', 'Room Info')
    facility_id = fields.Many2one('tt.hotel.facility', 'Type of Facility / Service', domain=[('is_paid', '=', True)])
    default_rule = fields.Boolean('Default Rule', default=False)
    # Price Calculation
    type = fields.Selection([
        ('fix', 'Fixed'),
        ('pct', 'Percent'),
    ], 'Type', default='fix')
    sale_nominal = fields.Float('Nominal', default=0, help='If type is Fix then its nominal or percentage')
    currency_id = fields.Many2one('res.currency', string="Currency")
    # qty = fields.Integer('')
    calculate_var = fields.Selection([
        ('once', 'Once per Reservation'),
        ('resv', 'Reservation Total'),
        ('room', 'Room'),
        ('cust', 'Customer'),
    ], 'Calculation Variable', default='resv', help='1. g peduli brpa lama nginep; 2. hitung total nominal sewa hotel sja;')
    # Maksimum Ambil
    max_qty = fields.Integer('Maximum Quantity', default=1)
    max_qty_multiple = fields.Selection([
        ('once', 'Once'),
        ('room', 'Room'),
        ('cust', 'Customer')], 'Max Qty Multiplier')
    is_fixed = fields.Boolean('Fixed Qty', default=False)
    # Others
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean('Active', default=True)
    charge_for = fields.Selection([
        ('all', 'For All Transaction'),
        ('provider', 'For a Partner'),
        ('hotel', 'For Hotel / Room'),
        ('other', 'For some Other options'),
    ], 'Charge for', required=True)
    rule_for = fields.Selection([
        ('all', 'All User'),
        ('agent', 'Agent'),
        ('end', 'End User'),
    ], 'Rule for', required=True, default='end')
    country_id = fields.Many2one('res.country', 'Country')
    city_id = fields.Many2one('res.city', 'City')
    partner_id = fields.Many2one('res.partner', 'Partner')

    @api.onchange('country_id')
    def onchange_hotel_id(self):
        res = {'domain': {'city_id': []}}
        if self.hotel_id:
            res['domain']['city_id'] = [('state_id.country_id', '=', self.country_id.id)]
            self.city_id = False
        return res

    @api.onchange('hotel_id')
    def onchange_hotel_id(self):
        res = {'domain': {'room_info_id': [], 'facility_id': []}}
        if self.hotel_id:
            res['domain']['room_info_id'] = [('hotel_id', '=', self.hotel_id.id)]
            res['domain']['facility_id'] = [('id', 'in', self.hotel_id.facility_ids.ids)]
            self.room_info_id = False
            self.facility_id = False
        return res

    @api.onchange('charge_for')
    def onchange_charge_for(self):
        self.default_rule = False
        self.provider = False
        self.hotel_id = False
        self.room_info_id = False
        self.facility_id = False

        if self.charge_for == 'all':
            self.default_rule = True

    # Rule yang nambah harga dipanggil seblum tampilkan harga ke website
    def get_default_increment_charge_rule(self):
        # charge ke provider
        # Contoh smua transaksi di + 10k
        rules = self.search([('provider', '=', False), ('hotel_id', '=', False), ('room_info_id', '=', False),
                             ('default_rule', '=', True), ('sale_nominal', '>', 0)], limit=1).ids
        return rules

    # Rule Tambah harga dari provider tidak ditampilkan ke website
    def get_provider_increment_charge_rule1(self, provider):
        return self.search([('rule_for', '=', 'agent'), ('provider', '=', provider), ('sale_nominal', '>=', 0)], limit=1).ids

    def get_agent_provider_charge_rule1(self, provider):
        return self.search([('rule_for', '=', 'agent'), ('provider', '=', provider)], limit=1).ids

    def get_provider_increment_charge_rule2(self, provider):
        return self.search([('rule_for', '=', 'end'), ('provider', '=', provider), ('sale_nominal', '>=', 0)], limit=1).ids

    # Rule Tambah harga khusus untuk Room Tertentu
    def get_room_increment_charge_rule(self, room_id):
        return self.search([('rule_for', '=', 'end'), ('room_info_id', '=', room_id), ('sale_nominal', '>=', 0)], limit=1).ids

    # Rule kurangin harga dari provider tidak ditampilkan ke website
    def get_provider_decrement_charge_rule(self, provider):
        return self.search([('rule_for', '=', 'end'), ('provider', '=', provider), ('sale_nominal', '<', 0)], limit=1).ids

    # Rule kurangin harga dari kita ditampilkan sebagai promo
    def get_default_decrement_charge_rule(self):
        return self.search([('provider', '=', False), ('hotel_id', '=', False), ('room_info_id', '=', False),
                            ('default_rule', '=', True), ('sale_nominal', '<', 0)], limit=1).ids

    # Rule fasilitas tambahan berdasarkan hotel
    def get_default_charge_rule(self, hotel_obj):
        rules = self.search([('rule_for', '=', 'agent'), ('hotel_id', '=', hotel_obj.id),
                             ('default_rule', '=', True)], limit=1).ids
        return rules
    def get_default_charge_rule_2(self, hotel_obj):
        rules = self.search([('rule_for', '=', 'end'), ('hotel_id', '=', hotel_obj.id),
                             ('default_rule', '=', True)], limit=1).ids
        return rules

    # Rule Tambah harga untuk provider tertentu yang digunakan untuk user agent saja / Cost_price
    def get_agent_provider_increment_charge_rule(self, provider):
        return self.search([('rule_for', '=', 'agent'), ('provider', '=', provider)], limit=1).ids

    # Rule fasilitas tambahan berdasarkan hotel
    def get_charge_rule(self, hotel_obj=False, room_obj=False):
        rules = self.search([('hotel_id', '=', hotel_obj.id), ('facility_id', '=', False)]).ids
        rules += self.search([('hotel_id', '=', hotel_obj.id), ('facility_id', '=', hotel_obj.facility_ids.ids)], limit=1).ids
        rules += self.search([('room_info_id', '=', room_obj.id), ('facility_id', '=', room_obj.facility_ids.ids)], limit=1).ids
        return rules

    def get_default_charge_rule_partner(self, partner_id):
        rules = self.search([('rule_for', '=', 'agent'), ('partner_id', '=', partner_id.id), ('default_rule', '=', True)], limit=1).ids
        return rules

    def get_default_charge_rule_partner2(self, partner_id):
        rules = self.search([('rule_for', '=', 'end'), ('partner_id', '=', partner_id.id), ('default_rule', '=', True)], limit=1).ids
        return rules

    @api.multi
    def search_rate_for_thisday(self, room_rate_id):
        list = self.get_default_increment_charge_rule()
        list += self.get_provider_increment_charge_rule2(room_rate_id.room_info_id.hotel_id.provider)
        list += self.get_provider_decrement_charge_rule(room_rate_id.room_info_id.hotel_id.provider)
        list += self.get_default_decrement_charge_rule()
        list += self.get_default_charge_rule(room_rate_id.room_info_id.hotel_id, room_rate_id.room_info_id)
        list += self.get_charge_rule(room_rate_id.room_info_id.hotel_id, room_rate_id.room_info_id)
        return list

    def count_sale_nominal(self, amount):
        if self.type == "fix":
            price = self.sale_nominal
        elif self.type == "pct":
            price = self.sale_nominal * amount / 100
        else:
            price = 0
        return price

    def count_max_qty(self, room, guest):
        return self.max_qty_multiple == 'once' and 1 or \
        self.max_qty_multiple == 'room' and self.max_qty * room or \
        self.max_qty_multiple == 'cust' and self.max_qty * guest or \
        self.max_qty

    def count_qty(self, room, guest):
        return not self.is_fixed and 0 or \
               self.calculate_var in ['once', 'resv'] and 1 or \
               self.calculate_var == 'room' and room or \
               self.calculate_var == 'cust' and guest

