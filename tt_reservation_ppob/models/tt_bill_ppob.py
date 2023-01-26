from odoo import api, fields, models, _
from ...tools import variables
import json
from datetime import datetime


class TtBillPPOB(models.Model):
    _name = 'tt.bill.ppob'
    _rec_name = 'description'
    _order = 'period'
    _description = 'Bill PPOB'

    provider_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.ppob', 'Order Number', related='provider_booking_id.booking_id', store=True)
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)

    sequence = fields.Integer('Sequence')

    period = fields.Date('Period')
    description = fields.Char('Description')
    amount_of_month = fields.Integer('Amount of Months', default=1)
    period_end_date = fields.Date('Period End Date')
    meter_read_date = fields.Date('Meter Read Date')
    meter_history_ids = fields.One2many('tt.ppob.meter.history', 'bill_ppob_id', 'Meter History')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    admin_fee = fields.Monetary('Admin Fee', default=0)
    admin_fee_switcher = fields.Monetary('Admin Fee Switcher', default=0)
    stamp_fee = fields.Monetary('Stamp Fee', default=0)
    ppn_tax_amount = fields.Monetary('PPN', default=0)
    ppj_tax_amount = fields.Monetary('PPJ', default=0)
    incentive = fields.Monetary('Incentive', default=0)
    fare_amount = fields.Monetary('Fare Amount (for Electricity)', default=0)
    fine_amount = fields.Monetary('Fine Amount', default=0)
    installment = fields.Monetary('Installment Amount', default=0)
    kwh_amount = fields.Float('KWH Amount Upon Payment', default=0)
    total = fields.Monetary('Total', readonly=True, default=0)
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
            'description': self.description and self.description or '',
            'amount_of_month': self.amount_of_month and self.amount_of_month or 1,
            'period_end_date': self.period_end_date and self.period_end_date.strftime('%Y-%m-%d') or '',
            'meter_read_date': self.meter_read_date and self.meter_read_date.strftime('%Y-%m-%d') or '',
            'meter_history': history_list,
            'currency': self.currency_id and self.currency_id.name or '',
            'admin_fee': self.admin_fee and self.admin_fee or 0,
            'admin_fee_switcher': self.admin_fee_switcher and self.admin_fee_switcher or 0,
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
    _order = 'sequence'
    _description = 'PPOB Meter History'

    before_meter = fields.Integer('Before Meter')
    after_meter = fields.Integer('After Meter')
    name = fields.Char('Name', compute='_fill_name')
    sequence = fields.Integer('Sequence')
    bill_ppob_id = fields.Many2one('tt.bill.ppob', 'PPOB Bill', ondelete='cascade')

    @api.multi
    @api.depends('before_meter', 'after_meter')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (str(rec.before_meter), str(rec.after_meter))


class TtBillDetailPPOB(models.Model):
    _name = 'tt.bill.detail.ppob'
    _rec_name = 'customer_number'
    _description = 'Bill Detail PPOB'

    provider_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.ppob', 'Order Number', related='provider_booking_id.booking_id', store=True)
    customer_number = fields.Char('Customer Number', readonly=True)
    customer_name = fields.Char('Customer Name', readonly=True)
    unit_code = fields.Char('Unit Code', readonly=True)
    unit_name = fields.Char('Unit Name', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id, string='Currency')
    total = fields.Monetary('Total', readonly=True, default=0)

    def to_dict(self):
        res = {
            'customer_number': self.customer_number and self.customer_number or '',
            'customer_name': self.customer_name and self.customer_name or '',
            'unit_code': self.unit_code and self.unit_code or '',
            'unit_name': self.unit_name and self.unit_name or '',
            'currency': self.currency_id and self.currency_id.name or '',
            'total': self.total and self.total or 0,
        }
        return res
