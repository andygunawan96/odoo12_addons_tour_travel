from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import traceback,logging
_logger = logging.getLogger(__name__)

STATE = [
    ('fail_booked', 'Failed (Book)'),
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


class VisaInterviewBiometrics(models.Model):
    _name = 'tt.reservation.visa.interview.biometrics'
    _description = 'Visa Interview Biometrics'

    passenger_interview_id = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger', readonly=1)
    passenger_biometrics_id = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger', readonly=1)
    pricelist_interview_id = fields.Many2one('tt.reservation.visa.pricelist', 'Pricelist',
                                             related="passenger_interview_id.pricelist_id", readonly=1)
    pricelist_biometrics_id = fields.Many2one('tt.reservation.visa.pricelist', 'Pricelist',
                                              related="passenger_biometrics_id.pricelist_id", readonly=1)
    location_interview_id = fields.Char('Location', compute='compute_location_interview', store=True)
    location_biometrics_id = fields.Char('Location', compute='compute_location_biometrics', store=True)
    datetime = fields.Datetime('Datetime')
    ho_employee = fields.Char('Employee')
    meeting_point = fields.Char('Meeting Point')
    description = fields.Char('Description')

    @api.depends('datetime')
    @api.onchange('datetime')
    def compute_location_interview(self):
        for rec in self:
            rec.location_interview_id = rec.passenger_interview_id.pricelist_id.description

    @api.depends('datetime')
    @api.onchange('datetime')
    def compute_location_biometrics(self):
        for rec in self:
            rec.location_biometrics_id = rec.passenger_biometrics_id.pricelist_id.description


class VisaOrderPassengers(models.Model):
    _inherit = ['mail.thread', 'tt.reservation.passenger']
    _name = 'tt.reservation.visa.order.passengers'
    _description = 'Tour & Travel - Visa Order Passengers'

    to_requirement_ids = fields.One2many('tt.reservation.visa.order.requirements', 'to_passenger_id', 'Requirements',
                                         readonly=0, states={'done': [('readonly', True)]})
    visa_id = fields.Many2one('tt.reservation.visa', 'Visa', readonly=1)  # readonly=1
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=1)  # readonly=1
    pricelist_id = fields.Many2one('tt.reservation.visa.pricelist', 'Visa Pricelist', readonly=1)  # readonly=1
    pricelist_id_str = fields.Char('Visa Pricelist', readonly=True, compute="_compute_visa_pricelist_id_str")
    passenger_type = fields.Selection(PASSENGER_TYPE, 'Pax Type', readonly=1)  # readonly=1
    age = fields.Char('Age', readonly=1, compute="_compute_age", store=True)
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Date(string='Passport Exp Date')
    process_status = fields.Selection(PROCESS_STATUS, string='Process Result',
                                      readonly=1)  # readonly=1

    interview = fields.Boolean('Needs Interview')
    biometrics = fields.Boolean('Needs Biometrics')
    interview_ids = fields.One2many('tt.reservation.visa.interview.biometrics', 'passenger_interview_id', 'Interview')
    biometrics_ids = fields.One2many('tt.reservation.visa.interview.biometrics', 'passenger_biometrics_id',
                                     'Biometrics')

    handling_ids = fields.One2many('tt.reservation.visa.order.handling', 'to_passenger_id', 'Handling Questions')
    handling_information = fields.Text('Handling Information')

    in_process_date = fields.Datetime('In Process Date', readonly=1)  # readonly=1
    payment_date = fields.Datetime('Payment Date', readonly=1)  # readonly=1
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)  # readonly=1
    call_date = fields.Date('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=1)
    to_HO_date = fields.Datetime('Send to HO Date', readonly=1)
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=1)
    done_date = fields.Datetime('Done Date', readonly=1)
    expired_date = fields.Date('Expired Date', readonly=1)

    use_vendor = fields.Boolean('Use Vendor', readonly=1, related='visa_id.use_vendor')

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_visa_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges', readonly=1)
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_visa_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')

    notes = fields.Text('Notes (Agent to Customer)')
    notes_HO = fields.Text('Notes (HO to Agent)')

    booking_state = fields.Selection(BOOKING_STATE, default='draft', string='Order State', readonly=1,
                                     related='visa_id.state_visa', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                to_vendor = Documents sent to Vendor
                                                vendor_process = Documents proceed by Vendor
                                                in_process = Documents proceed at Consulate
                                                to_HO = documents sent to HO
                                                waiting = Documents ready at HO
                                                done = Documents given to customer''')

    can_refund = fields.Boolean('Can Refund', related='visa_id.can_refund')

    state = fields.Selection(STATE, default='confirm', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                in_process = before payment
                                                in_process2 = process by consulate/immigration
                                                waiting = waiting interview or photo
                                                proceed = Has Finished the requirements
                                                accepted = Accepted by the Consulate
                                                rejected = Rejected by the Consulate
                                                done = Document at agent or picked up by customer''')
    is_ticketed = fields.Boolean('Ticketed')
    price_list_code = fields.Char('Visa Pricelist Code')

    @api.depends('pricelist_id')
    @api.onchange('pricelist_id')
    def _compute_visa_pricelist_id_str(self):
        for rec in self:
            rec.pricelist_id_str = rec.pricelist_id and rec.pricelist_id.name or ''

    def action_send_email_interview(self):
        """Dijalankan, jika user menekan tombol 'Send Email Interview'"""
        template = self.env.ref('tt_reservation_visa.template_mail_visa_interview')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        _logger.info("Email Interview Sent")

    def action_send_email_biometrics(self):
        """Dijalankan, jika user menekan tombol 'Send Email Biometrics'"""
        template = self.env.ref('tt_reservation_visa.template_mail_visa_biometrics')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        _logger.info("Email Biometrics Sent")

    def action_fail_booked(self):
        for rec in self:
            rec.write({
                'state': 'fail_booked'
            })
            rec.message_post(body='Passenger FAILED (Book)')

    def action_draft(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 335')
        for rec in self:
            rec.write({
                'state': 'draft'
            })
            # set juga state visa_id ke draft
            if rec.visa_id.state_visa == 'confirm':
                rec.visa_id.action_draft_visa()
            elif rec.visa_id.state_visa == 'cancel':
                is_all_draft = True
                for psg in rec.visa_id.passenger_ids:
                    if psg.state not in ['draft']:
                        is_all_draft = False
                if is_all_draft:
                    rec.visa_id.action_draft_visa()
            rec.message_post(body='Passenger DRAFT')

    def action_confirm(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 336')
        for rec in self:
            rec.write({
                'state': 'confirm'
            })
            rec.message_post(body='Passenger CONFIRMED')

    def action_validate(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 337')
        for rec in self:
            for req in rec.to_requirement_ids:
                if req.is_copy is True or req.is_ori is True:
                    if req.validate_HO is False:
                        raise UserError(_('You have to Validate All Passengers Documents.'))
            rec.write({
                'state': 'validate'
            })
            all_validate = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state != 'validate':
                    all_validate = False
            if all_validate:
                rec.visa_id.action_validate_visa()
            else:
                rec.visa_id.action_partial_validate_visa()
            rec.message_post(body='Passenger VALIDATED')

    def action_validate_api(self):
        for rec in self:
            for req in rec.to_requirement_ids:
                if req.is_copy is True:
                    req.is_copy = True
                elif req.is_ori is True:
                    req.is_ori = True
            rec.write({
                'state': 'validate'
            })
            all_validate = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state != 'validate':
                    all_validate = False
            if all_validate:
                rec.visa_id.action_validate_visa()
            else:
                rec.visa_id.action_partial_validate_visa()
            rec.message_post(body='Passenger VALIDATED')

    def action_re_validate(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 338')
        for rec in self:
            rec.write({
                'state': 're_validate',
            })
            rec.message_post(body='Passenger RE VALIDATE')
            rec.visa_id.sync_status_btbo2('re_validate')

    def action_re_confirm(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 339')
        for rec in self:
            rec.write({
                'state': 're_confirm',
            })
            rec.message_post(body='Passenger RE CONFIRM')
            rec.visa_id.sync_status_btbo2('re_confirm')

    def action_cancel_button(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 340')
        self.visa_id.action_cancel_visa()

    def action_cancel(self):
        for rec in self:
            rec.visa_id.write({
                'state': 'cancel',
                'state_visa': 'cancel'
            })
            for psg in rec.visa_id.passenger_ids:
                psg.write({
                    'state': 'cancel'
                })
            if rec.visa_id.state_visa in ['in_process','payment']:
                rec.visa_id.write({
                    'can_refund': True
                })
            rec.message_post(body='Passenger CANCELED')
            rec.visa_id.sync_status_btbo2('cancel')

    def action_in_process(self):
        for rec in self:
            rec.write({
                'state': 'in_process'
            })
            rec.message_post(body='Passenger IN PROCESS')

    def action_add_payment(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 341')
        for rec in self:
            rec.write({
                'state': 'add_payment',
            })
            rec.message_post(body='Passenger compute_price ADD PAYMENT')
            rec.visa_id.action_payment_visa()

    def action_confirm_payment(self):
        if not ({self.env.ref('tt_base.group_reservation_level_4').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 342')
        for rec in self:
            rec.sudo().write({
                'state': 'confirm_payment',
                'payment_date': datetime.now(),
                'payment_uid': self.env.user.id
            })
            rec.message_post(body='Passenger CONFIRM PAYMENT')

    def action_confirm_payment_api(self):
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
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 343')
        for rec in self:
            rec.write({
                'state': 'waiting',
            })
            is_proceed = False
            for psg in rec.visa_id.passenger_ids:
                if psg.state == 'proceed':
                    is_proceed = True
            if is_proceed:
                rec.visa_id.action_partial_proceed_visa()
            rec.message_post(body='Passenger WAITING')
            rec.visa_id.sync_status_btbo2('waiting')

    def action_proceed(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 344')
        for rec in self:
            # jika interview / biometrics dicentang & belum ada record interview / biometrics, tidak bisa proceed
            if rec.interview is True:
                if not rec.interview_ids:
                    raise UserError(_('You have to add interview record.'))
            if rec.biometrics is True:
                if not rec.biometrics_ids:
                    raise UserError(_('You have to add biometrics record.'))
            rec.write({
                'state': 'proceed',
            })
            rec.visa_id.sync_status_btbo2('proceed')
            rec.message_post(body='Passenger PROCEED')
            is_proceed = True
            is_approved = False
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['proceed', 'cancel']:
                    is_proceed = False
                if psg.process_status == 'accepted':
                    is_approved = True
            # jika ada sebagian state passenger yang belum proceed -> partial proceed
            if not is_approved:
                if not is_proceed:
                    rec.visa_id.action_partial_proceed_visa()
                else:  # else -> proceed
                    rec.visa_id.action_proceed_visa()

    def action_reject(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 345')
        for rec in self:
            rec.write({
                'state': 'rejected',
                'process_status': 'rejected',
                'out_process_date': datetime.now()
            })
            all_reject = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state != 'rejected':
                    all_reject = False
            if all_reject:
                rec.visa_id.action_rejected_visa()
            rec.visa_id.sync_status_btbo2('rejected')
            rec.message_post(body='Passenger REJECTED')

    def action_accept(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 346')
        for rec in self:
            rec.write({
                'state': 'accepted',
                'process_status': 'accepted',
                'out_process_date': datetime.now()
            })
            all_approve = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state != 'accepted':
                    all_approve = False
            if all_approve:
                rec.visa_id.action_approved_visa()
            else:
                rec.visa_id.action_partial_approved_visa()
            rec.visa_id.sync_status_btbo2('accept')
            rec.message_post(body='Passenger ACCEPTED')

    def action_to_HO(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 347')
        for rec in self:
            rec.write({
                'state': 'to_HO',
                'to_HO_date': datetime.now()
            })
            rec.visa_id.sync_status_btbo2('to_HO')
            rec.message_post(body='Passenger documents TO HO')
            is_sent = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['to_HO']:
                    is_sent = False
            if is_sent:
                rec.visa_id.action_delivered_visa()

    def action_to_agent(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 348')
        for rec in self:
            rec.write({
                'state': 'to_agent',
                'to_agent_date': datetime.now()
            })
            rec.visa_id.sync_status_btbo2('to_agent')
            rec.message_post(body='Passenger documents TO Agent')
            if rec.visa_id.state_visa != 'delivered':
                is_sent = True
                for psg in rec.visa_id.passenger_ids:
                    if psg.state not in ['to_agent']:
                        is_sent = False
                if is_sent:
                    rec.visa_id.action_delivered_visa()

    # def action_ready(self):
    #     for rec in self:
    #         rec.write({
    #             'state': 'ready',
    #             'ready_date': datetime.now(),
    #         })
    #         rec.message_post(body='Passenger documents READY')
    #         rec.visa_id.action_ready_visa()

    def action_done(self):
        if not ({self.env.ref('tt_base.group_tt_agent_user').id, self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 349')
        for rec in self:
            rec.write({
                'state': 'done',
                'done_date': datetime.now()
            })
            rec.visa_id.sync_status_btbo2('done')
            rec.message_post(body='Passenger DONE')
            is_done = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['done', 'cancel']:
                    is_done = False
            if is_done:
                rec.visa_id.action_done_visa()

    def get_all_handling_data(self):
        return self.env['tt.master.visa.handling'].search([])

    def action_sync_requirements(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 350')
        to_req_env = self.env['tt.reservation.visa.order.requirements']
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

    def action_sync_handling(self):
        if not ({self.env.ref('tt_base.group_tt_tour_travel').id, self.env.ref('base.group_erp_manager').id, self.env.ref('base.group_system').id}.intersection(set(self.env.user.groups_id.ids))):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 351')
        handling_env = self.env['tt.reservation.visa.order.handling']
        for rec in self:
            res = []
            handling_datas = rec.get_all_handling_data()
            for handling in handling_datas:
                if not rec.check_handling(handling.id):
                    vals = {
                        'handling_id': handling.id,
                        'to_passenger_id': rec.id,
                    }
                    handling_obj = handling_env.create(vals)
                    res.append(handling_obj.id)
            for data in res:
                rec.write({
                    'handling_ids': [(4, data)]
                })

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

    def check_handling(self, handling_id):
        for rec in self:
            for handling in rec.handling_ids:
                if handling.handling_id.id == handling_id:
                    return True
            return False

    # butuh field cost_service_charge_ids
    # def get_service_charges(self):
    #     sc_value = {}
    #     for p_sc in self.cost_service_charge_ids:
    #         p_charge_type = p_sc.charge_type
    #         pnr = p_sc.description
    #         if not sc_value.get(pnr):
    #             sc_value[pnr] = {}
    #         if not sc_value[pnr].get(p_charge_type):
    #             sc_value[pnr][p_charge_type] = {}
    #             sc_value[pnr][p_charge_type].update({
    #                 'amount': 0,
    #                 'foreign_amount': 0,
    #             })
    #
    #         if p_charge_type == 'RAC' and p_sc.charge_code != 'rac':
    #             if p_charge_type == 'RAC' and 'csc' not in p_sc.charge_code:
    #                 continue
    #
    #         sc_value[pnr][p_charge_type].update({
    #             'charge_code': p_sc.charge_code,
    #             'currency': p_sc.currency_id.name,
    #             'foreign_currency': p_sc.foreign_currency_id.name,
    #             'amount': sc_value[pnr][p_charge_type]['amount'] + p_sc.amount,
    #             # 'amount': p_sc.amount,
    #             'foreign_amount': sc_value[pnr][p_charge_type]['foreign_amount'] + p_sc.foreign_amount,
    #             'pax_type': p_sc.pax_type #untuk ambil pax_type to_dict
    #             # 'foreign_amount': p_sc.foreign_amount,
    #         })
    #
    #     return sc_value

    # butuh field channel_service_charge_ids
    def get_channel_service_charges(self):
        total = 0
        currency_code = 'IDR'
        for rec in self.channel_service_charge_ids:
            total += rec.amount
            currency_code = rec.currency_id.name

        return {
            'amount': total,
            'currency_code': currency_code
        }
