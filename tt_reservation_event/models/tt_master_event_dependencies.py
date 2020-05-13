from odoo import api, fields, models
from odoo.http import request
import logging
import json
from ...tools import session

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

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
    answer_type = fields.Selection([('text', 'Text'), ('password', 'Password'), ('number', 'Number'), ('email', 'Email')])
    # answer = fields.Char('Answer')
    is_required = fields.Boolean('Is Required', default=False)
    answer_ids = fields.One2many('tt.event.extra.question.answer', 'extra_question_id')
    reservation_answer_ids = fields.One2many('tt.reservation.event.extra.question', 'extra_question_id')

class MasterEventExtraQuestionAnswer(models.Model):
    _name = 'tt.event.extra.question.answer'
    _description = 'Rodex Event Model'

    extra_question_id = fields.Many2one('tt.event.extra.question', 'Extra Question ID')
    answer = fields.Char('Answer')

class MasterEventCategory(models.Model):
    _name = 'tt.event.category'
    _description = 'Rodex Event Model'

    uid = fields.Char('UID')
    name = fields.Char('Category Name')
    parent_id = fields.Many2one('tt.event.category', 'Parent ID')
    child_ids = fields.One2many('tt.event.category', 'parent_id')
    event_ids = fields.Many2many('tt.master.event','tt_event_category_rel', 'category_id', 'event_id', string='Event', readonly=True)

class EventOptions(models.Model):
    _name = 'tt.event.option'
    _description = 'Rodex Event Model'

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    option_code = fields.Char('Code')
    grade = fields.Char('Options')
    timeslot_ids = fields.One2many('tt.event.timeslot', 'event_option_id')
    # additionalInformation = fields.Many2many('')

    quota = fields.Integer('Quota')
    sales = fields.Integer('Sales', readonly=True)

    cancellation_policies = fields.Text("Cancellation Policies")
    is_non_refundable = fields.Boolean(' is Non Refundable')
    advance_booking_days = fields.Integer("Advance Booking Days", default=0)

    # minimumSellingPrice = fields.Integer("Minimum Selling Price", default=0)
    currency_id = fields.Many2one('res.currency', 'Currency')
    price = fields.Monetary('Price')
    # sku_ids = fields.One2many("tt.master.event.sku", 'event_option_id')
    active = fields.Boolean('Active', default=True)

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
    # active = fields.Boolean('Active', default=True)

class EventOptionAdditionalIformation(models.Model):
    _name = 'tt.event.option.additional'
    _description = 'Rodex Event Model'

    event_id = fields.Many2one('tt.master.event', 'Event ID')
    additional_information = fields.Html('Additional Information')
    additional_type = fields.Selection([('text', 'Text'), ('password', 'Password'), ('number', 'Number'), ('email', 'Email')])
    remark = fields.Char('Remark')
    priority = fields.Integer('Priority')
