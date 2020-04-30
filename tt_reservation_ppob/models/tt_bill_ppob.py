from odoo import api, fields, models, _
from ...tools import variables
import json
from datetime import datetime


class TtBillPPOB(models.Model):
    _name = 'tt.bill.ppob'
    _rec_name = 'period'
    _order = 'sequence'
    _description = 'Rodex Model'

    provider_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)

    booking_id = fields.Many2one('tt.reservation.ppob', 'Order Number', related='provider_booking_id.booking_id', store=True)
    sequence = fields.Integer('Sequence')

    period = fields.Date('Period')
    amount_of_month = fields.Integer('Amount of Months', default=0)
    period_end_date = fields.Date('Period End Date')
    meter_read_date = fields.Date('Meter Read Date')
    meter_history_ids = fields.One2many('tt.ppob.meter.history', 'bill_ppob_id', 'Meter History')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    admin_fee = fields.Monetary('Admin Fee', default=0)
    stamp_fee = fields.Monetary('Stamp Fee', default=0)
    ppn_tax_amount = fields.Monetary('PPN', default=0)
    ppj_tax_amount = fields.Monetary('PPJ', default=0)
    incentive = fields.Monetary('Incentive', default=0)
    fare_amount = fields.Monetary('Fare Amount (for Electricity)', default=0)
    fine_amount = fields.Monetary('Fine Amount', default=0)
    kwh_amount = fields.Integer('KWH Amount Upon Payment', default=0)
    installment = fields.Integer('Installment Amount', default=0)
    total = fields.Integer('Total', readonly=True, default=0)
    token = fields.Char('Token Number')

    def to_dict(self):
        history_list = []
        for rec in self.meter_history_ids:
            history_list.append({
                'before_meter': rec.before_meter,
                'after_meter': rec.after_meter
            })
        res = {
            'pnr': self.pnr and self.pnr or '',
            'provider': self.provider_id and self.provider_id.code or '',
            'sequence': self.sequence and self.sequence or 0,
            'period': self.period and self.period.strftime('%Y%m') or '',
            'amount_of_month': self.amount_of_month and self.amount_of_month or 0,
            'period_end_date': self.period_end_date and self.period_end_date.strftime('%Y-%m-%d') or '',
            'meter_read_date': self.meter_read_date and self.meter_read_date.strftime('%Y-%m-%d') or '',
            'meter_history': history_list,
            'currency': self.currency_id and self.currency_id.name or '',
            'admin_fee': self.admin_fee and self.admin_fee or 0,
            'stamp_fee': self.stamp_fee and self.stamp_fee or 0,
            'ppn_tax_amount': self.ppn_tax_amount and self.ppn_tax_amount or 0,
            'ppj_tax_amount': self.ppj_tax_amount and self.ppj_tax_amount or 0,
            'incentive': self.incentive and self.incentive or 0,
            'fare_amount': self.fare_amount and self.fare_amount or 0,
            'fine_amount': self.fine_amount and self.fine_amount or 0,
            'kwh_amount': self.kwh_amount and self.kwh_amount or 0,
            'installment': self.installment and self.installment or 0,
            'total': self.total and self.total or 0,
            'token': self.token and self.token or '',
        }
        return res


class TtPPOBMeterHistory(models.Model):
    _name = 'tt.ppob.meter.history'
    _description = 'Rodex Model'

    before_meter = fields.Integer('Before Meter')
    after_meter = fields.Integer('After Meter')
    name = fields.Char('Name', compute='_fill_name')
    bill_ppob_id = fields.Many2one('tt.bill.ppob', 'PPOB Bill', ondelete='cascade')

    @api.multi
    @api.depends('before_meter', 'after_meter')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (str(rec.before_meter), str(rec.after_meter))


class TtBillDetailPPOB(models.Model):
    _name = 'tt.bill.detail.ppob'
    _rec_name = 'customer_number'
    _description = 'Rodex Model'

    provider_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking', ondelete='cascade')
    customer_number = fields.Char('Customer Number', readonly=True, states={'draft': [('readonly', False)]})
    customer_name = fields.Char('Customer Name', readonly=True, states={'draft': [('readonly', False)]})
    unit_code = fields.Char('Unit Code', readonly=True, states={'draft': [('readonly', False)]})
    unit_name = fields.Char('Unit Name', readonly=True, states={'draft': [('readonly', False)]})
    total = fields.Integer('Total', readonly=True, default=0)
