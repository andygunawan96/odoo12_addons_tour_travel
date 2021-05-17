from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class TtReschedule(models.Model):
    _inherit = 'tt.reschedule'

    def send_ledgers_to_accounting(self):
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            ledger_list = []
            for rec in self.ledger_ids:
                if not rec.is_sent_to_acc:
                    if rec.transaction_type == 7:
                        trans_type = 'Reschedule'
                    elif rec.transaction_type == 6:
                        trans_type = 'Admin Fee'
                    else:
                        trans_type = ''

                    ledger_list.append({
                        'reference_number': rec.ref and rec.ref or '',
                        'name': rec.name and rec.name or '',
                        'debit': rec.debit and rec.debit or 0,
                        'credit': rec.credit and rec.credit or 0,
                        'currency_id': rec.currency_id and rec.currency_id.name or '',
                        'create_date': rec.create_date,
                        'date': rec.date and rec.date or '',
                        'create_uid': rec.create_uid and rec.create_uid.name or '',
                        'commission': 0.0,
                        'description': rec.description and rec.description or '',
                        'agent_id': rec.agent_id and rec.agent_id.name,
                        'company_sender': rec.agent_id and rec.agent_id.name,
                        'company_receiver': self.env.ref('tt_base.rodex_ho').name,
                        'state': 'Done',
                        'display_provider_name': '',
                        'pnr': '',
                        'url_legacy': base_url + '/web#id=' + str(rec.id) + '&model=tt.ledger&view_type=form',
                        'transaction_type': trans_type,
                        'transport_type': 'Reschedule',
                        'payment_method': '',
                        'NTA_amount_real': self.total_nta and self.total_nta or 0,
                        'payment_acquirer': self.payment_acquirer_id and self.payment_acquirer_id.name or '',
                    })
                    rec.sudo().write({
                        'is_sent_to_acc': True
                    })
            res = self.env['tt.accounting.connector'].add_sales_order(ledger_list)
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.info("Failed to send ledgers to accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)

    def validate_reschedule_from_button(self):
        super(TtReschedule, self).validate_reschedule_from_button()
        self.send_ledgers_to_accounting()
