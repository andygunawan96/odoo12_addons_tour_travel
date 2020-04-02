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

    name = fields.Char('Order Number', index=True, default='No Name', readonly=True)
    type = fields.Char('Type', readonly=True)
    template_id = fields.Many2one('mail.template', 'Mail Template', readonly=True)
    res_model = fields.Char('Related Model Name', index=True)
    res_id = fields.Integer('Related Model ID', index=True, help='Id of the followed resource')
    last_sent_attempt_date = fields.Datetime('Last Sent Attempt Date', readonly=True)
    failure_reason = fields.Text('Failure Reason', readonly=True)
    active = fields.Boolean('Active', default=True)

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

    def prepare_attachment_reservation_airline(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
            ticket_data = ref_obj.print_eticket({})
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

    def prepare_attachment_reservation_train(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
            ticket_data = ref_obj.print_eticket({})
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

    def prepare_attachment_reservation_activity(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
            ticket_data = ref_obj.get_vouchers_button()
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

    def prepare_attachment_reservation_tour(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
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

    def prepare_attachment_reservation_visa(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
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

    def prepare_attachment_reservation_hotel(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
            ticket_data = ref_obj.do_print_voucher({})
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

    def prepare_attachment_reservation_offline(self):
        attachment_id_list = []
        ref_obj = self.env[self.res_model].sudo().browse(int(self.res_id))
        if ref_obj.state == 'issued':
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
            if self.type == 'reservation_airline':
                self.prepare_attachment_reservation_airline()
            elif self.type == 'reservation_train':
                self.prepare_attachment_reservation_train()
            elif self.type == 'reservation_activity':
                self.prepare_attachment_reservation_activity()
            elif self.type == 'reservation_tour':
                self.prepare_attachment_reservation_tour()
            elif self.type == 'reservation_visa':
                self.prepare_attachment_reservation_visa()
            elif self.type == 'reservation_hotel':
                self.prepare_attachment_reservation_hotel()
            elif self.type == 'reservation_offline':
                self.prepare_attachment_reservation_offline()
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
