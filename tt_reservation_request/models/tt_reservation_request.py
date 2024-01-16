from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools import variables, util, ERR
import json
from ...tools.ERR import RequestException
import logging, traceback
from datetime import datetime, timedelta
import time
import odoo.tools as tools
import base64

_logger = logging.getLogger(__name__)


class TtReservationRequest(models.Model):
    _name = 'tt.reservation.request'
    _inherit = 'tt.history'
    _description = 'Reservation Request Model'
    _order = 'id DESC'

    name = fields.Char('Request Number', index=True, default='New', readonly=True)
    res_model = fields.Char('Reservation Name', index=True, readonly=True)
    res_id = fields.Integer('Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], required=True, default=lambda self: self.env.user.ho_id, readonly=True, states={'draft': [('readonly', False)]})
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id, readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True, store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]}, help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id', store=True, readonly=True)
    approval_ids = fields.One2many('tt.reservation.request.approval', 'request_id', 'Approved By', readonly=True)
    cur_approval_seq = fields.Integer('Current Approval Sequence', readonly=True, default=10)
    booker_job_position_id = fields.Many2one('tt.customer.job.position', 'Booker Job Position', readonly=1, compute='_compute_booker_job_position')
    state = fields.Selection([('draft', 'Draft'), ('on_process', 'On Process'), ('approved', 'Approved'),
                              ('rejected', 'Rejected'), ('cancel', 'Cancelled')], 'State', default='draft')
    user_id = fields.Many2one('res.users', 'Create By', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_cuid = fields.Many2one('tt.customer', 'Cancelled By Customer', readonly=True)
    cancel_date = fields.Datetime('Cancelled Date', readonly=True)
    reject_uid = fields.Many2one('res.users', 'Rejected By', readonly=True)
    reject_cuid = fields.Many2one('tt.customer', 'Rejected By Customer', readonly=True)
    reject_date = fields.Datetime('Rejected Date', readonly=True)

    upline_ids = fields.One2many('tt.reservation.request.res.users.rel', 'reservation_request_id', 'Upline', readonly=True)

    @api.model
    def create(self, vals_list):
        try:
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.reservation.request')
        except:
            pass
        return super(TtReservationRequest, self).create(vals_list)

    def get_reservation_data(self):
        return self.env[self.res_model].browse(self.res_id)

    def send_email_to_upline(self):
        for rec in self.upline_ids:
            if rec.state == 'draft':
                rec.send_email_upline_request_issued()
                rec.state = 'done'

    def get_reservation_request_url(self):
        try:
            if self.ho_id:
                base_url = self.ho_id.redirect_url_signup
            else:
                base_url = self.agent_id.ho_id.redirect_url_signup
            final_url = base_url + '/reservation_request/' + (base64.b64encode(str(self.name).encode())).decode()
        except Exception as e:
            _logger.info(str(e))
            final_url = '#'
        return final_url

    def get_btc_url(self):
        try:
            if self.ho_id:
                base_url = self.ho_id.redirect_url_signup
            else:
                base_url = self.agent_id.ho_id.redirect_url_signup
            book_obj = self.env[self.res_model].browse(self.res_id)
            final_url = base_url + '/' + str(book_obj.provider_type_id.code) + '/booking/' + (base64.b64encode(str(book_obj.name).encode())).decode()
        except Exception as e:
            _logger.info(str(e))
            final_url = '#'
        return final_url

    @api.depends('booker_id', 'customer_parent_id')
    @api.onchange('booker_id', 'customer_parent_id')
    def _compute_booker_job_position(self):
        for rec in self:
            booker_obj = self.env['tt.customer.parent.booker.rel'].search(
                [('customer_parent_id', '=', rec.customer_parent_id.id), ('customer_id', '=', rec.booker_id.id)], limit=1)
            if booker_obj:
                rec.booker_job_position_id = booker_obj.job_position_id.id
            else:
                rec.booker_job_position_id = False

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

    def to_dict(self, with_approval=True):
        resv_obj = self.env[self.res_model].browse(self.res_id)
        request_state_str = {
            'draft': 'New',
            'on_process': 'On Process',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'cancel': 'Cancelled',
        }
        final_dict = {
            'request_number': self.name,
            'reservation_data': resv_obj and resv_obj.to_dict() or {},
            'provider_type': resv_obj and resv_obj.provider_type_id.name or '',
            'provider_type_code': resv_obj and resv_obj.provider_type_id.code or '',
            'booker': self.booker_id.to_dict(),
            'agent_id': self.agent_id.id,
            'agent': self.agent_id.name,
            'customer_parent_id': self.customer_parent_id.id,
            'customer_parent': self.customer_parent_id.name,
            'booker_job_position': self.booker_job_position_id and self.booker_job_position_id.name or '',
            'current_approval_sequence': self.cur_approval_seq,
            'state': self.state,
            'state_description': request_state_str[self.state],
            'created_date': self.create_date,
        }
        if final_dict.get('reservation_data'):
            final_dict['reservation_data'].update({
                'total_price': resv_obj.total
            })
        if with_approval:
            final_dict.update({
                'approvals': [rec.to_dict() for rec in self.approval_ids]
            })
            if self.state == 'rejected':
                if self.reject_cuid:
                    reject_booker_obj = self.env['tt.customer.parent.booker.rel'].search(
                        [('customer_parent_id', '=', self.customer_parent_id.id), ('customer_id', '=', self.reject_cuid.id)],
                        limit=1)
                    final_dict['approvals'].append({
                        'request_number': self.name,
                        'approved_date': self.reject_date and self.reject_date.strftime('%Y-%m-%d %H:%M:%S') or '',
                        'approved_by': self.reject_uid and self.reject_uid.name or '',
                        'approved_by_customer': self.reject_cuid and self.reject_cuid.name or '',
                        'approved_job_position': reject_booker_obj and reject_booker_obj.job_position_id.name or '',
                        'action': 'Rejected'
                    })
        return final_dict

    def get_issued_request_api(self,req,context):
        try:
            if context.get('co_customer_parent_id') and context.get('co_job_position_sequence'):
                if req.get('request_id'):
                    request_obj = self.browse(int(req['request_id']))
                else:
                    request_obj = self.search([('name', '=', req['request_number'])], limit=1)
                if not request_obj:
                    return ERR.get_error(1003)

                res = request_obj.to_dict()
                return ERR.get_no_error(res)
            else:
                return ERR.get_error(1023)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1013)

    def get_issued_request_list_api(self, req, context):
        try:
            if context.get('co_customer_parent_id') and context.get('co_job_position_sequence'):
                search_params = [('agent_id', '=', context['co_agent_id']),
                                ('customer_parent_id', '=', context['co_customer_parent_id'])]
                if req.get('is_open'):
                    search_params += [('state', 'in', ['draft', 'on_process']),
                                      ('cur_approval_seq', '>', context['co_job_position_sequence'])]
                request_list = self.search(search_params)
                prev_hierarchy = self.env['tt.customer.job.position'].search([
                    ('sequence', '>', context['co_job_position_sequence'])], order='sequence', limit=1)
                prev_hi_seq = prev_hierarchy and prev_hierarchy[0].sequence or context['co_job_position_sequence'] + 1
            else:
                return ERR.get_error(1023)
            res = []
            for rec in request_list:
                temp_dict = rec.to_dict(False)
                if rec.state in ['draft', 'on_process'] and rec.cur_approval_seq == prev_hi_seq:
                    dir_approval = True
                else:
                    dir_approval = False
                temp_dict.update({
                    'direct_approval': dir_approval
                })
                res.append(temp_dict)
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1012)

    def approve_issued_request_api(self, req, context):
        try:
            if req.get('request_id'):
                request_obj = self.browse(int(req['request_id']))
            else:
                request_obj = self.search([('name', '=', req['request_number'])], limit=1)
            if not request_obj:
                return ERR.get_error(1003)

            if context.get('co_customer_seq_id') and context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and request_obj.cur_approval_seq > context.get('co_job_position_sequence'):
                for rec in request_obj.approval_ids:
                    if rec.approved_cuid.seq_id == context['co_customer_seq_id']:
                        return ERR.get_error(1023, additional_message='You have already approved this request.')
                request_obj.action_approve_issued_request(context)
            else:
                return ERR.get_error(1023)

            res = request_obj.to_dict()
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1039)

    def action_approve_issued_request(self, context):
        co_uid = self.env['res.users'].browse(context['co_uid'])
        co_cuid = self.env['tt.customer'].search([('seq_id', '=', context['co_customer_seq_id'])], limit=1)
        booker_objs = self.env['tt.customer.parent.booker.rel'].search([
            ('customer_parent_id', '=', context['co_customer_parent_id']), ('customer_id', '=', co_cuid.id)])
        job_pos_obj = False
        for book in booker_objs:
            if book.job_position_id.sequence == context['co_job_position_sequence']:
                job_pos_obj = book.job_position_id

        self.env['tt.reservation.request.approval'].create({
            'request_id': self.id,
            'approved_date': datetime.now(),
            'approved_uid': co_uid.id,
            'approved_cuid': co_cuid.id,
            'approved_job_position_id': job_pos_obj and job_pos_obj.id or False,
        })

        min_approval = context.get('co_job_position_min_approve_amt', 1)
        for rec in self.approval_ids:
            if rec.approved_job_position_id.sequence <= context['co_job_position_sequence']:
                min_approval -= 1
        if min_approval < 1:
            self.cur_approval_seq = context['co_job_position_sequence']
        next_hierarchy = self.env['tt.customer.job.position'].search([
            ('sequence', '<', self.cur_approval_seq)], order='sequence desc', limit=1)
        if not next_hierarchy:
            if self.state != 'approved':
                ### email yg request permission to approve, hanya email 1x
                self.send_email_approval_to_user()
            self.state = 'approved'
        elif self.state == 'draft':
            self.state = 'on_process'
            if min_approval == -1:
                ## jumlah approval sudah sesuai & request approval ke job yg lebih tinggi
                book_obj = self.env[self.res_model].browse(self.res_id)
                upline_user_list_id = book_obj.customer_parent_id.get_upline_user_customer_parent(next_hierarchy)
                for rec in upline_user_list_id:
                    self.env['tt.reservation.request.res.users.rel'].create({
                        "reservation_request_id": self.id,
                        "user_id": rec
                    })

                self.env.cr.commit()
                self.send_email_to_upline()
                ## send email to upline

    def send_email_approval_to_user(self):
        template = self.env.ref('tt_reservation_request.template_mail_approval_issued', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    def cancel_issued_request_api(self, req, context):
        try:
            if req.get('request_id'):
                request_obj = self.browse(int(req['request_id']))
            else:
                request_obj = self.search([('name', '=', req['request_number'])], limit=1)
            if not request_obj:
                return ERR.get_error(1003)

            if context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and (request_obj.cur_approval_seq > context.get('co_job_position_sequence') or request_obj.booker_id.seq_id == context.get('co_customer_seq_id')):
                request_obj.action_cancel(context)
            else:
                return ERR.get_error(1023)

            res = request_obj.to_dict()
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1039)

    def reject_issued_request_api(self, req, context):
        try:
            if req.get('request_id'):
                request_obj = self.browse(int(req['request_id']))
            else:
                request_obj = self.search([('name', '=', req['request_number'])], limit=1)
            if not request_obj:
                return ERR.get_error(1003)

            if context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and request_obj.cur_approval_seq > context.get('co_job_position_sequence'):
                for rec in request_obj.approval_ids:
                    if rec.approved_cuid.seq_id == context['co_customer_seq_id']:
                        return ERR.get_error(1023, additional_message='You have already approved this request.')
                request_obj.action_reject(context)
            else:
                return ERR.get_error(1023)

            res = request_obj.to_dict()
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1039)

    def action_cancel(self, context={}):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 263')
        if self.state in ['draft', 'on_process']:
            if not context.get('co_uid'):
                context['co_uid'] = self.env.user.id
            self.state = 'cancel'
            self.cancel_uid = context['co_uid']
            self.cancel_date = datetime.now()
            if context.get('co_customer_seq_id'):
                cancel_cust = self.env['tt.customer'].search([('seq_id', '=', context['co_customer_seq_id'])], limit=1)
                self.cancel_cuid = cancel_cust.id

    def action_set_to_approved(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 264')
        self.state = 'approved'

    def action_reject(self, context={}):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 265')
        if self.state in ['draft', 'on_process']:
            if not context.get('co_uid'):
                context['co_uid'] = self.env.user.id
            self.state = 'rejected'
            self.reject_uid = context['co_uid']
            self.reject_date = datetime.now()
            if context.get('co_customer_seq_id'):
                reject_cust = self.env['tt.customer'].search([('seq_id', '=', context['co_customer_seq_id'])], limit=1)
                self.reject_cuid = reject_cust.id

    def action_set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_reservation_level_4'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 266')
        self.state = 'draft'


class TtReservationRequestApproval(models.Model):
    _name = 'tt.reservation.request.approval'
    _description = 'Reservation Request Approval Model'
    _order = 'approved_date'

    request_id = fields.Many2one('tt.reservation.request', 'Reservation Request', readonly=1)
    approved_date = fields.Datetime('Approved Date', readonly=1)
    approved_uid = fields.Many2one('res.users', 'Approved By', readonly=1)
    approved_cuid = fields.Many2one('tt.customer', 'Approved By Cust', readonly=1)
    approved_job_position_id = fields.Many2one('tt.customer.job.position', 'Job Position', readonly=1)

    def to_dict(self):
        return {
            'request_number': self.request_id.name,
            'approved_date': self.approved_date and self.approved_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'approved_by': self.approved_uid and self.approved_uid.name or '',
            'approved_by_customer': self.approved_cuid and self.approved_cuid.name or '',
            'approved_job_position': self.approved_job_position_id and self.approved_job_position_id.name or '',
            'approved_cust_seq_id': self.approved_cuid and self.approved_cuid.seq_id or '',
            'action': 'Approved'
        }

class ResUsersApiInherit(models.Model):
    _inherit = 'res.users'

    reservation_request_id = fields.One2many('tt.reservation.request.res.users.rel', 'user_id', 'Reservation Request', readonly=True)


class TtReservationRequestResUsersRel(models.Model):
    _name = 'tt.reservation.request.res.users.rel'
    _description = 'Tour & Travel - Customer Parent Booker Rel'

    reservation_request_id = fields.Many2one('tt.reservation.request', 'Reservation Request', required=True)
    user_id = fields.Many2one('res.users', 'Reservation Request', required=True)
    agent_id = fields.Many2one('tt.agent', 'Agent Type', related='reservation_request_id.agent_id', readonly=True)
    state = fields.Selection([('draft','Draft'), ('done','Done')], default='draft') ## STATE UNTUK KIRIM EMAIL


    def send_email_upline_request_issued(self):
        template = self.env.ref('tt_reservation_request.template_mail_request_issued', raise_if_not_found=False)
        template.send_mail(self.id, force_send=True)

    def get_reservation_data(self):
        return self.env[self.reservation_request_id.res_model].browse(self.reservation_request_id.res_id)
