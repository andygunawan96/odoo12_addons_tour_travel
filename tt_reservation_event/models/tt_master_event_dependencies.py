from odoo import api, fields, models
from odoo.http import request
import logging
import json
from ...tools import session
from datetime import datetime, timedelta
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class MasterEventReservation(models.Model):
    _name = "tt.event.reservation"
    _description = "Rodex Event Model"
    _order = 'id desc'

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    vendor_id = fields.Many2one('tt.vendor', related="event_id.event_vendor_id", store=True)
    event_option_id = fields.Many2one('tt.event.option', 'Event option ID', readonly=True)
    quantity = fields.Integer("Quantity")
    currency_id = fields.Many2one('res.currency', 'Currency ID')
    event_ticket_price = fields.Monetary(compute='compute_ticket_price', store=True)
    pnr = fields.Char('PNR', readonly=True)
    validator_sequence = fields.Char('Sequence')
    booker_id = fields.Many2one('tt.customer', 'Booker', readonly=True)
    contact_id = fields.Many2one('tt.customer', 'Contact', readonly=True)
    sales_date = fields.Datetime('Sold Date')
    order_number = fields.Char('Client Order Number', help='Code must be distinct', readonly=True)
    state = fields.Selection([('draft', 'Draft'),('request', 'Request'), ('confirm', 'Confirm'), ('done', 'Paid')], default='draft')
    event_reservation_answer_ids = fields.One2many('tt.event.reservation.answer', 'event_reservation_id')
    ticket_number = fields.Char('Ticket Number', readonly=True, states={'draft': [('readonly', False)], 'request': [('readonly', False)]})
    special_request = fields.Text('Special Request', help='Request / Notes from customer')
    email_content = fields.Html('Temp untuk email')

    request_date = fields.Datetime('Request Date')
    request_uid = fields.Many2one('res.users', 'User Request')
    confirm_date = fields.Datetime('confirm Date')
    confirm_uid = fields.Many2one('res.users', 'User Confirm')
    paid_date = fields.Datetime('paid date')
    paid_uid = fields.Many2one('res.users', 'Paid User')

    def compute_ticket_price(self):
        for i in self:
            i.event_ticket_price = i.event_option_id.price
            i.currency_id = i.event_option_id.currency_id.id

    def action_confirm(self):
        if not self.ticket_number and self.state == 'request':
            raise UserError('Ticket Number Required to set this  Resv to Confirm')
        self.state = "confirm"
        self.confirm_date = datetime.now()
        self.confirm_uid = self.env.user.id

        # Little Naughty things here:
        event_obj = self.env['tt.reservation.event'].sudo().search([('pnr', '=', self.pnr)], limit=1)
        event_id = event_obj and event_obj[0].id or False
        val_obj = self.env['tt.reservation.event.option'].sudo().search([('validator_sequence', '=', self.validator_sequence), ('booking_id', '=', event_id)], limit=1)
        if val_obj:
            val_obj.sudo().update({'ticket_number': self.ticket_number})
        else:
            #TODO Passing ke Gateway
            val_obj.sudo().update({'ticket_number': self.ticket_number})

    def action_paid(self):
        self.state = "done"
        self.paid_date = datetime.now()
        self.paid_uid = self.env.user.id

    def action_request(self):
        self.state = "request"
        self.request_date = datetime.now()
        self.sales_date = datetime.now()
        self.request_uid = self.env.user.id
        self.compute_ticket_price()

    def action_request_by_api(self, co_uid):
        self.action_request()
        self.request_uid = co_uid

    # Temporary untuk benarkan data lama sja
    def action_calc_sales_date(self):
        for rec in self.search([]):
            rec.sales_date = rec.request_date

class EventReservationQuestionAnswer(models.Model):
    _name = "tt.event.reservation.answer"
    _description = "Rodex Event Model"

    event_reservation_id = fields.Many2one('tt.event.reservation', 'Event Option ID')
    extra_question_id = fields.Many2one("tt.event.extra.question", 'Event extra Question')
    question = fields.Char('Question')
    answer = fields.Char("Answer")

class MasterLocations(models.Model):
    _name = 'tt.event.location'
    _description = 'Rodex Event Location Master'

    event_id = fields.Many2one('tt.master.event', 'Event ID', ondelete="cascade")
    name = fields.Char('Name')
    address = fields.Char('Address')
    city_id = fields.Many2one('res.city', 'City')
    city_name = fields.Char('City Name', related='city_id.name', store=True)
    state_id = fields.Many2one('res.country.state', 'State')
    state_name = fields.Char('State Name', related='state_id.name', store=True)
    country_id = fields.Many2one('res.country', 'Country')
    country_name = fields.Char('Country Name', related="country_id.name", store=True)

class MasterEventExtraQuestion(models.Model):
    _name = 'tt.event.extra.question'
    _description = 'Rodex event Model'

    event_id = fields.Many2one('tt.master.event', 'Event ID', ondelete="cascade")
    question = fields.Char('Question')
    answer_type = fields.Selection([('text', 'Text'), ('password', 'Password'), ('number', 'Number'), ('email', 'Email'), ('boolean', 'Boolean'), ('selection', 'Selection'), ('date', 'Date'), ('checkbox', 'CheckBox')], default="text", required="1")
    # answer = fields.Char('Answer')
    is_required = fields.Boolean('Is Required', default=False)
    is_active = fields.Boolean('Is Active', default=True)
    max_length = fields.Integer('Max Length', default=255)
    answer_ids = fields.One2many('tt.event.extra.question.answer', 'extra_question_id')
    reservation_answer_ids = fields.One2many('tt.reservation.event.extra.question', 'extra_question_id')
    is_add_other = fields.Boolean('Other', default=False, help="When using checkbox you can add empty field to accept other answer from your customer")

class MasterEventExtraQuestionAnswer(models.Model):
    _name = 'tt.event.extra.question.answer'
    _description = 'Rodex Event Model'

    extra_question_id = fields.Many2one('tt.event.extra.question', 'Extra Question ID')
    answer = fields.Char('Answer')

class MasterEventCategory(models.Model):
    _name = 'tt.event.category'
    _description = 'Rodex Event Model'

    uid = fields.Char('UID', readonly=True)
    name = fields.Char('Category Name')
    desc = fields.Char('Category description')
    parent_id = fields.Many2one('tt.event.category', 'Parent ID')
    child_ids = fields.One2many('tt.event.category', 'parent_id', 'Child')
    event_ids = fields.Many2many('tt.master.event','tt_event_category_rel', 'category_id', 'event_id', string='Event', readonly=True)

    def parse_format(self):
        return {
            'category_id': self.id,
            'category_name': self.name,
            'child_category': []
        }

    def get_from_api(self, search_str, parent_objs, inc_list):
        parsed_obj = []
        if not parent_objs:
            parent_objs = search_str and self.search([('name', '=ilike', search_str)]) or self.search([])
        for rec in parent_objs:
            if rec.id not in inc_list:
                new_dict = rec.parse_format()
                inc_list.append(rec.id)
                for child in rec.child_ids:
                    new_dict['child_category'].append(child.get_from_api('', child, inc_list)[0])
                parsed_obj.append(new_dict)
        return parsed_obj

    def parse_format_api(self, data):
        return {
            'response': self.get_from_api(data['name'], False, []),
        }

class EventOptions(models.Model):
    _name = 'tt.event.option'
    _description = 'Rodex Event Model'
    _rec_name = 'grade'

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    option_code = fields.Char('Code', readonly=True)
    grade = fields.Char('Options', required=True)
    timeslot_ids = fields.One2many('tt.event.timeslot', 'event_option_id')
    # additionalInformation = fields.Many2many('')

    quota = fields.Integer('Quota', default=-1)
    on_hold = fields.Integer('On Hold')
    max_ticket = fields.Integer('Max Ticket', help='Max Ticket purchase per reservation; if -1 then it will give current quota', default=-1)
    sales = fields.Integer('Sales', readonly=True)

    date_start = fields.Datetime('Date Selling Start', required=True, default=datetime.now())
    date_end = fields.Datetime('Date Selling End')
    description = fields.Char('Description')

    cancellation_policies = fields.Text("Cancellation Policies")
    is_non_refundable = fields.Boolean(' is Non Refundable')
    advance_booking_days = fields.Integer("Advance Booking Days", default=0)

    # minimumSellingPrice = fields.Integer("Minimum Selling Price", default=0)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    price = fields.Monetary('Price')
    # sku_ids = fields.One2many("tt.master.event.sku", 'event_option_id')
    active = fields.Boolean('Active', default=True)

    option_image_ids = fields.Many2many('tt.upload.center', 'event_option_images_rel', 'event_option_id', 'image_id', 'Option Images')

    @api.model
    def create(self, val_list):
        try:
            parent_id = self.event_id and str(self.event_id.id) or str(val_list['event_id'])
            val_list['option_code'] = "EVT.{}.{}".format(parent_id, self.env['ir.sequence'].next_by_code(self._name))
        except:
            _logger.info('error while updating event option')
        return super(EventOptions, self).create(val_list)

    def action_hold_book(self, number_of_people):
        try:
            if (self.quota - self.on_hold) >= 0:
                self.on_hold += number_of_people
            else:
                return {
                    'response': "Waiting List"
                }
            return {
                'response': "Book On Hold"
            }
        except:
            return {
                'response': "Cannot proceed booking right now, try again in a few moment."
            }

    def making_sales(self, number_of_sales):
        try:
            if (self.quota - number_of_sales) >= 0:
                self.quota -= number_of_sales
                self.sales += number_of_sales
                self.on_hold -= number_of_sales
            else:
                return {
                    'response': "[ERROR] Items availability is less than requested"
                }
            return {
                'response': "Purchase made"
            }
        except:
            return {
                'response': "Unable to make purchase"
            }

    def to_dict(self):
        return self.read(['option_image_ids', 'option_code', 'grade', 'description',
                          'date_start', 'date_end'])


class MasterTimeslot(models.Model):
    _name = 'tt.event.timeslot'
    _description = 'Rodex Event model'

    event_option_id = fields.Many2one('tt.event.option', 'Product Type', ondelete="cascade")
    uuid = fields.Char('Uuid')
    # startTime = fields.Char('Start Time')
    # endTime = fields.Char('End time')
    start_hour = fields.Integer('Start Hour')
    start_minute = fields.Integer('Start Minute')
    end_hour = fields.Integer('End Hour')
    end_minute = fields.Integer('End Minute')
    # timezone = fields.Selection([('wib', 'WIB'), ('wita', 'WITA'), ('wit', 'WIT')])
    date = fields.Date('Date')
    all_day = fields.Boolean('all day')
    active = fields.Boolean('Active', default=True)

class EventOptionAdditionalIformation(models.Model):
    _name = 'tt.event.option.additional'
    _description = 'Rodex Event Model'

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    additional_information = fields.Html('Additional Information')
    additional_type = fields.Selection([('text', 'Text'), ('password', 'Password'), ('number', 'Number'), ('email', 'Email')])
    remark = fields.Char('Remark')
    priority = fields.Integer('Priority')
