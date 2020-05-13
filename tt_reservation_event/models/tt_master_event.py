from odoo import api, fields, models
from odoo.http import request
from ...tools import util, variables, ERR, session
from ...tools.ERR import RequestException
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

    uuid = fields.Char('Uuid', readonly=True)
    name = fields.Char('Event Name', readonly=True, states={'draft': [('readonly', False)]})
    category_ids = fields.Many2many('tt.event.category', 'tt_event_category_rel', 'event_id', 'category_id', string='Category', readonly=True, states={'draft': [('readonly', False)]})
    categories = fields.Char('Categories', readonly=True)
    event_type = fields.Selection([('offline', 'Offline'), ('online', 'Online')], readonly=True, states={'draft': [('readonly', False)]})
    # quota = fields.Integer('Quota', readonly=True, states={'draft': [('readonly', False)]})
    # sales = fields.Integer('Sold', readonly=True)
    # basePrice = fields.Many2one('Base Price', digits=(16, 2), readonly=True)
    includes = fields.Html('Price Includes', readonly=True, states={'draft': [('readonly', False)]})
    excludes = fields.Html('Price Excludes', readonly=True, states={'draft': [('readonly', False)]})

    description = fields.Html('Description', readonly=True, states={'draft': [('readonly', False)]})
    # highlights = fields.Html('Highlights', readonly=True)
    additional_info = fields.Html('Additional Info', readonly=True, states={'draft': [('readonly', False)]})
    kid_friendly = fields.Boolean('Kids Friendly', default=False)
    itinerary = fields.Html('Itinerary', readonly=True, states={'draft': [('readonly', False)]})
    to_notice = fields.Html('Warnings', readonly=True, states={'draft': [('readonly', False)]})
    extra_question_ids = fields.One2many('tt.event.extra.question', 'event_id', readonly=True, states={'draft':[('readonly', False)]})
    # safety = fields.Html('Safety', readonly=True)

    location_ids = fields.One2many('tt.event.location', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    locations = fields.Char('Locations', readonly=True)

    event_date_start = fields.Datetime(string="Starting Time", readonly=True, states={'draft': [('readonly', False)]})
    event_date_end = fields.Datetime(string="Finish", readonly=True, states={'draft': [('readonly', False)]})
    number_of_days = fields.Integer("Number of days", readonly=True, states={'draft': [('readonly', False)]})

    option_ids = fields.One2many('tt.event.option', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    image_ids = fields.One2many('tt.master.event.image', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    video_ids = fields.One2many('tt.master.event.video', 'event_id', readonly=True, states={'draft': [('readonly', False)]})
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True, states={'draft': [('readonly', False)]})
    provider_code = fields.Char('Provider Code', readonly=True)
    provider_fare_code = fields.Char('Provider Fare Code', readonly=True)
    # can_hold_booking = fields.Boolean('Can Hold Booking', default=False)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection(variables.PRODUCT_STATE, 'Product State', readonly=True, default='draft')

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

    def search_by_api(self, req, context):
        try:
            name = req.get('event_name') and '%' + req['event_game'] + '%' or ''
            city = req.get('city') and '%' + req['city'] or ''
            category = req.get('category') and '%' + req['category'] + '%' or ''
            online = req.get('online') and '%' + req['online'] + '%' or ''

            limitation = []
            if name != '':
                limitation.append(('name', '=ilike', name))
            if city != '':
                limitation.append(('locations', '=ilike', city))
            if category != '':
                limitation.append(('categories', '=ilike', category))
            if online != '':
                limitation.append(('event_type', '=', online))

            result = self.env['tt.master.event'].sudo().search(limitation)

            #built the return response

        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)


    def format_api_image(self, img):
        return {
            'url': img.image_url or img.image_path,
            'description': img.desc,
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
            'qty_available': '1',
            'min_qty': '1',
            'max_qty': '5',
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
            'lat': '',
            'long': '',
        }

    def format_api(self):
        return {
            'name': self.name,
            'tags': self.categories and self.categories.split(',') or [],
            'images': [self.format_api_image(img) for img in self.image_ids],
            'terms_and_condition': self.additional_info,
            'detail': self.description,
            'option': [self.format_api_option(opt.id) for opt in self.option_ids],
            'locations': [self.format_api_location(loc.id) for loc in self.location_ids],
        }


    def search_event_api(self, req, context):
        limit = context.get('limit') or 100
        result = []
        for rec in self.search(['|',('name', 'ilike', req['event_name']),('locations', 'ilike', req['event_name'])], limit=limit):
            result.append(rec.format_api())
        return {'response': result,}


    def get_cities_by_api(self, id):
        try:
            result_objs = self.env['res.city'].sudo().search([('country_id', '=', int(id))])
            cities = []
            for i in result_objs:
                cities.append({
                    'name': i.name,
                    'uuid': i.id
                })
            return ERR.get_no_error(cities)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_states_by_api(self, id):
        try:
            result_objs = self.env['res.country.state'].sudo().search([('country_id', '=', int(id))])
            states = []
            for i in result_objs:
                states.append({
                    'name': i.name,
                    'uuid': i.id
                })
            return ERR.get_no_error(states)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_cities_state_by_api(self, id):
        try:
            result_objs = self.env['res.city'].sudo().search([('state_id', '=', int(id))])
            cities = []
            for i in result_objs:
                cities.append({
                    'name': i.name,
                    'uuid': i.id
                })
                return ERR.get_no_error(cities)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def get_form_api(self, req, context):
        try:
            event_id = req.get('event_id') and '%' + req['event_id'] + '%' or ''

            result = self.env['tt.master.event'].sudo().search([('id', '=', event_id)])
            result[0].update({
                'extra_question_ids': self.env['tt.event.extra.question'].sudo().search([('event_id', '=', result[0]['id'])]),
                'event_option_ids': self.env['tt.event.option'].sudo().search([('event_id', '=', result[0]['id'])])
            })
            for i in result[0]['event_option_ids']:
                i.update({
                    'timeslot_ids': self.env['tt.event.timeslot'].sudo().search([('event_option_id', '=', i['id'])])
                })

            return ERR.get_no_error(result)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    # def get_detail_by_api(self, req, context):
    #     try:
    #         result_objs = self.env['tt.master.event.category'].sudo().search([])
    #         categories = result_objs.filtered(lambda x: x.type == ' category' and not x.parent_id)
    #         categories_list = []
    #         for i in categories:
    #             child_list = []
    #             for j in i.child_ids:
    #                 child_list.append({
    #                     'name': j.name,
    #                     'uuid': i.id
    #                 })
    #             categories_list.append({
    #                 'name': i.name,
    #                 'uuid': i.id,
    #                 'children': child_list
    #             })
    #         types = result_objs.filtered(lambda x: x.type == 'type')
    #         type_list = []
    #         for type in types:
    #             type_list.append({
    #                 'name': type.name,
    #                 'uuid': type.id
    #             })
    #
    #         country_list = []
    #         country_objs = self.env['res.country'].sudo().search([('provider_city_ids', '!=', False)])
    #         for country in country_objs:
    #             state = self.get_states_by_api(country.id)
    #             if state.get('error_code'):
    #                 _logger.info(state['error_msg'])
    #                 raise Exception(state['error_msg'])
    #             if len(state['response']) > 0:
    #                 state_list = []
    #                 for temp_state in state['response']:
    #                     city = self.get_cities_state_by_api(int(temp_state['uuid']))
    #                     if city.get('error_code'):
    #                         _logger.info(city['error_msg'])
    #                         raise Exception(city['error_msg'])
    #                     city_list = []
    #                     for temp_city in city['response']:
    #                         city_list.append(temp_city)
    #                     temp_state['cities'] = city_list
    #                     state_list.append(temp_state)
    #             else:
    #                 city = self.get_cities_by_api(country.id)
    #                 if city.get('error_code'):
    #                     _logger.info(city['error_msg'])
    #                     raise Exception(city['error_msg'])
    #                 city_list = []
    #                 for i in city['response']:
    #                     city_list.append(i)
    #                 state_list = [{
    #                     'name': False,
    #                     'uuid': False,
    #                     'cities': city_list
    #                 }]
    #
    #             country_list.append({
    #                 'name': country.name,
    #                 'code': country.code,
    #                 'uuid': country.id,
    #                 'states': state_list
    #             })
    #
    #         values = {
    #             'categories': {
    #                 'data': categories_list
    #             },
    #             'types': {
    #                 'data': type_list
    #             },
    #             'locations': [{
    #                 'countries': country_list
    #             }]
    #         }
    #         return ERR.get_no_error(values)
    #     except RequestException as e:
    #         _logger.error(traceback.format_exc())
    #         return e.error_dict()
    #     except Exception as e:
    #         _logger.error(traceback.format_exc())
    #         return ERR.get_error(1021)

    # def search_by_api(self, req, context):
    #     try:
    #         query = req.get('query') and '%' + req['query'] + '%' or ''
    #         country = req.get('country') and req['country'] or ''
    #         city = req.get('city') and req['city'] or ''
    #         type_id = 0
    #         if req.get('type'):
    #             temp_type_id = req['type'] != '0' and self.env['tt.master.event.category'].sudo().search([('id', '=', req['type']), ('type', '=', 'type')]) or ''
    #             type_id = temp_type_id and temp_type_id[0].id or 0
    #
    #         get_cat_instead = 0
    #         category = ''
    #         if req.get('sub_category'):
    #             if req['sub_category'] != '0':
    #                 category = req['sub_category']
    #             else:
    #                 get_cat_instead = 1
    #         else:
    #             get_cat_instead = 1
    #
    #         if get_cat_instead:
    #             if req.get('category'):
    #                 category = req['category'] != '0' and req['category'] or ''
    #             else:
    #                 category = ''
    #
    #         provider = req.get('provider', 'all')
    #         provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
    #         provider_id = provider_id and provider_id[0] or False
    #         provider_code = provider_id and provider_id[0].code or ''
    #
    #         sql_query = """
    #         SELECT event.*
    #         FROM tt_master_event event
    #         LEFT JOIN tt_event_location_rel locrel ON locrel.event_id = event.id
    #         LEFT JOIN tt_master_event_location location ON locrel.location_id = location.id
    #         """
    #
    #         if category:
    #             sql_query += """
    #             LEFT JOIN tt_event_category_rel catrel ON catrel.event_id = event.id
    #             """
    #         sql_query += "WHERE "
    #
    #         if query:
    #             sql_query += """
    #             event.name ILIKE '""" + str(query) + """'
    #             """
    #         else:
    #             sql_query += """
    #             event.active = TRUE AND event."basePrice" > 0
    #             """
    #
    #         if category:
    #             sql_query += """
    #             AND catrel.category_id = """ + str(category) + """
    #             """
    #
    #         if req.get('country') and not req.get('city'):
    #             sql_query += "AND (location.country_id = {}) ".format(str(country))
    #
    #         if req.get('city'):
    #             sql_query += "and (location.country_id = {} and location.city_id = {}) ".format(str(country), str(city))
    #
    #         if query:
    #             sql_query += 'AND event.active = True AND event."basePrice" > 0'
    #         sql_query += 'GROUP BY event.id'
    #
    #         self.env.cr.execute(sql_query)
    #
    #         result_id_list = self.env.cr.dictfetchall()
    #         result_list = []
    #
    #     except RequestException as e:
    #         _logger.error(traceback.format_exc())
    #         return e.error_dict()
    #     except Exception as e:
    #         _logger.error(traceback.format_exc())
    #         return ERR.get_error(1021)

    # def get_detail_by_api(self, req, context):
    #     try:
    #         print("HelloWorld")
    #     except RequestException as e:
    #         _logger.error(traceback.format_exc())
    #         return e.error_dict()
    #     except Exception as e:
    #         _logger.error(traceback.format_exc())
    #         return ERR.get_error(1022)

