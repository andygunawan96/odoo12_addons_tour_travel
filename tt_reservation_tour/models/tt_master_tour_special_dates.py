from odoo import api, fields, models, _
from datetime import datetime, date
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools.api import Response
import logging, traceback
import json

_logger = logging.getLogger(__name__)


class MasterTourSpecialDates(models.Model):
    _name = "tt.master.tour.special.dates"
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='Special Date Charge')
    date = fields.Date('Date', required=True)
    tour_line_id = fields.Many2one('tt.master.tour.lines', 'Master Tour Lines')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    additional_adult_fare = fields.Monetary('Additional Adult Fare', default=0)
    additional_adult_commission = fields.Monetary('Additional Adult Commission', default=0)
    additional_child_fare = fields.Monetary('Additional Child Fare', default=0)
    additional_child_commission = fields.Monetary('Additional Child Commission', default=0)
    additional_infant_fare = fields.Monetary('Additional Infant Fare', default=0)
    additional_infant_commission = fields.Monetary('Additional Infant Commission', default=0)
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        return {
            'name': self.name,
            'date': self.date.strftime("%Y-%m-%d"),
            'currency_code': self.currency_id.name,
            'additional_adult_price': self.additional_adult_fare + self.additional_adult_commission,
            'additional_child_price': self.additional_child_fare + self.additional_child_commission,
            'additional_infant_price': self.additional_infant_fare + self.additional_infant_commission
        }
