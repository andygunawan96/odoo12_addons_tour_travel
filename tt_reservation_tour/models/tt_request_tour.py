from odoo import api, fields, models, _
from ...tools import variables
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
import json
import base64
import logging
import traceback

_logger = logging.getLogger(__name__)
CLASS_OF_SERVICE = [
    ('economy', 'Economy'),
    ('Premium', 'Premium'),
    ('Business', 'Business'),
    ('first', 'First'),
]


class TtRequestTour(models.Model):
    _name = 'tt.request.tour'
    _inherit = 'tt.history'
    _order = 'id desc'
    _description = 'Request Tour'

    name = fields.Char('Request Order Number', default='New', readonly=True)

    def _get_ho_id_domain(self):
        return [('agent_type_id', '=', self.env.ref('tt_base.agent_type_ho').id)]

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=_get_ho_id_domain, required=False, readonly=True, default=lambda self: self.env.user.ho_id.id)
    agent_id = fields.Many2one('tt.agent', 'Agent', required=True, readonly=True, default=lambda self: self.env.user.agent_id.id)
    booker_id = fields.Many2one('tt.customer', 'Booker', ondelete='restrict', required=True, readonly=True, states={'draft':[('readonly',False)]}, domain="[('agent_id', '=', agent_id)]")
    contact_id = fields.Many2one('tt.customer', 'Contact Person', ondelete='restrict', required=True, readonly=True, states={'draft':[('readonly',False)]}, domain="[('agent_id', '=', agent_id)]")
    contact_number = fields.Char('Contact Number', required=True, readonly=True, states={'draft': [('readonly', False)]})
    contact_email = fields.Char('Contact Email', required=True, readonly=True, states={'draft': [('readonly', False)]})
    contact_address = fields.Char('Contact Address', required=True, readonly=True, states={'draft': [('readonly', False)]})
    tour_ref_id = fields.Many2one('tt.master.tour', 'Created Tour Package', domain="[('tour_category', '=', 'private'), ('agent_id', '=', agent_id)]")
    tour_ref_id_str = fields.Text('Created Tour Package', readonly=True, compute='_compute_tour_ref_id_str')
    tour_category = fields.Selection([('medical', 'Medical'),('education', 'Education'),('recreation', 'Recreation (Family / Group / Insentif / Corporate)'),
                                      ('meeting', 'Meeting'),('training', 'Training'),('religious', 'Religious Tour (Pilgrimage / Jerusalem / etc)'),
                                      ('cruise', 'Cruise'),('other', 'Other (Please Specify in Notes)')], 'Tour Category', default='recreation', required=True, readonly=True,
                                     states={'draft': [('readonly', False)]})
    est_departure_date = fields.Date('Estimated Departure Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    est_arrival_date = fields.Date('Estimated Return Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    est_departure_time = fields.Selection([('morning', 'Morning'), ('afternoon', 'Afternoon'), ('night', 'Night')], 'Estimated Departure Time', default='morning', required=True, readonly=True, states={'draft': [('readonly', False)]})
    est_return_time = fields.Selection([('morning', 'Morning'), ('afternoon', 'Afternoon'), ('night', 'Night')], 'Estimated Return Time', default='morning', required=True, readonly=True, states={'draft': [('readonly', False)]})
    location_ids = fields.Many2many('tt.tour.master.locations', 'tt_request_tour_location_rel', 'request_id',
                                    'location_id', string='Location', required=True, readonly=True, states={'draft': [('readonly', False)]})
    adult = fields.Integer('Adult (12-120 y.o)', default=1, required=True, readonly=True, states={'draft': [('readonly', False)]})
    child = fields.Integer('Child (2-11 y.o)', default=0, required=True, readonly=True, states={'draft': [('readonly', False)]})
    infant = fields.Integer('Infant (0-1 y.o)', default=0, required=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    min_budget = fields.Monetary('Min. Budget', default=0, readonly=True, states={'draft': [('readonly', False)]})
    max_budget = fields.Monetary('Max. Budget', default=0, readonly=True, states={'draft': [('readonly', False)]})
    hotel_star = fields.Selection([(0, 'No Preference'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'), (7, '7')], 'Hotel Star', default=0, readonly=True, states={'draft': [('readonly', False)]})
    est_hotel_price = fields.Monetary('Estimated Hotel Price', default=0, readonly=True, states={'draft': [('readonly', False)]})
    carrier_id = fields.Many2one('tt.transport.carrier', 'Airline Carrier', readonly=True, states={'draft': [('readonly', False)]}, domain=[('provider_type_id.name', '=', 'Airline')])
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Service Class', readonly=True, states={'draft': [('readonly', False)]})
    food_preference = fields.Selection([('no_preference', 'No Preference'), ('halal', 'Halal')], 'Food Preference', default='no_preference', readonly=True, states={'draft': [('readonly', False)]})
    notes = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    confirm_date = fields.Datetime('Confirm Date', readonly=True)
    confirm_uid = fields.Many2one('res.users', 'Confirmed by', readonly=True)
    approve_date = fields.Datetime('Approved Date', readonly=True)
    approve_uid = fields.Many2one('res.users', 'Approved by', readonly=True)
    done_date = fields.Datetime('Done Date', readonly=True)
    done_uid = fields.Many2one('res.users', 'Done by', readonly=True)
    reject_date = fields.Datetime('Rejected Date', readonly=True)
    reject_uid = fields.Many2one('res.users', 'Rejected by', readonly=True)
    cancel_date = fields.Datetime('Cancelled Date', readonly=True)
    cancel_uid = fields.Many2one('res.users', 'Cancelled by', readonly=True)
    state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirmed'), ('approved', 'Approved (In Process)'),
                              ('done', 'Done'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], 'State', default='draft')
    file_name = fields.Char("Filename", compute="_compute_filename", store=True)
    export_data = fields.Binary('Export JSON')

    @api.depends('tour_ref_id')
    @api.onchange('tour_ref_id')
    def _compute_tour_ref_id_str(self):
        for rec in self:
            rec.tour_ref_id_str = rec.tour_ref_id and rec.tour_ref_id.name or ''

    @api.depends("name")
    def _compute_filename(self):
        for rec in self:
            rec.file_name = rec.name + ".json"

    def action_send_email_notification(self):
        template = self.env.ref('tt_reservation_tour.template_mail_tour_request')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id, force_send=True)

    def action_confirm(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 308')
        if self.state != 'draft':
            raise UserError("Cannot Confirm because state is not 'draft'.")

        if self.adult < 1:
            raise UserError("Tour Request must have at least 1 Adult Passenger.")

        if self.est_departure_date >= self.est_arrival_date:
            raise UserError("Estimated Return Date must be later than Estimated Departure Date!")

        if self.min_budget > self.max_budget:
            raise UserError("Max. Budget must be greater than Min. Budget!")

        self.write({
            'name': self.env['ir.sequence'].next_by_code('request.tour') or 'New',
            'state': 'confirm',
            'confirm_uid': self.env.user.id,
            'confirm_date': datetime.now(),
        })
        self.env.cr.commit()

        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_num = self.env.ref('tt_reservation_tour.tt_request_tour_view_action').id
            menu_num = self.env.ref('tt_reservation_tour.submenu_request_tour_package').id

            data = {
                'url': base_url + "/web#id=" + str(self.id) + "&action=" + str(action_num) + "&model=tt.request.tour&view_type=form&menu_id=" + str(menu_num),
                'req_number': self.name
            }

            context = {
                'co_uid': self.env.user.id,
                'co_user_name': self.env.user.name,
                'co_agent_id': self.env.user.agent_id.id,
                'co_agent_name': self.env.user.agent_id.name,
            }
            self.env['tt.master.tour.api.con'].send_tour_request_notification(data, context)
        except Exception as e:
            _logger.error("Send Tour Request Notification Telegram Error\n" + traceback.format_exc())

        try:
            self.action_send_email_notification()
        except Exception as e:
            _logger.error("Send Tour Request Notification Email Error\n" + traceback.format_exc())

    def action_approve(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 309')
        if self.state != 'confirm':
            raise UserError("Cannot Approve because state is not 'confirm'.")

        self.write({
            'state': 'approved',
            'approve_uid': self.env.user.id,
            'approve_date': datetime.now(),
        })

    def action_done(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 310')
        if self.state != 'approved':
            raise UserError("Cannot Set to Done because state is not 'approved'.")

        self.write({
            'state': 'done',
            'done_uid': self.env.user.id,
            'done_date': datetime.now(),
        })

    def action_reject(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 311')
        self.write({
            'state': 'rejected',
            'reject_uid': self.env.user.id,
            'reject_date': datetime.now(),
        })

    def action_cancel(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 312')
        self.write({
            'state': 'cancelled',
            'cancel_uid': self.env.user.id,
            'cancel_date': datetime.now(),
        })

    def action_set_to_draft(self):
        if not self.env.user.has_group('tt_base.group_master_data_tour_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 313')
        self.write({
            'state': 'draft',
        })

    def export_to_json(self):
        location_list = []
        for rec in self.location_ids:
            location_list.append({
                'city_name': rec.city_id.name,
                'country_code': rec.country_id.code,
            })
        dict_data = {
            'tour_category': self.tour_category,
            'locations': location_list,
            'est_departure_date': self.est_departure_date.strftime('%d %B %Y'),
            'est_return_date': self.est_departure_date.strftime('%d %B %Y'),
            'est_departure_time': self.est_departure_time,
            'est_return_time': self.est_return_time,
            'adult': self.adult,
            'child': self.child,
            'infant': self.infant,
            'min_budget': self.min_budget,
            'max_budget': self.max_budget,
            'hotel_star': self.hotel_star,
            'est_hotel_price': self.est_hotel_price,
            'carrier_code': self.carrier_id.code,
            'class_of_service': self.class_of_service,
            'food_preference': self.food_preference,
            'notes': self.notes,
        }
        json_data = json.dumps(dict_data)
        self.sudo().write({
            'export_data': base64.b64encode(json_data.encode())
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def remove_export_json(self):
        self.sudo().write({
            'export_data': False
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
