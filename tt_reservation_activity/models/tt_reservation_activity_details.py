from odoo import api, fields, models, _
import re
import logging

_logger = logging.getLogger(__name__)


class ReservationActivityDetails(models.Model):
    _name = 'tt.reservation.activity.details'
    _description = 'Reservation Activity Details'

    activity_id = fields.Many2one('tt.master.activity', 'Activity')
    activity_product_id = fields.Many2one('tt.master.activity.lines', 'Activity Product')
    visit_date = fields.Datetime('Visit Date')
    timeslot = fields.Char('Timeslot')
    information = fields.Text('Additional Information')
    provider_booking_id = fields.Many2one('tt.provider.activity', 'Provider Booking', ondelete='cascade')
    booking_id = fields.Many2one('tt.reservation.activity', related='provider_booking_id.booking_id', string='Order Number', store=True)

    def cleanhtml(self, raw_html):
        if raw_html:
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', raw_html)
            return cleantext
        return ''

    def to_dict(self):
        image_urls = []
        if self.activity_id:
            for img in self.activity_id.image_ids:
                image_urls.append(str(img.photos_url) + str(img.photos_path))

        voucher_information = {
            'voucherUse': self.activity_product_id and self.cleanhtml(self.activity_product_id.voucherUse) or '',
            'voucher_validity_type': self.activity_product_id and self.activity_product_id.voucher_validity_type or '',
            'voucherRedemptionAddress': self.activity_product_id and self.cleanhtml(self.activity_product_id.voucherRedemptionAddress) or ''
        }

        res = {
            'activity': self.activity_id and self.activity_id.name or '',
            'activity_uuid': self.activity_id and self.activity_id.uuid or '',
            'activity_type': self.activity_product_id and self.activity_product_id.name or '',
            'activity_type_uuid': self.activity_product_id and self.activity_product_id.uuid or '',
            'visit_date': self.visit_date and self.visit_date.strftime('%Y-%m-%d') or '',
            'timeslot': self.timeslot and self.timeslot or '',
            'information': self.information and self.information or '',
            'warnings': self.activity_id and self.cleanhtml(self.activity_id.warnings) or '',
            'safety': self.activity_id and self.cleanhtml(self.activity_id.safety) or '',
            'priceIncludes': self.activity_id and self.cleanhtml(self.activity_id.priceIncludes) or '',
            'priceExcludes': self.activity_id and self.cleanhtml(self.activity_id.priceExcludes) or '',
            'image_urls': image_urls,
            'voucher_information': voucher_information
        }

        return res
