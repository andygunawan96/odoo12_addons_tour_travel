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

TITLE = [
    ('MR', 'MR'),
    ('MRS', 'MRS'),
    ('MS', 'MS'),
    ('MSTR', 'MSTR'),
    ('MISS', 'MISS')
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


class PassportOrderPassengers(models.Model):
    _inherit = ['mail.thread', 'tt.reservation.passenger']
    _name = 'tt.reservation.passport.order.passengers'
    _description = 'Tour & Travel - Passport Order Passengers'

    name = fields.Char('Name', related='passenger_id.first_name', readonly=0)  # readonly=1
    to_requirement_ids = fields.One2many('tt.reservation.passport.order.requirements', 'to_passenger_id', 'Requirements',
                                         readonly=0, states={'ready': [('readonly', True)],
                                                             'done': [('readonly', True)]})  # readonly=0
    passport_id = fields.Many2one('tt.reservation.passport', 'Passport', readonly=0)  # readonly=1
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=0)  # readonly=1
    pricelist_id = fields.Many2one('tt.reservation.passport.pricelist', 'Passport Pricelist', readonly=0)  # readonly=1
    passenger_type = fields.Selection(PASSENGER_TYPE, 'Pax Type', readonly=0)  # readonly=1
    title = fields.Selection(TITLE, 'Title', readonly=0)  # readonly=1
    age = fields.Char('Age', readonly=1, compute="_compute_age", store=True)
    passport_number = fields.Char(string='Passport Number')
    passport_expdate = fields.Datetime(string='Passport Exp Date')
    passenger_domicile = fields.Char('Domicile', related='passenger_id.domicile', readonly=0)  # readonly=1
    process_status = fields.Selection(PROCESS_STATUS, string='Process Result',
                                      readonly=0)  # readonly=1
    biometrics_interview = fields.Boolean('Biometrics / Interview')

    in_process_date = fields.Datetime('In Process Date', readonly=0)  # readonly=1
    payment_date = fields.Datetime('Payment Date', readonly=0)  # readonly=1
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=0)  # readonly=1
    call_date = fields.Datetime('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=0)  # readonly=1
    to_HO_date = fields.Datetime('Send to HO Date', readonly=0)  # readonly=1
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=0)  # readonly=1
    ready_date = fields.Datetime('Ready Date', readonly=0)  # readonly=1

    service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_passport_charge_rel', 'passenger_id',
                                          'service_charge_id', 'Service Charges')

    cost_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_passport_cost_charge_rel',
                                               'passenger_id', 'service_charge_id', 'Cost Service Charges')
    channel_service_charge_ids = fields.Many2many('tt.service.charge', 'tt_reservation_passport_channel_charge_rel',
                                                  'passenger_id', 'service_charge_id', 'Channel Service Charges')

    # use_vendor = fields.Boolean('Use Vendor', readonly=1, related='passport_id.use_vendor')
    notes = fields.Text('Notes (Agent to Customer)')
    notes_HO = fields.Text('Notes (HO to Agent)')

    booking_state = fields.Selection(BOOKING_STATE, default='draft', string='Order State', readonly=0,
                                     related='passport_id.state_passport', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                to_vendor = Documents sent to Vendor
                                                vendor_process = Documents proceed by Vendor
                                                in_process = Documents proceed at Consulat or Imigration
                                                to_HO = documents sent to HO
                                                waiting = Documents ready at HO
                                                done = Documents given to customer''')  # readonly=1

    state = fields.Selection(STATE, default='draft', help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                in_process = before payment
                                                in_process2 = process by consulate/immigration
                                                waiting = waiting interview or photo
                                                proceed = Has Finished the requirements
                                                accepted = Accepted by the Immigration
                                                rejected = Rejected by the Immigration
                                                ready = ready to pickup by customer
                                                done = picked up by customer''')

    def action_send_email_interview(self):
        """Dijalankan, jika user menekan tombol 'Send Email Interview'"""
        template = self.env.ref('tt_reservation_passport.template_mail_passport_interview')
        mail = self.env['mail.template'].browse(template.id)
        mail.send_mail(self.id)
        print("Email Sent")

    def action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
            if rec.passport_id.state_passport == 'confirm':
                rec.passport_id.action_draft_passport()
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
            rec.passport_id.action_payment_passport()

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
            if not rec.call_date:
                raise UserError(_('You have to Fill Passenger Call Date.'))
            rec.write({
                'state': 'proceed',
            })
            rec.message_post(body='Passenger PROCEED')
            is_proceed = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state not in ['proceed', 'cancel']:
                    is_proceed = False
            # jika ada sebagian state passenger yang belum proceed -> partial proceed
            if not is_proceed:
                rec.passport_id.action_partial_proceed_passport()
            else:  # else -> proceed
                rec.passport_id.action_proceed_passport()

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
            is_sent = True
            for psg in rec.passport_id.passenger_ids:
                if not psg.state in ['to_HO']:
                    is_sent = False
            if is_sent:
                rec.passport_id.action_delivered_passport()
            rec.message_post(body='Passenger documents TO HO')

    def action_to_agent(self):
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

    def action_ready(self):
        for rec in self:
            rec.write({
                'state': 'ready',
                'ready_date': datetime.now(),
            })
            rec.message_post(body='Passenger documents READY')
            rec.passport_id.action_ready_passport()

    def action_done(self):
        for rec in self:
            rec.write({
                'state': 'done'
            })
            rec.message_post(body='Passenger DONE')
            is_done = True
            for psg in rec.passport_id.passenger_ids:
                if psg.state not in ['done', 'cancel']:
                    is_done = False
            if is_done:
                rec.passport_id.action_done_passport()

    def action_sync(self):
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

    @api.depends('birth_date')
    @api.onchange('birth_date')
    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                today = date.today()
                range_date = relativedelta(today, rec.birth_date)
                age = str(range_date.years) + 'y ' + str(range_date.months) + 'm ' + str(range_date.days) + 'd'
                rec.age = age

    def check_requirement(self, id):
        for rec in self:
            for to_req in rec.to_requirement_ids:
                if to_req.requirement_id.id == id:
                    return True
            return False
