from odoo import api, fields, models, _
from odoo.exceptions import UserError
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
    res_name = fields.Char('Reference Name', compute='_compute_res_name')
    state = fields.Selection([('new', 'New'), ('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial'), ('manual_create', 'Manually Created on Vendor')], 'State', default='new', readonly=True)
    send_uid = fields.Many2one('res.users', 'Last Sent By', readonly=True)
    send_date = fields.Datetime('Last Sent Date', readonly=True)
    action = fields.Char('Action', readonly=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], readonly=True)

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rec in self:
            res_obj = self.env[rec.res_model].browse(rec.res_id)
            if res_obj.name:
                rec.res_name = res_obj.name
            else:
                rec.res_name = ''

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

    def set_to_manual_create(self):
        self.state = 'manual_create'

    def action_send_to_vendor(self):
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 30')
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
                is_send_commission = False
                accounting_obj = self.env['tt.accounting.setup'].search([('accounting_provider','=', self.accounting_provider), ('ho_id', '=', self.ho_id.id)], limit=1)
                if accounting_obj:
                    is_send_commission = accounting_obj.is_send_commission
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc and led.source_of_funds_type == 'balance': ## source_of_funds_type 0 untuk balance:
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
                            'agent_type_id': led.agent_type_id and led.agent_type_id.id or 0,
                            'agent_type_name': led.agent_type_id and led.agent_type_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                prov_book_list = []
                for prov in trans_obj.provider_booking_ids:
                    temp_prov_dict = prov.to_dict()
                    temp_prov_price_dict = {
                        'agent_nta': 0,
                        'total_nta': 0,
                        'parent_agent_commission': 0,
                        'agent_commission': 0,
                        'ho_commission': 0,
                        'total_commission': 0,
                        'total_fare': 0,
                        'total_tax': 0,
                        'total_upsell': 0,
                        'total_channel_upsell': 0,
                        'total_discount': 0,
                        'breakdown_service_fee': 0,
                        'breakdown_vat': 0,
                        'tax_service_charges': [],
                        'tax_details': []
                    }
                    prov_sale_id_list = []
                    for sale in prov.cost_service_charge_ids:
                        if sale.charge_code != 'csc' and sale.charge_type != 'DISC':
                            temp_prov_price_dict['total_nta'] += sale.total
                        if sale.charge_type == 'RAC' and sale.charge_code == 'rac':
                            temp_prov_price_dict['agent_commission'] -= sale.total
                            temp_prov_price_dict['agent_nta'] += sale.total
                        if sale.charge_type == 'RAC':
                            if trans_obj.agent_id.is_ho_agent or sale.charge_code != 'csc':
                                temp_prov_price_dict['total_commission'] -= sale.total
                            if sale.commission_agent_id.is_ho_agent:
                                temp_prov_price_dict['ho_commission'] -= sale.total
                            if sale.charge_code == 'csc':
                                temp_prov_price_dict['total_channel_upsell'] -= sale.total
                        if sale.charge_type == 'FARE':
                            temp_prov_price_dict['total_fare'] += sale.total
                        if sale.charge_type == 'TAX':
                            temp_prov_price_dict['total_tax'] += sale.total
                            temp_prov_price_dict['tax_details'].append({
                                'charge_code': sale.charge_code,
                                'amount': sale.total
                            })
                        if sale.charge_type == 'ROC' and sale.charge_code != 'csc':
                            temp_prov_price_dict['total_upsell'] += sale.total
                        if sale.charge_type != 'RAC' and sale.charge_code != 'csc':
                            temp_prov_price_dict['agent_nta'] += sale.total
                        if sale.charge_type == 'DISC':
                            temp_prov_price_dict['total_discount'] += sale.total
                        if sale.charge_type == 'ROCHSA':
                            temp_prov_price_dict['breakdown_service_fee'] += sale.total
                        if sale.charge_type in ['ROCHVA', 'ROCAVA', 'ROCHVC', 'ROCAVC']:
                            temp_prov_price_dict['breakdown_vat'] += sale.total
                        prov_sale_id_list.append(sale.id)
                    temp_prov_price_dict['parent_agent_commission'] = temp_prov_price_dict['total_commission'] - temp_prov_price_dict['agent_commission'] - temp_prov_price_dict['ho_commission']
                    temp_prov_price_dict['tax_service_charges'].append({
                        'charge_code': 'tax',
                        'amount': temp_prov_price_dict['agent_nta'] + temp_prov_price_dict['agent_commission'] - temp_prov_price_dict['ho_commission']
                    })
                    if trans_obj.agent_id.is_ho_agent:
                        temp_prov_price_dict['parent_agent_commission'] -= temp_prov_price_dict['total_channel_upsell']
                        temp_prov_price_dict['agent_commission'] += temp_prov_price_dict['total_channel_upsell']
                    # else:
                    #     temp_prov_price_dict['ho_commission'] += temp_prov_price_dict['total_channel_upsell']
                    temp_prov_dict.update(temp_prov_price_dict)

                    if temp_prov_dict.get('tickets'):
                        for tick in prov.ticket_ids:
                            temp_tick_price_dict = {
                                'agent_nta': 0,
                                'total_nta': 0,
                                'parent_agent_commission': 0,
                                'agent_commission': 0,
                                'ho_commission': 0,
                                'total_commission': 0,
                                'total_fare': 0,
                                'total_tax': 0,
                                'total_upsell': 0,
                                'total_channel_upsell': 0,
                                'total_discount': 0,
                                'breakdown_service_fee': 0,
                                'breakdown_vat': 0,
                                'tax_service_charges': [],
                                'tax_details': []
                            }
                            for sale in tick.passenger_id.cost_service_charge_ids.filtered(lambda x: x.id in prov_sale_id_list):
                                if sale.charge_code != 'csc' and sale.charge_type != 'DISC':
                                    temp_tick_price_dict['total_nta'] += sale.amount
                                if sale.charge_type == 'RAC' and sale.charge_code == 'rac':
                                    temp_tick_price_dict['agent_commission'] -= sale.amount
                                    temp_tick_price_dict['agent_nta'] += sale.amount
                                if sale.charge_type == 'RAC':
                                    if trans_obj.agent_id.is_ho_agent or sale.charge_code != 'csc':
                                        temp_tick_price_dict['total_commission'] -= sale.amount
                                    if sale.commission_agent_id.is_ho_agent:
                                        temp_tick_price_dict['ho_commission'] -= sale.amount
                                    if sale.charge_code == 'csc':
                                        temp_tick_price_dict['total_channel_upsell'] -= sale.amount
                                if sale.charge_type == 'FARE':
                                    temp_tick_price_dict['total_fare'] += sale.amount
                                if sale.charge_type == 'TAX':
                                    temp_tick_price_dict['total_tax'] += sale.amount
                                    temp_tick_price_dict['tax_details'].append({
                                        'charge_code': sale.charge_code,
                                        'amount': sale.amount
                                    })
                                if sale.charge_type == 'ROC' and sale.charge_code != 'csc':
                                    temp_tick_price_dict['total_upsell'] += sale.amount
                                if sale.charge_type != 'RAC' and sale.charge_code != 'csc':
                                    temp_tick_price_dict['agent_nta'] += sale.amount
                                if sale.charge_type == 'DISC':
                                    temp_tick_price_dict['total_discount'] += sale.amount
                                if sale.charge_type == 'ROCHSA':
                                    temp_tick_price_dict['breakdown_service_fee'] += sale.amount
                                if sale.charge_type in ['ROCHVA', 'ROCAVA', 'ROCHVC', 'ROCAVC']:
                                    temp_tick_price_dict['breakdown_vat'] += sale.amount
                            temp_tick_price_dict['parent_agent_commission'] = temp_tick_price_dict['total_commission'] - temp_tick_price_dict['agent_commission'] - temp_tick_price_dict['ho_commission']
                            temp_tick_price_dict['tax_service_charges'].append({
                                'charge_code': 'tax',
                                'amount': temp_tick_price_dict['agent_nta'] + temp_tick_price_dict['agent_commission'] - temp_tick_price_dict['ho_commission']
                            })
                            # for sale in tick.passenger_id.channel_service_charge_ids:
                            #     if sale.charge_code == 'csc':
                            #         temp_tick_price_dict['total_channel_upsell'] += abs(sale.amount)
                            if trans_obj.agent_id.is_ho_agent:
                                temp_tick_price_dict['parent_agent_commission'] -= temp_tick_price_dict['total_channel_upsell']
                                temp_tick_price_dict['agent_commission'] += temp_tick_price_dict['total_channel_upsell']
                            # else:
                            #     temp_tick_price_dict['ho_commission'] += temp_tick_price_dict['total_channel_upsell']

                            for prov_pax in temp_prov_dict['tickets']:
                                if prov_pax['passenger_number'] == tick.passenger_id.sequence:
                                    prov_pax.update(temp_tick_price_dict)

                    elif temp_prov_dict.get('passengers'):
                        for tick in trans_obj.passenger_ids:
                            temp_tick_price_dict = {
                                'agent_nta': 0,
                                'total_nta': 0,
                                'parent_agent_commission': 0,
                                'agent_commission': 0,
                                'ho_commission': 0,
                                'total_commission': 0,
                                'total_fare': 0,
                                'total_tax': 0,
                                'total_upsell': 0,
                                'total_channel_upsell': 0,
                                'total_discount': 0,
                                'breakdown_service_fee': 0,
                                'breakdown_vat': 0,
                                'tax_service_charges': [],
                                'tax_details': []
                            }
                            for sale in tick.cost_service_charge_ids.filtered(lambda x: x.id in prov_sale_id_list):
                                if sale.charge_code != 'csc' and sale.charge_type != 'DISC':
                                    temp_tick_price_dict['total_nta'] += sale.amount
                                if sale.charge_type == 'RAC' and sale.charge_code == 'rac':
                                    temp_tick_price_dict['agent_commission'] -= sale.amount
                                    temp_tick_price_dict['agent_nta'] += sale.amount
                                if sale.charge_type == 'RAC':
                                    if trans_obj.agent_id.is_ho_agent or sale.charge_code != 'csc':
                                        temp_tick_price_dict['total_commission'] -= sale.amount
                                    if sale.commission_agent_id.is_ho_agent:
                                        temp_tick_price_dict['ho_commission'] -= sale.amount
                                    if sale.charge_code == 'csc':
                                        temp_tick_price_dict['total_channel_upsell'] -= sale.amount
                                if sale.charge_type == 'FARE':
                                    temp_tick_price_dict['total_fare'] += sale.amount
                                if sale.charge_type == 'TAX':
                                    temp_tick_price_dict['total_tax'] += sale.amount
                                    temp_tick_price_dict['tax_details'].append({
                                        'charge_code': sale.charge_code,
                                        'amount': sale.amount
                                    })
                                if sale.charge_type == 'ROC' and sale.charge_code != 'csc':
                                    temp_tick_price_dict['total_upsell'] += sale.amount
                                if sale.charge_type != 'RAC' and sale.charge_code != 'csc':
                                    temp_tick_price_dict['agent_nta'] += sale.amount
                                if sale.charge_type == 'DISC':
                                    temp_tick_price_dict['total_discount'] += sale.amount
                                if sale.charge_type == 'ROCHSA':
                                    temp_tick_price_dict['breakdown_service_fee'] += sale.amount
                                if sale.charge_type in ['ROCHVA', 'ROCAVA', 'ROCHVC', 'ROCAVC']:
                                    temp_tick_price_dict['breakdown_vat'] += sale.amount
                            temp_tick_price_dict['parent_agent_commission'] = temp_tick_price_dict['total_commission'] - temp_tick_price_dict['agent_commission'] - temp_tick_price_dict['ho_commission']
                            temp_tick_price_dict['tax_service_charges'].append({
                                'charge_code': 'tax',
                                'amount': temp_tick_price_dict['agent_nta'] + temp_tick_price_dict['agent_commission'] - temp_tick_price_dict['ho_commission']
                            })
                            # for sale in tick.channel_service_charge_ids:
                            #     if sale.charge_code == 'csc':
                            #         temp_tick_price_dict['total_channel_upsell'] += abs(sale.amount)
                            if trans_obj.agent_id.is_ho_agent:
                                temp_tick_price_dict['parent_agent_commission'] -= temp_tick_price_dict['total_channel_upsell']
                                temp_tick_price_dict['agent_commission'] += temp_tick_price_dict['total_channel_upsell']
                            # else:
                            #     temp_tick_price_dict['ho_commission'] += temp_tick_price_dict['total_channel_upsell']

                            for prov_pax in temp_prov_dict['passengers']:
                                if prov_pax['sequence'] == tick.sequence:
                                    prov_pax.update(temp_tick_price_dict)

                    prov_book_list.append(temp_prov_dict)
                invoice_data = []
                billing_due_date = 0
                for rec in trans_obj.invoice_line_ids:
                    invoice_data.append(rec.invoice_id.name)
                    billing_due_date = rec.customer_parent_id.billing_due_date
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'customer_parent_id': trans_obj.customer_parent_id and trans_obj.customer_parent_id.id or 0,
                    'total_nta': trans_obj.total_nta or 0,
                    'parent_agent_commission': trans_obj.parent_agent_commission or 0,
                    'ho_commission': trans_obj.ho_commission or 0,
                    'total_commission': trans_obj.total_commission or 0,
                    'total_channel_upsell': trans_obj.total_channel_upsell or 0,
                    'payment_acquirer': pay_acq and pay_acq.jasaweb_name or '',
                    'provider_type_name': trans_obj.provider_type_id and trans_obj.provider_type_id.name or '',
                    'provider_bookings': prov_book_list,
                    'ledgers': ledger_list,
                    'category': 'reservation',
                    'invoice_data': invoice_data,
                    'total': trans_obj.total,
                    'total_discount': trans_obj.total_discount,
                    'is_send_commission': is_send_commission,
                    'billing_due_date': billing_due_date,
                    'issued_accounting_uid': trans_obj.issued_uid and trans_obj.issued_uid.accounting_uid or ''
                })
                if self.res_model == 'tt.reservation.airline':
                    request.update({
                        'sector_type': trans_obj.sector_type
                    })
                if self.res_model == 'tt.reservation.hotel':
                    request.update({
                        'nights': trans_obj.nights
                    })
                if self.action in ['reverse', 'split_reservation']:
                    if request.get('order_number'):
                        request.update({
                            'order_number': request['order_number'] + '.' + self.action
                        })
                    ho_id = trans_obj.agent_id.ho_id.id
                    self.env['tt.accounting.connector.api.con'].send_notif_reverse_ledger(ACC_TRANSPORT_TYPE.get(self._name, ''), trans_obj.name, self.accounting_provider, ho_id)
            elif self.res_model in ['tt.refund', 'tt.reschedule', 'tt.reschedule.periksain', 'tt.reschedule.phc']:
                request = trans_obj.to_dict()
                if self.res_model == 'tt.refund':
                    cat = 'refund'
                else:
                    cat = 'reschedule'
                ledger_list = []
                for led in trans_obj.ledger_ids:
                    if not led.is_sent_to_acc and led.source_of_funds_type == 'balance': ## source_of_funds_type 0 untuk balance:
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
                            'agent_type_id': led.agent_type_id and led.agent_type_id.id or 0,
                            'agent_type_name': led.agent_type_id and led.agent_type_id.name or '',
                            'display_provider_name': led.display_provider_name or '',
                            'pnr': led.pnr or '',
                            'transaction_type': led.transaction_type
                        })
                        led.sudo().write({
                            'is_sent_to_acc': True
                        })
                new_segment_list = []
                invoice_data = []
                billing_due_date = 0
                if self.res_model == 'tt.reschedule':
                    for segment_obj in trans_obj.new_segment_ids:
                        new_segment_list.append(segment_obj.to_dict())

                    for rec in trans_obj.invoice_line_ids:
                        invoice_data.append(rec.invoice_id.name)
                        billing_due_date = rec.customer_parent_id.billing_due_date

                book_obj = self.env[trans_obj.res_model].browse(trans_obj.res_id)
                book_data = book_obj.to_dict()
                book_invoice_data = []
                prov_book_list = []
                for prov in book_obj.provider_booking_ids:
                    prov_book_list.append(prov.to_dict())

                for rec in book_obj.invoice_line_ids:
                    book_invoice_data.append(rec.invoice_id.name)
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'customer_parent_id': trans_obj.customer_parent_id and trans_obj.customer_parent_id.id or 0,
                    'ledgers': ledger_list,
                    'category': cat,
                    'new_segment': new_segment_list,
                    'invoice_data': invoice_data,
                    'billing_due_date': billing_due_date,
                    'reservation_name': book_obj.name if book_obj else '',
                    'reservation_data': book_data,
                    'reservation_invoice_data': book_invoice_data,
                    'provider_bookings': prov_book_list,
                    'customer_parent_name': book_obj.customer_parent_id.name,
                    'customer_parent_type_id': {
                        'code': book_obj.customer_parent_type_id.code
                    },
                    'booker': {
                        'name': book_obj.booker_id.name
                    }
                })
            elif self.res_model == 'tt.top.up':
                request = trans_obj.to_dict_acc()
                ledger_list = []
                if not trans_obj.ledger_id.is_sent_to_acc and trans_obj.ledger_id.source_of_funds_type == 'balance': ## source_of_funds_type 0 untuk balance
                    ledger_list.append({
                        'id': trans_obj.ledger_id.id,
                        'ref': trans_obj.ledger_id.ref or '',
                        'name': trans_obj.ledger_id.name or '',
                        'debit': trans_obj.ledger_id.debit or 0,
                        'credit': trans_obj.ledger_id.credit or 0,
                        'currency_id': trans_obj.ledger_id.currency_id and trans_obj.ledger_id.currency_id.name or '',
                        'create_date': trans_obj.ledger_id.create_date and datetime.strftime(trans_obj.ledger_id.create_date, '%Y-%m-%d %H:%M:%S') or '',
                        'date': trans_obj.ledger_id.date and datetime.strftime(trans_obj.ledger_id.date, '%Y-%m-%d') or '',
                        'create_uid': trans_obj.ledger_id.create_uid and trans_obj.ledger_id.create_uid.name or '',
                        'description': trans_obj.ledger_id.description or '',
                        'agent_id': trans_obj.ledger_id.agent_id and trans_obj.ledger_id.agent_id.id or 0,
                        'agent_name': trans_obj.ledger_id.agent_id and trans_obj.ledger_id.agent_id.name or '',
                        'agent_type_id': trans_obj.ledger_id.agent_type_id and trans_obj.ledger_id.agent_type_id.id or 0,
                        'agent_type_name': trans_obj.ledger_id.agent_type_id and trans_obj.ledger_id.agent_type_id.name or '',
                        'display_provider_name': trans_obj.ledger_id.display_provider_name or '',
                        'pnr': trans_obj.ledger_id.pnr or '',
                        'transaction_type': trans_obj.ledger_id.transaction_type
                    })
                    trans_obj.ledger_id.sudo().write({
                        'is_sent_to_acc': True
                    })
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'acquirer_type': trans_obj.acquirer_id and trans_obj.acquirer_id.type or '',
                    'ledgers': ledger_list,
                    'category': 'top_up',
                    'bank': trans_obj.acquirer_id.bank_id.name
                })
            elif self.res_model == 'tt.customer.parent':
                request = trans_obj.to_dict_acc()
            else:
                request = {}
            if request:
                request.update({
                    'accounting_queue_id': self.id,
                    'ho_id': self.ho_id.id
                })
                if self.res_model == 'tt.customer.parent':
                    res = self.env['tt.accounting.connector.%s' % self.accounting_provider].add_customer(request)
                else:
                    res = self.env['tt.accounting.connector.%s' % self.accounting_provider].add_sales_order(request)
                self.response = json.dumps(res)
                self.state = res.get('status') and res['status'] or 'failed'
            else:
                self.response = 'Failed to fetch request from reference model.'
                self.state = 'failed'
                raise Exception('Failed to fetch request from reference model.')
        except Exception as e:
            _logger.error(traceback.format_exc(e))
            self.state = 'failed'
            self.response = traceback.format_exc(e)

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
                is_send_commission = False
                accounting_obj = self.env['tt.accounting.setup'].search([('accounting_provider', '=', self.accounting_provider), ('ho_id', '=', self.ho_id.id)], limit=1)
                if accounting_obj:
                    is_send_commission = accounting_obj.is_send_commission
                for led in trans_obj.ledger_ids:
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
                        'agent_type_id': led.agent_type_id and led.agent_type_id.id or 0,
                        'agent_type_name': led.agent_type_id and led.agent_type_id.name or '',
                        'display_provider_name': led.display_provider_name or '',
                        'pnr': led.pnr or '',
                        'transaction_type': led.transaction_type
                    })

                invoice_data = []
                billing_due_date = 0
                for rec in trans_obj.invoice_line_ids:
                    invoice_data.append(rec.invoice_id.name)
                    billing_due_date = rec.customer_parent_id.billing_due_date
                request.update({
                    'create_by': trans_obj.create_uid and trans_obj.create_uid.name or '',
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'agent_type': trans_obj.agent_type_id and trans_obj.agent_type_id.name or '',
                    'agent_email': trans_obj.agent_id and trans_obj.agent_id.email or '',
                    'customer_parent_name': trans_obj.customer_parent_id and trans_obj.customer_parent_id.name or '',
                    'customer_parent_type': trans_obj.customer_parent_type_id and trans_obj.customer_parent_type_id.name or '',
                    'total_nta': trans_obj.total_nta or 0,
                    'parent_agent_commission': trans_obj.parent_agent_commission or 0,
                    'ho_commission': trans_obj.ho_commission or 0,
                    'total_commission': trans_obj.total_commission or 0,
                    'total_channel_upsell': trans_obj.total_channel_upsell or 0,
                    'commission_booker': trans_obj.booker_insentif or 0,
                    'payment_acquirer': pay_acq and pay_acq.jasaweb_name or '',
                    'provider_type_name': trans_obj.provider_type_id and trans_obj.provider_type_id.name or '',
                    'ledgers': ledger_list,
                    'passenger_pricings': trans_obj.get_passenger_pricing_breakdown(),
                    'category': 'reservation',
                    'invoice_data': invoice_data,
                    'total': trans_obj.total,
                    'total_discount': trans_obj.total_discount,
                    'is_send_commission': is_send_commission,
                    'billing_due_date': billing_due_date
                })
                if self.action in ['reverse', 'split_reservation']:
                    if request.get('order_number'):
                        request.update({
                            'order_number': request['order_number'] + '.' + self.action
                        })
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
                invoice_data = []
                billing_due_date = 0
                for rec in trans_obj.invoice_line_ids:
                    invoice_data.append(rec.invoice_id.name)
                    billing_due_date = rec.customer_parent_id.billing_due_date
                for led in trans_obj.ledger_ids:
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
                        'agent_type_id': led.agent_type_id and led.agent_type_id.id or 0,
                        'agent_type_name': led.agent_type_id and led.agent_type_id.name or '',
                        'display_provider_name': led.display_provider_name or '',
                        'pnr': led.pnr or '',
                        'transaction_type': led.transaction_type
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
                    'fare': 0,
                    'tax': 0,
                    'agent_nta': amt,
                    'agent_commission': agent_adm,
                    'parent_agent_commission': 0,
                    'upsell': 0,
                    'discount': 0,
                    'ho_nta': real_amt,
                    'ho_commission': ho_adm,
                    'total_commission': agent_adm + ho_adm,
                    'total_channel_upsell': 0,
                    'grand_total': trans_obj.total_amount or 0,
                    'category': cat,
                    'invoice_data': invoice_data,
                    'billing_due_date': billing_due_date
                })
            elif self.res_model == 'tt.top.up':
                request = trans_obj.to_dict_acc()
                ledger_list = [{
                    'id': trans_obj.ledger_id.id,
                    'ref': trans_obj.ledger_id.ref or '',
                    'name': trans_obj.ledger_id.name or '',
                    'debit': trans_obj.ledger_id.debit or 0,
                    'credit': trans_obj.ledger_id.credit or 0,
                    'currency_id': trans_obj.ledger_id.currency_id and trans_obj.ledger_id.currency_id.name or '',
                    'create_date': trans_obj.ledger_id.create_date and datetime.strftime(trans_obj.ledger_id.create_date,
                                                                                    '%Y-%m-%d %H:%M:%S') or '',
                    'date': trans_obj.ledger_id.date and datetime.strftime(trans_obj.ledger_id.date, '%Y-%m-%d') or '',
                    'create_uid': trans_obj.ledger_id.create_uid and trans_obj.ledger_id.create_uid.name or '',
                    'description': trans_obj.ledger_id.description or '',
                    'agent_id': trans_obj.ledger_id.agent_id and trans_obj.ledger_id.agent_id.id or 0,
                    'agent_name': trans_obj.ledger_id.agent_id and trans_obj.ledger_id.agent_id.name or '',
                    'display_provider_name': trans_obj.ledger_id.display_provider_name or '',
                    'pnr': trans_obj.ledger_id.pnr or '',
                    'transaction_type': trans_obj.ledger_id.transaction_type
                }]
                request.update({
                    'agent_name': trans_obj.agent_id and trans_obj.agent_id.name or '',
                    'acquirer_type': trans_obj.acquirer_id and trans_obj.acquirer_id.type or '',
                    'ledgers': ledger_list,
                    'fare': trans_obj.amount,
                    'tax': trans_obj.unique_amount,
                    'agent_nta': 0,
                    'agent_commission': 0,
                    'parent_agent_commission': 0,
                    'upsell': 0,
                    'discount': 0,
                    'ho_nta': 0,
                    'ho_commission': 0,
                    'total_commission': 0,
                    'total_channel_upsell': 0,
                    'grand_total': trans_obj.total,
                    'category': 'top_up'
                })
            else:
                request = {}
            return request
        except Exception as e:
            _logger.error(traceback.format_exc())

    def multi_mass_send_to_vendor(self):
        _logger.info("Mass Accounting Queue Send To Vendor Starting")
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 463')
        for rec in self:
            if rec.state not in ['success', 'manual_create']:
                _logger.info("%s %s (%s: %s)" % (rec.accounting_provider, rec.action, rec.res_model, str(rec.res_id)))
                rec.action_send_to_vendor()

    def multi_mass_set_to_manual_create(self):
        _logger.info("Mass Accounting Queue Set To Manually Created On Vendor Starting")
        if not self.env.user.has_group('tt_base.group_after_sales_master_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 464')
        for rec in self:
            if rec.state not in ['success', 'manual_create']:
                _logger.info("%s %s (%s: %s)" % (rec.accounting_provider, rec.action, rec.res_model, str(rec.res_id)))
                rec.set_to_manual_create()
