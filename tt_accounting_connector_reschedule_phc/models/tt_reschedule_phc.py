from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
from datetime import datetime
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtReschedulePHC(models.Model):
    _inherit = 'tt.reschedule.phc'

    def send_ledgers_to_accounting(self, func_action, vendor_list):
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
                        'create_date': rec.create_date and datetime.strftime(rec.create_date, '%Y-%m-%d %H:%M:%S') or '',
                        'date': rec.date and datetime.strftime(rec.date, '%Y-%m-%d') or '',
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
                        'NTA_amount_real': self.total_amount and self.total_amount or 0,
                        'payment_acquirer': self.payment_acquirer_id and self.payment_acquirer_id.jasaweb_name or '',
                    })
                    rec.sudo().write({
                        'is_sent_to_acc': True
                    })
            if ledger_list:
                res = []
                for ven in vendor_list:
                    new_obj = self.env['tt.accounting.queue'].create({
                        'accounting_provider': ven,
                        'request': json.dumps(ledger_list),
                        'transport_type': ACC_TRANSPORT_TYPE.get(self._name, ''),
                        'action': func_action,
                        'res_model': self._name
                    })
                    res.append(new_obj.to_dict())
            else:
                res = {}
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.info("Failed to send ledgers to accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)

    def validate_reschedule_from_button(self):
        super(TtReschedulePHC, self).validate_reschedule_from_button()
        setup_list = self.env['tt.accounting.setup'].search(
            [('cycle', '=', 'real_time'), ('is_send_reschedule_phc', '=', True)])
        if setup_list:
            vendor_list = []
            for rec in setup_list:
                if rec.accounting_provider not in vendor_list:
                    vendor_list.append(rec.accounting_provider)
            self.send_ledgers_to_accounting('validate', vendor_list)

    def cancel_reschedule_from_button(self):
        super(TtReschedulePHC, self).cancel_reschedule_from_button()
        setup_list = self.env['tt.accounting.setup'].search(
            [('cycle', '=', 'real_time'), ('is_send_reschedule_phc', '=', True)])
        if setup_list:
            vendor_list = []
            for rec in setup_list:
                if rec.accounting_provider not in vendor_list:
                    vendor_list.append(rec.accounting_provider)
            self.send_ledgers_to_accounting('cancel', vendor_list)
