from odoo import api, fields, models, _
from ...tools import variables, util, ERR
from ...tools.ERR import RequestException
import logging, traceback
from datetime import datetime


_logger = logging.getLogger(__name__)


class TtEmailQueue(models.Model):
    _name = 'tt.email.queue'
    _inherit = 'tt.history'
    _description = 'Email Queue'
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
        if data.get('provider_type') in ['airline', 'train', 'hotel', 'visa', 'passport', 'activity', 'tour', 'ppob', 'bus', 'periksain', 'phc', 'medical', 'swabexpress', 'labpintar', 'sentramedika']:
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

                #ini agent
                template = self.env.ref('tt_reservation_{}.template_mail_reservation_{}_{}'.format(data['provider_type'], data.get('type', 'issued'), data['provider_type'])).id
                self.env['tt.email.queue'].sudo().create({
                    'name': type_str + ' ' + resv.name,
                    'type': '{}_{}'.format(data.get('type', 'issued'), data['provider_type']),
                    'template_id': template,
                    'res_model': resv._name,
                    'res_id': resv.id,
                })


                #ini customer
                if resv.agent_id.is_send_email_cust:
                    template = self.env.ref('tt_reservation_{}.template_mail_reservation_{}_{}_cust'.format(data['provider_type'], data.get('type', 'issued'), data['provider_type'])).id
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
            try:
                self.env.get('tt.billing.statement')._name
            except:
                raise Exception('Module tt.billing.statement not found!')

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
        elif data.get('provider_type') == 'refund':
            try:
                self.env.get('tt.refund')._name
            except:
                raise Exception('Module tt.refund not found!')

            resv = self.env['tt.refund'].search([('name', '=ilike', data.get('order_number')), ('agent_id', '=', context.get('co_agent_id', -1))], limit=1)
            if resv:
                if data.get('type') == 'done':
                    type_str = 'Done'
                elif data.get('type') == 'finalized':
                    type_str = 'Finalized'
                else:
                    type_str = 'Confirmed'

                template = self.env.ref('tt_accounting.template_mail_{}_{}'.format(data['provider_type'], data.get('type', 'confirmed'))).id
                self.env['tt.email.queue'].sudo().create({
                    'name': 'Refund ' + type_str + ': ' + resv.name,
                    'type': '{}_{}'.format(data['provider_type'], data.get('type', 'confirmed')),
                    'template_id': template,
                    'res_model': resv._name,
                    'res_id': resv.id,
                })

                if resv.agent_id.is_send_email_cust and resv.booker_id.email:
                    template = self.env.ref('tt_accounting.template_mail_{}_{}_cust'.format(data['provider_type'], data.get('type', 'confirmed'))).id
                    self.env['tt.email.queue'].sudo().create({
                        'name': 'Refund ' + type_str + ': ' + resv.name,
                        'type': '{}_{}'.format(data['provider_type'], data.get('type', 'confirmed')),
                        'template_id': template,
                        'res_model': resv._name,
                        'res_id': resv.id,
                    })
            else:
                raise RequestException(1001)

        elif data.get('provider_type') == 'voucher':
            try:
                self.env.get('tt.voucher.detail')._name
            except:
                raise Exception('Module tt.voucher.detail not found!')

            resv = self.env['tt.voucher.detail'].search([('voucher_reference_code', '=', data.get('ref_code')), ('voucher_period_reference', '=', data.get('period_code'))], limit=1)
            if resv:
                if data.get('type') == 'created':
                    type_str = 'Created'
                elif data.get('type') == 'used':
                    type_str = 'Used'
                else:
                    type_str = ''

                if type_str:
                    template = self.env.ref('tt_vouchers.template_mail_{}_{}'.format(data['provider_type'], data.get('type', 'used'))).id
                    self.env['tt.email.queue'].sudo().create({
                        'name': 'Voucher ' + type_str + ': ' + resv.voucher_reference_code + '.' + resv.voucher_period_reference,
                        'type': '{}_{}'.format(data['provider_type'], data.get('type', 'used')),
                        'template_id': template,
                        'res_model': resv._name,
                        'res_id': resv.id,
                    })

                    if resv.voucher_id.voucher_customer_id.agent_id.is_send_email_cust and resv.voucher_id.voucher_customer_id.email:
                        template = self.env.ref('tt_vouchers.template_mail_{}_{}_cust'.format(data['provider_type'], data.get('type', 'used'))).id
                        self.env['tt.email.queue'].sudo().create({
                            'name': 'Voucher ' + type_str + ': ' + resv.voucher_reference_code + '.' + resv.voucher_period_reference,
                            'type': '{}_{}'.format(data['provider_type'], data.get('type', 'used')),
                            'template_id': template,
                            'res_model': resv._name,
                            'res_id': resv.id,
                        })
            else:
                raise RequestException(1001)
        elif data.get('provider_type') == 'tour_installment':
            try:
                self.env.get(data['res_model'])._name
                data_id = data['res_id']
            except:
                raise Exception('Module %s not found!' % (data.get('res_model') or ''))

            resv = self.env[data['res_model']].browse(data_id)
            if resv:
                if data.get('type') == 'reminder':
                    type_str = 'Reminder'
                elif data.get('type') == 'overdue':
                    type_str = 'Overdue'
                else:
                    type_str = ''

                if type_str:
                    template = self.env.ref('tt_reservation_tour.template_mail_{}_{}'.format(data['provider_type'], data.get('type', 'reminder'))).id
                    self.env['tt.email.queue'].sudo().create({
                        'name': 'Tour Installment ' + type_str + ': ' + resv.booking_id.name,
                        'type': '{}_{}'.format(data['provider_type'], data.get('type', 'reminder')),
                        'template_id': template,
                        'res_model': resv._name,
                        'res_id': resv.id,
                    })

                    if resv.booking_id.agent_id.is_send_email_cust and resv.booking_id.contact_email:
                        template = self.env.ref('tt_reservation_tour.template_mail_{}_{}_cust'.format(data['provider_type'], data.get('type', 'reminder'))).id
                        self.env['tt.email.queue'].sudo().create({
                            'name': 'Tour Installment ' + type_str + ': ' + resv.booking_id.name,
                            'type': '{}_{}'.format(data['provider_type'], data.get('type', 'reminder')),
                            'template_id': template,
                            'res_model': resv._name,
                            'res_id': resv.id,
                        })
            else:
                raise RequestException(1001)

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
            if self.type in ['issued_airline', 'issued_train', 'issued_activity', 'issued_hotel', 'issued_ppob']:
                if self.type in ['issued_airline', 'issued_train', 'issued_ppob']:
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

    def prepare_attachment_refund(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if self.type == 'refund_done' and ref_obj.state == 'done':
            printout_data = ref_obj.print_refund_to_cust()
        elif self.type == 'refund_finalized' and ref_obj.state in ['final','approve','payment','approve_cust','done']:
            printout_data = ref_obj.print_refund_to_agent_cust()
        elif self.type == 'refund_confirmed' and ref_obj.state != 'draft':
            printout_data = ref_obj.print_refund_to_cust_est()
        else:
            printout_data = {}
        if printout_data.get('url'):
            headers = {
                'Content-Type': 'application/json',
            }
            upload_data = util.send_request(printout_data['url'], data={}, headers=headers, method='GET',
                                            content_type='content', timeout=600)
            if upload_data['error_code'] == 0:
                attachment_obj = self.env['ir.attachment'].create({
                    'name': 'Refund ' + ref_obj.name + '.pdf',
                    'datas_fname': 'Refund ' + ref_obj.name + '.pdf',
                    'datas': upload_data['response'],
                })
                attachment_id_list.append(attachment_obj.id)
            else:
                _logger.info(upload_data['error_msg'])
                raise Exception(_('Failed to convert refund attachment!'))
        else:
            raise Exception(_('Failed to get refund attachment!'))
        self.template_id.attachment_ids = [(6, 0, attachment_id_list)]

    def prepare_attachment_voucher(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        ticket_data = ref_obj.print_voucher()
        if ticket_data.get('url'):
            headers = {
                'Content-Type': 'application/json',
            }
            upload_data = util.send_request(ticket_data['url'], data={}, headers=headers, method='GET',
                                            content_type='content', timeout=600)
            if upload_data['error_code'] == 0:
                attachment_obj = self.env['ir.attachment'].create({
                    'name': 'Voucher.pdf',
                    'datas_fname': 'Voucher.pdf',
                    'datas': upload_data['response'],
                })
                attachment_id_list.append(attachment_obj.id)
            else:
                _logger.info(upload_data['error_msg'])
                raise Exception(_('Failed to convert voucher attachment!'))
        else:
            raise Exception(_('Failed to get voucher attachment!'))
        self.template_id.attachment_ids = [(6, 0, attachment_id_list)]

    def action_send_email(self):
        try:
            if self.type in ['issued_airline', 'issued_train', 'issued_activity', 'issued_tour', 'issued_visa', 'issued_passport', 'issued_hotel', 'issued_offline', 'issued_ppob', 'issued_bus', 'issued_periksain', 'issued_phc', 'issued_medical', 'issued_swabexpress', 'issued_labpintar', 'issued_sentramedika']:
                self.prepare_attachment_reservation_issued()
            elif self.type == 'billing_statement':
                self.prepare_attachment_billing_statement()
            elif self.type in ['refund_confirmed', 'refund_finalized', 'refund_done']:
                self.prepare_attachment_refund()
            elif self.type == 'voucher_created':
                self.prepare_attachment_voucher()
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
                'failure_reason': '%s : %s' % (traceback.format_exc(), str(e))
            })
