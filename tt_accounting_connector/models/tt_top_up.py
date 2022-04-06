from odoo import api,models,fields,_
from ...tools import util,ERR
import logging,traceback
from datetime import datetime
import json
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)


class TtTopUp(models.Model):
    _inherit = 'tt.top.up'

    posted_acc_actions = fields.Char('Posted to Accounting after Recon', default='')

    def send_ledgers_to_accounting(self, func_action, vendor_list):
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if self.acquirer_id:
                pay_method = self.acquirer_id.type in ['payment_gateway', 'va'] and 'Payment Gateway' or 'Rodex Gateway'
            else:
                pay_method = ''
            ledger_obj = self.ledger_id
            ledger_list = []
            if ledger_obj.agent_id.agent_type_id.id == self.env.ref('tt_base.agent_type_ho').id:
                if not ledger_obj.is_sent_to_acc:
                    ledger_list.append({
                        "create_date": ledger_obj.create_date and datetime.strftime(ledger_obj.create_date, '%Y-%m-%d %H:%M:%S') or '',
                        "payment_method": pay_method,
                        "currency_id": ledger_obj.currency_id and ledger_obj.currency_id.name or '',
                        "create_uid": ledger_obj.create_uid and ledger_obj.create_uid.name or '',
                        "company_sender": ledger_obj.agent_id and ledger_obj.agent_id.name or '',
                        "payment_acquirer": self.acquirer_id and self.acquirer_id.jasaweb_name or '',
                        "commission": 0,
                        "state": "Done",
                        "debit": ledger_obj.debit and ledger_obj.debit or 0,
                        "description": ledger_obj.description and ledger_obj.description or '',
                        "url_legacy": base_url + '/web#id=' + str(ledger_obj.id) + '&model=tt.ledger&view_type=form',
                        "display_provider_name": "",
                        "pnr": "",
                        "agent_id": ledger_obj.agent_id and ledger_obj.agent_id.name or '',
                        "company_receiver": self.env.ref('tt_base.rodex_ho').name,
                        'date': ledger_obj.date and datetime.strftime(ledger_obj.date, '%Y-%m-%d') or '',
                        "reference_number": ledger_obj.ref and ledger_obj.ref or '',
                        "NTA_amount_real": ledger_obj.debit and ledger_obj.debit or 0,
                        "name": ledger_obj.name and ledger_obj.name or '',
                        "transaction_type": "Top Up / Agent Payment",
                        "credit": ledger_obj.credit and ledger_obj.credit or 0,
                        "transport_type": "Top Up"
                    })
                    ledger_obj.sudo().write({
                        'is_sent_to_acc': True
                    })
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
            return ERR.get_no_error(res)
        except Exception as e:
            _logger.info("Failed to send ledgers to accounting software. Ignore this message if tt_accounting_connector is currently not installed.")
            _logger.error(traceback.format_exc())
            return ERR.get_error(1000)

    def action_approve_top_up(self):
        super(TtTopUp, self).action_approve_top_up()
        temp_post = self.posted_acc_actions or ''
        if 'approve' not in temp_post.split(','):
            setup_list = self.env['tt.accounting.setup'].search(
                [('cycle', '=', 'real_time'), ('is_send_topup', '=', True)])
            if setup_list:
                vendor_list = [rec.accounting_provider for rec in setup_list]
                self.send_ledgers_to_accounting('', vendor_list)
                if temp_post:
                    temp_post += ',approve'
                else:
                    temp_post += 'approve'
                self.write({
                    'posted_acc_actions': temp_post
                })
