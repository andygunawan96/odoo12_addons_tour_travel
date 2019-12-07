from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

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
    ('ready', 'Ready'),
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
    location_id = fields.Many2one('tt.master.visa.locations')  # self.get_domain_location() [] , domain=lambda self: self.onchange_pricelist() , domain=lambda self: [('id', 'in', self.passenger_interview_id.pricelist_id.visa_location_ids.ids)]
    datetime = fields.Datetime('Datetime')
    ho_employee = fields.Many2one('res.users', 'Employee', domain=lambda self: self.get_user_HO())
    meeting_point = fields.Char('Meeting Point')
    description = fields.Char('Description')

    @api.model
    def get_user_HO(self):
        return [('agent_id.name', '=', self.env.ref('tt_base.rodex_ho').name)]


class VisaOrderPassengers(models.Model):
    _inherit = ['mail.thread', 'tt.reservation.passenger']
    _name = 'tt.reservation.visa.order.passengers'
    _description = 'Tour & Travel - Visa Order Passengers'

    to_requirement_ids = fields.One2many('tt.reservation.visa.order.requirements', 'to_passenger_id', 'Requirements',
                                         readonly=0, states={'ready': [('readonly', True)],
                                                             'done': [('readonly', True)]})
    visa_id = fields.Many2one('tt.reservation.visa', 'Visa', readonly=1)  # readonly=1
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=1)  # readonly=1
    pricelist_id = fields.Many2one('tt.reservation.visa.pricelist', 'Visa Pricelist', readonly=1)  # readonly=1
    passenger_type = fields.Selection(PASSENGER_TYPE, 'Pax Type', readonly=1)  # readonly=1
    age = fields.Char('Age', readonly=1, compute="_compute_age", store=True)
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Date(string='Passport Exp Date')
    passenger_domicile = fields.Char('Domicile', related='passenger_id.domicile', readonly=1)  # readonly=1
    process_status = fields.Selection(PROCESS_STATUS, string='Process Result',
                                      readonly=1)  # readonly=1

    interview = fields.Boolean('Needs Interview')
    biometrics = fields.Boolean('Needs Biometrics')
    interview_ids = fields.One2many('tt.reservation.visa.interview.biometrics', 'passenger_interview_id', 'Interview')
    biometrics_ids = fields.One2many('tt.reservation.visa.interview.biometrics', 'passenger_biometrics_id',
                                     'Biometrics')

    handling_ids = fields.One2many('tt.reservation.visa.order.handling', 'to_passenger_id', 'Handling Questions')
    handling_information = fields.Text('Handling Information')

    # biometrics_datetime = fields.Datetime('Datetime')
    # biometrics_ho_employee = fields.Many2one('res.users', 'Employee', domain=lambda self: self.get_user_HO())
    # biometrics_meeting_point = fields.Char('Meeting Point')
    # biometrics_location = fields.Char('Biometrics Location')

    # interview_datetime = fields.Datetime('Datetime')
    # interview_ho_employee = fields.Many2one('res.users', 'Employee', domain=lambda self: self.get_user_HO())
    # interview_meeting_point = fields.Char('Meeting Point')
    # interview_location = fields.Char('Interview Location')

    in_process_date = fields.Datetime('In Process Date', readonly=1)  # readonly=1
    payment_date = fields.Datetime('Payment Date', readonly=1)  # readonly=1
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)  # readonly=1
    call_date = fields.Date('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=1)
    to_HO_date = fields.Datetime('Send to HO Date', readonly=1)
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)
    expired_date = fields.Date('Expired Date', readonly=1)

    use_vendor = fields.Boolean('Use Vendor', readonly=1, related='visa_id.use_vendor')

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_visa_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges', readonly=1)
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_visa_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')

    # use_vendor = fields.Boolean('Use Vendor', readonly=1, related='passport_id.use_vendor')
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
                                                ready = ready to pickup by customer
                                                done = picked up by customer''')

    def action_send_email_interview(self):
        """Dijalankan, jika user menekan tombol 'Send Email Interview'"""
        template = self.env.ref('tt_reservation_visa.template_mail_visa_interview')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        print("Email Interview Sent")

    def action_send_email_biometrics(self):
        """Dijalankan, jika user menekan tombol 'Send Email Biometrics'"""
        template = self.env.ref('tt_reservation_visa.template_mail_visa_biometrics')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        print("Email Biometrics Sent")

    def action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
            # set juga state visa_id ke draft
            if rec.visa_id.state_visa == 'confirm':
                rec.visa_id.action_draft_visa()
            rec.message_post(body='Passenger DRAFT')

    def action_confirm(self):
        for rec in self:
            rec.write({
                'state': 'confirm'
            })
            rec.message_post(body='Passenger CONFIRMED')

    def action_validate(self):
        for rec in self:
            rec.write({
                'state': 'validate'
            })
            for req in self.to_requirement_ids:
                if req.is_copy is True or req.is_ori is True:
                    if req.validate_HO is False:
                        raise UserError(_('You have to Validate All Passengers Documents.'))
            rec.message_post(body='Passenger VALIDATED')

    def action_re_validate(self):
        for rec in self:
            rec.write({
                'state': 're_validate',
            })
            rec.message_post(body='Passenger RE VALIDATE')

    def action_re_confirm(self):
        for rec in self:
            rec.write({
                'state': 're_confirm',
            })
            rec.message_post(body='Passenger RE CONFIRM')

    def action_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel'
            })
            rec.message_post(body='Passenger CANCELED')

    def action_in_process(self):
        for rec in self:
            rec.write({
                'state': 'in_process'
            })
            rec.message_post(body='Passenger IN PROCESS')

    def action_add_payment(self):
        for rec in self:
            rec.write({
                'state': 'add_payment',
            })
            rec.message_post(body='Passenger compute_price ADD PAYMENT')
            rec.visa_id.action_payment_visa()

    def action_confirm_payment(self):
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
        for rec in self:
            rec.write({
                'state': 'waiting',
            })
            rec.message_post(body='Passenger WAITING')

    def action_proceed(self):
        for rec in self:
            # jika belum ada tanggal wawancara / call_date, tidak bisa proceed
            # if not rec.call_date:
            #     raise UserError(_('You have to Fill Passenger Call Date.'))
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
            rec.message_post(body='Passenger PROCEED')
            is_proceed = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['proceed', 'cancel']:
                    is_proceed = False
            # jika ada sebagian state passenger yang belum proceed -> partial proceed
            if not is_proceed:
                rec.visa_id.action_partial_proceed_visa()
            else:  # else -> proceed
                rec.visa_id.action_proceed_visa()

    def action_reject(self):
        for rec in self:
            rec.write({
                'state': 'rejected',
                'process_status': 'rejected',
                'out_process_date': datetime.now()
            })
            rec.message_post(body='Passenger REJECTED')

    def action_accept(self):
        for rec in self:
            rec.write({
                'state': 'accepted',
                'process_status': 'accepted',
                'out_process_date': datetime.now()
            })
            rec.message_post(body='Passenger REJECTED')

    def action_to_HO(self):
        for rec in self:
            rec.write({
                'state': 'to_HO',
                'to_HO_date': datetime.now()
            })
            rec.message_post(body='Passenger documents TO HO')
            is_sent = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['to_HO']:
                    is_sent = False
            if is_sent:
                rec.visa_id.action_delivered_visa()

    def action_to_agent(self):
        for rec in self:
            rec.write({
                'state': 'to_agent',
                'to_agent_date': datetime.now()
            })
            rec.message_post(body='Passenger documents TO Agent')
            is_sent = True
            for psg in rec.visa_id.passenger_ids:
                if psg.state not in ['to_agent']:
                    is_sent = False
            if is_sent:
                rec.visa_id.action_delivered_visa()

    def action_ready(self):
        for rec in self:
            rec.write({
                'state': 'ready',
                'ready_date': datetime.now(),
            })
            rec.message_post(body='Passenger documents READY')
            rec.visa_id.action_ready_visa()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done'
            })
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
