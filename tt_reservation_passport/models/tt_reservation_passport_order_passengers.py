from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import traceback,logging
_logger = logging.getLogger(__name__)

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('validate', 'Validated'),
    ('re_validate', 'Re-Validate'),
    ('re_confirm', 'Re-Confirm'),
    ('cancel', 'Canceled'),
    ('in_process', 'In Process'),
    ('add_payment', 'Payment'),
    ('confirm_payment', 'Confirmed Payment'),
    ('in_process2', 'Processed by Consulate/Immigration'),
    ('waiting', 'Waiting'),
    ('proceed', 'Proceed'),
    ('rejected', 'Rejected'),
    ('accepted', 'Accepted'),
    ('to_HO', 'To HO'),
    ('to_agent', 'To Agent'),
    # ('ready', 'Ready'),
    ('done', 'Done')
]

BOOKING_STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm to HO'),
    ('validate', 'Validated by HO'),
    ('to_vendor', 'Send to Vendor'),
    ('vendor_process', 'Proceed by Vendor'),
    ('cancel', 'Canceled'),
    ('in_process', 'In Process'),
    ('partial_proceed', 'Partial Proceed'),
    ('proceed', 'Proceed'),
    ('done', 'Done')
]

PASSENGER_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

PROCESS_STATUS = [
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected')
]


class PassportInterviewBiometrics(models.Model):
    _name = 'tt.reservation.passport.interview.biometrics'
    _description = 'Passport Interview Biometrics'

    passenger_interview_id = fields.Many2one('tt.reservation.passport.order.passengers', 'Passenger', readonly=1)
    passenger_biometrics_id = fields.Many2one('tt.reservation.passport.order.passengers', 'Passenger', readonly=1)
    pricelist_interview_id = fields.Many2one('tt.reservation.passport.pricelist', 'Pricelist',
                                             related="passenger_interview_id.pricelist_id", readonly=1)
    location_interview_id = fields.Char('Location', compute='compute_location_interview', store=True)  # related="pricelist_interview_id.description"
    datetime = fields.Datetime('Datetime')
    ho_employee = fields.Char('Employee')
    meeting_point = fields.Char('Meeting Point')
    description = fields.Char('Description')

    @api.depends('datetime')
    @api.onchange('datetime')
    def compute_location_interview(self):
        for rec in self:
            rec.location_interview_id = rec.passenger_interview_id.pricelist_id.description


class PassportOrderPassengers(models.Model):
    _inherit = ['mail.thread', 'tt.reservation.passenger']
    _name = 'tt.reservation.passport.order.passengers'
    _description = 'Tour & Travel - Passport Order Passengers'

    to_requirement_ids = fields.One2many('tt.reservation.passport.order.requirements', 'to_passenger_id', 'Requirements',
                                         readonly=0, states={'done': [('readonly', True)]})  # readonly=0
    passport_id = fields.Many2one('tt.reservation.passport', 'Passport', readonly=1)  # readonly=1
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=1)  # readonly=1
    pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Passport Pricelist', readonly=1)  # readonly=1
    pricelist_id_str = fields.Char('Passport Pricelist', readonly=1, compute="_compute_passport_pricelist_id_str")
    passenger_type = fields.Selection(PASSENGER_TYPE, 'Pax Type', readonly=1)  # readonly=1
    age = fields.Char('Age', readonly=1, compute="_compute_age", store=True)
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Date(string='Passport Exp Date')
    process_status = fields.Selection(PROCESS_STATUS, string='Process Result',
                                      readonly=1)  # readonly=1

    interview = fields.Boolean('Needs Interview', readonly=0)
    interview_ids = fields.One2many('tt.reservation.passport.interview.biometrics', 'passenger_interview_id', 'Interview')

    in_process_date = fields.Datetime('In Process Date', readonly=1)  # readonly=1
    payment_date = fields.Datetime('Payment Date', readonly=1)  # readonly=1
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)  # readonly=1
    call_date = fields.Datetime('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=1)  # readonly=1
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=1)  # readonly=1
    done_date = fields.Datetime('Done Date', readonly=1)  # readonly=1
    expired_date = fields.Date('Expired Date', readonly=1)  # readonly=1

    # use_vendor = fields.Boolean('Use Vendor', readonly=1, related='passport_id.use_vendor')

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_passport_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges', readonly=1)
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_passport_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')

    notes = fields.Text('Notes (Agent to Customer)')
    notes_HO = fields.Text('Notes (HO to Agent)')

    booking_state = fields.Selection(BOOKING_STATE, default='draft', string='Order State', readonly=1,
                                     related='passport_id.state_passport', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                in_process = Documents proceed at Consulat or Imigration
                                                to_HO = documents sent to HO
                                                waiting = Documents ready at HO
                                                done = Documents given to customer''')  # readonly=1

    state = fields.Selection(STATE, default='confirm', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                in_process = before payment
                                                in_process2 = process by consulate/immigration
                                                waiting = waiting interview or photo
                                                proceed = Has Finished the requirements
                                                accepted = Accepted by the Immigration
                                                rejected = Rejected by the Immigration
                                                done = picked up by customer''')
    description = fields.Char('Description')

    @api.depends('pricelist_id')
    @api.onchange('pricelist_id')
    def _compute_passport_pricelist_id_str(self):
        for rec in self:
            rec.pricelist_id_str = rec.pricelist_id and rec.pricelist_id.name or ''

    def action_send_email_interview(self):
        """Dijalankan, jika user menekan tombol 'Send Email Interview'"""
        template = self.env.ref('tt_reservation_passport.template_mail_passport_interview')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        _logger.info("Email Sent")

    def action_fail_booked(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked'
            })
            rec.message_post(body='Passenger FAILED (Book)')

    def action_draft(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 218')
        for rec in self:
            rec.write({
                'state': 'draft'
            })
            if rec.passport_id.state_passport == 'confirm':
                rec.passport_id.action_draft_passport()
            rec.message_post(body='Passenger DRAFT')

    def action_confirm(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 219')
        for rec in self:
            rec.write({
                'state': 'confirm'
            })
            rec.message_post(body='Passenger CONFIRMED')

    def action_validate(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 220')
        for rec in self:
            for req in rec.to_requirement_ids:
                if req.is_copy is True or req.is_ori is True:
                    if req.validate_HO is False:
                        raise UserError(_('You have to Validate All Passengers Documents.'))
            rec.write({
                'state': 'validate'
            })
            all_validate = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state != 'validate':
                    all_validate = False
            if all_validate:
                rec.passport_id.action_validate_passport()
            else:
                rec.passport_id.action_partial_validate_passport()
            rec.message_post(body='Passenger VALIDATED')

    def action_re_validate(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 221')
        for rec in self:
            rec.write({
                'state': 're_validate',
            })
            rec.message_post(body='Passenger RE VALIDATE')

    def action_re_confirm(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 222')
        for rec in self:
            rec.write({
                'state': 're_confirm',
            })
            rec.message_post(body='Passenger RE CONFIRM')

    def action_cancel_button(self):
        self.passport_id.action_cancel_passport()

    def action_cancel(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 223')
        for rec in self:
            rec.passport_id.write({
                'state': 'cancel',
                'state_passport': 'cancel'
            })
            for psg in rec.passport_id.passenger_ids:
                psg.write({
                    'state': 'cancel'
                })
            if rec.passport_id.state_passport in ['in_process', 'payment']:
                rec.passport_id.write({
                    'can_refund': True
                })
            rec.message_post(body='Passenger CANCELED')

    def action_in_process(self):
        for rec in self:
            rec.write({
                'state': 'in_process'
            })
            rec.message_post(body='Passenger IN PROCESS')

    def action_add_payment(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 224')
        for rec in self:
            rec.write({
                'state': 'add_payment',
            })
            rec.message_post(body='Passenger compute_price ADD PAYMENT')
            rec.passport_id.action_payment_passport()

    def action_confirm_payment(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 225')
        for rec in self:
            rec.sudo().write({
                'state': 'confirm_payment',
                'payment_date': datetime.now(),
                'payment_uid': self.env.user.id
            })
            rec.message_post(body='Passenger CONFIRM PAYMENT')

    def action_in_process2(self):
        for rec in self:
            rec.write({
                'state': 'in_process2',
                'in_process_date': datetime.now()
            })
            rec.message_post(body='Passenger IN PROCESS')

    def action_waiting(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 226')
        for rec in self:
            rec.write({
                'state': 'waiting',
            })
            is_proceed = False
            for psg in rec.passport_id.passenger_ids:
                if psg.state == 'proceed':
                    is_proceed = True
            if is_proceed:
                rec.passport_id.action_partial_proceed_passport()
            rec.message_post(body='Passenger WAITING')

    def action_proceed(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 227')
        for rec in self:
            # jika interview dicentang & belum ada record interview, tidak bisa proceed
            if rec.interview is True:
                if not rec.interview_ids:
                    raise UserError(_('You have to add interview record.'))
            rec.write({
                'state': 'proceed',
            })
            rec.message_post(body='Passenger PROCEED')
            is_proceed = True
            is_approved = False
            for psg in rec.passport_id.passenger_ids:
                if psg.state not in ['proceed', 'cancel']:
                    is_proceed = False
                if psg.process_status == 'accepted':
                    is_approved = True
            # jika ada sebagian state passenger yang belum proceed -> partial proceed
            if not is_approved:
                if not is_proceed:
                    rec.passport_id.action_partial_proceed_passport()
                else:  # else -> proceed
                    rec.passport_id.action_proceed_passport()

    def action_reject(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 228')
        for rec in self:
            rec.write({
                'state': 'rejected',
                'process_status': 'rejected',
                'out_process_date': datetime.now()
            })
            all_reject = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state != 'rejected':
                    all_reject = False
            if all_reject:
                rec.passport_id.action_rejected_passport()
            rec.message_post(body='Passenger REJECTED')

    def action_accept(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 229')
        for rec in self:
            rec.write({
                'state': 'accepted',
                'process_status': 'accepted',
                'out_process_date': datetime.now()
            })
            all_approve = True
            for psg in rec.passport_id.passenger_ids:
                if psg.process_status != 'accepted':
                    all_approve = False
            if all_approve:
                rec.passport_id.action_approved_passport()
            else:
                rec.passport_id.action_partial_approved_passport()
            rec.message_post(body='Passenger ACCEPTED')

    def action_to_agent(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 230')
        for rec in self:
            rec.write({
                'state': 'to_agent',
                'to_agent_date': datetime.now()
            })
            rec.message_post(body='Passenger documents TO Agent')
            is_sent = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state not in ['to_agent']:
                    is_sent = False
            if is_sent:
                rec.passport_id.action_delivered_passport()

    def action_done(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 231')
        for rec in self:
            rec.write({
                'state': 'done',
                'done_date': datetime.now()
            })
            rec.message_post(body='Passenger DONE')
            is_done = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state not in ['done', 'cancel']:
                    is_done = False
            if is_done:
                rec.passport_id.action_done_passport()

    def action_sync_requirements(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 232')
        to_req_env = self.env['tt.reservation.passport.order.requirements']
        for rec in self:
            res = []
            for def_req in rec.pricelist_id.requirement_ids:
                if not rec.check_requirement(def_req.id):
                    vals = {
                        'requirement_id': def_req.id,
                        'to_passenger_id': rec.id,
                    }
                    to_req_obj = to_req_env.create(vals)
                    res.append(to_req_obj.id)
            for data in res:
                rec.write({
                    'to_requirement_ids': [(4, data)]
                })

    # def action_sync_handling(self):
    #     handling_env = self.env['tt.reservation.passport.order.handling']
    #     for rec in self:
    #         res = []
    #         handling_datas = rec.get_all_handling_data()
    #         for handling in handling_datas:
    #             if not rec.check_handling(handling.id):
    #                 vals = {
    #                     'handling_id': handling.id,
    #                     'to_passenger_id': rec.id,
    #                 }
    #                 handling_obj = handling_env.create(vals)
    #                 res.append(handling_obj.id)
    #         for data in res:
    #             rec.write({
    #                 'handling_ids': [(4, data)]
    #             })

    @api.depends('birth_date')
    @api.onchange('birth_date')
    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                today = date.today()
                range_date = relativedelta(today, rec.birth_date)
                age = str(range_date.years) + 'y ' + str(range_date.months) + 'm ' + str(range_date.days) + 'd'
                rec.age = age

    def check_requirement(self, req_id):
        for rec in self:
            for to_req in rec.to_requirement_ids:
                if to_req.requirement_id.id == req_id:
                    return True
            return False

    # def check_handling(self, handling_id):
    #     for rec in self:
    #         for handling in rec.handling_ids:
    #             if handling.handling_id.id == handling_id:
    #                 return True
    #         return False
