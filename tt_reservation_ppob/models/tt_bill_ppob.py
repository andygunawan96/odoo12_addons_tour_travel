from odoo import api, fields, models, _
from ...tools import variables
import json
from datetime import datetime


class TtBillPPOB(models.Model):
    _name = 'tt.bill.ppob'
    _rec_name = 'carrier_name'
    _order = 'sequence'
    _description = 'Rodex Model'

    provider_booking_id = fields.Many2one('tt.provider.ppob', 'Provider Booking', ondelete='cascade')
    provider_id = fields.Many2one('tt.provider', related='provider_booking_id.provider_id', store=True)
    pnr = fields.Char('PNR', related='provider_booking_id.pnr', store=True)

    booking_id = fields.Many2one('tt.reservation.ppob', 'Order Number')
    carrier_id = fields.Many2one('tt.transport.carrier', 'Product')
    carrier_code = fields.Char('Product Code')
    carrier_name = fields.Char('Product Name')
    sequence = fields.Integer('Sequence')

    period = fields.Char('Period')
    amount_of_month = fields.Integer('Amount of Months')
    period_end_date = fields.Date('Period End Date')
    meter_read_date = fields.Date('Meter Read Date')
    meter_history_ids = fields.One2many('tt.ppob.meter.history', 'bill_ppob_id', 'Meter History')

    def to_dict(self):
        res = {
            'pnr': self.pnr,
            'carrier_name': self.carrier_id.name,
            'carrier_code': self.carrier_code,
            'provider': self.provider_id.code,
            'sequence': self.sequence,
        }
        return res


class TtPPOBMeterHistory(models.Model):
    _name = 'tt.ppob.meter.history'
    _rec_name = 'carrier_name'
    _description = 'Rodex Model'

    before_meter = fields.Integer('Before Meter')
    after_meter = fields.Integer('After Meter')
    name = fields.Char('Name', compute='_fill_name')
    bill_ppob_id = fields.Many2one('tt.bill.ppob', 'PPOB Bill')

    @api.multi
    @api.depends('before_meter', 'after_meter')
    def _fill_name(self):
        for rec in self:
            rec.name = "%s - %s" % (str(rec.before_meter), str(rec.after_meter))
