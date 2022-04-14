from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
from datetime import date, timedelta
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtReservationPassport(models.Model):
    _inherit = 'tt.reconcile.transaction'

    def send_recon_batches_to_accounting(self, days):
        start_date = date.today() - timedelta(days=days)
        recon_list = self.env['tt.reconcile.transaction.lines'].search([('state', '=', 'match'), ('reconcile_transaction_id.transaction_date', '>=', start_date)])
        for rec in recon_list:
            found_rec = []
            if rec.type == 'reissue':
                found_rec = self.compare_reissue_recon_data({
                    'pnr': rec.pnr,
                    'total': abs(rec.total)
                })
            elif rec.type == 'nta':
                prov_rec = self.env['tt.provider.%s' % (rec.reconcile_transaction_id.provider_type_id.code)].search(
                    [('pnr', '=', rec.pnr),
                     ('total_price', '=', abs(rec.total)), ('reconcile_line_id', '!=', False)],
                    limit=1)
                if prov_rec:
                    found_rec = prov_rec.booking_id
                else:  # kalau tidak ketemu di provider masing masing cari di offline
                    prov_rec = self.env['tt.provider.offline'].search([('pnr', '=', rec.pnr),
                                                                       ('total_price', '=',
                                                                        abs(rec.total)),
                                                                       ('reconcile_line_id', '!=', False)], limit=1)
                    if prov_rec:
                        found_rec = prov_rec.booking_id
            elif rec.type == 'refund':
                found_rec = self.env['tt.refund'].search([('referenced_pnr', '=', rec.pnr),
                                                          ('state', '=', 'final'),
                                                          ('reconcile_line_id', '!=', False)], limit=1)
            if found_rec:
                temp_post = found_rec[0].posted_acc_actions or ''
                if 'reconcile' not in temp_post.split(',') and 'transaction_batch' not in temp_post.split(','):
                    setup_list = self.env['tt.accounting.setup'].search(
                        [('cycle', '=', 'per_batch'), ('is_recon_only', '=', True),
                         ('is_send_%s' % (rec.reconcile_transaction_id.provider_type_id.code), '=', True)])
                    if setup_list:
                        vendor_list = []
                        for rec2 in setup_list:
                            if rec2.accounting_provider not in vendor_list:
                                vendor_list.append(rec2.accounting_provider)
                        found_rec[0].send_ledgers_to_accounting('reconcile', vendor_list)
                        if temp_post:
                            temp_post += ',reconcile'
                        else:
                            temp_post += 'reconcile'
                        found_rec[0].write({
                            'posted_acc_actions': temp_post
                        })
