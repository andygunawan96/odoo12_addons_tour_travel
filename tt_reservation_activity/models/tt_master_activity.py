from odoo import api, fields, models, _
from odoo.http import request
from ...tools import util,variables,ERR
from ...tools.ERR import RequestException
from ...tools.db_connector import GatewayConnector
import logging, traceback
import json
import base64
import pickle
from datetime import datetime
import csv
import os, shutil
import re
import copy
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from ...tools import session
SESSION_NT = session.Session()


class ActivitySyncProducts(models.TransientModel):
    _name = "activity.sync.product.wizard"
    _description = 'Activity Sync Products Wizard'

    action_type = fields.Selection([('configure_product', 'Configure Product'), ('generate_json', 'Generate Json'), ('sync_products', 'Sync Products')], 'Action', required=True)

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_activity.tt_provider_type_activity').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)

    # generate json
    query = fields.Char('Search Query')
    country_id = fields.Many2one('res.country', 'Country (leave empty to search all countries)')
    per_page_amt = fields.Integer('Amount of Data Per Page (only used for certain providers)', default=100)
    is_create_progress_tracking = fields.Boolean('Create and Use Progress Tracking', default=False)

    # sync products
    start_num = fields.Char('Start Number', default='1')
    end_num = fields.Char('End Number', default='1')

    def check_json_length(self):
        file_ext = 'json'
        self.env['tt.master.activity'].action_check_json_length(self.provider_id.code, file_ext, True)

    def execute_wizard(self):
        if self.action_type == 'configure_product':
            self.env['tt.master.activity'].action_sync_config(self.provider_id.code)
        elif self.action_type == 'generate_json':
            filter_data = {
                'query': self.query and self.query or '',
                'country_id': self.country_id and self.country_id.id or 0,
                'per_page_amt': self.per_page_amt,
                'is_empty_json_directory': True,
                'is_create_progress_tracking': self.is_create_progress_tracking
            }
            self.env['tt.master.activity'].action_generate_json(self.provider_id.code, filter_data)
        else:
            self.env['tt.master.activity'].action_sync_products(self.provider_id.code, self.start_num, self.end_num)

    def deactivate_product(self):
        products = self.env['tt.master.activity'].sudo().search([('provider_id', '=', self.provider_id.id)])
        prod_count = 0
        for rec in products:
            if rec.active:
                rec.sudo().write({
                    'active': False
                })
                prod_count += 1
                if prod_count >= 80:
                    self.env.cr.commit()
                    prod_count = 0


class ActivitySyncProgressTracking(models.Model):
    _name = 'tt.activity.sync.progress.tracking'
    _description = 'Activity Sync Generate Products JSON Progress Tracking'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_activity.tt_provider_type_activity').id
        return [('provider_type_id.id', '=', int(domain_id))]

    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain, required=True)
    query = fields.Char('Search Query')
    per_page_amt = fields.Integer('Amount of Data Per Page (only used for certain providers)', default=100, required=True)
    country_id = fields.Many2one('res.country', 'Country')
    country_provider_codes_str = fields.Char('Country Provider Codes')
    vendor_last_page = fields.Integer('Vendor Last Page', default=0)
    last_json_number = fields.Integer('Last JSON Number', default=0)
    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    active = fields.Boolean('Active', default=True)

    def continue_generate_json(self):
        filter_data = {
            'query': self.query and self.query or '',
            'country_id': self.country_id and self.country_id.id or 0,
            'per_page_amt': self.per_page_amt,
            'is_empty_json_directory': False,
            'country_provider_codes': self.country_provider_codes_str,
            'vendor_last_page': self.vendor_last_page,
            'last_json_number': self.last_json_number,
            'progress_tracking_id': self.id
        }
        self.env['tt.master.activity'].action_generate_json(self.provider_id.code, filter_data)

class MasterActivity(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.master.activity'
    _description = 'Master Activity'

    uuid = fields.Char('Uuid', readonly=True)
    name = fields.Char('Activity Name', readonly=True)
    type_ids = fields.Many2many('tt.activity.category', 'tt_activity_type_rel', 'activity_id', 'type_id', string='Types', readonly=True)
    category_ids = fields.Many2many('tt.activity.category', 'tt_activity_category_rel', 'activity_id', 'category_id', string='Categories', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    basePrice = fields.Float('Base Price', digits=(16, 2), readonly=True)
    priceIncludes = fields.Html('Price Includes', readonly=True)
    priceExcludes = fields.Html('Price Excludes', readonly=True)

    description = fields.Html('Description', readonly=True)
    highlights = fields.Html('Highlights', readonly=True)
    additionalInfo = fields.Html('Additional Info', readonly=True)
    itinerary = fields.Html('Itinerary', readonly=True)
    warnings = fields.Html('Warnings', readonly=True)
    safety = fields.Html('Safety', readonly=True)

    latitude = fields.Float('Latitude', digits=(11, 7), readonly=True)
    longitude = fields.Float('Longitude', digits=(11, 7), readonly=True)
    location_ids = fields.Many2many('tt.activity.master.locations', 'tt_activity_location_rel', 'product_id', 'location_id', string='Location', readonly=True)

    minPax = fields.Integer('Adult Min', readonly=True)
    maxPax = fields.Integer('Adult Max', readonly=True)
    reviewCount = fields.Integer('Review Count', readonly=True)
    reviewAverageScore = fields.Float('Review Average Score', digits=(10, 2), readonly=True)
    businessHoursFrom = fields.Char(string='Business Hours From', readonly=True)
    businessHoursTo = fields.Char(string='Business Hours To', readonly=True)
    hotelPickup = fields.Boolean('Hotel Pickup', readonly=True)
    airportPickup = fields.Boolean('Airport Pickup', readonly=True)

    line_ids = fields.One2many('tt.master.activity.lines', 'activity_id', 'Product Types', readonly=True)
    image_ids = fields.One2many('tt.activity.master.images', 'activity_id', 'Images Path', readonly=True)
    video_ids = fields.One2many('tt.activity.master.videos', 'activity_id', 'Video Path', readonly=True)
    provider_id = fields.Many2one('tt.provider', 'Provider', readonly=True)
    provider_code = fields.Char('Provider Code', readonly=True)
    can_hold_booking = fields.Boolean('Can Hold Booking', default=False, readonly=True)
    active = fields.Boolean('Active', default=True)
    owner_ho_id = fields.Many2one('tt.agent', 'Owner Head Office', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    ho_ids = fields.Many2many('tt.agent', 'tt_master_activity_ho_agent_rel', 'activity_id', 'ho_id', string='Allowed Head Office(s)', domain=[('is_ho_agent', '=', True)])

    @api.depends('provider_id')
    @api.onchange('provider_id')
    def _compute_provider_code(self):
        self.provider_code = self.provider_id.code

    def reprice_currency(self, req, context={}):
        _logger.info('REPRICE CURRENCY ACTIVITY')
        _logger.info(json.dumps(req))
        provider = req['provider']
        from_currency = req['from_currency']
        base_amount = req['base_amount']
        to_currency = req.get('to_currency') and req['to_currency'] or 'IDR'
        from_currency_id = self.env['res.currency'].sudo().search([('name', '=', from_currency)], limit=1)
        from_currency_id = from_currency_id and from_currency_id[0] or False
        try:
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            provider_id = provider_id[0]
            multiplier = self.env['tt.provider.rate'].sudo().search([('provider_ho_data_id.provider_id', '=', provider_id.id), ('date', '<=', datetime.now()), ('currency_id', '=', from_currency_id.id)], limit=1)
            computed_amount = base_amount * multiplier[0].sell_rate
        except Exception as e:
            computed_amount = self.env['res.currency']._compute(from_currency_id, self.env.user.company_id.currency_id, base_amount)
            _logger.info('Cannot convert to vendor price: ' + str(e))
        return computed_amount

    @api.model
    def create(self, vals):
        if not vals.get('owner_ho_id'):
            vals.update({
                'owner_ho_id': self.env.user.ho_id.id
            })
        if not vals.get('ho_ids'):
            vals.update({
                'ho_ids': [(4, self.env.user.ho_id.id)]
            })
        res = super(MasterActivity, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if not self.env.user.has_group('base.group_erp_manager') and not self.env.user.id in [admin_obj_id, root_obj_id] and self.env.user.ho_id.id != self.owner_ho_id.id:
            raise UserError('You do not have permission to edit this record.')
        return super(MasterActivity, self).write(vals)

    def action_sync_config(self, provider_code):
        self.sync_config(provider_code)

    def action_check_json_length(self, provider_code, file_ext='json', is_human=False):
        search_dir = "/var/log/tour_travel/%s_master_data/" % provider_code
        file_prefix = "%s_master_data" % provider_code
        try:
            list_of_files = [filename for filename in os.listdir(search_dir) if os.path.isfile(os.path.join(search_dir, filename)) and file_prefix in filename]
        except:
            raise UserError('Files are not generated yet.')

        if not list_of_files:
            raise UserError('Files are not generated yet.')

        def extract_number(f):
            s = re.findall("(\d+).%s" % file_ext, f)
            return int(s[0]) if s else -1, f

        max_file = max(list_of_files, key=extract_number)
        if is_human:
            raise UserError('Latest file is: %s' % max_file)
        else:
            num_str = ''
            for m in max_file:
                if m.isdigit():
                    num_str += str(m)
            return int(num_str)

    def empty_json_directory(self, directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    def action_generate_json(self, provider_code, filter_data):
        per_page_amt = filter_data.get('per_page_amt') and int(filter_data['per_page_amt']) or 100
        folder_path = '/var/log/tour_travel/%s_master_data' % provider_code
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        elif filter_data.get('is_empty_json_directory'):
            self.empty_json_directory(folder_path)
        start_page = filter_data.get('vendor_last_page') and int(filter_data['vendor_last_page']) + 1 or 1
        starting_json_number = filter_data.get('last_json_number') and int(filter_data['last_json_number']) + 1 or 1
        provider_obj = self.env['tt.provider'].search([('code', '=', provider_code), ('provider_type_id.code', '=', 'activity')], limit=1)
        provider_id = provider_obj and provider_obj[0].id or False
        if filter_data.get('progress_tracking_id'):
            progress_tracking_obj = self.env['tt.activity.sync.progress.tracking'].browse(int(filter_data['progress_tracking_id']))
        elif filter_data.get('is_create_progress_tracking'):
            progress_tracking_obj = self.env['tt.activity.sync.progress.tracking'].create({
                'provider_id': provider_id,
                'query': filter_data.get('query') and filter_data['query'] or '',
                'country_id': filter_data.get('country_id') and int(filter_data['country_id']) or False,
                'per_page_amt': per_page_amt,
                'ho_id': self.env.user.ho_id.id
            })
        else:
            progress_tracking_obj = False

        if provider_code == 'bemyguest':
            provider_code_objs = []
            if filter_data.get('country_id'):
                if provider_id:
                    provider_code_objs = self.env['tt.provider.code'].search([('provider_id', '=', provider_id), ('country_id', '=', int(filter_data['country_id']))], limit=1)
            req_post = {
                'query': filter_data.get('query') and filter_data['query'] or '',
                'country': provider_code_objs and provider_code_objs[0] or '',
                'sort': 'price',
                'page': start_page,
                'per_page': per_page_amt,
                'provider': provider_code
            }

            temp = {}
            res = self.env['tt.master.activity.api.con'].search_provider(req_post)
            if res['error_code'] == 0:
                temp = res['response']
            if temp:
                total_pages = temp['total_pages']
                if temp.get('product_detail'):
                    file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(start_page)), 'w')
                    file.write(json.dumps(temp))
                    file.close()

                if progress_tracking_obj:
                    progress_tracking_obj.write({
                        'vendor_last_page': start_page,
                        'last_json_number': start_page
                    })
                    self.env.cr.commit()
                for page in range(start_page, total_pages):
                    req_post = {
                        'query': filter_data.get('query') and filter_data['query'] or '',
                        'country': provider_code_objs and provider_code_objs[0] or '',
                        'sort': 'price',
                        'page': page + 1,
                        'per_page': per_page_amt,
                        'provider': provider_code
                    }
                    temp = {}
                    res = self.env['tt.master.activity.api.con'].search_provider(req_post)
                    if res['error_code'] == 0:
                        temp = res['response']
                    if temp.get('product_detail'):
                        file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(page + 1)), 'w')
                        file.write(json.dumps(temp))
                        file.close()
                    if progress_tracking_obj:
                        progress_tracking_obj.write({
                            'vendor_last_page': page + 1,
                            'last_json_number': page + 1
                        })
                        self.env.cr.commit()
        elif provider_code == 'globaltix':
            if filter_data.get('country_provider_codes'):
                gt_country_codes = json.loads(filter_data['country_provider_codes'])
            else:
                if provider_id:
                    if filter_data.get('country_id'):
                        second_search_param = ('country_id', '=', int(filter_data['country_id']))
                    else:
                        second_search_param = ('country_id', '!=', False)
                    provider_code_objs = self.env['tt.provider.code'].search([('provider_id', '=', provider_id), second_search_param])
                else:
                    provider_code_objs = []
                gt_country_codes = []
                for rec in provider_code_objs:
                    if str(rec.code) not in gt_country_codes:
                        gt_country_codes.append(str(rec.code))

            country_codes_progress = gt_country_codes
            storage_page = starting_json_number
            item_count = 0
            batch_data = {
                'product_detail': []
            }
            for rec in gt_country_codes:
                req_post = {
                    'query': filter_data.get('query') and filter_data['query'] or '',
                    'country': rec,
                    'provider': provider_code
                }
                if start_page > 1:
                    req_post.update({
                        'page': start_page
                    })
                res = self.env['tt.master.activity.api.con'].search_provider(req_post)
                if res['error_code'] == 0:
                    for temp in res['response']:
                        if temp.get('product_detail'):
                            batch_data['product_detail'] += temp['product_detail']
                            item_count += len(temp['product_detail'])
                            if item_count >= per_page_amt:
                                file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(storage_page)), 'w')
                                file.write(json.dumps(batch_data))
                                file.close()
                                if progress_tracking_obj:
                                    progress_tracking_obj.write({
                                        'vendor_last_page': 1,
                                        'last_json_number': storage_page
                                    })
                                    self.env.cr.commit()
                                batch_data = {
                                    'product_detail': []
                                }
                                item_count = 0
                                storage_page += 1
                country_codes_progress.remove(rec)
                if progress_tracking_obj:
                    progress_tracking_obj.write({
                        'country_provider_codes_str': json.dumps(country_codes_progress),
                    })
                    self.env.cr.commit()

            if item_count > 0:
                file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(storage_page)), 'w')
                file.write(json.dumps(batch_data))
                file.close()
        elif provider_code == 'rodextrip_activity':
            provider_code_objs = []
            if filter_data.get('country_id'):
                if provider_id:
                    provider_code_objs = self.env['tt.provider.code'].search([('provider_id', '=', provider_id), ('country_id', '=', int(filter_data['country_id']))], limit=1)
            req_post = {
                'query': filter_data.get('query') and filter_data['query'] or '',
                'country': provider_code_objs and provider_code_objs[0] or '',
                'provider': provider_code
            }
            res = self.env['tt.master.activity.api.con'].search_provider(req_post)
            if res['error_code'] == 0:
                temp = res['response']
                if temp.get('product_detail'):
                    batch_data = {
                        'product_detail': []
                    }
                    page = starting_json_number
                    for temp2 in temp['product_detail']:
                        batch_data['product_detail'].append(temp2)
                        if len(batch_data['product_detail']) >= per_page_amt:
                            file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(page)), 'w')
                            file.write(json.dumps(batch_data))
                            file.close()
                            if progress_tracking_obj:
                                progress_tracking_obj.write({
                                    'vendor_last_page': 1,
                                    'last_json_number': page
                                })
                                self.env.cr.commit()
                            batch_data = {
                                'product_detail': []
                            }
                            page += 1
                    if len(batch_data['product_detail']) > 0:
                        file = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(page)), 'w')
                        file.write(json.dumps(batch_data))
                        file.close()
            else:
                _logger.error('ACTIVITY ERROR, Generate rodextrip_activity JSON: %s, %s' % (res['error_code'], res['error_msg']))
        else:
            pass
        if progress_tracking_obj:
            progress_tracking_obj.write({
                'active': False,
                'country_provider_codes_str': '',
                'vendor_last_page': 0,
                'last_json_number': 0
            })
            self.env.cr.commit()

    def action_sync_products(self, provider_code, start, end):
        for i in range(int(start), int(end) + 1):
            try:
                file_dat = open('/var/log/tour_travel/%s_master_data/%s_master_data%s.json' % (provider_code, provider_code, str(i)), 'r')
                file = json.loads(file_dat.read())
                file_dat.close()
                if file:
                    self.sync_products(provider_code, file)
            except Exception as e:
                _logger.error('Error: Failed to sync products activity (File Number: %s). \n %s : %s' % (str(i), traceback.format_exc(), str(e)))
                provider_obj = self.env['tt.provider'].search([('code', '=', provider_code)], limit=1)
                data = {
                    'code': 9902,
                    'message': 'Activity Sync Products Failed (File Number: %s). %s : %s' % (str(i), traceback.format_exc(), str(e)),
                    'provider': provider_obj and provider_obj[0] or '',
                }
                ## tambah context
                GatewayConnector().telegram_notif_api(data, {})

    # temporary function
    def update_activity_uuid_temp(self):
        all_activity = self.env['tt.master.activity'].search([])
        for rec in all_activity:
            if rec.provider_id and rec.uuid:
                prefix = rec.provider_id.alias and rec.provider_id.alias + '~' or ''
                rec.write({
                    'uuid': prefix + rec.uuid
                })

    # temporary function
    def update_activity_lines_uuid_temp(self):
        all_activity_lines = self.env['tt.master.activity.lines'].search([])
        for rec in all_activity_lines:
            if rec.activity_id:
                if rec.activity_id.provider_id and rec.uuid:
                    prefix = rec.activity_id.provider_id.alias and rec.activity_id.provider_id.alias + '~' or ''
                    rec.write({
                        'uuid': prefix + rec.uuid
                    })

    def sync_config(self, provider):
        req_post = {
            'provider': provider
        }

        file = {}
        res = self.env['tt.master.activity.api.con'].get_config(req_post)
        if res['error_code'] == 0:
            file = json.loads(res['response'])

        if file:
            try:
                vendor_id = self.env['tt.provider'].search([('code', '=', provider)], limit=1)
                vendor_id = vendor_id[0].id
                continent_id = False
                if file.get('countries'):
                    for key, country in file['countries'].items():
                        country_id = self.env['res.country'].update_provider_data(country['name'], country['uuid'], vendor_id, continent_id)
                        if country.get('states'):
                            for key2, state in country['states'].items():
                                state_id = False
                                if state.get('name'):
                                    state_id = self.env['res.country.state'].update_provider_data(state['name'], state['uuid'], vendor_id, country_id)
                                if state.get('cities'):
                                    for key3, city in state['cities'].items():
                                        self.env['res.city'].update_provider_data(city['name'], city['uuid'], vendor_id, state_id, country_id)

                type_lib = {
                    'categories': 'category',
                    'types': 'type',
                }
                for index in ['categories', 'types']:
                    if file.get(index):
                        for rec in file[index]:
                            obj_id = self.env['tt.activity.category'].search([('name', '=', rec['name'])], limit=1)
                            if obj_id:
                                obj_id = obj_id[0]
                                line_obj = self.env['tt.activity.category.lines'].search([('category_id', '=', obj_id.id), ('provider_id', '=', vendor_id)], limit=1)
                                if not line_obj:
                                    self.env['tt.activity.category.lines'].sudo().create({
                                        'uuid': rec['uuid'],
                                        'provider_id': vendor_id,
                                        'category_id': obj_id.id,
                                    })
                                else:
                                    line_obj[0].sudo().write({
                                        'uuid': rec['uuid']
                                    })
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
                                    child_id = self.env['tt.activity.category'].search([('name', '=', child['name'])], limit=1)
                                    if child_id:
                                        child_id = child_id[0]
                                        child_lines = self.env['tt.activity.category.lines'].search([('category_id', '=', child_id.id), ('provider_id', '=', vendor_id)], limit=1)
                                        if not child_lines:
                                            self.env['tt.activity.category.lines'].sudo().create({
                                                'uuid': child['uuid'],
                                                'provider_id': vendor_id,
                                                'category_id': child_id.id,
                                            })
                                        else:
                                            child_lines[0].sudo().write({
                                                'uuid': child['uuid']
                                            })
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
                _logger.error('Error: Failed to sync config activity. \n %s : %s' % (traceback.format_exc(), str(e)))
                return False
        else:
            _logger.info('Error: Failed to sync config activity. No response from gateway.')
            return False

    def sync_products(self, provider=None, data=None, page=None):
        file = data
        if file:
            product_data_list = []
            for rec in file['product_detail']:
                provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
                provider_id = provider_id and provider_id[0] or False
                product_obj = self.env['tt.master.activity'].search([('uuid', '=', rec['product']['uuid']), ('provider_id', '=', provider_id.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                product_obj = product_obj and product_obj[0] or False
                temp = []
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
                            'provider_id': provider_id.id,
                            'category_id': category_obj.id,
                        })
                        self.env.cr.commit()
                    temp.append(category_obj.id)

                temp2 = []
                if rec['product'].get('country_id'):
                    rec_provider_codes = self.env['tt.provider.code'].sudo().search([('code', '=', rec['product']['country_id']), ('provider_id', '=', int(provider_id.id))])
                    for prov_data in rec_provider_codes:
                        city_id = self.env['res.city'].sudo().search([('name', '=', rec['product']['cities'][0])], limit=1)
                        search_params = []
                        if prov_data.country_id:
                            search_params.append(('country_id', '=', prov_data.country_id.id))
                        if city_id:
                            search_params.append(('city_id', '=', city_id[0].id))
                        if search_params:
                            temp_loc = self.env['tt.activity.master.locations'].sudo().search(search_params, limit=1)
                            if temp_loc:
                                new_loc = temp_loc[0]
                            else:
                                new_loc = self.env['tt.activity.master.locations'].sudo().create({
                                    'country_id': prov_data.country_id and prov_data.country_id.id or False,
                                    'city_id': city_id and city_id[0].id or False,
                                    'state_id': False
                                })
                                self.env.cr.commit()
                            temp2.append(new_loc.id)
                else:
                    for idx, countries in enumerate(rec['product']['countries']):
                        country_id = self.env['res.country'].sudo().search([('name', '=', countries)], limit=1)
                        city_id = self.env['res.city'].sudo().search([('name', '=', rec['product']['cities'][idx])], limit=1)
                        search_params = []
                        if country_id:
                            search_params.append(('country_id', '=', country_id[0].id))
                        if city_id:
                            search_params.append(('city_id', '=', city_id[0].id))
                        if search_params:
                            temp_loc = self.env['tt.activity.master.locations'].sudo().search(search_params, limit=1)
                            if temp_loc:
                                new_loc = temp_loc[0]
                            else:
                                new_loc = self.env['tt.activity.master.locations'].sudo().create({
                                    'country_id': country_id and country_id[0].id or False,
                                    'city_id': city_id and city_id[0].id or False,
                                    'state_id': False,
                                })
                                self.env.cr.commit()
                            temp2.append(new_loc.id)

                types_temp = temp
                cur_obj = False
                if rec['product'].get('currency'):
                    cur_obj = self.env['res.currency'].search([('name', '=', rec['product']['currency'])], limit=1)
                    if not cur_obj:
                        cur_obj = self.env['res.currency'].search([('name', '=', 'IDR')], limit=1)

                vals = {
                    'name': rec['product'].get('title') and rec['product']['title'] or '',
                    'type_ids': [(6, 0, types_temp)],
                    'category_ids': [(6, 0, temp)],
                    'location_ids': [(6, 0, temp2)],
                    'currency_id': cur_obj and cur_obj[0].id or False,
                    'basePrice': rec['product'].get('basePrice') and rec['product']['basePrice'] or 0,
                    'priceIncludes': rec['product'].get('priceIncludes') and rec['product']['priceIncludes'] or '',
                    'priceExcludes': rec['product'].get('priceExcludes') and rec['product']['priceExcludes'] or '',
                    'description': rec['product'].get('description') and rec['product']['description'] or '',
                    'highlights': rec['product'].get('highlights') and rec['product']['highlights'] or '',
                    'additionalInfo': rec['product'].get('additionalInfo') and rec['product']['additionalInfo'] or '',
                    'itinerary': rec['product'].get('itinerary') and rec['product']['itinerary'] or '',
                    'warnings': rec['product'].get('warnings') and rec['product']['warnings'] or '',
                    'safety': rec['product'].get('safety') and rec['product']['safety'] or '',
                    'latitude': rec['product'].get('latitude') and rec['product']['latitude'] or 0,
                    'longitude': rec['product'].get('longitude') and rec['product']['longitude'] or 0,
                    'minPax': rec['product'].get('minPax') and rec['product']['minPax'] or 0,
                    'maxPax': rec['product'].get('maxPax') and rec['product']['maxPax'] or 0,
                    'reviewCount': rec['product'].get('reviewCount') and rec['product']['reviewCount'] or 0,
                    'reviewAverageScore': rec['product'].get('reviewAverageScore') and rec['product']['reviewAverageScore'] or 0,
                    'businessHoursFrom': rec['product'].get('businessHoursFrom') and rec['product']['businessHoursFrom'] or '',
                    'businessHoursTo': rec['product'].get('businessHoursTo') and rec['product']['businessHoursTo'] or '',
                    'hotelPickup': rec['product'].get('hotelPickup') and rec['product']['hotelPickup'] or False,
                    'airportPickup': rec['product'].get('airportPickup') and rec['product']['airportPickup'] or False,
                    'can_hold_booking': rec['product'].get('can_hold_booking') and rec['product']['can_hold_booking'] or False,
                    'active': True,
                    'provider_id': provider_id.id,
                }
                if product_obj:
                    if not product_obj.owner_ho_id:
                        vals.update({
                            'owner_ho_id': self.env.user.ho_id.id
                        })
                    if self.env.user.ho_id.id not in product_obj.ho_ids.ids:
                        vals.update({
                            'ho_ids': [(4, self.env.user.ho_id.id)]
                        })
                    util.pop_empty_key(vals)
                    product_obj.write(vals)
                else:
                    vals.update({
                        'uuid': rec['product']['uuid'],
                        'owner_ho_id': self.env.user.ho_id.id,
                        'ho_ids': [(6,0,[self.env.user.ho_id.id])]
                    })
                    if not cur_obj:
                        cur_obj = self.env['res.currency'].search([('name', '=', 'IDR')], limit=1)
                        vals.update({
                            'currency_id': cur_obj and cur_obj[0].id or False
                        })
                    product_obj = self.env['tt.master.activity'].sudo().create(vals)
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

                product_data_list.append({
                    'product_data': rec,
                    'product_id': product_obj.id
                })
            self.env['tt.master.activity'].sync_type_products(product_data_list, provider)

    def sync_type_products(self, product_data_list, provider):
        req_post = {
            'product_data_list': product_data_list,
            'provider': provider
        }
        res = self.env['tt.master.activity.api.con'].get_details_bulk(req_post)
        if res['error_code'] == 0:
            for prod_rec in res['response']:
                product_id = prod_rec['product_id']
                activity_old_obj = self.env['tt.master.activity.lines'].sudo().search([('activity_id', '=', product_id)])
                for temp_old in activity_old_obj:
                    temp_old.sudo().write({
                        'active': False
                    })
                for rec in prod_rec['activity_lines']:
                    rec.update({
                        'activity_id': product_id,
                        'active': True
                    })
                    activity_type_exist = self.env['tt.master.activity.lines'].sudo().search([('activity_id', '=', product_id), ('uuid', '=', rec['uuid']), '|',('active', '=', False), ('active', '=', True)], limit=1)
                    vals = rec

                    if 'voucher_validity' in vals.keys():
                        vals.pop('voucher_validity')
                    sku_list = 'skus' in vals.keys() and vals.pop('skus') or []
                    option_list = 'options' in vals.keys() and vals.pop('options') or {}
                    timeslot_list = 'timeslots' in vals.keys() and vals.pop('timeslots') or []

                    if activity_type_exist:
                        activity_obj = activity_type_exist[0]
                        activity_obj.sudo().write(vals)
                    else:
                        activity_obj = self.env['tt.master.activity.lines'].sudo().create(vals)
                    self.env.cr.commit()

                    for temp_sku in sku_list:
                        old_sku = self.env['tt.master.activity.sku'].sudo().search([('activity_line_id', '=', activity_obj.id), ('sku_id', '=', temp_sku['sku_id']), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                        temp_sku.update({
                            'active': True,
                            'activity_line_id': activity_obj.id,
                        })
                        if old_sku:
                            old_sku[0].sudo().write(temp_sku)
                        else:
                            self.env['tt.master.activity.sku'].sudo().create(temp_sku)
                        self.env.cr.commit()

                    old_timeslot = self.env['tt.activity.master.timeslot'].sudo().search([('product_type_id', '=', activity_obj.id)])
                    for old_time in old_timeslot:
                        old_time.sudo().write({
                            'active': False
                        })
                    for temp_time in timeslot_list:
                        old_timeslot = self.env['tt.activity.master.timeslot'].sudo().search([('product_type_id', '=', activity_obj.id), ('uuid', '=', temp_time['uuid']), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                        temp_time.update({
                            'product_type_id': activity_obj.id,
                            'active': True,
                        })
                        if old_timeslot:
                            old_timeslot[0].sudo().write(temp_time)
                        else:
                            self.env['tt.activity.master.timeslot'].sudo().create(temp_time)
                        self.env.cr.commit()

                    option_ids = []
                    for temp_opt in option_list['perBooking']:
                        temp_opt_items = temp_opt.get('items') and temp_opt.pop('items') or []
                        temp_cur_code_opt = temp_opt.get('currency_code') and temp_opt.pop('currency_code') or False
                        cur_obj_opt = temp_cur_code_opt and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code_opt)],limit=1) or False
                        temp_opt.update({
                            'currency_id': cur_obj_opt and cur_obj_opt[0].id or False,
                        })
                        opt_obj = self.env['tt.activity.booking.option'].sudo().create(temp_opt)
                        self.env.cr.commit()
                        for temp_item in temp_opt_items:
                            temp_cur_code = temp_item.get('currency_code') and temp_item.pop('currency_code') or False
                            cur_obj = temp_cur_code and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code)], limit=1) or False
                            temp_item.update({
                                'currency_id': cur_obj and cur_obj[0].id or False,
                                'booking_option_id': opt_obj.id,
                            })
                            self.env['tt.activity.booking.option.line'].sudo().create(temp_item)
                            self.env.cr.commit()
                        option_ids.append(opt_obj.id)

                    for temp_opt in option_list['perPax']:
                        temp_opt_items = temp_opt.get('items') and temp_opt.pop('items') or []
                        temp_cur_code_opt = temp_opt.get('currency_code') and temp_opt.pop('currency_code') or False
                        cur_obj_opt = temp_cur_code_opt and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code_opt)], limit=1) or False
                        temp_opt.update({
                            'currency_id': cur_obj_opt and cur_obj_opt[0].id or False,
                        })
                        opt_obj = self.env['tt.activity.booking.option'].sudo().create(temp_opt)
                        self.env.cr.commit()
                        for temp_item in temp_opt_items:
                            temp_cur_code = temp_item.get('currency_code') and temp_item.pop('currency_code') or False
                            cur_obj = temp_cur_code and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code)], limit=1) or False
                            temp_item.update({
                                'currency_id': cur_obj and cur_obj[0].id or False,
                                'booking_option_id': opt_obj.id,
                            })
                            self.env['tt.activity.booking.option.line'].sudo().create(temp_item)
                            self.env.cr.commit()
                        option_ids.append(opt_obj.id)

                    activity_obj.update({
                        'option_ids': [(6, 0, option_ids)],
                    })
        else:
            return res

    def get_config_by_api(self):
        try:
            result_objs = self.env['tt.activity.category'].sudo().search([])
            categories = result_objs.filtered(lambda x: x.type == 'category' and not x.parent_id)
            categories_list = []
            for rec in categories:
                child_list = []
                for child in rec.child_ids:
                    child_list.append({
                        'name': child.name,
                        'uuid': child.id,
                    })
                categories_list.append({
                    'name': rec.name,
                    'uuid': rec.id,
                    'children': child_list
                })
            types = result_objs.filtered(lambda x: x.type == 'type')
            types_list = []
            for type in types:
                types_list.append({
                    'name': type.name,
                    'uuid': type.id,
                })

            countries_dict = {}
            activity_loc_objs = self.env['tt.activity.master.locations'].search([('country_id', '!=', False)])
            for loc in activity_loc_objs:
                if loc.country_id.code:
                    if not countries_dict.get(loc.country_id.code):
                        countries_dict.update({
                            loc.country_id.code: {
                                'name': loc.country_id.name,
                                'code': loc.country_id.code,
                                'uuid': str(loc.country_id.id),
                                'states': {}
                            }
                        })
                    if loc.state_id:
                        cur_state = str(loc.state_id.id)
                        if not countries_dict[loc.country_id.code]['states'].get(cur_state):
                            countries_dict[loc.country_id.code]['states'].update({
                                cur_state: {
                                    'name': loc.state_id.name,
                                    'uuid': str(loc.state_id.id),
                                    'cities': {}
                                }
                            })
                    else:
                        cur_state = '0'
                        if not countries_dict[loc.country_id.code]['states'].get(cur_state):
                            countries_dict[loc.country_id.code]['states'].update({
                                cur_state: {
                                    'name': 'No State',
                                    'uuid': '0',
                                    'cities': {}
                                }
                            })
                    if loc.city_id:
                        cur_city_id = str(loc.city_id.id)
                        if not countries_dict[loc.country_id.code]['states'][cur_state]['cities'].get(cur_city_id):
                            countries_dict[loc.country_id.code]['states'][cur_state]['cities'].update({
                                cur_city_id: {
                                    'name': loc.city_id.name,
                                    'uuid': str(loc.city_id.id),
                                }
                            })

            values = {
                'categories': categories_list,
                'types': types_list,
                'countries': countries_dict,
            }
            return ERR.get_no_error(values)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1021)

    def search_by_api(self, req, context):
        try:
            query = req.get('query') and '%' + req['query'] + '%' or ''
            country = req.get('country') and req['country'] or ''
            city = req.get('city') and req['city'] or ''
            type_id = 0
            if req.get('type'):
                temp_type_id = req['type'] != '0' and self.env['tt.activity.category'].sudo().search([('id', '=', req['type']), ('type', '=', 'type')]) or ''
                type_id = temp_type_id and temp_type_id[0].id or 0

            get_cat_instead = 0
            category = ''
            if req.get('sub_category'):
                if req['sub_category'] != '0':
                    category = req['sub_category']
                else:
                    get_cat_instead = 1
            else:
                get_cat_instead = 1

            if get_cat_instead:
                if req.get('category'):
                    category = req['category'] != '0' and req['category'] or ''
                else:
                    category = ''

            provider = req.get('provider', 'all')
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', provider)], limit=1)
            provider_id = provider_id and provider_id[0] or False

            sql_query = 'select themes.* from tt_master_activity themes left join tt_activity_location_rel locrel on locrel.product_id = themes.id left join tt_activity_master_locations loc on loc.id = locrel.location_id '
            sql_query += 'left join tt_master_activity_ho_agent_rel act_ho_rel on act_ho_rel.activity_id = themes.id '

            if category:
                sql_query += 'left join tt_activity_category_rel catrel on catrel.activity_id = themes.id '

            if type_id:
                sql_query += 'left join tt_activity_type_rel typerel on typerel.activity_id = themes.id '

            sql_query += "where "

            if query:
                sql_query += "themes.name ilike '" + str(query) + "' "
            else:
                sql_query += 'themes.active = True and themes."basePrice" > 0 '

            sql_query += 'and (act_ho_rel.ho_id IS NULL'
            if context.get('co_ho_id'):
                sql_query += ' or themes.owner_ho_id = ' + str(context['co_ho_id']) + ''
                sql_query += ' or act_ho_rel.ho_id = ' + str(context['co_ho_id']) + ''
            elif context.get('ho_seq_id'):
                ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['ho_seq_id'])], limit=1)
                if ho_obj:
                    sql_query += ' or themes.owner_ho_id = ' + str(ho_obj[0].id) + ''
                    sql_query += ' or act_ho_rel.ho_id = ' + str(ho_obj[0].id) + ''
            sql_query += ') '

            if type_id:
                sql_query += 'and typerel.type_id = ' + str(type_id) + ' '

            if category:
                sql_query += 'and catrel.category_id = ' + str(category) + ' '

            if req.get('country') and not req.get('city'):
                sql_query += "and (loc.country_id = " + str(country) + ") "

            if req.get('city'):
                sql_query += "and (loc.country_id = " + str(country) + " and loc.city_id = " + str(city) + ") "

            if provider in ['globaltix', 'bemyguest', 'rodextrip_activity'] and provider_id:
                sql_query += "and themes.provider_id = " + str(provider_id.id) + " "

            if query:
                sql_query += 'and themes.active = True and themes."basePrice" > 0 '
            sql_query += 'group by themes.id '

            self.env.cr.execute(sql_query)
            result_id_list = self.env.cr.dictfetchall()
            result_list = []
            dupe_id_check = []
            for result in result_id_list:
                if int(result['id']) not in dupe_id_check:
                    dupe_id_check.append(int(result['id']))
                    res_provider = result.get('provider_id') and self.env['tt.provider'].browse(result['provider_id']) or None
                    result = {
                        'additionalInfo': result.get('additionalInfo') and result['additionalInfo'] or '',
                        'airportPickup': result.get('airportPickup') and result['airportPickup'] or False,
                        'basePrice': result['basePrice'],
                        'businessHoursFrom': result.get('businessHoursFrom') and result['businessHoursFrom'] or '',
                        'businessHoursTo': result.get('businessHoursTo') and result['businessHoursTo'] or '',
                        'currency_id': result.get('currency_id') and result['currency_id'] or False,
                        'description': result.get('description') and result['description'] or '',
                        'highlights': result.get('highlights') and result['highlights'] or '',
                        'hotelPickup': result.get('hotelPickup') and result['hotelPickup'] or False,
                        'itinerary': result.get('itinerary') and result['itinerary'] or '',
                        'latitude': result.get('latitude') and result['latitude'] or 0.0,
                        'longitude': result.get('longitude') and result['longitude'] or 0.0,
                        'maxPax': result['maxPax'] or 0,
                        'minPax': result['minPax'] or 0,
                        'name': result['name'],
                        'priceExcludes': result.get('priceExcludes') and result['priceExcludes'] or '',
                        'priceIncludes': result.get('priceIncludes') and result['priceIncludes'] or '',
                        'provider_id': res_provider and res_provider.id or '',
                        'provider': res_provider and res_provider.code or '',
                        'reviewAverageScore': result.get('reviewAverageScore') and result['reviewAverageScore'] or 0.0,
                        'reviewCount': result.get('reviewCount') and result['reviewCount'] or 0,
                        'safety': result.get('safety') and result['safety'] or '',
                        'uuid': result['uuid'],
                        'warnings': result.get('warnings') and result['warnings'] or '',
                        'can_hold_booking': result.get('can_hold_booking') and result['can_hold_booking'] or False,
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

                    result_obj = self.env['tt.master.activity'].search([('uuid', '=', result['uuid'])], limit=1)
                    result_obj = result_obj and result_obj[0] or False
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
                                    'path': '',
                                    'url': '',
                                }
                                image_temp.append(img_temp)
                    else:
                        img_temp = {
                            'path': '',
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
                            'category_uuid': '',
                            'category_id': category_obj.id,
                        }
                        for cat_line in category_obj.line_ids:
                            if cat_line.provider_id.id == res_provider.id:
                                cat_temp.update({
                                    'category_uuid': cat_line.uuid,
                                })
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

                    if result.get('provider'):
                        req = {
                            'provider': result['provider'],
                            'from_currency': from_currency.name,
                            'base_amount': result['basePrice']
                        }
                        temp = self.reprice_currency(req, context)
                    else:
                        temp = self.env['res.currency']._compute(from_currency, self.env.user.company_id.currency_id,
                                                                 result['basePrice'])

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

                    temp_alt_cur = result.get('currency_id') and self.env['res.currency'].sudo().browse(int(result['currency_id'])) or False
                    alt_currency_code = temp_alt_cur and temp_alt_cur.name or False

                    result.pop('basePrice')
                    result.update({
                        'activity_price': int(sale_price),
                        'provider_id': result['provider_id'],
                        'provider': res_provider.code,
                        'currency_code': 'IDR',
                        'activity_currency_code': alt_currency_code,
                    })
                    result_list.append(result)

            return ERR.get_no_error(result_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def get_details_by_api(self, req, context):
        try:
            provider_obj = self.env['tt.provider'].sudo().search([('alias', '=', req['provider'])], limit=1)
            if not provider_obj:
                raise RequestException(1002)
            provider_obj = provider_obj[0]
            activity_id = self.search([('uuid', '=', provider_obj.alias + '~' + req['activity_uuid']), ('provider_id', '=', provider_obj.id)], limit=1)
            if not activity_id:
                raise RequestException(1022, additional_message='Activity not found.')
            activity_id = activity_id[0]
            if context.get('co_ho_id') and int(context['co_ho_id']) not in activity_id.ho_ids.ids and activity_id.owner_ho_id.id != int(context['co_ho_id']) and activity_id.ho_ids:
                raise RequestException(1022, additional_message='Activity not found.')
            provider = provider_obj.code
            result_id_list = self.env['tt.master.activity.lines'].search([('activity_id', '=', activity_id.id)])
            res = {
                'uuid': activity_id.uuid and activity_id.uuid or '',
                'name': activity_id.name and activity_id.name or '',
                'additionalInfo': activity_id.additionalInfo and activity_id.additionalInfo.replace('<p>', '\n').replace('</p>', '') or '',
                'airportPickup': activity_id.airportPickup and activity_id.airportPickup or False,
                'basePrice': activity_id.basePrice and activity_id.basePrice or 0,
                'businessHoursFrom': activity_id.businessHoursFrom and activity_id.businessHoursFrom or '',
                'businessHoursTo': activity_id.businessHoursTo and activity_id.businessHoursTo or '',
                'currency': activity_id.currency_id and activity_id.currency_id.name or '',
                'description': activity_id.description and activity_id.description.replace('<p>', '\n').replace('</p>', '') or '',
                'highlights': activity_id.highlights and activity_id.highlights.replace('<p>', '\n').replace('</p>', '') or '',
                'hotelPickup': activity_id.hotelPickup and activity_id.hotelPickup or False,
                'itinerary': activity_id.itinerary and activity_id.itinerary.replace('<p>', '\n').replace('</p>', '') or '',
                'latitude': activity_id.latitude and activity_id.latitude or 0.0,
                'longitude': activity_id.longitude and activity_id.longitude or 0.0,
                'maxPax': activity_id.maxPax and activity_id.maxPax or 0,
                'minPax': activity_id.minPax and activity_id.minPax or 0,
                'priceExcludes': activity_id.priceExcludes and activity_id.priceExcludes.replace('<p>', '\n').replace('</p>', '') or '',
                'priceIncludes': activity_id.priceIncludes and activity_id.priceIncludes.replace('<p>', '\n').replace('</p>', '') or '',
                'provider_code': activity_id.provider_id and activity_id.provider_id.code or '',
                'reviewAverageScore': activity_id.reviewAverageScore and activity_id.reviewAverageScore or 0.0,
                'reviewCount': activity_id.reviewCount and activity_id.reviewCount or 0,
                'safety': activity_id.safety and activity_id.safety.replace('<p>', '\n').replace('</p>', '') or '',
                'warnings': activity_id.warnings and activity_id.warnings.replace('<p>', '\n').replace('</p>', '') or '',
                'can_hold_booking': activity_id.can_hold_booking and activity_id.can_hold_booking or False
            }

            image_temp = []
            if activity_id.image_ids:
                image_objs = activity_id.image_ids
                for image_obj in image_objs:
                    if image_obj.photos_path and image_obj.photos_url:
                        img_temp = {
                            'path': image_obj.photos_path,
                            'url': image_obj.photos_url,
                        }
                        image_temp.append(img_temp)
                    else:
                        img_temp = {
                            'path': '',
                            'url': '',
                        }
                        image_temp.append(img_temp)
            else:
                img_temp = {
                    'path': '',
                    'url': '',
                }
                image_temp.append(img_temp)
            res.update({
                'images': image_temp,
            })

            video_temp = []
            if activity_id.video_ids:
                video_objs = activity_id.video_ids
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
            res.update({
                'videos': video_temp,
            })

            category_objs = activity_id.category_ids
            category_temp = []
            for category_obj in category_objs:
                cat_temp = {
                    'category_name': category_obj.name,
                    'category_uuid': '',
                    'category_id': category_obj.id,
                }
                for cat_line in category_obj.line_ids:
                    if cat_line.provider_id.id == provider_obj.id:
                        cat_temp.update({
                            'category_uuid': cat_line.uuid,
                        })
                category_temp.append(cat_temp)
            res.update({
                'categories': category_temp,
            })

            location_objs = activity_id.location_ids
            location_temp = []
            for location_obj in location_objs:
                loc_temp = {
                    'country_name': location_obj.country_id.name,
                    'state_name': location_obj.state_id.name,
                    'city_name': location_obj.city_id.name,
                }
                location_temp.append(loc_temp)
            res.update({
                'locations': location_temp,
            })

            temp = []
            for result_id in result_id_list:
                result = {
                    'uuid': result_id.uuid,
                    'name': result_id.name,
                    'provider_code': provider,
                    'description': result_id.description and result_id.description.replace('<p>', '\n').replace('</p>', '') or '',
                    'durationDays': result_id.durationDays and result_id.durationDays or 0,
                    'durationHours': result_id.durationHours and result_id.durationHours or 0,
                    'durationMinutes': result_id.durationMinutes and result_id.durationMinutes or 0,
                    'isNonRefundable': result_id.isNonRefundable and result_id.isNonRefundable or True,
                    'minPax': result_id.minPax and result_id.minPax or 1,
                    'maxPax': result_id.maxPax and result_id.maxPax or 100,
                    'voucherUse': result_id.voucherUse and result_id.voucherUse.replace('<p>', '\n').replace('</p>', '') or '',
                    'voucherRedemptionAddress': result_id.voucherRedemptionAddress and result_id.voucherRedemptionAddress.replace('<p>', '\n').replace('</p>', '') or '',
                    'voucherRequiresPrinting': result_id.voucherRequiresPrinting and result_id.voucherRequiresPrinting or '',
                    'cancellationPolicies': result_id.cancellationPolicies and result_id.cancellationPolicies or '',
                    'meetingLocation': result_id.meetingLocation and result_id.meetingLocation or '',
                    'meetingAddress': result_id.meetingAddress and result_id.meetingAddress or '',
                    'meetingTime': result_id.meetingTime and result_id.meetingTime or '',
                    'instantConfirmation': result_id.instantConfirmation and result_id.instantConfirmation or False,
                    'voucher_validity_type': result_id.voucher_validity_type and result_id.voucher_validity_type or False,
                    'voucher_validity_days': result_id.voucher_validity_days and result_id.voucher_validity_days or 0,
                    'voucher_validity_date': result_id.voucher_validity_date and result_id.voucher_validity_date or False,
                    'advanceBookingDays': result_id.advanceBookingDays and result_id.advanceBookingDays or 0,
                }

                if result_id.voucher_validity_type == 'only_visit_date':
                    voucher_validity = 'Valid only on the stated visit date'
                elif result_id.voucher_validity_type == 'from_travel_date':
                    voucher_validity = 'Valid until ' + str(result_id.voucher_validity_days) + ' days after from the stated visit date'
                elif result_id.voucher_validity_type == 'after_issue_date':
                    voucher_validity = 'Valid until ' + str(result_id.voucher_validity_days) + ' days after issued date'
                elif result_id.voucher_validity_type == 'until_date':
                    voucher_validity = 'Valid until ' + str(result_id.voucher_validity_date)
                else:
                    voucher_validity = '-'

                result.update({
                    'voucher_validity': voucher_validity,
                })
                skus = []
                if result_id.sku_ids:
                    for sku in result_id.sku_ids.ids:
                        sku_obj = self.env['tt.master.activity.sku'].browse(int(sku))
                        sku_temp = {
                            'id': sku_obj.id,
                            'sku_id': sku_obj.sku_id,
                            'title': sku_obj.title,
                            'pax_type': sku_obj.pax_type,
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
                            'currency_id': activity_opt_obj.currency_id and activity_opt_obj.currency_id.id or False,
                            'currency_code': activity_opt_obj.currency_id and activity_opt_obj.currency_id.name or False,
                        }
                        description = (temp_opt['description'].replace('<p>', '\n').replace('</p>',''))[1:]
                        temp_opt.update({
                            'description': description,
                        })
                        if activity_opt_obj.price:
                            req = {
                                'provider': provider,
                                'from_currency': from_currency.name,
                                'base_amount': activity_opt_obj.price
                            }
                            price = self.reprice_currency(req, context)
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
                                    'currency_id': item.currency_id and item.currency_id.id or False,
                                    'currency_code': item.currency_id and item.currency_id.name or False,
                                }
                                if item.price:
                                    req = {
                                        'provider': provider,
                                        'from_currency': from_currency.name,
                                        'base_amount': item.price
                                    }
                                    price2 = self.reprice_currency(req, context)
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
            res.update({
                'activity_lines': temp
            })
            activity_carrier = self.env['tt.transport.carrier'].search([('code', '=', 'ACT')], limit=1)
            if activity_carrier:
                res.update({
                    'carrier_data': activity_carrier[0].to_dict()
                })
            return ERR.get_no_error(res)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def get_autocomplete_api(self, req, context):
        try:
            search_params = []
            if req.get('name'):
                search_params.append(('name', 'ilike', req['name']))
            if context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            result_id_list = self.env['tt.master.activity'].search(search_params)
            result_list = []
            for result in result_id_list:
                result_list.append({
                    'name': result.name and result.name or '',
                })
            return ERR.get_no_error(result_list)
        except RequestException as e:
            _logger.error(traceback.format_exc())
            return e.error_dict()
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(1022)

    def product_update_webhook(self, req, context):
        provider = req.get('provider') and req['provider'] or ''
        self.sync_products(provider, req)
        response = {
            'success': True
        }
        return ERR.get_no_error(response)

    def product_type_new_webhook(self, req, context):
        provider_id = self.env['tt.provider'].sudo().search([('code', '=', req['provider'])], limit=1)
        if not provider_id:
            raise RequestException(1002)
        provider_id = provider_id[0]
        activity_id = self.env['tt.master.activity'].sudo().search(
            [('uuid', '=', provider_id[0].alias + '~' + req['productUuid']), ('provider_id', '=', provider_id.id)],
            limit=1)
        activity_id = activity_id[0]
        product_data_list = [{
            'product_data': {
                'product': {
                    'uuid': provider_id[0].alias + '~' + req['productUuid']
                }
            },
            'product_id': activity_id.id
        }]
        self.env['tt.master.activity'].sync_type_products(product_data_list, req['provider'])
        response = {
            'success': True
        }
        return ERR.get_no_error(response)

    def product_type_update_webhook(self, req, context):
        provider_id = self.env['tt.provider'].sudo().search([('code', '=', req['provider'])], limit=1)
        if not provider_id:
            raise RequestException(1002)
        provider_id = provider_id[0]
        if req.get('productUuid'):
            activity_id = self.env['tt.master.activity'].sudo().search(
                [('uuid', '=', provider_id[0].alias + '~' + req['productUuid']), ('provider_id', '=', provider_id.id)], limit=1)
            product_id = activity_id and activity_id[0].id or False
        else:
            product_id = False
        act_type_search_list = [('uuid', '=', provider_id[0].alias + '~' + req['data']['uuid']), '|', ('active', '=', False), ('active', '=', True)]
        if product_id:
            act_type_search_list.insert(0, ('activity_id', '=', product_id))
        activity_type_exist = self.env['tt.master.activity.lines'].search(act_type_search_list, limit=1)
        vals = req['data']
        vals.update({
            'uuid': provider_id[0].alias + '~' + req['data']['uuid']
        })
        if product_id:
            vals.update({
                'activity_id': product_id
            })

        sku_list = 'skus' in vals.keys() and vals.pop('skus') or []
        option_list = 'options' in vals.keys() and vals.pop('options') or {}
        timeslot_list = 'timeslots' in vals.keys() and vals.pop('timeslots') or []

        if vals.get('voucher_validity_date') == '':
            vals.pop('voucher_validity_date')
        if activity_type_exist:
            activity_obj = activity_type_exist[0]
            activity_obj.sudo().write(vals)
        else:
            activity_obj = self.env['tt.master.activity.lines'].sudo().create(vals)
        self.env.cr.commit()

        for temp_sku in sku_list:
            old_sku = self.env['tt.master.activity.sku'].sudo().search(
                [('activity_line_id', '=', activity_obj.id), ('sku_id', '=', temp_sku['sku_id']), '|',
                 ('active', '=', False), ('active', '=', True)], limit=1)
            temp_sku.update({
                'active': True,
                'activity_line_id': activity_obj.id,
            })
            if old_sku:
                old_sku[0].sudo().write(temp_sku)
            else:
                self.env['tt.master.activity.sku'].sudo().create(temp_sku)
            self.env.cr.commit()

        old_timeslot = self.env['tt.activity.master.timeslot'].sudo().search(
            [('product_type_id', '=', activity_obj.id)])
        for old_time in old_timeslot:
            old_time.sudo().write({
                'active': False
            })
        for temp_time in timeslot_list:
            old_timeslot = self.env['tt.activity.master.timeslot'].sudo().search(
                [('product_type_id', '=', activity_obj.id), ('uuid', '=', temp_time['uuid']), '|',
                 ('active', '=', False), ('active', '=', True)], limit=1)
            temp_time.update({
                'product_type_id': activity_obj.id,
                'active': True,
            })
            if old_timeslot:
                old_timeslot[0].sudo().write(temp_time)
            else:
                self.env['tt.activity.master.timeslot'].sudo().create(temp_time)
            self.env.cr.commit()

        option_ids = []
        for temp_opt in option_list['perBooking']:
            temp_opt_items = temp_opt.get('items') and temp_opt.pop('items') or []
            temp_cur_code_opt = temp_opt.get('currency_code') and temp_opt.pop('currency_code') or False
            cur_obj_opt = temp_cur_code_opt and self.env['res.currency'].sudo().search(
                [('name', '=', temp_cur_code_opt)], limit=1) or False
            temp_opt.update({
                'currency_id': cur_obj_opt and cur_obj_opt[0].id or False,
            })
            opt_obj = self.env['tt.activity.booking.option'].sudo().create(temp_opt)
            self.env.cr.commit()
            for temp_item in temp_opt_items:
                temp_cur_code = temp_item.get('currency_code') and temp_item.pop('currency_code') or False
                cur_obj = temp_cur_code and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code)],
                                                                                   limit=1) or False
                temp_item.update({
                    'currency_id': cur_obj and cur_obj[0].id or False,
                    'booking_option_id': opt_obj.id,
                })
                self.env['tt.activity.booking.option.line'].sudo().create(temp_item)
                self.env.cr.commit()
            option_ids.append(opt_obj.id)

        for temp_opt in option_list['perPax']:
            temp_opt_items = temp_opt.get('items') and temp_opt.pop('items') or []
            temp_cur_code_opt = temp_opt.get('currency_code') and temp_opt.pop('currency_code') or False
            cur_obj_opt = temp_cur_code_opt and self.env['res.currency'].sudo().search(
                [('name', '=', temp_cur_code_opt)], limit=1) or False
            temp_opt.update({
                'currency_id': cur_obj_opt and cur_obj_opt[0].id or False,
            })
            opt_obj = self.env['tt.activity.booking.option'].sudo().create(temp_opt)
            self.env.cr.commit()
            for temp_item in temp_opt_items:
                temp_cur_code = temp_item.get('currency_code') and temp_item.pop('currency_code') or False
                cur_obj = temp_cur_code and self.env['res.currency'].sudo().search([('name', '=', temp_cur_code)],
                                                                                   limit=1) or False
                temp_item.update({
                    'currency_id': cur_obj and cur_obj[0].id or False,
                    'booking_option_id': opt_obj.id,
                })
                self.env['tt.activity.booking.option.line'].sudo().create(temp_item)
                self.env.cr.commit()
            option_ids.append(opt_obj.id)

        activity_obj.update({
            'option_ids': [(6, 0, option_ids)],
        })

        response = {
            'success': True
        }
        return ERR.get_no_error(response)

    def product_type_inactive_webhook(self, req, context):
        provider_id = self.env['tt.provider'].sudo().search([('code', '=', req['provider'])], limit=1)
        if not provider_id:
            raise RequestException(1002)
        provider_id = provider_id[0]
        activity_id = self.env['tt.master.activity'].sudo().search([('uuid', '=', provider_id[0].alias + '~' + req['productUuid']), ('provider_id', '=', provider_id.id)], limit=1)
        activity_id = activity_id[0]
        product_type_obj = self.env['tt.master.activity.lines'].sudo().search([('uuid', '=', provider_id[0].alias + '~' + req['productTypeUuid']), ('activity_id', '=', activity_id.id)], limit=1)
        for rec in product_type_obj:
            rec.sudo().write({
                'active': False
            })
        response = {
            'success': True
        }
        return ERR.get_no_error(response)

    def product_sync_webhook_nosend(self, req, context):
        try:
            _logger.info("Receiving activity data from webhook...")
            provider_id = self.env['tt.provider'].sudo().search([('code', '=', req['provider'])], limit=1)
            if not provider_id:
                raise RequestException(1002)
            for rec in req['data']:
                currency_obj = self.env['res.currency'].sudo().search([('name', '=', rec['currency_code'])], limit=1)
                vals = {
                    'name': rec['name'],
                    'uuid': provider_id[0].alias + '~' + rec['uuid'],
                    'latitude': rec['latitude'],
                    'longitude': rec['longitude'],
                    'businessHoursFrom': rec['businessHoursFrom'],
                    'businessHoursTo': rec['businessHoursTo'],
                    'minPax': rec['minPax'],
                    'maxPax': rec['maxPax'],
                    'reviewAverageScore': rec['reviewAverageScore'],
                    'reviewCount': rec['reviewCount'],
                    'airportPickup': rec['airportPickup'],
                    'hotelPickup': rec['hotelPickup'],
                    'provider_id': provider_id[0].id,
                    'currency_id': currency_obj and currency_obj[0].id or False,
                    'basePrice': rec['basePrice'],
                    'priceIncludes': rec['priceIncludes'],
                    'priceExcludes': rec['priceExcludes'],
                    'description': rec['description'],
                    'highlights': rec['highlights'],
                    'itinerary': rec['itinerary'],
                    'additionalInfo': rec['additionalInfo'],
                    'warnings': rec['warnings'],
                    'safety': rec['safety'],
                    'can_hold_booking': rec['can_hold_booking'],
                }
                activity_obj = self.env['tt.master.activity'].sudo().search([('uuid', '=', provider_id[0].alias + '~' + rec['uuid']), ('provider_id', '=', provider_id[0].id)], limit=1)
                if activity_obj:
                    activity_obj = activity_obj[0]
                    activity_obj.sudo().write(vals)
                    for img in activity_obj.image_ids:
                        img.sudo().unlink()
                    for vid in activity_obj.video_ids:
                        vid.sudo().unlink()
                    for line in activity_obj.line_ids:
                        line.sudo().write({
                            'active': False
                        })
                else:
                    activity_obj = self.env['tt.master.activity'].sudo().create(vals)
                self.env.cr.commit()

                location_list = []
                for rec2 in rec['location_ids']:
                    search_params = []
                    country_obj = self.env['res.country'].sudo().search([('code', '=', rec2['country_code'])], limit=1)
                    if country_obj:
                        search_params.append(('country_id', '=', country_obj[0].id))
                    city_obj = self.env['res.city'].sudo().search([('name', '=', rec2['city_name'])], limit=1)
                    if city_obj:
                        search_params.append(('city_id', '=', city_obj[0].id))
                    loc_obj = self.env['tt.activity.master.locations'].sudo().search(search_params, limit=1)
                    if loc_obj:
                        loc_obj = loc_obj[0]
                    else:
                        loc_obj = self.env['tt.activity.master.locations'].sudo().create({
                            'country_id': country_obj and country_obj[0].id or False,
                            'city_id': city_obj and city_obj[0].id or False,
                        })
                    location_list.append(loc_obj.id)

                category_list = []
                for rec2 in rec['category_ids']:
                    cat_search_params = [('name', '=', rec2['name']), ('type', '=', 'category')]
                    cat_parent_obj = False
                    if rec2.get('parent_name'):
                        cat_parent_obj = self.env['tt.activity.category'].sudo().search([('name', '=', rec2['parent_name']), ('type', '=', 'category')], limit=1)
                        if cat_parent_obj:
                            cat_parent_obj = cat_parent_obj[0]
                        else:
                            cat_parent_obj = self.env['tt.activity.category'].sudo().create({
                                'name': rec2['parent_name'],
                                'type': 'category'
                            })
                        cat_search_params.append(('parent_id', '=', cat_parent_obj.id))
                    cat_obj = self.env['tt.activity.category'].sudo().search(cat_search_params, limit=1)
                    if cat_obj:
                        cat_obj = cat_obj[0]
                    else:
                        cat_obj = self.env['tt.activity.category'].sudo().create({
                            'name': rec2['name'],
                            'type': 'category',
                            'parent_id': cat_parent_obj and cat_parent_obj.id or False,
                        })
                    category_list.append(cat_obj.id)

                for rec2 in rec['image_ids']:
                    self.env['tt.activity.master.images'].sudo().create({
                        'activity_id': activity_obj.id,
                        'photos_path': rec2['photos_path'],
                        'photos_url': rec2['photos_url'],
                    })
                for rec2 in rec['video_ids']:
                    self.env['tt.activity.master.videos'].sudo().create({
                        'activity_id': activity_obj.id,
                        'video_url': rec2['video_url'],
                    })

                for rec2 in rec['line_ids']:
                    line_vals = {
                        'activity_id': activity_obj.id,
                        'uuid': provider_id[0].alias + '~' + rec2['uuid'],
                        'name': rec2['name'],
                        'description': rec2['description'],
                        'durationDays': rec2['durationDays'],
                        'durationHours': rec2['durationHours'],
                        'durationMinutes': rec2['durationMinutes'],
                        'advanceBookingDays': rec2['advanceBookingDays'],
                        'minimumSellingPrice': rec2['minimumSellingPrice'],
                        'minPax': rec2['minPax'],
                        'maxPax': rec2['maxPax'],
                        'isNonRefundable': rec2['isNonRefundable'],
                        'voucherUse': rec2['voucherUse'],
                        'voucherRedemptionAddress': rec2['voucherRedemptionAddress'],
                        'voucherRequiresPrinting': rec2['voucherRequiresPrinting'],
                        'voucher_validity_type': rec2['voucher_validity_type'],
                        'voucher_validity_days': rec2['voucher_validity_days'],
                        'voucher_validity_date': rec2['voucher_validity_date'],
                        'meetingLocation': rec2['meetingLocation'],
                        'meetingAddress': rec2['meetingAddress'],
                        'meetingTime': rec2['meetingTime'],
                        'cancellationPolicies': rec2['cancellationPolicies'],
                        'instantConfirmation': rec2['instantConfirmation'],
                        'active': True
                    }
                    line_obj = self.env['tt.master.activity.lines'].sudo().search([('uuid', '=', provider_id[0].alias + '~' + rec2['uuid']), ('activity_id', '=', activity_obj.id), '|', ('active', '=', False), ('active', '=', True)], limit=1)
                    if line_obj:
                        line_obj = line_obj[0]
                        line_obj.sudo().write(line_vals)
                        for temp_sku in line_obj.sku_ids:
                            temp_sku.sudo().write({
                                'active': False
                            })
                        for temp_time in line_obj.timeslot_ids:
                            temp_time.sudo().write({
                                'active': False
                            })
                    else:
                        line_obj = self.env['tt.master.activity.lines'].sudo().create(line_vals)
                    self.env.cr.commit()
                    for rec3 in rec2['sku_ids']:
                        sku_vals = {
                            'activity_line_id': line_obj.id,
                            'sku_id': rec3['sku_id'],
                            'title': rec3['title'],
                            'pax_type': rec3['pax_type'],
                            'add_information': rec3['add_information'],
                            'minPax': rec3['minPax'],
                            'maxPax': rec3['maxPax'],
                            'minAge': rec3['minAge'],
                            'maxAge': rec3['maxAge'],
                            'active': True
                        }
                        sku_obj = self.env['tt.master.activity.sku'].sudo().search([('activity_line_id', '=', line_obj.id), ('sku_id', '=', rec3['sku_id']), '|',('active', '=', False), ('active', '=', True)], limit=1)
                        if sku_obj:
                            sku_obj = sku_obj[0]
                            sku_obj.sudo().write(sku_vals)
                        else:
                            sku_obj = self.env['tt.master.activity.sku'].sudo().create(sku_vals)

                    for rec3 in rec2['timeslot_ids']:
                        timeslot_vals = {
                            'product_type_id': line_obj.id,
                            'uuid': rec3['uuid'],
                            'startTime': rec3['startTime'],
                            'endTime': rec3['endTime'],
                            'active': True
                        }
                        timeslot_obj = self.env['tt.activity.master.timeslot'].sudo().search([('product_type_id', '=', line_obj.id), ('uuid', '=', rec3['uuid']), '|',('active', '=', False), ('active', '=', True)], limit=1)
                        if timeslot_obj:
                            timeslot_obj = timeslot_obj[0]
                            timeslot_obj.sudo().write(timeslot_vals)
                        else:
                            timeslot_obj = self.env['tt.activity.master.timeslot'].sudo().create(timeslot_vals)

                    option_list = []
                    for rec3 in rec2['option_ids']:
                        opt_currency_obj = self.env['res.currency'].sudo().search([('name', '=', rec3['currency_code'])], limit=1)
                        option_vals = {
                            'uuid': rec3['uuid'],
                            'name': rec3['name'],
                            'description': rec3['description'],
                            'required': rec3['required'],
                            'formatRegex': rec3['formatRegex'],
                            'inputType': rec3['inputType'],
                            'type': rec3['type'],
                            'price': rec3['price'],
                            'currency_id': opt_currency_obj and opt_currency_obj[0].id or False,
                        }
                        option_obj = self.env['tt.activity.booking.option'].sudo().create(option_vals)
                        self.env.cr.commit()
                        for rec4 in rec3['items']:
                            item_currency_obj = self.env['res.currency'].sudo().search([('name', '=', rec4['currency_code'])], limit=1)
                            opt_item_vals = {
                                'booking_option_id': option_obj.id,
                                'label': rec4['label'],
                                'value': rec4['value'],
                                'price': rec4['price'],
                                'currency_id': item_currency_obj and item_currency_obj[0].id or False,
                            }
                            opt_item_obj = self.env['tt.activity.booking.option.line'].sudo().create(opt_item_vals)
                        option_list.append(option_obj.id)
                    line_obj.sudo().write({
                        'option_ids': [(6, 0, option_list)]
                    })

                activity_obj.sudo().write({
                    'location_ids': [(6, 0, location_list)],
                    'category_ids': [(6, 0, category_list)],
                })

            response = {
                'success': True
            }
            return ERR.get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error()


class ActivitySyncProductsChildren(models.TransientModel):
    _name = "activity.sync.product.children.wizard"
    _description = 'Activity Sync Product Children Wizard'

    def sync_data_to_children(self):
        try:
            activity_data_list = []
            activity_datas = self.env['tt.master.activity'].sudo().search([('basePrice', '>', 0)])
            for rec in activity_datas:
                ho_obj = self.env.ref('tt_base.rodex_ho')
                new_currency = ho_obj.currency_id and ho_obj.currency_id.name or 'IDR'
                new_base_amt = rec.reprice_currency({
                    'provider': rec.provider_id.code,
                    'from_currency': rec.currency_id.name,
                    'base_amount': rec.basePrice
                })
                dict_vals = {
                    'name': rec.name,
                    'uuid': rec.uuid,
                    'latitude': rec.latitude,
                    'longitude': rec.longitude,
                    'businessHoursFrom': rec.businessHoursFrom,
                    'businessHoursTo': rec.businessHoursTo,
                    'minPax': rec.minPax,
                    'maxPax': rec.maxPax,
                    'reviewAverageScore': rec.reviewAverageScore,
                    'reviewCount': rec.reviewCount,
                    'airportPickup': rec.airportPickup,
                    'hotelPickup': rec.hotelPickup,
                    'currency_code': new_currency,
                    'basePrice': new_base_amt,
                    'priceIncludes': rec.priceIncludes,
                    'priceExcludes': rec.priceExcludes,
                    'description': rec.description,
                    'highlights': rec.highlights,
                    'itinerary': rec.itinerary,
                    'additionalInfo': rec.additionalInfo,
                    'warnings': rec.warnings,
                    'safety': rec.safety,
                    'can_hold_booking': rec.can_hold_booking,
                }
                location_list = []
                for rec2 in rec.location_ids:
                    location_list.append({
                        'city_name': rec2.city_id.name,
                        'country_code': rec2.country_id.code
                    })
                category_list = []
                for rec2 in rec.category_ids:
                    category_list.append({
                        'name': rec2.name,
                        'parent_name': rec2.parent_id.name
                    })
                image_list = []
                for rec2 in rec.image_ids:
                    image_list.append({
                        'photos_url': rec2.photos_url,
                        'photos_path': rec2.photos_path,
                    })

                video_list = []
                for rec2 in rec.video_ids:
                    video_list.append({
                        'video_url': rec2.video_url,
                    })

                product_type_list = []
                for rec2 in rec.line_ids:
                    type_data = {
                        'uuid': rec2.uuid,
                        'name': rec2.name,
                        'description': rec2.description,
                        'durationDays': rec2.durationDays,
                        'durationHours': rec2.durationHours,
                        'durationMinutes': rec2.durationMinutes,
                        'advanceBookingDays': rec2.advanceBookingDays,
                        'minimumSellingPrice': rec2.minimumSellingPrice,
                        'minPax': rec2.minPax,
                        'maxPax': rec2.maxPax,
                        'isNonRefundable': rec2.isNonRefundable,
                        'voucherUse': rec2.voucherUse,
                        'voucherRedemptionAddress': rec2.voucherRedemptionAddress,
                        'voucherRequiresPrinting': rec2.voucherRequiresPrinting,
                        'voucher_validity_type': rec2.voucher_validity_type,
                        'voucher_validity_days': rec2.voucher_validity_days,
                        'voucher_validity_date': rec2.voucher_validity_date and rec2.voucher_validity_date.strftime("%Y-%m-%d"),
                        'meetingLocation': rec2.meetingLocation,
                        'meetingAddress': rec2.meetingAddress,
                        'meetingTime': rec2.meetingTime,
                        'cancellationPolicies': rec2.cancellationPolicies,
                        'instantConfirmation': rec2.instantConfirmation,
                    }
                    sku_list = []
                    for rec3 in rec2.sku_ids:
                        sku_list.append({
                            'sku_id': rec3.sku_id,
                            'title': rec3.title,
                            'pax_type': rec3.pax_type,
                            'add_information': rec3.add_information,
                            'minPax': rec3.minPax,
                            'maxPax': rec3.maxPax,
                            'minAge': rec3.minAge,
                            'maxAge': rec3.maxAge,
                        })

                    timeslot_list = []
                    for rec3 in rec2.timeslot_ids:
                        timeslot_list.append({
                            'uuid': rec3.uuid,
                            'startTime': rec3.startTime,
                            'endTime': rec3.endTime,
                        })
                    option_list = []
                    for rec3 in rec2.option_ids:
                        item_list = []
                        for rec4 in rec3.items:
                            if rec4.currency_id and rec4.price:
                                new_rec4_price = rec.reprice_currency({
                                    'provider': rec.provider_id.code,
                                    'from_currency': rec4.currency_id.name,
                                    'base_amount': rec4.price
                                })
                            else:
                                new_rec4_price = 0
                            item_list.append({
                                'label': rec4.label,
                                'value': rec4.value,
                                'price': new_rec4_price,
                                'currency_code': new_currency,
                            })

                        if rec3.currency_id and rec3.price:
                            new_rec3_price = rec.reprice_currency({
                                'provider': rec.provider_id.code,
                                'from_currency': rec3.currency_id.name,
                                'base_amount': rec3.price
                            })
                        else:
                            new_rec3_price = 0
                        option_list.append({
                            'uuid': rec3.uuid,
                            'name': rec3.name,
                            'description': rec3.description,
                            'required': rec3.required,
                            'formatRegex': rec3.formatRegex,
                            'inputType': rec3.inputType,
                            'type': rec3.type,
                            'price': new_rec3_price,
                            'currency_code': new_currency,
                            'items': item_list,
                        })

                    type_data.update({
                        'sku_ids': sku_list,
                        'timeslot_ids': timeslot_list,
                        'option_ids': option_list
                    })
                    product_type_list.append(type_data)

                dict_vals.update({
                    'location_ids': location_list,
                    'category_ids': category_list,
                    'image_ids': image_list,
                    'video_ids': video_list,
                    'line_ids': product_type_list
                })
                activity_data_list.append(dict_vals)

            # gw_timeout = int(len(activity_data_list) / 3) > 120 and int(len(activity_data_list) / 3) or 120 # kalau 60 timeout
            gw_timeout = 10

            def chunks(list_data, amt_per_list):
                """Yield successive amt_per_list-sized chunks from list_data."""
                for i in range(0, len(list_data), amt_per_list):
                    yield list_data[i:i + amt_per_list]

            for rec in list(chunks(activity_data_list, 1000)):
                vals = {
                    'provider_type': 'activity',
                    'action': 'sync_products_to_children',
                    'data': rec,
                    'fail_send_limit': 1,  # 1 x saja supaya tidak ulang ulang proses di btbo2
                    'timeout': gw_timeout
                }
                self.env['tt.api.webhook.data'].notify_subscriber(vals)
        except Exception as e:
            raise UserError(_('Failed to sync activity data to children!'))
