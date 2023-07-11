from odoo import api, fields, models, _
import json,copy
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from ...tools import ERR
from ...tools.api import Response
import traceback, logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class TtCheckSegmentWizard(models.TransientModel):
    _name = "tt.check.segment.wizard"
    _description = "Check Segment Wizard"

    departure_start = fields.Datetime('Departure Date Start', required=True)
    departure_end = fields.Datetime('Departure Date End')
    all_ongoing_flights = fields.Boolean('All Ongoing Flights', default=True)
    is_booked = fields.Boolean('Booked Status', default=False)
    is_issued = fields.Boolean('Issued Status', default=True)
    is_expired = fields.Boolean('Expired Status', default=True)
    provider_text = fields.Char('Provider List', help='Separate by comma', default='amadeus')
    provider_ids = fields.One2many('tt.provider.pnr.wizard', 'check_id')

    def get_all_reservation_records(self):
        self.ensure_one()
        self.name = "Check Segment Wizard"

        state_list = []
        if self.is_booked:
            state_list.append('booked')
        if self.is_issued:
            state_list.append('issued')
        if self.is_expired:
            state_list.append('cancel')
            state_list.append('cancel2')

        inp_provider_list = []
        provider_text_list = self.provider_text.split(',')
        for rec in provider_text_list:
            inp_provider_list.append(rec.strip())

        params = [
            ('departure_date', '>=', self.departure_start),
        ]
        if not self.all_ongoing_flights:
            params.append(('departure_date', '<=', self.departure_end))

        pnr_list = []
        provider_ids = []
        objs = self.env['tt.segment.airline'].search(params)
        for obj in objs:
            if not obj.journey_id:
                continue

            journey_obj = obj.journey_id
            if not journey_obj.provider_booking_id:
                continue

            provider_obj = journey_obj.provider_booking_id
            if provider_obj.state not in state_list:
                continue
            pnr = provider_obj.pnr
            pnr2 = provider_obj.pnr2
            reference = provider_obj.reference
            if not pnr:
                continue
            if pnr in pnr_list:
                continue
            pnr_list.append(pnr)
            provider = provider_obj.provider_id.code if provider_obj.provider_id else ''
            if not provider:
                continue
            if provider not in inp_provider_list:
                continue

            if not pnr2:
                pnr2 = pnr
            if not reference:
                reference = pnr

            departure_date_list = []
            for j in provider_obj.journey_ids:
                for s in j.segment_ids:
                    if not s.departure_date:
                        continue
                    departure_date_list.append(s.departure_date)

            departure_date_text = '; '.join(departure_date_list)

            order_number = provider_obj.booking_id.name if provider_obj.booking_id else ''
            vals = {
                'pnr': pnr,
                'pnr2': pnr2,
                'reference': reference,
                'order_number': order_number,
                'provider': provider,
                'state': provider_obj.state,
                'departure_date_text': departure_date_text,
                'provider_id': provider_obj.id,
            }
            provider_ids.append((0, 0, vals))

        self.provider_ids.unlink()
        self.update({
            'provider_ids': provider_ids
        })
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tt.check.segment.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def do_sync_reservation(self):
        if not self.provider_ids:
            raise UserError('Please Get Reservation First')

        for rec in self.provider_ids:
            try:
                provider_obj = rec.provider_id
                provider_obj.action_check_segment_provider()
            except:
                _logger.error('Error Action Check Segment Provider, %s' % traceback.format_exc())


class TtProviderPnrWizard(models.TransientModel):
    _name = "tt.provider.pnr.wizard"
    _description = "Provider PNR Wizard"

    order_number = fields.Char('Order Number')
    pnr = fields.Char('PNR')
    pnr2 = fields.Char('PNR2')
    provider = fields.Char('Provider')
    reference = fields.Char('Reference')
    departure_date_text = fields.Char('Departure Date List')
    state = fields.Char('State')
    check_id = fields.Many2one('tt.check.segment.wizard')
    provider_id = fields.Many2one('tt.provider.airline', 'Provider')
