from odoo import api, fields, models, modules, tools
from ..accounting_models.tt_accounting_connector import SalesOrder
import logging, traceback
import json

_logger = logging.getLogger(__name__)


class TtLedger(models.Model):
    _inherit = 'tt.ledger'

    @api.model
    def create(self, vals):
        ledger = super(TtLedger, self).create(vals)
        self.env.cr.commit()

        try:
            pass
        except Exception as e:
            _logger.error('Error: Failed to create Accounting Data. \n %s : %s' % (traceback.format_exc(), str(e)))
            self.env['tt.accounting.history'].sudo().create({
                'request':'none',
                'response': str(e),
                'state': 'odoo_failed'
            })
        return ledger
