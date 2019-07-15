from odoo import api, fields, models, _
from ...tools import test_to_dict

PAX_TYPE = [
    ('YCD', 'Elder'),
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]


class TbServiceCharge(models.Model, test_to_dict.ToDict):
    _name = 'tt.service.charge'

    #fixme inherit 1 nanti
    # provider_booking_id = fields.Many2one('tt.tb.provider', 'Provider Booking ID')

    charge_code = fields.Char('Charge Code', default='fare', required=True)
    charge_type = fields.Char('Charge Type')  # FARE, INF, TAX, SSR, CHR
    pax_type = fields.Selection(PAX_TYPE, string='Pax Type')
    # total asumsi dari api sudah dengan harga total
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pax_count = fields.Integer('Pax Count', default=1)
    amount = fields.Monetary('Amount', currency_field='currency_id')
    total = fields.Float('Total', compute='_compute_total', store=False, readonly=True)
    foreign_currency_id = fields.Many2one('res.currency', 'Foreign Currency',
                                          default=lambda self: self.env.user.company_id.currency_id)
    foreign_amount = fields.Monetary('Foreign Amount', currency_field='foreign_currency_id')

    sequence = fields.Integer('Sequence')
    description = fields.Text('Description')

    pax_disc_code = fields.Char('Pax Disc. Code')
    fare_disc_code = fields.Char('Fare Disc. Code')
    commision_agent_id = fields.Many2one('tt.agent', 'Agent ( Commission )', help='''Agent who get commision''')

    #fixme inherit 1 nanti
    # segment_id = fields.Many2one('tt.tb.segment', 'Segment', ondelete='cascade', index=True, copy=False)
    # booking_id = fields.Many2one('tt.transport.booking', 'Booking', ondelete='cascade', index=True, copy=False)

    @api.one
    @api.depends('pax_count', 'amount')
    def _compute_total(self):
        self.total = self.pax_count * self.amount