from odoo import api, fields, models, _
from ...tools import variables, util, ERR
from ...tools.ERR import RequestException
import logging, traceback
from datetime import datetime


_logger = logging.getLogger(__name__)


class TtEmailQueue(models.Model):
    _name = 'tt.email.queue'
    _inherit = 'tt.history'
    _description = 'Rodex Model'
    _order = 'id DESC'

    name = fields.Char('Name', default='No Name', readonly=True)
    type = fields.Char('Type', readonly=True)
    template_id = fields.Many2one('mail.template', 'Mail Template', readonly=True)
    res_model = fields.Char('Related Model Name', index=True)
    res_id = fields.Integer('Related Model ID', index=True, help='Id of the followed resource')
    last_sent_attempt_date = fields.Datetime('Last Sent Attempt Date', readonly=True)
    failure_reason = fields.Text('Failure Reason', readonly=True)
    active = fields.Boolean('Active', default=True)

    def create_email_queue(self, data, context=None):
        # Data {'provider_type':'', 'url_booking':'', 'order_number':'', 'type':''}
        if data.get('provider_type') in ['airline', 'train', 'hotel', 'visa', 'passport', 'activity', 'tour']:
            try:
                self.env.get('tt.reservation.{}'.format(data['provider_type']))._name
            except:
                raise Exception('Module tt.reservation.{} not found!'.format(data['provider_type']))

            resv = self.env['tt.reservation.{}'.format(data['provider_type'])].search([('name', '=ilike', data.get('order_number')), ('agent_id', '=', context.get('co_agent_id', -1))], limit=1)
            if resv:
                if data.get('type') == 'booked':
                    type_str = 'Booked'
                else:
                    type_str = 'Issued'
                template = self.env.ref('tt_reservation_{}.template_mail_reservation_{}_{}'.format(data['provider_type'], data.get('type', 'issued'), data['provider_type'])).id
                self.env['tt.email.queue'].sudo().create({
                    'name': type_str + ' ' + resv.name,
                    'type': '{}_{}'.format(data.get('type', 'issued'), data['provider_type']),
                    'template_id': template,
                    'res_model': resv._name,
                    'res_id': resv.id,
                })
            else:
                raise RequestException(1001)
        elif data.get('provider_type') == 'billing_statement':
            if self.env.get('tt.billing.statement'):
                resv = self.env['tt.billing.statement'].search([('name', '=ilike', data.get('order_number')), ('agent_id', '=', context.get('co_agent_id', -1))], limit=1)
                if resv:
                    template = self.env.ref('tt_billing_statement.template_mail_billing_statement').id
                    self.env['tt.email.queue'].sudo().create({
                        'name': resv.agent_id.name + ' e-Billing Statement for ' + resv.customer_parent_id.name,
                        'type': 'billing_statement',
                        'template_id': template,
                        'res_model': resv._name,
                        'res_id': resv.id,
                    })
                else:
                    raise RequestException(1001)
            else:
                raise Exception('Module tt.billing.statement not found!')

    def open_reference(self):
        try:
            form_id = self.env[self.res_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.res_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Model',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

    def prepare_attachment_reservation_issued(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
            if self.type in ['issued_airline', 'issued_train', 'issued_activity', 'issued_hotel']:
                if self.type in ['issued_airline', 'issued_train']:
                    ticket_data = ref_obj.print_eticket({})
                elif self.type == 'issued_activity':
                    ticket_data = ref_obj.get_vouchers_button()
                elif self.type == 'issued_hotel':
                    ticket_data = ref_obj.do_print_voucher({})
                else:
                    ticket_data = {}
                if ticket_data.get('url'):
                    headers = {
                        'Content-Type': 'application/json',
                    }
                    upload_data = util.send_request(ticket_data['url'], data={}, headers=headers, method='GET',
                                                    content_type='content', timeout=600)
                    if upload_data['error_code'] == 0:
                        attachment_obj = self.env['ir.attachment'].create({
                            'name': ref_obj.name + ' E-Ticket.pdf',
                            'datas_fname': ref_obj.name + ' E-Ticket.pdf',
                            'datas': upload_data['response'],
                        })
                        attachment_id_list.append(attachment_obj.id)
                    else:
                        _logger.info(upload_data['error_msg'])
                        raise Exception(_('Failed to convert ticket attachment!'))
                else:
                    raise Exception(_('Failed to get ticket attachment!'))

            resv_has_invoice = False
            printed_inv_ids = []
            for rec in ref_obj.invoice_line_ids:
                if rec.invoice_id.id not in printed_inv_ids and rec.invoice_id.state != 'cancel':
                    inv_data = rec.invoice_id.print_invoice()
                    if inv_data.get('url'):
                        headers = {
                            'Content-Type': 'application/json',
                        }
                        upload_data = util.send_request(inv_data['url'], data={}, headers=headers, method='GET',
                                                        content_type='content', timeout=600)
                        if upload_data['error_code'] == 0:
                            attachment_obj = self.env['ir.attachment'].create({
                                'name': ref_obj.name + ' Invoice.pdf',
                                'datas_fname': ref_obj.name + ' Invoice.pdf',
                                'datas': upload_data['response'],
                            })
                            attachment_id_list.append(attachment_obj.id)
                            resv_has_invoice = True
                        else:
                            _logger.info(upload_data['error_msg'])
                            raise Exception(_('Failed to convert invoice attachment!'))
                    else:
                        raise Exception(_('Failed to get invoice attachment!'))
                    printed_inv_ids.append(rec.invoice_id.id)
            if not resv_has_invoice:
                raise Exception(_('Reservation has no Invoice!'))
            self.template_id.attachment_ids = [(6, 0, attachment_id_list)]
        else:
            raise Exception(_('Reservation is not issued!'))

    def prepare_attachment_billing_statement(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state != 'cancel':
            ticket_data = ref_obj.print_report_billing_statement()
            if ticket_data.get('url'):
                headers = {
                    'Content-Type': 'application/json',
                }
                upload_data = util.send_request(ticket_data['url'], data={}, headers=headers, method='GET',
                                                content_type='content', timeout=600)
                if upload_data['error_code'] == 0:
                    attachment_obj = self.env['ir.attachment'].create({
                        'name': 'e-Billing Statement.pdf',
                        'datas_fname': 'e-Billing Statement.pdf',
                        'datas': upload_data['response'],
                    })
                    attachment_id_list.append(attachment_obj.id)
                else:
                    _logger.info(upload_data['error_msg'])
                    raise Exception(_('Failed to convert billing attachment!'))
            else:
                raise Exception(_('Failed to get billing attachment!'))
            self.template_id.attachment_ids = [(6, 0, attachment_id_list)]
        else:
            raise Exception(_('Billing is already cancelled!'))

    def action_send_email(self):
        try:
            if self.type in ['issued_airline', 'issued_train', 'issued_activity', 'issued_tour', 'issued_visa', 'issued_hotel', 'issued_offline']:
                self.prepare_attachment_reservation_issued()
            elif self.type == 'billing_statement':
                self.prepare_attachment_billing_statement()
            else:
                self.template_id.attachment_ids = [(6, 0, [])]

            self.template_id.send_mail(self.res_id, force_send=True)
            self.write({
                'last_sent_attempt_date': datetime.now(),
                'active': False,
                'failure_reason': ''
            })
        except Exception as e:
            self.write({
                'last_sent_attempt_date': datetime.now(),
                'active': False,
                'failure_reason': str(e)
            })
