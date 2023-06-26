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
    _inherit = ['tt.history']
    _description = "Orbis Event Model"

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_event.tt_provider_type_event').id
        return [('provider_type_id.id', '=', int(domain_id))]

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
    guests = fields.Char('Guest / Speaker')

    # event_by_id = fields.Many2one('tt.event.by', 'Event By', readonly=True, states={'draft': [('readonly', False)]})
    event_date_start = fields.Datetime(string="Starting Time", readonly=True, states={'draft': [('readonly', False)]}, required=True)
    event_date_end = fields.Datetime(string="Finish", readonly=True, states={'draft': [('readonly', False)]})
    number_of_days = fields.Integer("Number of days", readonly=True, states={'draft': [('readonly', False)]})

    option_ids = fields.One2many('tt.event.option', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    image_ids = fields.Many2many('tt.upload.center', 'event_images_rel', 'event_id', 'image_id', 'Images', readonly=True, states={'draft': [('readonly', False)]})
    active = fields.Boolean('Active', default=True)
    state = fields.Selection(variables.PRODUCT_STATE, 'Product State', default='draft')

    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True, states={'draft': [('readonly', False)]}, domain=get_domain, default=lambda self: self.env.ref('tt_reservation_event.tt_event_provider_internal'))
    provider_code = fields.Char('Provider Code', readonly=True)
    provider_fare_code = fields.Char('Provider Fare Code', readonly=True)

    event_vendor_id = fields.Many2one('tt.vendor', 'Vendor ID')
    booking_event_ids = fields.One2many('tt.event.reservation', 'event_id')

    draft_date = fields.Datetime('Draft at')
    draft_uid = fields.Many2one('res.users', 'User Draft')
    confirm_date = fields.Datetime('Confirm at')
    confirm_uid = fields.Many2one('res.users', 'User Confirm')
    cancel_date = fields.Datetime('Cancel at')
    cancel_uid = fields.Many2one('res.users', 'User Cancel')
    postpone_date = fields.Datetime('Postpone at')
    postpone_uid = fields.Many2one('res.users', 'User Cancel')
    soldout_date = fields.Datetime('Sold-out at')
    soldout_uid = fields.Many2one('res.users', 'User sold-out')
    expired_date = fields.Datetime('Expired at')
    expired_uid = fields.Many2one('res.users', 'User Expired')
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])


    @api.model
    def create(self, vals_list):
        try:
            vals_list['uuid'] = self.env['ir.sequence'].next_by_code(self._name)
            if not vals_list.get('event_vendor_id'):
                vals_list['event_vendor_id'] = self.env.user.vendor_id.id or False
        except:
            pass
        return super(MasterEvent, self).create(vals_list)

    @api.onchange('eligible_age')
    @api.depends('eligible_age')
    def event_date_validation(self):
        if self.eligible_age < 0:
            raise UserError('Eligible Age Minimum is 0')

    @api.onchange('event_date_start', 'event_date_end')
    @api.depends('event_date_start', 'event_date_end')
    def event_age_validation(self):
        if self.event_date_start and self.event_date_end:
            if self.event_date_start > self.event_date_end:
                raise UserError('End Date must Higher then Start Date')

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
            'state': 'draft',
            'draft_date': datetime.now(),
            'draft_uid': self.env.user.id,
        })

    def action_confirm(self):
        if not self.option_ids:
            raise UserError('Ticket Option(s) Must be filled')

        self.write({
            'state': 'confirm',
            'confirm_date': datetime.now(),
            'confirm_uid': self.env.user.id,
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel',
            'cancel_date': datetime.now(),
            'cancel_uid': self.env.user.id,
        })

    def action_postpone(self):
        self.write({
            'state': 'postpone',
            'postpone_date': datetime.now(),
            'postpone_uid': self.env.user.id,
        })

    def action_soldout(self):
        self.write({
            'state': 'sold-out',
            'soldout_date': datetime.now(),
            'soldout_uid': self.env.user.id,
        })

    def action_expired(self):
        self.write({
            'state': 'expired',
            'expired_date': datetime.now(),
            'expired_uid': self.env.user.id,
        })

    def search_event_api(self, req, context):
        try:
            name = req.get('event_name') or ''
            city = req.get('city') or ''
            category = req.get('category') or ''
            online = req.get('online') or ''
            vendor = req.get('vendor') or ''

            limitation = [('state', 'in', ['confirm', 'sold-out', 'expired'])]
            if name != '': #Check by name jika category tidak di kirim
                limitation = ['|',('name', 'ilike', name),('guests', 'ilike', name)]
            if vendor != '':
                limitation = [('state', 'in', ['confirm', 'expired']), ('event_vendor_id', '=', vendor)]
            if category != '' and category != 'all':
                categ_id = self.env['tt.event.category'].search([('name', '=ilike', category)], limit=1)
                limitation.append(('category_ids', 'ilike', categ_id.id))
            if city != '':
                limitation.append(('locations', 'ilike', city))
            if online != '':
                limitation.append(('event_type', '=', online))

            result = self.env['tt.master.event'].sudo().search(limitation)
            to_return = []
            utc = 7
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            for i in result:
                temp_dict = {
                    'id': i.uuid,
                    'name': i.name,
                    'active': i.active,
                    'start_date': i.event_date_start and datetime.strftime(i.event_date_start + relativedelta(hours=utc), '%d %b %Y') or False,
                    'end_date': i.event_date_end and datetime.strftime(i.event_date_end + relativedelta(hours=utc), '%d %b %Y') or False,
                    'start_time': i.event_date_start and datetime.strftime(i.event_date_start + relativedelta(hours=utc), '%H:%M') or False,
                    'end_time': i.event_date_end and datetime.strftime(i.event_date_end + relativedelta(hours=utc), '%H:%M') or False,
                    'category': [rec.name for rec in i.category_ids],
                    'locations': [self.format_api_location(loc.id) for loc in i.location_ids],
                    'description': i.description,
                    'itinerary': i.itinerary,
                    'additional_info': i.additional_info,
                    'to_notice': i.to_notice,
                    'includes': i.includes,
                    'excludes': i.excludes,
                    'provider': i.provider_id.name,
                    'provider_code': i.provider_id.code, ## utk ambil passenger max length
                    'option': i.state not in ['expired',] and [i.format_api_option(opt.id) for opt in i.option_ids] or [],
                    'vendor_obj': {
                        'vendor_id': i.event_vendor_id.id,
                        'vendor_name': i.event_vendor_id.name,
                        'vendor_logo': i.event_vendor_id.logo and '{}/web/image?model={}&id={}&field={}'.format(base_url, i.event_vendor_id._name, str(i.event_vendor_id.id), 'logo') or '',
                        'vendor_address': i.event_vendor_id.address_ids and {
                            'address': i.event_vendor_id.address_ids[0].address or False,
                            'city': i.event_vendor_id.address_ids[0].city_id and i.event_vendor_id.address_ids[0].city_id.name or False,
                            'country': i.event_vendor_id.address_ids[0].country_id and i.event_vendor_id.address_ids[0].country_id.name or False,
                        } or {
                            'address': False,
                            'city': False,
                            'country': False,
                        },
                        'description': i.event_vendor_id.description or False,
                        'est_date': i.event_vendor_id.est_date or False,
                        'join_date': i.event_vendor_id.join_date or False,
                    },
                    'images': [i.format_api_image(img) for img in i.image_ids],
                    # 'age_restriction': i.age_restriction,
                    'eligible_age': i.eligible_age,
                    'utc': utc,
                    'guests': i.guests,
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
            'url': img.url or img.path,
            'description': img.file_reference,
        }

    def format_api_timeslot(self, timeslot_id):
        def str_time_std(str_time):
            if not str_time:
                return '00'
            return '0' + str_time if len(str_time) < 2 else str_time

        timeslot = self.env['tt.event.timeslot'].browse(timeslot_id)
        return {
            'start_date': timeslot.date and datetime.strftime(timeslot.date, '%d %B %Y') or '',
            'end_date': '',
            'start_hour': str_time_std(str(timeslot.start_hour)) + ':' + str_time_std(str(timeslot.start_minute)),
            'end_hour': str_time_std(str(timeslot.end_hour)) + ':' + str_time_std(str(timeslot.end_minute)),
        }

    def format_currency(self, price, orig_currency, new_currency, provider):
        provider_obj = self.env['tt.provider.ho.data'].search([('provider_id.id','=', provider)])
        ## SEHARUSNYA KALAU RATE TIDAK KETEMU & BEDA DENGAN CURRENCY HO ERROR need fix here
        if provider_obj:
            for rate in provider_obj.rate_ids:
                if rate.currency_id.name == orig_currency:
                    return rate.sell_rate * price
        return price

    def format_api_option(self, option_id, currency='IDR'):
        timeslot = self.env['tt.event.option'].sudo().browse(option_id)
        if timeslot.date_end and datetime.now() > timeslot.date_end:
            # Sdah Lewat waktu jual nya
            ticket_qty = 0
        elif timeslot.date_start and datetime.now() < timeslot.date_start:
            # Blum Waktu nya jual
            ticket_qty = -1
        else:
            ticket_qty = timeslot.quota == -1 and 99 or timeslot.quota
        utc = 7
        return {
            'option_id': timeslot.option_code,
            'grade': timeslot.grade,
            'images': [self.format_api_image(i) for i in timeslot.option_image_ids],
            'price': timeslot.currency_id.name == currency and timeslot.price or self.format_currency(timeslot.price, timeslot.currency_id.name, currency, timeslot.event_id.provider_id.id),
            'currency': currency,
            'is_non_refundable': timeslot.is_non_refundable,
            'advance_booking_days': timeslot.advance_booking_days,
            'qty_available': ticket_qty,
            'min_qty': 1,
            'max_qty': timeslot.max_ticket == -1 and ticket_qty or timeslot.max_ticket,
            'cancellation_policy': timeslot.cancellation_policies,
            'description': timeslot.description,
            'timeslot': [self.format_api_timeslot(slot.id) for slot in timeslot.timeslot_ids],
            'ticket_sale_start_day': timeslot.date_start and datetime.strftime(timeslot.date_start + relativedelta(hours=utc), '%Y-%m-%d') or '',
            'ticket_sale_start_hour': timeslot.date_start and datetime.strftime(timeslot.date_start + relativedelta(hours=utc), '%H:%M') or '',
            'ticket_sale_end_day': timeslot.date_end and datetime.strftime(timeslot.date_end + relativedelta(hours=utc), '%Y-%m-%d') or '',
            'ticket_sale_end_hour': timeslot.date_end and datetime.strftime(timeslot.date_end + relativedelta(hours=utc), '%H:%M') or '',
            'utc': utc
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
            'provider': self.provider_id.code,
        }

    def get_form_api(self, req, context):
        try:
            res = self.env['tt.master.event'].sudo().search([('uuid', '=', req['event_code'])])
            result = [{
                'question': rec.question,
                'type': rec.answer_type,
                'required': rec.is_required,
                'is_add_other': rec.is_add_other, #Checkbox
                'answers': rec.answer_type != 'boolean' and [aws.answer for aws in rec.answer_ids] or ['True', 'False'],
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
        event_obj = self.env['tt.master.event'].sudo().search([('state','=','confirm')])
        for i in event_obj:
            temp_dict = {
                'name': i.name,
                'locations': [self.format_api_location(loc.id) for loc in i.location_ids],
                'category': [rec.name for rec in i.category_ids],
                'image_url': [j.url for j in i.image_ids]
            }
            result['event'].append(temp_dict)
        return ERR.get_no_error(result)

    def booking_master_event_from_api(self, req, context):
        # def format_idx(idx):
        #     idx = str(idx)
        #     for a in range(3 - len(idx)):
        #         idx = '0' + idx
        #     return idx

        event_id = self.sudo().search([('uuid', '=', req['event_code'])], limit=1)
        # Check apakah Order Number yg dikirim sdah pernah ada di DB kita?
        if self.env['tt.event.reservation'].sudo().search([('order_number', '=', req['order_number'])]):
            return 'Error'
        # Check apa kah order_number yg dikirim ada di resv event
        book_id = self.env['tt.reservation.event'].search([('name', '=', req['order_number'])], limit=1)
        pnr = self.env['ir.sequence'].next_by_code('pnr_sequence')

        for rec in req['option_ids']:
            opt_id = self.env['tt.event.option'].search([('event_id', '=', event_id.id), ('option_code', '=', rec['option']['event_option_id']['option_code'])], limit=1)
            temp_event_reservation_dict = {
                'event_id': event_id.id,
                'event_option_id': opt_id.id,
                'order_number': req['order_number'],
                'pnr': pnr,
                'validator_sequence': rec['option']['validator_sequence'],
            }
            if book_id:
                temp_event_reservation_dict.update({
                    'booker_id': book_id.booker_id.id,
                    'contact_id': book_id.contact_id.id,
                    'reservation_id': book_id.id,
                })
            opt_obj = self.env['tt.event.reservation'].sudo().create(temp_event_reservation_dict)

            for j1 in rec['option']['extra_question']:
                temp_extra_question_dict = {
                    'event_reservation_id': opt_obj.id,
                    # 'extra_question_id': j1['question_id'],
                    'question': j1['question'],
                    'answer': j1['answer'],
                }
                self.env['tt.event.reservation.answer'].create(temp_extra_question_dict)
            # event_answer.pop(idx)

        for i in req['event_option_codes']:
            option_obj = self.env['tt.event.option'].sudo().search([('option_code', '=', i['option_code'])])
            option_obj.action_hold_book(i['qty'])
        return ERR.get_no_error({
            'pnr': pnr,
            'hold_date': str(datetime.now() + relativedelta(minutes=45))[:16]+':00',
        })

    def issued_master_event_from_api(self, pnr, context={}):
        try:
            #search all of the reservation
            booking_event_objs = self.env['tt.event.reservation'].sudo().search([('pnr', '=', pnr)])

            email_content = "<ul>"
            for i in booking_event_objs:
                i.action_request_by_api(context.get('co_uid'))
                i.event_option_id.making_sales(1)
                email_content += "<li>{}</li>".format(i.order_number)
            email_content += "</ul>"

            #notificate the vendor
            booking_event_obj = booking_event_objs[0]
            booking_event_obj.email_content = email_content
            template = self.env.ref('tt_reservation_event.template_mail_vendor_notification')
            mail = self.env['mail.template'].browse(template.id)
            mail.send_mail(booking_event_obj.id, force_send=True)
            booking_event_obj.email_content = False
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