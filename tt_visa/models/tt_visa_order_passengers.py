from odoo import models, fields, _
from datetime import datetime
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


class VisaOrderPassengers(models.Model):
    _inherit = ['mail.thread']
    _name = 'tt.visa.order.passengers'
    _description = 'Tour & Travel - Visa Order Passengers'

    name = fields.Char('Name', related='passenger_id.first_name', readonly=1)
    to_requirement_ids = fields.One2many('tt.visa.order.requirements', 'to_passenger_id', 'Requirements')
    visa_id = fields.Many2one('tt.visa', 'Visa', readonly=1)
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=1)
    pricelist_id = fields.Many2one('tt.visa.pricelist', 'Visa Pricelist', readonly=1)
    passenger_type = fields.Selection(PASSENGER_TYPE, 'Pax Type', readonly=1)
    passenger_domicile = fields.Char('Domicile', related='passenger_id.domicile', readonly=1)
    process_status = fields.Selection(PROCESS_STATUS, string='Process Result',
                                      readonly=1)

    in_process_date = fields.Datetime('In Process Date', readonly=1)
    payment_date = fields.Datetime('Payment Date', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)
    call_date = fields.Datetime('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=1)
    to_HO_date = fields.Datetime('Send to HO Date', readonly=1)
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

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

    state = fields.Selection(STATE, default='draft', help='''draft = requested
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
            if not rec.call_date:
                raise UserError(_('You have to Fill Passenger Call Date.'))
            rec.write({
                'state': 'proceed',
            })
            rec.message_post(body='Passenger PROCEED')
            is_proceed = True
            for psg in rec.visa_id.to_passenger_ids:
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
            for psg in rec.visa_id.to_passenger_ids:
                if not psg.state in ['to_HO']:
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
            for psg in rec.visa_id.to_passenger_ids:
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
            for psg in rec.visa_id.to_passenger_ids:
                if psg.state not in ['done', 'cancel']:
                    is_done = False
            if is_done:
                rec.visa_id.action_done_visa()

    def action_sync(self):
        to_req_env = self.env['tt.visa.order.requirements']
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

    def check_requirement(self, id):
        for rec in self:
            for to_req in rec.to_requirement_ids:
                if to_req.requirement_id.id == id:
                    return True
            return False
