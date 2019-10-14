from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime


class TtProviderVisa(models.Model):
    _name = 'tt.provider.visa'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider', 'Provider')
    booking_id = fields.Many2one('tt.reservation.visa', 'Order Number', ondelete='cascade')
    visa_id = fields.Many2one('tt.reservation.visa.pricelist', 'Tour')
    state = fields.Selection(variables.BOOKING_STATE, 'Status', default='draft')
    cost_service_charge_ids = fields.One2many('tt.service.charge', 'provider_visa_booking_id', 'Cost Service Charges')

    country_id = fields.Many2one('res.country', 'Country', ondelete="cascade", readonly=True,
                                 states={'draft': [('readonly', False)]})
    departure_date = fields.Char('Journey Date', readonly=True, states={'draft': [('readonly', False)]})

    use_vendor = fields.Boolean('Use Vendor', readonly=True, default=False)

    confirmed_date = fields.Datetime('Confirmed Date', readonly=1)
    confirmed_uid = fields.Many2one('res.users', 'Confirmed By', readonly=1)

    validate_date = fields.Datetime('Validate Date', readonly=1)
    validate_uid = fields.Many2one('res.users', 'Validate By', readonly=1)

    to_vendor_date = fields.Datetime('Send To Vendor Date', readonly=1)
    vendor_process_date = fields.Datetime('Vendor Process Date', readonly=1)
    in_process_date = fields.Datetime('In Process Date', readonly=1)

    done_date = fields.Datetime('Done Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    expired_date = fields.Datetime('Expired Date', readonly=True)

    is_ledger_created = fields.Boolean('Ledger Created', default=False, readonly=True,
                                       states={'draft': [('readonly', False)]})

    vendor_ids = fields.One2many('tt.reservation.visa.vendor.lines', 'provider_id', 'Sub-Vendor')

    passenger_ids = fields.One2many('tt.provider.visa.passengers', 'provider_id', 'Passengers')


class TtTicketActivity(models.Model):
    _name = 'tt.provider.visa.passengers'
    _description = 'Rodex Model'

    provider_id = fields.Many2one('tt.provider.visa', 'Provider')
    passenger_id = fields.Many2one('tt.reservation.visa.order.passenger', 'Passenger')
    pax_type = fields.Selection(variables.PAX_TYPE, 'Pax Type')
