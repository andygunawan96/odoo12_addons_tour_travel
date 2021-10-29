import pytz

from odoo import api,models,fields, _
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.api import Response
import logging,traceback
from datetime import datetime,date, timedelta
import base64
import json


_logger = logging.getLogger(__name__)

MAX_PER_SLOT = 5

class TtPriceListSwabExpress(models.Model):
    _name = 'tt.price.list.swabexpress'
    _description = 'Rodex Model Price List Swab Express'
    _rec_name = 'name'
    _order = 'min_pax'

    seq_id = fields.Char('Sequence ID',readonly=True)
    name = fields.Char('Name', required=True)
    min_pax = fields.Integer('Minimum Pax', required=True, default=1)
    commission = fields.Monetary('Commission per PAX')
    base_price = fields.Monetary('Base Price per PAX')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    active = fields.Boolean('Active', default='True')

    @api.model
    def create(self, vals_list):
        vals_list['seq_id'] = self.env['ir.sequence'].next_by_code('tt.price.list.swabexpress')
        return super(TtPriceListSwabExpress, self).create(vals_list)
