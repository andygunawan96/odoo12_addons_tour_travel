from odoo import api, fields, models, _
import traceback,logging

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    jasaweb_name = fields.Char('Jasaweb Name', default='')
