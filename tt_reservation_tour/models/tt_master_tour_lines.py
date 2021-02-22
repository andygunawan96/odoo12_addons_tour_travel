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
        if self.state == 'draft':
            self.state = 'open'
            if not self.tour_line_code:
                self.tour_line_code = self.env['ir.sequence'].next_by_code('master.tour.line.code')

    def action_closed(self):
        self.state = 'on_going'

    def action_definite(self):
        self.state = 'definite'

    def action_cancel(self):
        self.state = 'cancel'

    def set_to_draft(self):
        self.state = 'draft'

    def action_done(self):
        self.state = 'done'

    def action_sold(self):
        self.state = 'sold'

    def action_reopen(self):
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

        if self.master_tour_id.tour_type == 'open':
            special_dates = []
            for rec in self.special_dates_ids:
                special_dates.append(rec.to_dict())
            res_dict.update({
                'special_date_list': special_dates
            })
        return res_dict
