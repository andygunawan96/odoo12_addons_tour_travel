from odoo import api, fields, models, _
import logging, traceback
import requests
from datetime import datetime
import json
from ...tools import ERR,variables,util
from ...tools.db_connector import GatewayConnector
from ...tools.variables import ACC_TRANSPORT_TYPE, ACC_TRANSPORT_TYPE_REVERSE

_logger = logging.getLogger(__name__)

class TtAccountingQueue(models.Model):
    _name = 'tt.accounting.queue'
    _inherit = 'tt.history'
    _description = 'Accounting Queue'
    _order = 'id DESC'

    accounting_provider = fields.Selection(variables.ACCOUNTING_VENDOR, 'Accounting Provider')
    request = fields.Text('Request', readonly=True)
    response = fields.Text('Response', readonly=True)
    transport_type = fields.Char('Transport Type', readonly=True)
    res_model = fields.Char('Related Model', readonly=True)
    res_id = fields.Integer('Related ID', index=True, help='Id of the followed resource')
    state = fields.Selection([('new', 'New'), ('success', 'Success'), ('failed', 'Failed')], 'State', default='new', readonly=True)
    send_uid = fields.Many2one('res.users', 'Last Sent By', readonly=True)
    send_date = fields.Datetime('Last Sent Date', readonly=True)
    action = fields.Char('Action', readonly=True)

    def to_dict(self):
        return {
            'accounting_provider': self.accounting_provider,
            'request': self.request,
            'transport_type': self.transport_type,
            'action': self.action,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'state': self.state
        }

    def open_reference(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def action_send_to_vendor(self):
        try:
            self.send_uid = self.env.user.id
            self.send_date = fields.Datetime.now()
            trans_obj = self.env[self.res_model].browse(self.res_id)
            if self.res_model in ['tt.reservation.airline', 'tt.reservation.activity', 'tt.reservation.event',
                                  'tt.reservation.hotel', 'tt.reservation.passport', 'tt.reservation.periksain',
                                  'tt.reservation.phc', 'tt.reservation.ppob', 'tt.reservation.tour',
                                  'tt.reservation.train', 'tt.reservation.visa']:
                pay_acq = self.env['payment.acquirer'].search([('seq_id', '=', trans_obj.payment_method)], limit=1)
                request = trans_obj.to_dict()
                ledger_list = []
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc:
                        ledger_list.append({
                            'id': led.id,
                            'ref': led.ref or '',
                            'name': led.name or '',
                            'debit': led.debit or 0,
                            'credit': led.credit or 0,
                            'currency_id': led.currency_id and led.currency_id.name or '',
                            'create_date': led.create_date and datetime.strftime(led.create_date, '%Y-%m-%d %H:%M:%S') or '',
                            'date': led.date and datetime.strftime(led.date, '%Y-%m-%d') or '',
                            'create_uid': led.create_uid and led.create_uid.name or '',
                            'description': led.description or '',
                            'agent_id': led.agent_id and led.agent_id.id or 0,
                            'agent_name': led.agent_id and led.agent_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'total_nta': trans_obj.total_nta or 0,
                    'payment_acquirer': pay_acq and pay_acq.jasaweb_name or '',
                    'provider_type_name': trans_obj.provider_type_id and trans_obj.provider_type_id.name or '',
                    'provider_bookings': [prov.to_dict() for prov in trans_obj.provider_booking_ids],
                    'ledgers': ledger_list,
                    'category': 'reservation'
                })
                if self.action in ['reverse', 'split_reservation']:
                    self.env['tt.accounting.connector.api.con'].send_notif_reverse_ledger(ACC_TRANSPORT_TYPE.get(self._name, ''), trans_obj.name, self.accounting_provider)
            elif self.res_model in ['tt.refund', 'tt.reschedule', 'tt.reschedule.periksain', 'tt.reschedule.phc']:
                request = trans_obj.to_dict()
                if self.res_model == 'tt.refund':
                    cat = 'refund'
                else:
                    cat = 'reschedule'
                ledger_list = []
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc:
                        ledger_list.append({
                            'id': led.id,
                            'ref': led.ref or '',
                            'name': led.name or '',
                            'debit': led.debit or 0,
                            'credit': led.credit or 0,
                            'currency_id': led.currency_id and led.currency_id.name or '',
                            'create_date': led.create_date and datetime.strftime(led.create_date, '%Y-%m-%d %H:%M:%S') or '',
                            'date': led.date and datetime.strftime(led.date, '%Y-%m-%d') or '',
                            'create_uid': led.create_uid and led.create_uid.name or '',
                            'description': led.description or '',
                            'agent_id': led.agent_id and led.agent_id.id or 0,
                            'agent_name': led.agent_id and led.agent_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'ledgers': ledger_list,
                    'category': cat
                })
            elif self.res_model == 'tt.top.up':
                request = trans_obj.to_dict_acc()
                ledger_list = []
                if not self.ledger_id.is_sent_to_acc:
                    ledger_list.append({
                        'id': self.ledger_id.id,
                        'ref': self.ledger_id.ref or '',
                        'name': self.ledger_id.name or '',
                        'debit': self.ledger_id.debit or 0,
                        'credit': self.ledger_id.credit or 0,
                        'currency_id': self.ledger_id.currency_id and self.ledger_id.currency_id.name or '',
                        'create_date': self.ledger_id.create_date and datetime.strftime(self.ledger_id.create_date, '%Y-%m-%d %H:%M:%S') or '',
                        'date': self.ledger_id.date and datetime.strftime(self.ledger_id.date, '%Y-%m-%d') or '',
                        'create_uid': self.ledger_id.create_uid and self.ledger_id.create_uid.name or '',
                        'description': self.ledger_id.description or '',
                        'agent_id': self.ledger_id.agent_id and self.ledger_id.agent_id.id or 0,
                        'agent_name': self.ledger_id.agent_id and self.ledger_id.agent_id.name or '',
                        'display_provider_name': self.ledger_id.display_provider_name or '',
                        'pnr': self.ledger_id.pnr or '',
                        'transaction_type': self.ledger_id.transaction_type
                    })
                    self.ledger_id.sudo().write({
                        'is_sent_to_acc': True
                    })
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'acquirer_type': trans_obj.acquirer_id and trans_obj.acquirer_id.type or '',
                    'ledgers': ledger_list,
                    'category': 'top_up'
                })
            else:
                request = {}
            if request:
                res = self.env['tt.accounting.connector.%s' % self.accounting_provider].add_sales_order(request)
                self.state = res.get('status', 'failed')
            else:
                raise Exception('Failed to fetch request from reference model.')
            self.response = json.dumps(res)
        except Exception as e:
            _logger.error(traceback.format_exc())

    def get_request_data(self):
        try:
            trans_obj = self.env[self.res_model].browse(self.res_id)
            if self.res_model in ['tt.reservation.airline', 'tt.reservation.activity', 'tt.reservation.event',
                                  'tt.reservation.hotel', 'tt.reservation.passport', 'tt.reservation.periksain',
                                  'tt.reservation.phc', 'tt.reservation.ppob', 'tt.reservation.tour',
                                  'tt.reservation.train', 'tt.reservation.visa']:
                pay_acq = self.env['payment.acquirer'].search([('seq_id', '=', trans_obj.payment_method)], limit=1)
                request = trans_obj.to_dict()
                ledger_list = []
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc:
                        ledger_list.append({
                            'id': led.id,
                            'ref': led.ref or '',
                            'name': led.name or '',
                            'debit': led.debit or 0,
                            'credit': led.credit or 0,
                            'currency_id': led.currency_id and led.currency_id.name or '',
                            'create_date': led.create_date and datetime.strftime(led.create_date,
                                                                                 '%Y-%m-%d %H:%M:%S') or '',
                            'date': led.date and datetime.strftime(led.date, '%Y-%m-%d') or '',
                            'create_uid': led.create_uid and led.create_uid.name or '',
                            'description': led.description or '',
                            'agent_id': led.agent_id and led.agent_id.id or 0,
                            'agent_name': led.agent_id and led.agent_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                request.update({
                    'create_by': trans_obj.create_uid and trans_obj.create_uid.name or '',
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'agent_type': trans_obj.agent_type_id and trans_obj.agent_type_id.name or '',
                    'agent_email': trans_obj.agent_id and trans_obj.agent_id.email or '',
                    'customer_parent_name': trans_obj.customer_parent_id and trans_obj.customer_parent_id.name or '',
                    'customer_parent_type': trans_obj.customer_parent_type_id and trans_obj.customer_parent_type_id.name or '',
                    'total_nta': trans_obj.total_nta or 0,
                    'commission_booker': trans_obj.booker_insentif or 0,
                    'payment_acquirer': pay_acq and pay_acq.jasaweb_name or '',
                    'provider_type_name': trans_obj.provider_type_id and trans_obj.provider_type_id.name or '',
                    'carrier_name': trans_obj.carrier_name or '',
                    'ledgers': ledger_list,
                    'passenger_pricings': trans_obj.get_passenger_pricing_breakdown(),
                    'category': 'reservation'
                })
                if self.action in ['reverse', 'split_reservation']:
                    self.env['tt.accounting.connector.api.con'].send_notif_reverse_ledger(ACC_TRANSPORT_TYPE.get(self._name, ''), trans_obj.name, self.accounting_provider)
            elif self.res_model in ['tt.refund', 'tt.reschedule', 'tt.reschedule.periksain', 'tt.reschedule.phc']:
                request = trans_obj.to_dict()
                if self.res_model == 'tt.refund':
                    cat = 'refund'
                    pnr = trans_obj.referenced_pnr or ''
                    amt = trans_obj.refund_amount or 0
                    real_amt = trans_obj.real_refund_amount or 0
                    ho_adm = trans_obj.admin_fee_ho
                    agent_adm = trans_obj.admin_fee_agent
                else:
                    cat = 'reschedule'
                    if trans_obj.new_pnr != trans_obj.referenced_pnr:
                        pnr = '%s to %s' % (trans_obj.referenced_pnr, trans_obj.new_pnr)
                    else:
                        pnr = trans_obj.referenced_pnr or ''
                    amt = trans_obj.reschedule_amount or 0
                    real_amt = trans_obj.real_reschedule_amount or 0
                    ho_adm = trans_obj.admin_fee
                    agent_adm = 0
                ledger_list = []
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc:
                        ledger_list.append({
                            'id': led.id,
                            'ref': led.ref or '',
                            'name': led.name or '',
                            'debit': led.debit or 0,
                            'credit': led.credit or 0,
                            'currency_id': led.currency_id and led.currency_id.name or '',
                            'create_date': led.create_date and datetime.strftime(led.create_date,
                                                                                 '%Y-%m-%d %H:%M:%S') or '',
                            'date': led.date and datetime.strftime(led.date, '%Y-%m-%d') or '',
                            'create_uid': led.create_uid and led.create_uid.name or '',
                            'description': led.description or '',
                            'agent_id': led.agent_id and led.agent_id.id or 0,
                            'agent_name': led.agent_id and led.agent_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                request.update({
                    'create_by': trans_obj.create_uid and trans_obj.create_uid.name or '',
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'agent_type': trans_obj.agent_type_id and trans_obj.agent_type_id.name or '',
                    'agent_email': trans_obj.agent_id and trans_obj.agent_id.email or '',
                    'customer_parent_name': trans_obj.customer_parent_id and trans_obj.customer_parent_id.name or '',
                    'customer_parent_type': trans_obj.customer_parent_type_id and trans_obj.customer_parent_type_id.name or '',
                    'pnr': pnr,
                    'ledgers': ledger_list,
                    'agent_nta': amt,
                    'agent_commission': agent_adm,
                    'upsell': 0,
                    'ho_nta': real_amt,
                    'total_commission': agent_adm + ho_adm,
                    'tax': 0,
                    'grand_total': trans_obj.total_amount or 0,
                    'category': cat
                })
            elif self.res_model == 'tt.top.up':
                request = trans_obj.to_dict_acc()
                ledger_list = []
                if not self.ledger_id.is_sent_to_acc:
                    ledger_list.append({
                        'id': self.ledger_id.id,
                        'ref': self.ledger_id.ref or '',
                        'name': self.ledger_id.name or '',
                        'debit': self.ledger_id.debit or 0,
                        'credit': self.ledger_id.credit or 0,
                        'currency_id': self.ledger_id.currency_id and self.ledger_id.currency_id.name or '',
                        'create_date': self.ledger_id.create_date and datetime.strftime(self.ledger_id.create_date,
                                                                                        '%Y-%m-%d %H:%M:%S') or '',
                        'date': self.ledger_id.date and datetime.strftime(self.ledger_id.date, '%Y-%m-%d') or '',
                        'create_uid': self.ledger_id.create_uid and self.ledger_id.create_uid.name or '',
                        'description': self.ledger_id.description or '',
                        'agent_id': self.ledger_id.agent_id and self.ledger_id.agent_id.id or 0,
                        'agent_name': self.ledger_id.agent_id and self.ledger_id.agent_id.name or '',
                        'display_provider_name': self.ledger_id.display_provider_name or '',
                        'pnr': self.ledger_id.pnr or '',
                        'transaction_type': self.ledger_id.transaction_type
                    })
                    self.ledger_id.sudo().write({
                        'is_sent_to_acc': True
                    })
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'acquirer_type': trans_obj.acquirer_id and trans_obj.acquirer_id.type or '',
                    'ledgers': ledger_list,
                    'agent_nta': trans_obj.amount,
                    'agent_commission': 0,
                    'upsell': 0,
                    'ho_nta': 0,
                    'total_commission': 0,
                    'tax': trans_obj.unique_amount,
                    'grand_total': trans_obj.total,
                    'category': 'top_up'
                })
            else:
                request = {}
            return request
        except Exception as e:
            _logger.error(traceback.format_exc())
