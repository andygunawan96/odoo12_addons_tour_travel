from odoo import api, fields, models
from odoo.http import request
from ...tools import util, variables, ERR, session
from ...tools.ERR import RequestException
from dateutil.relativedelta import relativedelta
import logging, traceback
import json
import base64
import pickle
from datetime import datetime
import csv
import os
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
SESSION_NT = session.Session()

class MasterEvent(models.Model):
    _name = "tt.master.event"
    _description = "Rodex Event Model"

    uuid = fields.Char('UUID', readonly=True, required=False, states={'draft': [('readonly', False)]})
    name = fields.Char('Event Name', readonly=True, states={'draft': [('readonly', False)]})

    category_ids = fields.Many2many('tt.event.category', 'tt_event_category_rel', 'event_id', 'category_id', string='Category', readonly=True, states={'draft': [('readonly', False)]})
    categories = fields.Char('Categories', readonly=True)

    event_type = fields.Selection([('offline', 'Offline'), ('online', 'Online')], readonly=True, states={'draft': [('readonly', False)]})
    includes = fields.Html('Price Includes', readonly=True, states={'draft': [('readonly', False)]})
    excludes = fields.Html('Price Excludes', readonly=True, states={'draft': [('readonly', False)]})

    description = fields.Html('Description', readonly=True, states={'draft': [('readonly', False)]})
    additional_info = fields.Html('Additional Info', readonly=True, states={'draft': [('readonly', False)]})
    kid_friendly = fields.Boolean('Age Restriction', default=False, readonly=True, states={'draft': [('readonly', False)]})
    eligible_age = fields.Integer('Eligible Age', default=1, readonly=True, states={'draft': [('readonly', False)]})
    itinerary = fields.Html('Itinerary', readonly=True, states={'draft': [('readonly', False)]})
    to_notice = fields.Html('Warnings', readonly=True, states={'draft': [('readonly', False)]})
    extra_question_ids = fields.One2many('tt.event.extra.question', 'event_id', readonly=True, states={'draft':[('readonly', False)]})

    location_ids = fields.One2many('tt.event.location', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    locations = fields.Char('Locations', readonly=True)

    # event_by_id = fields.Many2one('tt.event.by', 'Event By', readonly=True, states={'draft': [('readonly', False)]})
    event_date_start = fields.Datetime(string="Starting Time", readonly=True, states={'draft': [('readonly', False)]})
    event_date_end = fields.Datetime(string="Finish", readonly=True, states={'draft': [('readonly', False)]})
    number_of_days = fields.Integer("Number of days", readonly=True, states={'draft': [('readonly', False)]})

    option_ids = fields.One2many('tt.event.option', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    image_ids = fields.Many2many('tt.upload.center', 'event_images_rel', 'event_id', 'image_id', 'Images')
    active = fields.Boolean('Active', default=True)
    state = fields.Selection(variables.PRODUCT_STATE, 'Product State', default='draft')

    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True, states={'draft': [('readonly', False)]}, domain=[('provider_type_id', '=', lambda self: self.env.ref('tt_reservation_event.tt_provider_type_event') )])
    provider_code = fields.Char('Provider Code', readonly=True)
    provider_fare_code = fields.Char('Provider Fare Code', readonly=True)

    event_vendor_id = fields.Many2one('tt.vendor', 'Vendor ID')
    booking_event_ids = fields.One2many('tt.event.reservation', 'event_id')
    email_content = fields.Char('Temp untuk email')

    @api.model
    def create(self, vals_list):
        try:
            vals_list['uuid'] = self.env['ir.sequence'].next_by_code(self._name)
            vals_list['event_vendor_id'] = self.env.user.vendor_id.id or False
        except:
            pass
        return super(MasterEvent, self).create(vals_list)

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id and self.provider_id.code or ''

    @api.onchange('location_ids')
    def _onchange_location_ids(self):
        temp = ""
        for i in self.location_ids:
            temp += "{},".format(i.city_name)
        self.locations = temp

    @api.onchange('category_ids')
    @api.depends('category_ids')
    def _onchange_category_ids(self):
        self.categories = ','.join([rec.name for rec in self.category_ids])

    def action_draft(self):
        self.write({
            'state': 'draft'
        })

    def action_confirm(self):
        self.write({
            'state': 'confirm'
        })

    def search_event_api(self, req, context):
        try:
            name = req.get('event_name') and req['event_name'] or ''
            city = req.get('city') and req['city'] or ''
            category = req.get('category') and req['category'] or ''
            online = req.get('online') and req['online'] or ''
            vendor = req.get('vendor') and req['vendor'] or ''

            limitation = []
            if name != '':
                limitation.append(('name', 'ilike', name))
            if city != '':
                limitation.append(('locations', 'ilike', city))
            if category != '':
                limitation.append(('categories', 'ilike', category))
            if online != '':
                limitation.append(('event_type', '=', online))
            if vendor != '':
                limitation.append(('vendor_id', '=', vendor))


            result = self.env['tt.master.event'].sudo().search(limitation)
            to_return = []
            for i in result:
                temp_dict = {
                    'id': i.uuid,
                    'name': i.name,
                    'category': [rec.name for rec in i.category_ids],
                    'locations': [self.format_api_location(loc.id) for loc in i.location_ids],
                    'detail': i.description,
                    'terms_and_condition': i.additional_info,
                    'provider': i.provider_id.name,
                    'option': [i.format_api_option(opt.id) for opt in i.option_ids],
                    'vendor_obj': {
                        'vendor_name': i.event_vendor_id.name,
                        'vendor_logo': i.event_vendor_id.logo or False
                    },
                    'images': [i.format_api_image(img) for img in self.image_ids],
                    # 'age_restriction': i.age_restriction,
                    'eligible_age': i.eligible_age
                }
                # temp_dict = i.format_api()
                to_return.append(temp_dict)
                # i.update({
                #     'image_ids': self.env['tt.master.event.image'].sudo().search([('event_id', '=', i.id)]),
                #     'video_ids': self.env['tt.master.event.video'].sudo().search([('event_id', '=', i.id)]),
                #     'location_ids': self.env['tt.event.location'].sudo().search([('event_id', '=', i.id)]),
                #     'option_ids': self.env['tt.event.option'].sudo().search([('event_id', '=', i.id)]),
                # })
                #
                # for j in i['option_ids']:
                #     j.update({
                #         'timeslot_ids': self.env['tt.event.timeslot'].sudo().search([('event_option_id', '=', j.id)])
                #     })
            return ERR.get_no_error(to_return)
            #built the return response

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    # Temp
    # def search_event_api(self, req, context):
    #     limit = context.get('limit') or 100
    #     result = []
    #     for rec in self.search(['|',('name', 'ilike', req['event_name']),('locations', 'ilike', req['event_name'])], limit=limit):
    #         result.append(rec.format_api())
    #     return {'response': result,}

    def format_api_image(self, img):
        return {
            'url': img.path or img.url,
            'description': img.file_reference,
        }

    def format_api_timeslot(self, timeslot_id):
        timeslot = self.env['tt.event.timeslot'].browse(timeslot_id)
        return {
            'start_date': timeslot.date,
            'end_date': '',
            'start_hour': str(timeslot.start_hour) + ':' + str(timeslot.start_minute),
            'end_hour': str(timeslot.end_hour) + ':' + str(timeslot.end_minute),
        }

    def format_api_option(self, option_id):
        timeslot = self.env['tt.event.option'].sudo().browse(option_id)
        return {
            'option_id': timeslot.option_code,
            'grade': timeslot.grade,
            'images': [],
            'price': timeslot.price,
            'currency': timeslot.currency_id.name,
            'is_non_refundable': timeslot.is_non_refundable,
            'advance_booking_days': timeslot.advance_booking_days,
            'qty_available': timeslot.quota,
            'min_qty': '1',
            'max_qty': timeslot.max_ticket == -1 and timeslot.quota or timeslot.max_ticket,
            'description': timeslot.cancellation_policies,
            # 'timeslot': [self.format_api_timeslot(slot.id) for slot in timeslot.timeslot_ids]
            'timeslot': []
        }

    def format_api_location(self, location_id):
        location = self.env['tt.event.location'].browse(location_id)
        return {
            'location_name': location.name,
            'location_address': location.address,
            'city_name': location.city_name,
            'country_name': location.country_name,
            'lat': '',
            'long': '',
        }

    def format_api_extra_question(self, location_id):
        location = self.env['tt.event.location'].browse(location_id)
        return {
            'location_name': location.name,
            'location_address': location.address,
            'city_name': location.city_name,
            'country_name': location.country_name,
            'lat': '',
            'long': '',
        }

    def format_api(self):
        return {
            'id': self.uuid, # Todo Sequence
            'name': self.name,
            'tags': [rec.name for rec in self.category_ids],
            'images': [self.format_api_image(img) for img in self.image_ids],
            'terms_and_condition': self.additional_info,
            'detail': self.description,
            'option': [self.format_api_option(opt.id) for opt in self.option_ids],
            'locations': [self.format_api_location(loc.id) for loc in self.location_ids],
            'vendor_obj': {
                'vendor_name': self.event_vendor_id.name,
                'vendor_logo': self.event_vendor_id.logo or False,
            },
            'provider': self.provider_id.name,
        }

    def get_form_api(self, req, context):
        try:
            res = self.env['tt.master.event'].sudo().search([('uuid', '=', req['event_code'])])
            result = [{
                'question': rec.question,
                'type': rec.answer_type,
                'required': rec.is_required,
                'is_add_other': rec.is_add_other, #Checkbox
                'answers': [{
                    'answer': aws.answer
                } for aws in rec.answer_ids]
            } for rec in res.extra_question_ids]
            return ERR.get_no_error(result)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_config_api(self):
        result = {
            'event': [],
            'category': self.env['tt.event.category'].get_from_api('', False, [])
        }
        #get all data
        event_obj = self.env['tt.master.event'].sudo().search([])
        for i in event_obj:
            temp_dict = {
                'name': i.name,
                'locations': i.locations,
                'category': i.categories,
                'image_url': []
            }
            for j in i.image_ids:
                temp_dict['image_url'].append(j.url)
            result['event'].append(temp_dict)

        return ERR.get_no_error(result)

    def booking_master_event_from_api(self, req, context):
        event_id = self.sudo().search([('uuid', '=', req['event_code'])], limit=1)
        # Check apakah Order Number yg dikirim sdah pernah ada di DB kita?
        if self.env['tt.event.reservation'].sudo().search([('order_number', '=', req['order_number'])]):
            return 'Error'
        for rec in req['event_option_codes']:
            opt_id = self.env['tt.event.option'].search([('event_id','=',event_id.id), ('option_code','=',rec['option_code'])], limit=1)
            temp_event_reservation_dict = {
                'event_id': event_id.id,
                'event_option_id': opt_id.id,
                'order_number': req['order_number'],
            }
            # Check apa kah order_number yg dikirim ada di resv event
            book_id = self.env['tt.reservation.event'].search([('name', '=', req['order_number'])], limit=1)
            if book_id:
                temp_event_reservation_dict.update({
                    'booker_id': book_id.booker_id.id,
                    'reservation_id': book_id.id
                })
                pnr = self.env['ir.sequence'].next_by_code('pnr_sequence')
            else:
                pnr = 'E' + req['order_number']

            temp_event_reservation_dict.update({'pnr': pnr,})
            self.env['tt.event.reservation'].sudo().create(temp_event_reservation_dict)
        for i in req['event_option_codes']:
            option_obj = self.env['tt.event.option'].sudo().search([('option_code', '=', i['option_code'])])
            option_obj.action_hold_book(1)
        return ERR.get_no_error({'pnr': pnr, 'hold_date': str(datetime.now() + relativedelta(minutes=45))[:16]+':00' })

    def issued_master_event_from_api(self, pnr):
        try:
            #search all of the reservation
            booking_event_obj = self.env['tt.event.reservation'].sudo().search([('pnr', '=', pnr)])

            email_content = "<ul>"
            for i in booking_event_obj:
                i.event_option_id.making_sales(1)
                email_content += "<li>{}</li>".format(i.order_number)
            email_content += "</ul>"

            #notificate the vendor
            self.email_content = email_content
            template = self.env.ref('tt_reservation_event.template_mail_vendor_notification')
            mail = self.env['mail.template'].browse(template.id)
            mail.send_mail(self.id)
            self.email_content = False
            return ERR.get_no_error()
        except:
            return ERR.get_no_error()

    # def reprice_currency(self, req,  context):
    #     _logger.info('REPRICE CURRENCY EVENT')
    #     _logger.info(json.dumps(req))
    #     provider = req['provider']
    #     from_currency = req['from_currency']
    #     base_amount = req['base_amount']
    #     to_currency = req.get('to_currency') and req['to_currency'] or 'IDR'
    #     from_currency_id = self.env['res_currency'].sudo().search([('name', '=', from_currency)], limit=1)
    #     from_currency_id = from_currency_id and from_currency_id[0] or False
    #     try:
    #         provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
    #         provider_id = provider_id[0]
    #         multiplier = self.env['tt.provider.rate'].sudo().search([('provider_id', '=', provider_id.id), ('date', '<=', datetime.now()), ('currency_id', '=', from_currency_id.id)], limit=1)
    #         computed_amount = base_amount * multiplier[0].sell_rate
    #     except Exception as e:
    #         computed_amount = self.env['res.currency'].compute(from_currency_id, self.env.user.company_id.currency_id, base_amount)
    #         _logger.info("Cannot convert to vendor price: " + str(e))
    #     return computed_amount