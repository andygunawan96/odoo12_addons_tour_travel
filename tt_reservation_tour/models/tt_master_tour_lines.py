from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError
import logging, traceback

_logger = logging.getLogger(__name__)


class MasterTourLines(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.tour.lines'
    _description = 'Master Tour Lines'
    _order = 'sequence'

    name = fields.Char('Name', readonly=True, compute='_compute_name')
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('definite', 'Definite'), ('sold', 'Sold Out'),
                              ('on_going', 'On Going'), ('done', 'Done'), ('closed', 'Closed'),
                              ('cancel', 'Canceled')],
                             'State', copy=False, default='draft', help="draft = tidak tampil di front end"
                                                                        "definite = pasti berangkat"
                                                                        "done = sudah pulang"
                                                                        "closed = sisa uang sdh masuk ke HO"
                                                                        "cancelled = tidak jadi berangkat")
    tour_line_code = fields.Char('Tour Line Code', readonly=True, copy=False)
    departure_date = fields.Date('Departure Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    arrival_date = fields.Date('Arrival Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    seat = fields.Integer('Seat Available', required=True, default=1, readonly=True, states={'draft': [('readonly', False)]})
    quota = fields.Integer('Quota', required=True, default=1, readonly=True, states={'draft': [('readonly', False)]})
    sequence = fields.Integer('Sequence', default=3, required=True, readonly=True, states={'draft': [('readonly', False)]})
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True, related='master_tour_id.provider_id', store=True)
    special_dates_ids = fields.One2many('tt.master.tour.special.dates', 'tour_line_id', 'Special Dates', readonly=True, states={'draft': [('readonly', False)]})
    down_payment = fields.Float('Down Payment (%)', default=100)
    payment_rules_ids = fields.One2many('tt.payment.rules', 'tour_lines_id')
    master_tour_id = fields.Many2one('tt.master.tour', 'Master Tour', readonly=True)
    is_restrict_monday = fields.Boolean('Restrict Monday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_tuesday = fields.Boolean('Restrict Tuesday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_wednesday = fields.Boolean('Restrict Wednesday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_thursday = fields.Boolean('Restrict Thursday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_friday = fields.Boolean('Restrict Friday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_saturday = fields.Boolean('Restrict Saturday', readonly=True, states={'draft': [('readonly', False)]})
    is_restrict_sunday = fields.Boolean('Restrict Sunday', readonly=True, states={'draft': [('readonly', False)]})
    active = fields.Boolean('Active', default=True)

    @api.multi
    def write(self, vals):
        if vals.get('down_payment'):
            total_percent = 0
            for rec in self.payment_rules_ids:
                total_percent += rec.payment_percentage
            if total_percent + vals['down_payment'] > 100.00:
                raise UserError(_('Total Installments and Down Payment cannot be more than 100%. Please re-adjust your Installment Payment Rules!'))
        return super(MasterTourLines, self).write(vals)

    @api.depends('departure_date', 'arrival_date')
    @api.onchange('departure_date', 'arrival_date')
    def _compute_name(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                rec.name = rec.departure_date.strftime('%d %b %Y') + ' - ' + rec.arrival_date.strftime('%d %b %Y')

    @api.onchange('payment_rules_ids')
    def _calc_dp(self):
        dp = 100
        for rec in self:
            for pp in rec.payment_rules_ids:
                dp -= pp.payment_percentage
            rec.dp = dp

    def action_validate(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 299')
        if self.state == 'draft':
            self.state = 'open'
            if not self.tour_line_code:
                self.tour_line_code = self.env['ir.sequence'].next_by_code('master.tour.line.code')

    def action_closed(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 300')
        self.state = 'closed'

    def action_definite(self):
        self.state = 'definite'

    def action_on_going(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 301')
        self.state = 'on_going'

    def action_cancel(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 302')
        self.state = 'cancel'

    def set_to_draft(self):
        self.state = 'draft'

    def action_done(self):
        self.state = 'done'

    def action_sold(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 303')
        self.state = 'sold'

    def action_reopen(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 304')
        self.state = 'open'

    def book_line_quota(self, pax_amount):
        temp_seat = self.seat
        temp_seat -= pax_amount  # seat tersisa dikurangi jumlah orang yang di book
        temp_state = ''
        if temp_seat < 0:
            temp_seat = 0
        elif temp_seat == 0:
            temp_state = 'sold'  # kuota habis
        elif temp_seat <= int(0.2 * self.quota):
            temp_state = 'definite'  # pasti berangkat jika kuota >=80%
        else:
            temp_state = 'open'

        write_vals = {
            'seat': temp_seat
        }
        if temp_state:
            write_vals.update({
                'state': temp_state
            })
        self.write(write_vals)

    def cancel_book_line_quota(self, pax_amount):
        temp_seat = self.seat
        temp_seat += pax_amount
        temp_state = ''
        if temp_seat > self.quota:
            temp_seat = self.quota
        elif temp_seat == 0:
            temp_state = 'sold'  # kuota habis
        elif temp_seat <= int(0.2 * self.quota):
            temp_state = 'definite'  # pasti berangkat jika kuota >=80%
        else:
            temp_state = 'open'

        write_vals = {
            'seat': temp_seat
        }
        if temp_state:
            write_vals.update({
                'state': temp_state
            })
        self.write(write_vals)

    def get_restricted_days(self, mode=''):
        restricted_days = []
        if mode == 'index':
            if self.is_restrict_monday:
                restricted_days.append('1')
            if self.is_restrict_tuesday:
                restricted_days.append('2')
            if self.is_restrict_wednesday:
                restricted_days.append('3')
            if self.is_restrict_thursday:
                restricted_days.append('4')
            if self.is_restrict_friday:
                restricted_days.append('5')
            if self.is_restrict_saturday:
                restricted_days.append('6')
            if self.is_restrict_sunday:
                restricted_days.append('7')
        else:
            if self.is_restrict_monday:
                restricted_days.append('Monday')
            if self.is_restrict_tuesday:
                restricted_days.append('Tuesday')
            if self.is_restrict_wednesday:
                restricted_days.append('Wednesday')
            if self.is_restrict_thursday:
                restricted_days.append('Thursday')
            if self.is_restrict_friday:
                restricted_days.append('Friday')
            if self.is_restrict_saturday:
                restricted_days.append('Saturday')
            if self.is_restrict_sunday:
                restricted_days.append('Sunday')
        return restricted_days

    def to_dict(self):
        res_dict = {
            'tour_line_code': self.tour_line_code,
            'departure_date': self.departure_date.strftime("%Y-%m-%d"),
            'arrival_date': self.arrival_date.strftime("%Y-%m-%d"),
            'seat': self.seat,
            'quota': self.quota,
            'down_payment': self.down_payment,
            'state': self.state,
            'state_str': dict(self._fields['state'].selection).get(self.state),
            'sequence': self.sequence
        }
        payment_rules = []
        for rec in self.payment_rules_ids:
            payment_rules.append({
                'name': rec.name,
                'payment_percentage': rec.payment_percentage,
                'description': rec.description,
                'due_date': rec.due_date,
            })
        res_dict.update({
            'payment_rules_list': payment_rules
        })

        if self.master_tour_id.tour_type_id.is_open_date:
            special_dates = []
            for rec in self.special_dates_ids:
                special_dates.append(rec.to_dict())

            res_dict.update({
                'special_date_list': special_dates,
                'restricted_days_idx': self.get_restricted_days('index')
            })
        return res_dict
