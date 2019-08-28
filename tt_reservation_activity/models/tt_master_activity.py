from odoo import api, fields, models
from odoo.http import request
from ...tools import util,variables,ERR
from .ApiConnector_Activity import ApiConnectorActivity
import logging, traceback
import json
import base64
import pickle
from datetime import datetime
import csv

_logger = logging.getLogger(__name__)

from ...tools import session
SESSION_NT = session.Session()


class ActivitySyncProducts(models.TransientModel):
    _name = "activity.sync.product.wizard"
    _description = 'Rodex Model'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_activity.tt_provider_type_activity').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    provider_code = fields.Char('Provider Code')
    add_parameter = fields.Char('Additional Parameter', default='')

    def sync_product(self):
        def_name = 'action_sync_%s' % self.provider_id.code
        add_parameter = self.add_parameter
        if hasattr(self.env['tt.master.activity'], def_name):
            getattr(self.env['tt.master.activity'], def_name)(add_parameter)

    def config_product(self):
        def_name = 'action_sync_config_%s' % self.provider_id.code
        add_parameter = self.add_parameter
        if hasattr(self.env['tt.master.activity'], def_name):
            getattr(self.env['tt.master.activity'], def_name)(add_parameter)

    def deactivate_product(self):
        products = self.env['tt.master.activity'].sudo().search([('provider_id', '=', self.provider_id.id)])
        for rec in products:
            if rec.active:
                rec.sudo().write({
                    'active': False
                })

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id.code


class MasterActivity(models.Model):
    _name = 'tt.master.activity'
    _description = 'Rodex Model'

    uuid = fields.Char('Uuid')
    name = fields.Char('Activity Name')
    # type_id = fields.Many2one('tt.activity.category', 'Type')
    type_ids = fields.Many2many('tt.activity.category', 'tt_activity_type_rel', 'activity_id', 'type_id', string='Types')
    category_ids = fields.Many2many('tt.activity.category', 'tt_activity_category_rel', 'activity_id', 'category_id', string='Categories')
    currency_id = fields.Many2one('res.currency', 'Currency')
    basePrice = fields.Float('Base Price', digits=(16, 2))
    priceIncludes = fields.Html('Price Includes')
    priceExcludes = fields.Html('Price Excludes')

    description = fields.Html('Description')
    highlights = fields.Html('Highlights')
    additionalInfo = fields.Html('Additional Info')
    itinerary = fields.Html('Itinerary')
    warnings = fields.Html('Warnings')
    safety = fields.Html('Safety')

    latitude = fields.Float('Latitude', digits=(11, 7))
    longitude = fields.Float('Longitude', digits=(11, 7))
    location_ids = fields.Many2many('tt.activity.master.locations', 'tt_activity_location_rel', 'product_id', 'location_id', string='Location')

    minPax = fields.Integer('Adult Min')
    maxPax = fields.Integer('Adult Max')
    reviewCount = fields.Integer('Review Count')
    reviewAverageScore = fields.Float('Review Average Score', digits=(10, 2))
    businessHoursFrom = fields.Char(string='Business Hours From')
    businessHoursTo = fields.Char(string='Business Hours To')
    hotelPickup = fields.Boolean('Hotel Pickup')
    airportPickup = fields.Boolean('Airport Pickup')

    line_ids = fields.One2many('tt.master.activity.lines', 'activity_id', 'Product Types')
    image_ids = fields.One2many('tt.activity.master.images', 'activity_id', 'Images Path')
    video_ids = fields.One2many('tt.activity.master.videos', 'activity_id', 'Video Path')
    provider_id = fields.Many2one('tt.provider', 'Provider')
    provider_code = fields.Char('Provider Code')
    active = fields.Boolean('Active', default=True)

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id.code

    def reprice_currency(self, provider, from_currency, base_amount, to_currency='IDR'):
        from_currency_id = self.env['res.currency'].sudo().search([('name', '=', from_currency)], limit=1)
        from_currency_id = from_currency_id and from_currency_id[0] or False
        provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
        provider_id = provider_id[0]
        multiplier = self.env['tt.provider.rate'].sudo().search([('provider_id', '=', provider_id.id), ('date', '<=', datetime.now()), ('currency_id', '=', from_currency_id.id)], limit=1)
        computed_amount = base_amount * multiplier[0].sell_rate
        return computed_amount

    def action_sync_config_globaltix(self, add_parameter):
        self.sync_config('globaltix')

    def action_sync_config_bemyguest(self, add_parameter):
        self.sync_config('bemyguest')

    def action_sync_config_klook(self, add_parameter):
        activity_id_list = []
        temp_act_id_list = []
        with open("/var/log/tour_travel/klook_master_data/klook_master_data" + str(add_parameter) + ".csv", 'r') as file:
            file_content = csv.reader(file)
            for idx, rec in enumerate(file_content):
                if idx == 0:
                    continue
                temp_act = rec[2]
                klook_act_id = temp_act.split(' - ')[0]
                if klook_act_id.isdigit():
                    if int(klook_act_id) not in temp_act_id_list:
                        temp_act_id_list.append(int(klook_act_id))
                        activity_id_list.append({
                            'id': int(klook_act_id)
                        })
            print(activity_id_list)
        file.close()

    def action_sync_products(self, provider, add_parameter):
        cookie = None
        res = ApiConnectorActivity().signin()
        if res.get('response'):
            temp_res = json.loads(res['response'])
            if temp_res['result'].get('response'):
                cookie = temp_res['result']['response'].get('signature') and temp_res['result']['response']['signature'] or None

        req_post = {
            'query': '',
            'type': '',
            'category': '',
            'country': '',
            'city': '',
            'sort': 'price',
            'page': 1,
            'per_page': 1,
            'provider': provider
        }

        file = {}
        res = ApiConnectorActivity().search(req_post, cookie)
        if res['error_code'] == 0:
            file = res['response']
        if file:
            total_pages = file['total_pages']
            for page in range(total_pages):
                self.sync_products(provider, add_parameter, page+1)

    def action_sync_globaltix(self, add_parameter):
        provider = 'globaltix'

        cookie = None
        res = ApiConnectorActivity().signin()
        if res.get('response'):
            try:
                temp_res = json.loads(res['response'])
            except Exception as e:
                temp_res = res['response']
                _logger.info(res)
                _logger.info(res['response'])
            if temp_res['result'].get('response'):
                cookie = temp_res['result']['response'].get('signature') and temp_res['result']['response']['signature'] or None

        req_post = {
            'provider': provider
        }

        file = []
        res = ApiConnectorActivity().get_countries(req_post, cookie)
        if res['error_code'] == 0:
            file = res['response']

        for country in file:
            req_post = {
                'query': '',
                'type': '',
                'category': '',
                'country': country,
                'city': '',
                'sort': 'price',
                'page': 1,
                'per_page': 1,
                'provider': provider
            }

            file2 = []
            res2 = ApiConnectorActivity().search(req_post, cookie)
            if res2['error_code'] == 0:
                file2 = res2['response']

            if file2:
                self.sync_products(provider, file2)

    def action_sync_bemyguest(self, add_parameter):
        self.action_sync_products('bemyguest', add_parameter)

    def action_sync_klook(self, add_parameter):
        self.action_sync_products('klook', add_parameter)

    def sync_config(self, provider):
        cookie = None
        res = ApiConnectorActivity().signin()
        if res.get('response'):
            temp_res = json.loads(res['response'])
            if temp_res['result'].get('response'):
                cookie = temp_res['result']['response'].get('signature') and temp_res['result']['response']['signature'] or None

        req_post = {
            'provider': provider
        }

        file = {}
        res = ApiConnectorActivity().get_config(req_post, cookie)
        if res['error_code'] == 0:
            file = json.loads(res['response'])

        if file:
            try:
                vendor_id = self.env['tt.provider'].search([('code', '=', provider)], limit=1)
                vendor_id = vendor_id[0].id
                continent_id = False
                for continent in file['locations']:
                    for country in continent['countries']:
                        country_id = self.env['res.country'].update_provider_data(country['name'], country['uuid'], vendor_id, continent_id)
                        if country.get('states'):
                            for state in country['states']:
                                state_id = False
                                if state.get('name'):
                                    state_id = self.env['res.country.state'].update_provider_data(state['name'], state['uuid'], vendor_id, country_id)
                                if state.get('cities'):
                                    for city in state['cities']:
                                        self.env['res.city'].update_provider_data(city['name'], city['uuid'], vendor_id, state_id)
                if provider == 'bemyguest':
                    type_lib = {
                        'categories': 'category',
                        'types': 'type',
                    }
                    for index in ['categories', 'types']:
                        for rec in file[index]['data']:
                            obj_id = self.env['tt.activity.category'].search([('name', '=', rec['name'])])
                            if obj_id:
                                line_obj = self.env['tt.activity.category.lines'].search([('category_id', '=', obj_id.id), ('provider_id', '=', vendor_id)])
                                line_obj.uuid = rec['uuid']
                                obj_id.parent_id = False
                            else:
                                obj_id = self.env['tt.activity.category'].sudo().create({
                                    'name': rec['name'],
                                    'type': type_lib[index],
                                    'parent_id': False,
                                })
                                self.env.cr.commit()
                                self.env['tt.activity.category.lines'].sudo().create({
                                    'uuid': rec['uuid'],
                                    'provider_id': vendor_id,
                                    'category_id': obj_id.id,
                                })
                                self.env.cr.commit()
                            if rec.get('children'):
                                for child in rec['children']:
                                    child_id = self.env['tt.activity.category'].search([('name', '=', child['name'])])
                                    if child_id:
                                        child_lines = self.env['tt.activity.category.lines'].search([('category_id', '=', child_id.id), ('provider_id', '=', vendor_id)])
                                        child_lines.uuid = child['uuid']
                                        child_id.parent_id = obj_id.id
                                    else:
                                        child_id = self.env['tt.activity.category'].sudo().create({
                                            'name': child['name'],
                                            'type': type_lib[index],
                                            'parent_id': obj_id.id,
                                        })
                                        self.env.cr.commit()
                                        self.env['tt.activity.category.lines'].sudo().create({
                                            'uuid': child['uuid'],
                                            'provider_id': vendor_id,
                                            'category_id': child_id.id,
                                        })
                                        self.env.cr.commit()
                return True
            except Exception as e:
                return False
        else:
            return False

    def sync_products(self, provider=None, data=None, page=None):
        file = False
        if provider in ['bemyguest', 'klook']:
            cookie = None
            res = ApiConnectorActivity().signin()
            if res.get('response'):
                temp_res = json.loads(res['response'])
                if temp_res['result'].get('response'):
                    cookie = temp_res['result']['response'].get('signature') and temp_res['result']['response']['signature'] or None

            req_post = {
                'query': '',
                'type': '',
                'category': '',
                'country': '',
                'city': '',
                'sort': 'price',
                'page': page,
                'per_page': 100,
                'provider': provider
            }

            if provider == 'klook':
                activity_id_list = []
                with open("/var/log/tour_travel/klook_master_data/klook_master_data.csv", 'r') as file:
                    file_content = csv.reader(file)
                    for idx, rec in enumerate(file_content):
                        if idx == 0:
                            continue
                        temp_act = rec[2]
                        activity_id_list.append({
                            'id': temp_act.split(' - ')[0]
                        })
                    print(activity_id_list)
                file.close()

                req_post.update({
                    'master_data': activity_id_list,
                    'data_size': len(activity_id_list),
                })

            file = {}
            res = ApiConnectorActivity().search(req_post, cookie)
            if res['error_code'] == 0:
                file = res['response']
            else:
                _logger.error('ERROR Sync Activity %s: %s, %s' % (request.session.sid, res['error_code'], res['error_msg']))

        if provider == 'globaltix':
            file = data

        if file:
            for rec in file['product_detail']:
                provider_id = self.env['tt.provider'].sudo().search([('code', '=', rec['product']['provider'])], limit=1)
                provider_id = provider_id and provider_id[0] or False
                product_obj = self.env['tt.master.activity'].search([('uuid', '=', rec['product']['uuid']), ('provider_id', '=', provider_id.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                product_obj = product_obj and product_obj[0] or False
                temp = []
                temp3 = self.env['tt.provider'].search([('code', '=', provider)], limit=1)
                temp3 = temp3[0]
                if provider == 'klook':
                    parent_cat_obj = False
                    for category in rec['product']['categories']:
                        category_obj = self.env['tt.activity.category'].search(
                            [('name', '=', category['name']), ('type', '=', 'category')], limit=1)
                        parent_cat_obj = category_obj
                        if not category_obj:
                            parent_cat_obj = self.env['tt.activity.category'].sudo().create({
                                'name': category['name'],
                                'type': 'category',
                                'parent_id': False,
                            })
                            self.env.cr.commit()
                    for child_cat in rec['product']['subcategories']:
                        child_cat_obj = self.env['tt.activity.category'].search(
                            [('name', '=', child_cat['name']), ('type', '=', 'category')], limit=1)
                        if not child_cat_obj:
                            child_cat_obj = self.env['tt.activity.category'].sudo().create({
                                'name': child_cat['name'],
                                'type': 'category',
                                'parent_id': parent_cat_obj.id,
                            })
                            self.env.cr.commit()
                            self.env['tt.activity.category.lines'].sudo().create({
                                'uuid': child_cat['uuid'],
                                'provider_id': temp3.id,
                                'category_id': child_cat_obj.id,
                            })
                            self.env.cr.commit()
                        temp.append(child_cat_obj.id)
                else:
                    for category in rec['product']['categories']:
                        category_obj = self.env['tt.activity.category'].search([('name', '=', category['name']), ('type', '=', 'category')], limit=1)
                        if not category_obj:
                            category_obj = self.env['tt.activity.category'].sudo().create({
                                'name': category['name'],
                                'type': 'category',
                                'parent_id': False,
                            })
                            self.env.cr.commit()
                            self.env['tt.activity.category.lines'].sudo().create({
                                'uuid': category['uuid'],
                                'provider_id': temp3.id,
                                'category_id': category_obj.id,
                            })
                            self.env.cr.commit()
                        temp.append(category_obj.id)
                temp2 = []

                if rec['product'].get('country_id'):
                    rec_prov = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
                    rec_prov_id = rec_prov[0].id
                    rec_provider_codes = self.env['tt.provider.code'].sudo().search([('code', '=', rec['product']['country_id']), ('provider_id', '=', rec_prov_id)])
                    for prov_data in rec_provider_codes:
                        new_loc = self.env['tt.activity.master.locations'].sudo().create({
                            'country_id': prov_data.country_id.id,
                            'city_id': False,
                            'state_id': False,
                        })
                        self.env.cr.commit()
                        city_id = self.env['res.city'].sudo().search([('name', '=', rec['product']['cities'][0])], limit=1)
                        new_loc.city_id = city_id
                        temp2.append(new_loc.id)
                else:
                    for idx, countries in enumerate(rec['product']['countries']):
                        country_id = self.env['res.country'].sudo().search([('name', '=', countries)], limit=1)
                        new_loc = self.env['tt.activity.master.locations'].sudo().create({
                            'country_id': country_id.id,
                            'city_id': False,
                            'state_id': False,
                        })
                        self.env.cr.commit()
                        city_id = self.env['res.city'].sudo().search([('name', '=', rec['product']['cities'][idx])], limit=1)
                        new_loc.city_id = city_id
                        temp2.append(new_loc.id)

                types_temp = []
                if provider == 'klook':
                    for type_temp in rec['product']['type']:
                        tipe = self.env['tt.activity.category'].search([('name', '=', type_temp['category']), ('type', '=', 'type')])
                        for tip in tipe:
                            types_temp.append(tip.id)

                if product_obj:
                    product_obj.update({
                        'name': rec['product']['title'],
                        'type_ids': [(6, 0, types_temp)],
                        'category_ids': [(6, 0, temp)],
                        'location_ids': [(6, 0, temp2)],
                        'currency_id': self.env['res.currency'].search([('name', '=', rec['product']['currency'])], limit=1).id,
                        'basePrice': rec['product']['basePrice'],
                        'priceIncludes': rec['product']['priceIncludes'],
                        'priceExcludes': rec['product']['priceExcludes'],
                        'description': rec['product']['description'],
                        'highlights': rec['product']['highlights'],
                        'additionalInfo': rec['product']['additionalInfo'],
                        'itinerary': rec['product']['itinerary'],
                        'warnings': rec['product']['warnings'],
                        'safety': rec['product']['safety'],
                        'latitude': rec['product']['latitude'],
                        'longitude': rec['product']['longitude'],
                        'minPax': rec['product']['minPax'],
                        'maxPax': rec['product']['maxPax'],
                        'reviewCount': rec['product']['reviewCount'],
                        'reviewAverageScore': rec['product']['reviewAverageScore'],
                        'businessHoursFrom': rec['product']['businessHoursFrom'],
                        'businessHoursTo': rec['product']['businessHoursTo'],
                        'hotelPickup': rec['product']['hotelPickup'],
                        'airportPickup': rec['product']['airportPickup'],
                        'active': True,
                        'provider_id': provider_id.id,
                    })
                else:
                    vals = {
                        'uuid': rec['product']['uuid'],
                        'name': rec['product']['title'],
                        'type_ids': [(6, 0, temp)],
                        'category_ids': [(6, 0, temp)],
                        'location_ids': [(6, 0, temp2)],
                        'currency_id': self.env['res.currency'].search([('name', '=', rec['product']['currency'])], limit=1).id,
                        'basePrice': rec['product']['basePrice'],
                        'priceIncludes': rec['product']['priceIncludes'],
                        'priceExcludes': rec['product']['priceExcludes'],
                        'description': rec['product']['description'],
                        'highlights': rec['product']['highlights'],
                        'additionalInfo': rec['product']['additionalInfo'],
                        'itinerary': rec['product']['itinerary'],
                        'warnings': rec['product']['warnings'],
                        'safety': rec['product']['safety'],
                        'latitude': rec['product']['latitude'],
                        'longitude': rec['product']['longitude'],
                        'minPax': rec['product']['minPax'],
                        'maxPax': rec['product']['maxPax'],
                        'reviewCount': rec['product']['reviewCount'],
                        'reviewAverageScore': rec['product']['reviewAverageScore'],
                        'businessHoursFrom': rec['product']['businessHoursFrom'],
                        'businessHoursTo': rec['product']['businessHoursTo'],
                        'hotelPickup': rec['product']['hotelPickup'],
                        'airportPickup': rec['product']['airportPickup'],
                        'active': True,
                        'provider_id': provider_id.id,
                    }
                    product_obj = self.env['tt.master.activity'].sudo().create(vals)
                    if rec['product']['provider'] == 'bemyguest':
                        try:
                            uuid = rec['product']['uuid']
                            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                            product_an_req = {
                                'uuid': uuid,
                                'provider': rec['product']['provider'],
                                'productUrl': base_url + '/agent/activity/product_details?uuid=' + uuid,
                                'environment': 'live',
                                'platform': 'web',
                            }
                            res = ApiConnectorActivity().send_product_analytics(product_an_req, cookie)
                        except Exception as e:
                            _logger.error('Error: Failed send Product Analytics. \n %s : %s' % (traceback.format_exc(), str(e)))
                    self.env.cr.commit()

                images = self.env['tt.activity.master.images'].search([('activity_id', '=', product_obj.id)])
                images.sudo().unlink()
                for img in rec['product']['photos']:
                    data_values = {
                        'activity_id': product_obj.id,
                        'photos_url': rec['product']['photosUrl'],
                        'photos_path': img,
                    }
                    self.env['tt.activity.master.images'].sudo().create(data_values)
                    self.env.cr.commit()

                videos = self.env['tt.activity.master.videos'].search([('activity_id', '=', product_obj.id)])
                videos.sudo().unlink()
                if rec['product'].get('videos'):
                    for vid in rec['product']['videos']:
                        data_values = {
                            'activity_id': product_obj.id,
                            'video_url': vid,
                        }
                        self.env['tt.activity.master.videos'].sudo().create(data_values)
                        self.env.cr.commit()

                def_name = 'sync_type_products_%s' % provider
                if hasattr(self, def_name):
                    getattr(self.env['tt.master.activity'], def_name)(rec, product_obj.id, provider)

    def sync_type_products_bemyguest(self, result, product_id, provider):
        cookie = None
        res = ApiConnectorActivity().signin()
        if res.get('response'):
            temp_res = json.loads(res['response'])
            if temp_res['result'].get('response'):
                cookie = temp_res['result']['response'].get('signature') and temp_res['result']['response']['signature'] or None

        req_post = {
            'product_uuid': result['product']['uuid'],
            'provider': provider
        }
        res = ApiConnectorActivity().get_details(req_post, cookie)
        if res['error_code'] == 0:
            activity_old_obj = self.env['tt.master.activity.lines'].search([('activity_id', '=', product_id)])
            activity_old_obj.sudo().unlink()
            for rec in res['response']:
                cancellationPolicies = ''
                if rec['type_details']['data']['cancellationPolicies']:
                    for cancel in rec['type_details']['data']['cancellationPolicies']:
                        cancellationPolicies += 'Please refund ' + str(cancel['numberOfDays']) + ' days before the stated visit date to accept ' + str(cancel['refundPercentage']) + '% cashback.\n'
                vals = {
                    'activity_id': product_id,
                    'uuid': rec['type_details']['data']['uuid'],
                    'name': rec['type_details']['data']['title'],
                    'description': rec['type_details']['data']['description'],
                    'durationDays': rec['type_details']['data']['durationDays'],
                    'durationHours': rec['type_details']['data']['durationHours'],
                    'durationMinutes': rec['type_details']['data']['durationMinutes'],
                    'isNonRefundable': rec['type_details']['data']['isNonRefundable'],
                    'minPax': rec['type_details']['data']['minGroup'],
                    'maxPax': rec['type_details']['data']['maxGroup'],
                    'voucherUse': rec['type_details']['data']['voucherUse'],
                    'voucherRedemptionAddress': rec['type_details']['data']['voucherRedemptionAddress'],
                    'voucherRequiresPrinting': rec['type_details']['data']['voucherRequiresPrinting'],
                    'cancellationPolicies': cancellationPolicies,
                    'voucher_validity_type': rec['type_details']['data']['validity']['type'],
                    'voucher_validity_days': rec['type_details']['data']['validity']['days'],
                    'voucher_validity_date': rec['type_details']['data']['validity']['date'],
                    'meetingLocation': rec['type_details']['data']['meetingLocation'],
                    'meetingAddress': rec['type_details']['data']['meetingAddress'],
                    'meetingTime': rec['type_details']['data']['meetingTime'],
                    'instantConfirmation': rec['type_details']['data']['instantConfirmation'],
                    'advanceBookingDays': 0,
                    'minimumSellingPrice': 0,
                }
                activity_obj = self.env['tt.master.activity.lines'].sudo().create(vals)
                self.env.cr.commit()

                sku_vals = {
                    'activity_line_id': activity_obj.id,
                    'sku_id': 'Adult',
                    'title': 'Adult',
                    'minPax': rec['type_details']['data']['minPax'],
                    'maxPax': rec['type_details']['data']['maxPax'],
                    'minAge': rec['type_details']['data']['minAdultAge'],
                    'maxAge': rec['type_details']['data']['maxAdultAge'],
                }
                sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                self.env.cr.commit()

                if rec['type_details']['data']['allowChildren']:
                    sku_vals = {
                        'activity_line_id': activity_obj.id,
                        'sku_id': 'Child',
                        'title': 'Child',
                        'minPax': rec['type_details']['data']['minChildren'],
                        'maxPax': rec['type_details']['data']['maxChildren'],
                        'minAge': rec['type_details']['data']['minChildAge'],
                        'maxAge': rec['type_details']['data']['maxChildAge'],
                    }
                    sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                    self.env.cr.commit()

                if rec['type_details']['data']['allowSeniors']:
                    sku_vals = {
                        'activity_line_id': activity_obj.id,
                        'sku_id': 'Senior',
                        'title': 'Senior',
                        'minPax': rec['type_details']['data']['minSeniors'],
                        'maxPax': rec['type_details']['data']['maxSeniors'],
                        'minAge': rec['type_details']['data']['minSeniorAge'],
                        'maxAge': rec['type_details']['data']['maxSeniorAge'],
                    }
                    sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                    self.env.cr.commit()

                if rec['type_details']['data']['allowInfant']:
                    sku_vals = {
                        'activity_line_id': activity_obj.id,
                        'sku_id': 'Infant',
                        'title': 'Infant',
                        'minPax': 0,
                        'maxPax': 5,
                        'minAge': rec['type_details']['data']['minInfantAge'],
                        'maxAge': rec['type_details']['data']['maxInfantAge'],
                    }
                    sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                    self.env.cr.commit()

                if rec['type_details']['data']['timeslots']:
                    for time in rec['type_details']['data']['timeslots']:
                        value = {
                            'product_type_id': activity_obj.id,
                            'uuid': time['uuid'],
                            'startTime': time['startTime'],
                            'endTime': time['endTime'],
                        }
                        self.env['tt.activity.master.timeslot'].sudo().create(value)
                        self.env.cr.commit()
                option_ids = []
                if rec['type_details']['data']['options']['perBooking']:
                    for book in rec['type_details']['data']['options']['perBooking']:
                        value2 = {
                            # 'product_type_id': activity_obj.id,
                            'uuid': book['uuid'],
                            'name': book['name'],
                            'description': book['description'],
                            'required': book['required'],
                            'formatRegex': book['formatRegex'],
                            'inputType': book['inputType'],
                            'price': book.get('price', 0),
                            'type': 'perBooking',
                        }
                        temp2 = self.env['tt.activity.booking.option'].sudo().create(value2)
                        self.env.cr.commit()
                        if book.get('items'):
                            for item in book['items']:
                                value4 = {
                                    'booking_option_id': temp2.id,
                                    'label': item['label'],
                                    'value': item['value'],
                                    'price': item.get('price', 0),
                                    'currency_id': self.env['res.currency'].search([('name', '=', 'SGD')], limit=1).id,
                                }
                                self.env['tt.activity.booking.option.line'].sudo().create(value4)
                                self.env.cr.commit()
                        option_ids.append(temp2.id)
                if rec['type_details']['data']['options']['perPax']:
                    for pax in rec['type_details']['data']['options']['perPax']:
                        value3 = {
                            # 'product_type_id': activity_obj.id,
                            'uuid': pax['uuid'],
                            'name': pax['name'],
                            'description': pax['description'],
                            'required': pax['required'],
                            'formatRegex': pax['formatRegex'],
                            'inputType': pax['inputType'],
                            'price': pax.get('price', 0),
                            'type': 'perPax',
                        }
                        temp = self.env['tt.activity.booking.option'].sudo().create(value3)
                        self.env.cr.commit()
                        if pax.get('items'):
                            for item in pax['items']:
                                value5 = {
                                    'booking_option_id': temp.id,
                                    'label': item['label'],
                                    'value': item['value'],
                                    'price': item.get('price', 0),
                                    'currency_id': self.env['res.currency'].search([('name', '=', 'SGD')], limit=1).id,
                                }
                                self.env['tt.activity.booking.option.line'].sudo().create(value5)
                                self.env.cr.commit()
                        option_ids.append(temp.id)
                activity_obj.update({
                    'option_ids': [(6, 0, option_ids)],
                })

    def sync_type_products_globaltix(self, result, product_id, provider):
        activity_old_obj = self.env['tt.master.activity.lines'].search([('activity_id', '=', product_id)])
        activity_old_obj.sudo().unlink()

        for rec2 in result['product_detail']:
            cancel = ''
            if rec2['cancellationPolicySettings']:
                cancel = 'Please refund ' + str(rec2['cancellationPolicySettings']['refundDuration']) + ' days before the stated visit date to accept ' + str(rec2['cancellationPolicySettings']['percentReturn']) + '% cashback.\n'
            is_senior = False
            is_adult = False
            is_child = False
            if rec2.get('variation'):
                if rec2['variation']['name'] == 'ADULT':
                    is_adult = True
                elif rec2['variation']['name'] == 'CHILD':
                    is_child = True
                elif rec2['variation']['name'] == 'SENIOR_CITIZEN':
                    is_senior = True

            vals = {
                'activity_id': product_id,
                'uuid': rec2['id'],
                'name': rec2['name'],
                'description': rec2['description'],
                'durationDays': 1,
                'durationHours': 0,
                'durationMinutes': 0,
                'isNonRefundable': rec2['cancellationPolicySettings'] and rec2['cancellationPolicySettings']['isActive'] or True,
                'minPax': rec2['minimumPax'] or 1,
                'maxPax': rec2['maximumPax'] or 30,
                'minAdultAge': 13,
                'maxAdultAge': 65,
                'allowChildren': is_child,
                'minChildren': 0,
                'maxChildren': 10,
                'minChildAge': 4,
                'maxChildAge': 12,
                'allowSeniors': is_senior,
                'minSeniors': 0,
                'maxSeniors': 10,
                'minSeniorAge': 66,
                'maxSeniorAge': 120,
                'allowInfant': True,
                'minInfantAge': 0,
                'maxInfantAge': 3,
                'voucherUse': rec2['termsAndConditions'],
                'voucherRedemptionAddress': '',
                'voucherRequiresPrinting': False,
                'cancellationPolicies': cancel,
                'voucher_validity_type': '',
                'voucher_validity_days': '',
                'voucher_validity_date': False,
                'meetingLocation': '',
                'meetingAddress': '',
                'meetingTime': '',
                'instantConfirmation': True,
                'advanceBookingDays': rec2['visitDate']['advanceBookingDays'],
                'minimumSellingPrice': rec2['minimumSellingPrice'] or 0,
                # 'ticketTypeFormat': '',
            }
            activity_obj = self.env['tt.master.activity.lines'].sudo().create(vals)
            self.env.cr.commit()

            if is_adult:
                sku_vals = {
                    'activity_line_id': activity_obj.id,
                    'sku_id': 'Adult',
                    'title': 'Adult',
                    'minPax': 1,
                    'maxPax': 10,
                    'minAge': 13,
                    'maxAge': 65,
                }
                sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                self.env.cr.commit()

            if is_child:
                sku_vals = {
                    'activity_line_id': activity_obj.id,
                    'sku_id': 'Child',
                    'title': 'Child',
                    'minPax': 0,
                    'maxPax': 10,
                    'minAge': 4,
                    'maxAge': 12,
                }
                sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                self.env.cr.commit()

            if is_senior:
                sku_vals = {
                    'activity_line_id': activity_obj.id,
                    'sku_id': 'Senior',
                    'title': 'Senior',
                    'minPax': 0,
                    'maxPax': 10,
                    'minAge': 66,
                    'maxAge': 120,
                }
                sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
                self.env.cr.commit()

            sku_vals = {
                'activity_line_id': activity_obj.id,
                'sku_id': 'Infant',
                'title': 'Infant',
                'minPax': 0,
                'maxPax': 5,
                'minAge': 0,
                'maxAge': 3,
            }
            sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)
            self.env.cr.commit()

            option_ids = []
            for book in rec2['questions']:
                type_lib = {
                    'FREETEXT': 4,
                    'DATE': 6,
                    'OPTION': 1,
                }
                value2 = {
                    'uuid': book['id'],
                    'name': book['question'],
                    'description': book['tourInfo'],
                    'required': book['optional'] and False or True,
                    'formatRegex': '',
                    'inputType': type_lib[book['type']['name']],
                    'price': 0,
                    'type': 'perBooking',
                }
                temp2 = self.env['tt.activity.booking.option'].sudo().create(value2)
                self.env.cr.commit()
                for item in book['options']:
                    value4 = {
                        'booking_option_id': temp2.id,
                        'label': item,
                        'value': item,
                        'price': 0,
                        'currency_id': self.env['res.currency'].search([('name', '=', 'SGD')], limit=1).id,
                    }
                    self.env['tt.activity.booking.option.line'].sudo().create(value4)
                    self.env.cr.commit()
                option_ids.append(temp2.id)
            activity_obj.update({
                'option_ids': [(6, 0, option_ids)],
            })

    def sync_type_products_klook(self, result, product_id, provider):
        activity_old_obj = self.env['tt.master.activity.lines'].search([('activity_id', '=', product_id)])
        activity_old_obj.sudo().unlink()

        for rec2 in result['product_detail']:
            if rec2.get('confirmation_type'):
                confirm = rec2['confirmation_type'] in ['Instant Confirmation', 'InstantConfirmation', 'Instant'] and True or False
            elif result['product'].get('confirmation'):
                confirm = result['product']['confirmation'] in ['Instant Confirmation', 'InstantConfirmation', 'Instant'] and True or False
            else:
                confirm = False

            duration_day = 0
            duration_hour = 0
            duration_min = 0
            if result['product']['duration'] != 'N/A':
                full_dur = result['product']['duration'].split('Duration')[0]
                split_day = full_dur.split('Day(s)')
                split_hour = ''
                split_min = ''
                if len(split_day) > 1:
                    if str(split_day[0]).isdigit():
                        duration_day = split_day[0]
                    if split_day[1]:
                        split_hour = split_day[1].split('Hrs')
                    else:
                        duration_hour = 0
                        duration_min = 0
                else:
                    duration_day = 0
                    split_hour = full_dur.split('Hrs')

                if len(split_hour) > 1:
                    if str(split_hour[0]).isdigit():
                        duration_hour = split_hour[0]
                    if split_hour[1]:
                        split_min = split_hour[1].split('Min')
                    else:
                        duration_min = 0
                else:
                    duration_hour = 0
                    if len(split_day) > 1:
                        split_min = split_day[1].split('Min')
                    else:
                        split_min = full_dur.split('Min')

                if len(split_min) > 1:
                    if str(split_min[0]).isdigit():
                        duration_min = split_min[0]
                else:
                    duration_min = 0

            sku_ids = []
            if rec2.get('skus'):
                for rec3 in rec2['skus']:
                    sku_temp = rec3.get('title') and rec3['title'].split('(') or []
                    if len(sku_temp) > 1:
                        sku_temp = sku_temp[1].split(' ')[0].split(')')[0].split('-')
                        if len(sku_temp) > 1:
                            min_age = sku_temp[0].isdigit() and int(sku_temp[0]) or 0
                            max_age = sku_temp[1].isdigit() and int(sku_temp[1]) or 0
                        else:
                            min_age = sku_temp[0].split('+')[0].isdigit() and int(sku_temp[0].split('+')[0]) or 0
                            max_age = 120
                    else:
                        min_age = 0
                        max_age = 0

                    sku_min_pax = 0
                    sku_max_pax = 100
                    temp_sku_min_pax = 0
                    if rec3.get('required'):
                        temp_sku_min_pax = 1
                    if rec3.get('sku_min_pax'):
                        sku_min_pax = rec3['sku_min_pax'] >= temp_sku_min_pax and rec3['sku_min_pax'] or temp_sku_min_pax
                    if rec3.get('sku_max_pax'):
                        sku_max_pax = rec3['sku_max_pax'] <= 100 and rec3['sku_max_pax'] or 100
                    sku_create_vals = {
                        'sku_id': rec3.get('sku_id') and rec3['sku_id'] or '',
                        'title': rec3.get('title') and rec3['title'] or '',
                        'minPax': sku_min_pax,
                        'maxPax': sku_max_pax,
                        'minAge': min_age,
                        'maxAge': max_age,
                    }
                    temp_sku_id = self.env['tt.master.activity.sku'].sudo().create(sku_create_vals)
                    sku_ids.append(temp_sku_id.id)

            voucher_usage = rec2.get('voucher_usage') and rec2['voucher_usage'] or ''
            voucher_type_desc = rec2.get('voucher_type_desc') and rec2['voucher_type_desc'].replace('\n', '<br/>') or ''
            voucher_validity = rec2.get('voucher_validity') and rec2['voucher_validity'].replace('\n', '<br/>') or ''
            redemption_process = rec2.get('redemption_process') and rec2['redemption_process'].replace('\n', '<br/>') or ''
            voucher_identity = rec2.get('voucher_identity') and rec2['voucher_identity'].replace('\n', '<br/>') or ''

            desc = rec2.get('detail') and rec2['detail'].replace('\n', '<br/>') or ''
            desc2 = rec2.get('open_hours') and rec2['open_hours'].replace('\n', '<br/>') or ''
            voucher_use = voucher_usage + '<br/><br/>' + voucher_type_desc + '<br/>' + voucher_validity + '<br/>' + redemption_process + '<br/>' + voucher_identity
            cancel_type = rec2.get('cancelation_type') and rec2['cancelation_type'] or ''
            if 'No' in cancel_type.split(' '):
                refundable = True
            else:
                refundable = False
            vals = {
                'activity_id': product_id,
                'uuid': rec2.get('product_id') and rec2['product_id'] or '',
                'name': rec2.get('title') and rec2['title'] or '',
                'description': desc + '<br/>' + desc2,
                'durationDays': duration_day,
                'durationHours': duration_hour,
                'durationMinutes': duration_min,
                'isNonRefundable': refundable,
                'voucherUse': voucher_use,
                'voucherRedemptionAddress': '',
                'voucherRequiresPrinting': False,
                'cancellationPolicies': cancel_type,
                'voucher_validity_type': '',
                'voucher_validity_days': '',
                'voucher_validity_date': False,
                'meetingLocation': '',
                'meetingAddress': '',
                'meetingTime': '',
                'instantConfirmation': confirm,
                'advanceBookingDays': 0,
                'minimumSellingPrice': 0,
                'minPax': rec2.get('product_min_pax') and rec2['product_min_pax'] or 1,
                'maxPax': rec2.get('product_max_pax') and rec2['product_max_pax'] or 999,
            }
            if sku_ids:
                vals.update({
                    'sku_ids': [(6, 0, sku_ids)],
                })

            activity_obj = self.env['tt.master.activity.lines'].sudo().create(vals)
            self.env.cr.commit()

            if rec2.get('timeslots'):
                for time in rec2['timeslots']:
                    value = {
                        'product_type_id': activity_obj.id,
                        'uuid': time.get('uuid') and time['uuid'] or '',
                        'startTime': time.get('startTime') and time['startTime'] or '',
                        'endTime': time.get('endTime') and time['endTime'] or '',
                    }
                    self.env['tt.activity.master.timeslot'].sudo().create(value)
                    self.env.cr.commit()

            extra_info = rec2.get('extra_info')
            if extra_info:
                option_ids = []
                if extra_info.get('general'):
                    for book in extra_info['general']:
                        type_lib = {
                            'text': 4,
                            'date': 6,
                            'list': 1,
                            'checkBox': 5,
                        }
                        value2 = {
                            'uuid': book.get('type_id') and book['type_id'] or '',
                            'name': book.get('content') and book['content'] or '',
                            'description': book.get('hint') and book['hint'] or '',
                            'required': book.get('required') and book['required'] or False,
                            'formatRegex': '',
                            'inputType': book.get('type') and type_lib[book['type']] or 4,
                            'price': 0,
                            'type': 'perBooking',
                        }
                        temp2 = self.env['tt.activity.booking.option'].sudo().create(value2)
                        self.env.cr.commit()
                        if book.get('options'):
                            for idx, item in enumerate(book['options']):
                                value4 = {
                                    'booking_option_id': temp2.id,
                                    'label': item[str(idx + 1)],
                                    'value': str(idx + 1),
                                    'price': 0,
                                    'currency_id': self.env['res.currency'].search([('name', '=', 'SGD')], limit=1).id,
                                }
                                self.env['tt.activity.booking.option.line'].sudo().create(value4)
                                self.env.cr.commit()
                        option_ids.append(temp2.id)

                if extra_info.get('travelers'):
                    for book in extra_info['travelers']:
                        type_lib = {
                            'text': 4,
                            'date': 6,
                            'list': 1,
                            'checkBox': 5,
                        }
                        value2 = {
                            'uuid': book.get('type_id') and book['type_id'] or '',
                            'name': book.get('content') and book['content'] or '',
                            'description': book.get('hint') and book['hint'] or '',
                            'required': book.get('required') and book['required'] or False,
                            'formatRegex': '',
                            'inputType': book.get('type') and  type_lib[book['type']] or 4,
                            'price': 0,
                            'type': 'perPax',
                        }
                        temp2 = self.env['tt.activity.booking.option'].sudo().create(value2)
                        self.env.cr.commit()
                        if book.get('options'):
                            for idx, item in enumerate(book['options']):
                                value4 = {
                                    'booking_option_id': temp2.id,
                                    'label': item[str(idx + 1)],
                                    'value': str(idx + 1),
                                    'price': 0,
                                    'currency_id': self.env['res.currency'].search([('name', '=', 'SGD')], limit=1).id,
                                }
                                self.env['tt.activity.booking.option.line'].sudo().create(value4)
                                self.env.cr.commit()
                        option_ids.append(temp2.id)
                activity_obj.update({
                    'option_ids': [(6, 0, option_ids)],
                })

    def get_config_by_api(self):
        try:
            result_objs = self.env['tt.activity.category'].sudo().search([])
            categories = result_objs.filtered(lambda x: x.type == 'category' and not x.parent_id)
            sub_categories = {}
            categories_list = []
            for rec in categories:
                categories_list.append({
                    'name': rec.name,
                    'id': rec.id,
                })
                child_list = []
                for child in rec.child_ids:
                    child_list.append({
                        'name': child.name,
                        'id': child.id,
                    })
                sub_categories[rec.name] = child_list
            types = result_objs.filtered(lambda x: x.type == 'type')
            types_list = []
            for type in types:
                types_list.append({
                    'name': type.name,
                    'id': type.id,
                })

            countries_list = []
            country_objs = self.env['res.country'].sudo().search([('provider_city_ids', '!=', False)])
            for country in country_objs:
                # for rec in country.provider_city_ids:
                #     if rec.provider_id.id == vendor_id:
                city = self.get_cities_by_api(country.id)
                countries_list.append({
                    'name': country.name,
                    'id': country.id,
                    'city': city
                })

            values = {
                'categories': categories_list,
                'sub_categories': sub_categories,
                'types': types_list,
                'countries': countries_list,
            }
            return ERR.get_no_error(values)
        except Exception as e:
            _logger.info('Activity Get Config Error')
            return ERR.get_error(500)

    def get_cities_by_api(self, id):
        try:
            result_objs = self.env['res.city'].sudo().search([('country_id', '=', int(id))])
            cities = []
            for rec in result_objs:
                cities.append({
                    'name': rec.name,
                    'id': rec.id,
                })
            return ERR.get_no_error(cities)
        except Exception as e:
            _logger.info('Activity Get Cities Error')
            return ERR.get_error(500)

    def search_by_api(self, req):
        try:
            query = req.get('query') and '%' + req['query'] + '%' or ''
            country = req.get('country') and req['country'] or ''
            city = req.get('city') and req['city'] or ''

            type_id = req['type_id'] != '0' and self.env['tt.activity.category'].sudo().search([('id', '=', req['type_id']), ('type', '=', 'type')]).id or ''
            # sub_category = sub_category != '0' and sub_category or ''
            category = req['sub_category'] and (req['sub_category'] != '0' and req['sub_category'] or (req['category'] != '0' and req['category'] or '')) or ''
            provider = req.get('provider', 'all')
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            provider_id = provider_id and provider_id[0] or False
            provider_code = provider_id and provider_id[0].code or ''

            sql_query = 'select themes.* from tt_master_activity themes left join tt_activity_location_rel locrel on locrel.product_id = themes.id left join tt_activity_master_locations loc on loc.id = locrel.location_id '

            if category:
                sql_query += 'left join tt_activity_category_rel catrel on catrel.activity_id = themes.id '

            if type_id:
                sql_query += 'left join tt_activity_type_rel typerel on typerel.activity_id = themes.id '

            sql_query += "where "

            if query:
                sql_query += "themes.name ilike '" + query + "' "
            else:
                sql_query += "themes.active = True "

            if type_id:
                sql_query += 'and typerel.type_id = ' + type_id + ' '

            if category:
                sql_query += 'and catrel.category_id = "' + category + '" '

            if req.get('country') and not req.get('city'):
                sql_query += "and (loc.country_id = " + country + ") "

            if req.get('city'):
                sql_query += "and (loc.country_id = " + country + " and loc.city_id = " + city + ") "

            if provider in ['globaltix', 'bemyguest', 'klook']:
                if provider_id:
                    sql_query += "and themes.provider_id = '" + provider_id.id + "' "

            if query:
                sql_query += 'and themes.active = True '
            sql_query += 'group by themes.id '

            self.env.cr.execute(sql_query)

            result_id_list = self.env.cr.dictfetchall()
            result_list = []

            for result in result_id_list:
                res_provider = result.get('provider_id') and self.env['tt.provider'].browse(result['provider_id']) or None
                result = {
                    'additionalInfo': result.get('additionalInfo') and result['additionalInfo'] or '',
                    'airportPickup': result.get('airportPickup') and result['airportPickup'] or False,
                    'basePrice': result['basePrice'],
                    'businessHoursFrom': result.get('businessHoursFrom') and result['businessHoursFrom'] or '',
                    'businessHoursTo': result.get('businessHoursTo') and result['businessHoursTo'] or '',
                    'currency_id': result['currency_id'],
                    'description': result.get('description') and result['description'] or '',
                    'highlights': result.get('highlights') and result['highlights'] or '',
                    'hotelPickup': result.get('hotelPickup') and result['hotelPickup'] or False,
                    'id': result['id'],
                    'itinerary': result.get('itinerary') and result['itinerary'] or '',
                    'latitude': result.get('latitude') and result['latitude'] or 0.0,
                    'longitude': result.get('longitude') and result['longitude'] or 0.0,
                    'maxPax': result['maxPax'] or 0,
                    'minPax': result['minPax'] or 0,
                    'name': result['name'],
                    'priceExcludes': result.get('priceExcludes') and result['priceExcludes'] or '',
                    'priceIncludes': result.get('priceIncludes') and result['priceIncludes'] or '',
                    'provider_id': result.get('provider_id') and result['provider_id'] or '',
                    'provider': res_provider and res_provider.code or '',
                    'reviewAverageScore': result.get('reviewAverageScore') and result['reviewAverageScore'] or 0.0,
                    'reviewCount': result.get('reviewCount') and result['reviewCount'] or 0,
                    'safety': result.get('safety') and result['safety'] or '',
                    'type_id': result.get('type_id') and result['type_id'] or 0,
                    'uuid': result['uuid'],
                    'warnings': result.get('warnings') and result['warnings'] or '',
                }

                additionalInfo = (result['additionalInfo'].replace('<p>', '\n').replace('</p>', ''))[1:]
                description = (result['description'].replace('<p>', '\n').replace('</p>', ''))[1:]
                highlights = (result['highlights'].replace('<p>', '\n').replace('</p>', ''))[1:]
                itinerary = (result['itinerary'].replace('<p>', '\n').replace('</p>', ''))[1:]
                safety = (result['safety'].replace('<p>', '\n').replace('</p>', ''))[1:]
                warnings = (result['warnings'].replace('<p>', '\n').replace('</p>', ''))[1:]
                priceExcludes = (result['priceExcludes'].replace('<p>', '\n').replace('</p>', ''))[1:]
                priceIncludes = (result['priceIncludes'].replace('<p>', '\n').replace('</p>', ''))[1:]

                result.update({
                    'additionalInfo': additionalInfo,
                    'description': description,
                    'highlights': highlights,
                    'itinerary': itinerary,
                    'safety': safety,
                    'warnings': warnings,
                    'priceExcludes': priceExcludes,
                    'priceIncludes': priceIncludes,
                })

                result_obj = self.env['tt.master.activity'].browse(result['id'])
                image_temp = []
                if result_obj.image_ids:
                    image_objs = result_obj.image_ids
                    for image_obj in image_objs:
                        if image_obj.photos_path and image_obj.photos_url:
                            img_temp = {
                                'path': image_obj.photos_path,
                                'url': image_obj.photos_url,
                            }
                            image_temp.append(img_temp)
                        else:
                            img_temp = {
                                'path': 'http://static.skytors.id/tour_packages/not_found.png',
                                'url': '',
                            }
                            image_temp.append(img_temp)
                else:
                    img_temp = {
                        'path': 'http://static.skytors.id/tour_packages/not_found.png',
                        'url': '',
                    }
                    image_temp.append(img_temp)
                result.update({
                    'images': image_temp,
                })

                video_temp = []
                if result_obj.video_ids:
                    video_objs = result_obj.video_ids
                    for video_obj in video_objs:
                        if video_obj.video_url:
                            vid_temp = {
                                'url': video_obj.video_url,
                            }
                            video_temp.append(vid_temp)
                        else:
                            vid_temp = {
                                'url': '',
                            }
                            video_temp.append(vid_temp)
                else:
                    vid_temp = {
                        'url': '',
                    }
                    video_temp.append(vid_temp)
                result.update({
                    'videos': video_temp,
                })

                category_objs = result_obj.category_ids
                category_temp = []
                for category_obj in category_objs:
                    cat_temp = {
                        'category_name': category_obj.name,
                        'category_uuid': category_obj.line_ids.uuid,
                        'category_id': category_obj.id,
                    }
                    category_temp.append(cat_temp)
                result.update({
                    'categories': category_temp,
                })

                location_objs = result_obj.location_ids
                location_temp = []
                for location_obj in location_objs:
                    loc_temp = {
                        'country_name': location_obj.country_id.name,
                        'state_name': location_obj.state_id.name,
                        'city_name': location_obj.city_id.name,
                    }
                    location_temp.append(loc_temp)
                result.update({
                    'locations': location_temp,
                })

                from_currency = self.env['res.currency'].browse(result['currency_id'])

                try:
                    if result.get('provider'):
                        temp = self.reprice_currency(result['provider'], from_currency.name, result['basePrice'])
                    else:
                        temp = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id,
                                                                 result['basePrice'])
                except Exception as e:
                    temp = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id,
                                                             result['basePrice'])
                    _logger.info('Cannot convert to vendor price: ' + str(e))

                converted_price = temp + 10000

                sale_price = 0
                # pembulatan sale price keatas
                for idx in range(10):
                    if (converted_price % 100) == 0:
                        sale_price = converted_price
                        break
                    if idx == 9 and ((converted_price % 1000) < int(str(idx + 1) + '00')) and converted_price > 0:
                        sale_price = str(int(converted_price / 1000) + 1) + '000'
                        break
                    elif (converted_price % 1000) < int(str(idx + 1) + '00') and converted_price > 0:
                        if int(converted_price / 1000) == 0:
                            sale_price = str(idx + 1) + '00'
                        else:
                            sale_price = str(int(converted_price / 1000)) + str(idx + 1) + '00'
                        break

                result.update({
                    'converted_price': int(sale_price),
                    'currency_code': from_currency.name,
                    'provider_id': result['provider_id'],
                    'provider': res_provider.code,
                })
                result_list.append(result)

            return ERR.get_no_error(result_list)
        except Exception as e:
            _logger.info('Activity Search Error')
            return ERR.get_error(500)

    def get_details_by_api(self, req):
        try:
            activity_id = self.search([('uuid', '=', req['uuid']), ('provider_id', '=', int(req['provider_id']))], limit=1)
            activity_id = activity_id and activity_id[0] or None
            provider = activity_id.provider_id.code
            result_id_list = self.env['tt.master.activity.lines'].search([('activity_id', '=', activity_id.id)])
            temp = []
            for result_id in result_id_list:
                result = {
                    'activity_id': result_id.activity_id.id,
                    'uuid': result_id.uuid,
                    'name': result_id.name,
                    'provider_code': provider,
                    'description': result_id.description and result_id.description or '',
                    'durationDays': result_id.durationDays and result_id.durationDays or 0,
                    'durationHours': result_id.durationHours and result_id.durationHours or 0,
                    'durationMinutes': result_id.durationMinutes and result_id.durationMinutes or 0,
                    'isNonRefundable': result_id.isNonRefundable and result_id.isNonRefundable or True,
                    'minPax': result_id.minPax and result_id.minPax or 1,
                    'maxPax': result_id.maxPax and result_id.maxPax or 100,
                    'voucherUse': result_id.voucherUse and result_id.voucherUse or '',
                    'voucherRedemptionAddress': result_id.voucherRedemptionAddress and result_id.voucherRedemptionAddress or '',
                    'voucherRequiresPrinting': result_id.voucherRequiresPrinting and result_id.voucherRequiresPrinting or '',
                    'cancellationPolicies': result_id.cancellationPolicies and result_id.cancellationPolicies or '',
                    'meetingLocation': result_id.meetingLocation and result_id.meetingLocation or '',
                    'meetingAddress': result_id.meetingAddress and result_id.meetingAddress or '',
                    'meetingTime': result_id.meetingTime and result_id.meetingTime or '',
                    'instantConfirmation': result_id.instantConfirmation and result_id.instantConfirmation or False,
                }
                description = (result['description'].replace('<p>', '\n').replace('</p>', ''))[1:]
                voucherUse = (result['voucherUse'].replace('<p>', '\n').replace('</p>', ''))[1:]
                voucherRedemptionAddress = (result['voucherRedemptionAddress'].replace('<p>', '\n').replace('</p>', ''))[1:]

                if result_id.voucher_validity_type == 'only_visit_date':
                    voucher_validity = 'Valid only on the stated visit date'
                elif result_id.voucher_validity_type == 'from_travel_date':
                    voucher_validity = 'Valid until ' + str(
                        result_id.voucher_validity_days) + ' days after from the stated visit date'
                elif result_id.voucher_validity_type == 'after_issue_date':
                    voucher_validity = 'Valid until ' + str(result_id.voucher_validity_days) + ' days after issued date'
                elif result_id.voucher_validity_type == 'until_date':
                    voucher_validity = 'Valid until ' + result_id.voucher_validity_date
                else:
                    voucher_validity = '-'

                result.update({
                    'description': description,
                    'voucherUse': voucherUse,
                    'voucherRedemptionAddress': voucherRedemptionAddress,
                    'voucher_validity': voucher_validity,
                })
                skus = []
                if result_id.sku_ids:
                    for sku in result_id.sku_ids.ids:
                        sku_obj = self.env['tt.master.activity.sku'].browse(int(sku))
                        sku_temp = {
                            'sku_id': sku_obj.sku_id,
                            'title': sku_obj.title,
                            'minPax': sku_obj.minPax,
                            'maxPax': sku_obj.maxPax,
                            'minAge': sku_obj.minAge,
                            'maxAge': sku_obj.maxAge,
                            'add_information': sku_obj.add_information,
                        }
                        skus.append(sku_temp)
                    result.update({
                        'skus': skus
                    })

                per_book = []
                per_pax = []
                from_currency = self.env['res.currency'].search([('name', '=', 'SGD')], limit=1)
                if result_id.option_ids:
                    for opt in result_id.option_ids.ids:
                        activity_opt_obj = self.env['tt.activity.booking.option'].browse(opt)
                        temp_opt = {
                            'uuid': activity_opt_obj.uuid,
                            'name': activity_opt_obj.name,
                            'description': activity_opt_obj.description and activity_opt_obj.description or '',
                            'required': activity_opt_obj.required,
                            'formatRegex': activity_opt_obj.formatRegex,
                            'inputType': activity_opt_obj.inputType,
                            'type': activity_opt_obj.type,
                            'price': activity_opt_obj.price,
                            'currency_id': activity_opt_obj.currency_id.id,
                        }
                        description = (temp_opt['description'].replace('<p>', '\n').replace('</p>',''))[1:]
                        temp_opt.update({
                            'description': description,
                        })
                        if activity_opt_obj.price:
                            try:
                                price = self.reprice_currency(provider, from_currency.name, activity_opt_obj.price)
                            except Exception as e:
                                price = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, activity_opt_obj.price)
                            temp_opt.update({
                                'price': price,
                            })
                        opt_item = []
                        if activity_opt_obj.items:
                            for item in activity_opt_obj.items:
                                temp_item = {
                                    'label': item.label,
                                    'value': item.value,
                                    'price': item.price,
                                    'currency_id': item.currency_id.id,
                                }
                                if item.price:
                                    try:
                                        price2 = self.reprice_currency(provider, from_currency.name, item.price)
                                    except Exception as e:
                                        price2 = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, item.price)
                                    temp_item.update({
                                        'price': price2,
                                    })
                                opt_item.append(temp_item)
                            temp_opt.update({
                                'items': opt_item,
                            })

                        if activity_opt_obj.type == 'perPax':
                            per_pax.append(temp_opt)
                        elif activity_opt_obj.type == 'perBooking':
                            per_book.append(temp_opt)
                result.update({
                    'options': {
                        'perPax': per_pax,
                        'perBooking': per_book,
                    }
                })

                timeslot = []
                if result_id.timeslot_ids:
                    for time in result_id.timeslot_ids.ids:
                        timeslot_obj = self.env['tt.activity.master.timeslot'].browse(time)
                        time_temp = {
                            'uuid': timeslot_obj.uuid,
                            'startTime': timeslot_obj.startTime,
                            'endTime': timeslot_obj.endTime,
                        }
                        timeslot.append(time_temp)
                result.update({
                    'timeslots': timeslot
                })
                temp.append(result)
            return ERR.get_no_error(temp)
        except Exception as e:
            _logger.info('Activity Search Detail Error')
            return ERR.get_error(500)

    def get_pricing_by_api(self, result, context):
        try:
            agent_type = self.env['res.users'].browse(context['co_uid']).agent_id.agent_type_id.id
            if agent_type in [self.env.ref('tt_base.agent_type_citra').id, self.env.ref('tt_base.agent_type_btbo').id]:
                multiplier = 1
            elif agent_type in [self.env.ref('tt_base.agent_type_japro').id, self.env.ref('tt_base.agent_type_btbr').id]:
                multiplier = 0.8
            elif agent_type in [self.env.ref('tt_base.agent_type_fipro').id]:
                multiplier = 0.6
            else:
                multiplier = 0

            list = ['adults', 'children', 'seniors']
            for res in list:
                if result['type_pricing'].get('data'):
                    for results in result['type_pricing']['data']:
                        for rec in results:
                            if rec['prices'][res]:
                                from_currency = self.env['res.currency'].search([('name', '=', rec['currency'])])
                                for key, value in rec['prices'][res].iteritems():
                                    try:
                                        to_currency = self.reprice_currency(result['provider'], from_currency.name, value)
                                    except Exception as e:
                                        to_currency = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id, value)
                                    if to_currency:
                                        final_price = to_currency + 10000
                                    else:
                                        final_price = 0

                                    price_temp = int(final_price * 1.03)

                                    sale_price = 0
                                    # pembulatan sale price keatas
                                    for idx in range(10):
                                        if (price_temp % 100) == 0:
                                            sale_price = price_temp
                                            break
                                        if idx == 9 and ((price_temp % 1000) < int(str(idx + 1) + '00')) and price_temp > 0:
                                            sale_price = str(int(price_temp / 1000) + 1) + '000'
                                            break
                                        elif (price_temp % 1000) < int(str(idx + 1) + '00') and price_temp > 0:
                                            if int(price_temp / 1000) == 0:
                                                sale_price = str(idx + 1) + '00'
                                            else:
                                                sale_price = str(int(price_temp / 1000)) + str(idx + 1) + '00'
                                            break

                                    temp = int((int(sale_price) - final_price) * multiplier)
                                    commission_price = 0
                                    # pembulatan commission price kebawah
                                    for idx in range(10):
                                        if (temp % 1000) < int(str(idx + 1) + '00') and temp > 0:
                                            if int(temp / 1000) == 0:
                                                commission_price = (str(idx) + '00')
                                            else:
                                                commission_price = str(int(temp / 1000)) + (str(idx) + '00')
                                            break

                                    rec['prices'][res].update({
                                        key: {
                                            'sale_price': int(sale_price),
                                            'commission_price': int(commission_price),
                                        },
                                    })

                                    rec.update({
                                        'currency_code': self.env.user.company_id.currency_id.name
                                    })

            response = []
            if result['type_pricing'].get('data'):
                for results in result['type_pricing']['data']:
                    for rec in results:
                        rec.get('links') and rec.pop('links')
                        rec.get('currency') and rec.pop('currency')
                        rec.get('options') and rec.pop('options')
                        rec.get('timeslots') and rec.pop('timeslots')
                        rec.get('weekday') and rec.pop('weekday')
                        rec['prices'].get('cancellationPolicy') and rec['prices'].pop('cancellationPolicy')
                    response.append(results)

            return ERR.get_no_error(response)
        except Exception as e:
            _logger.info('Activity Get Pricing Error')
            return ERR.get_error(500)



