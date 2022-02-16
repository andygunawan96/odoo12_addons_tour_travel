from odoo import api, fields, models, _
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

    name = fields.Char('Request Number', index=True, default='New', readonly=True)
    res_model = fields.Char('Reservation Name', index=True, readonly=True)
    res_id = fields.Integer('Reservation ID', index=True, help='Id of the followed resource', readonly=True)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', readonly=True)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, default=lambda self: self.env.user.agent_id, readonly=True, states={'draft': [('readonly', False)]})
    agent_type_id = fields.Many2one('tt.agent.type', 'Agent Type', related='agent_id.agent_type_id', readonly=True, store=True)
    customer_parent_id = fields.Many2one('tt.customer.parent', 'Customer', readonly=True, states={'draft': [('readonly', False)]}, help='COR / POR')
    customer_parent_type_id = fields.Many2one('tt.customer.parent.type', 'Customer Type', related='customer_parent_id.customer_parent_type_id', store=True, readonly=True)
    approval_ids = fields.One2many('tt.reservation.request.approval', 'request_id', 'Approved By', readonly=True)
    cur_approval_seq = fields.Integer('Current Approval Sequence', readonly=True, default=10)
    booker_job_position_id = fields.Many2one('tt.customer.job.position', 'Booker Job Position', readonly=1, compute='_compute_booker_job_position')
    state = fields.Selection([('draft', 'Draft'), ('on_process', 'On Process'), ('approved', 'Approved'),
                              ('rejected', 'Rejected'), ('cancel', 'Cancelled')], 'State', default='draft')
    cancel_uid = fields.Many2one('res.users', 'Cancelled By', readonly=True)
    cancel_date = fields.Datetime('Cancelled Date', readonly=True)
    reject_uid = fields.Many2one('res.users', 'Rejected By', readonly=True)
    reject_date = fields.Datetime('Rejected Date', readonly=True)

    @api.model
    def create(self, vals_list):
        try:
            vals_list['name'] = self.env['ir.sequence'].next_by_code('tt.reservation.request')
        except:
            pass
        return super(TtReservationRequest, self).create(vals_list)

    @api.depends('booker_id', 'customer_parent_id')
    @api.onchange('booker_id', 'customer_parent_id')
    def _compute_booker_job_position(self):
        booker_obj = self.env['tt.customer.parent.booker.rel'].search(
            [('customer_parent_id', '=', self.customer_parent_id.id), ('customer_id', '=', self.booker_id.id)], limit=1)
        if booker_obj:
            self.booker_job_position_id = booker_obj.job_position_id.id
        else:
            self.booker_job_position_id = False

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
            'current_approval_sequence': self.cur_approval_seq,
            'state': self.state,
            'state_description': request_state_str[self.state],
            'created_date': self.create_date,
            'created_by': self.create_uid.name
        }
        if with_approval:
            final_dict.update({
                'approvals': [rec.to_dict() for rec in self.approval_ids]
            })
        return final_dict

    def get_issued_request_api(self,req,context):
        try:
            if context.get('co_customer_parent_id') and context.get('co_hierarchy_sequence'):
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
            if context.get('co_customer_parent_id') and context.get('co_hierarchy_sequence'):
                request_list = self.search([('agent_id', '=', context['co_agent_id']),
                                            ('customer_parent_id', '=', context['co_customer_parent_id']),
                                            ('state', 'in', ['draft', 'on_process']),
                                            ('cur_approval_seq', '>', context['co_hierarchy_sequence'])])
                prev_hierarchy = self.env['tt.customer.job.hierarchy'].search([
                    ('sequence', '>', context['co_hierarchy_sequence'])], order='sequence', limit=1)
                prev_hi_seq = prev_hierarchy and prev_hierarchy[0].sequence or context['co_hierarchy_sequence'] + 1
            else:
                return ERR.get_error(1023)
            res = []
            for rec in request_list:
                temp_dict = rec.to_dict(False)
                temp_dict.update({
                    'direct_approval': rec.cur_approval_seq == prev_hi_seq and True or False
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

            if context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and request_obj.cur_approval_seq > context.get('co_hierarchy_sequence'):
                for rec in request_obj.approval_ids:
                    if rec.approved_uid.id == int(context['co_uid']):
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
        booker_objs = self.env['tt.customer.parent.booker.rel'].search([
            ('customer_parent_id', '=', context['co_customer_parent_id']), ('customer_id', '=', co_uid.customer_id.id)])
        job_pos_obj = False
        for book in booker_objs:
            if book.job_position_id.sequence == context['co_job_position_sequence']:
                job_pos_obj = book.jos_position_id

        self.env['tt.reservation.request.approval'].create({
            'request_id': self.id,
            'approved_date': datetime.now(),
            'approved_uid': co_uid.id,
            'approved_job_position_id': job_pos_obj and job_pos_obj.id or False,
        })

        min_approval = context.get('co_hierarchy_min_approve_amt', 1)
        for rec in self.approval_ids:
            if rec.approved_job_position_id.hierarchy_id == context['co_hierarchy_sequence']:
                min_approval -= 1
        if min_approval <= 0:
            self.cur_approval_seq = context['co_hierarchy_sequence']
        next_hierarchy = self.env['tt.customer.job.hierarchy'].search([
            ('sequence', '<', self.cur_approval_seq)], order='sequence desc', limit=1)
        if not next_hierarchy:
            self.state = 'approved'
        elif self.state == 'draft':
            self.state = 'on_process'

    def cancel_issued_request_api(self, req, context):
        try:
            if req.get('request_id'):
                request_obj = self.browse(int(req['request_id']))
            else:
                request_obj = self.search([('name', '=', req['request_number'])], limit=1)
            if not request_obj:
                return ERR.get_error(1003)

            if context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and (request_obj.cur_approval_seq > context.get('co_hierarchy_sequence') or request_obj.create_uid.id == context.get('co_uid')):
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

            if context.get('co_agent_id') == request_obj.agent_id.id and context.get('co_customer_parent_id') == request_obj.customer_parent_id.id and request_obj.cur_approval_seq > context.get('co_hierarchy_sequence'):
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
        if self.state in ['draft', 'on_process']:
            if not context.get('co_uid'):
                context['co_uid'] = self.env.user.id
            self.state = 'cancel'
            self.cancel_uid = context['co_uid']
            self.cancel_date = datetime.now()

    def action_set_to_approved(self):
        self.state = 'approved'

    def action_reject(self, context={}):
        if self.state in ['draft', 'on_process']:
            if not context.get('co_uid'):
                context['co_uid'] = self.env.user.id
            self.state = 'rejected'
            self.reject_uid = context['co_uid']
            self.reject_date = datetime.now()

    def action_set_to_draft(self):
        self.state = 'draft'


class TtReservationRequestApproval(models.Model):
    _name = 'tt.reservation.request.approval'
    _description = 'Reservation Request Approval Model'

    request_id = fields.Many2one('tt.reservation.request', 'Reservation Request', readonly=1)
    approved_date = fields.Datetime('Approved Date', readonly=1)
    approved_uid = fields.Many2one('res.users', 'Approved By', readonly=1)
    approved_job_position_id = fields.Many2one('tt.customer.job.position', 'Job Position', readonly=1)

    def to_dict(self):
        return {
            'request_number': self.request_id.name,
            'approved_date': self.approved_date and self.approved_date.strftime('%Y-%m-%d %H:%M:%S') or '',
            'approved_uid': self.approved_uid and self.approved_uid.name or '',
            'approved_job_position': self.approved_job_position_id and self.approved_job_position_id.name or '',
        }
