from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools.api import Response
import html2text
import json,traceback,logging
from bs4 import BeautifulSoup
import base64
import requests
import os
from ...tools import util,variables,ERR

_logger = logging.getLogger(__name__)

PAX_TYPE = [
    ('ADT', 'Adult'),
    ('CHD', 'Children'),
    ('INF', 'Infant')
]

ENTRY_TYPE = [
    ('single', 'Single'),
    ('double', 'Double'),
    ('multiple', 'Multiple')
]

VISA_TYPE = [
    ('tourist', 'Tourist'),
    ('business', 'Business'),
    ('student', 'Student')
]

PROCESS_TYPE = [
    ('regular', 'Regular'),
    ('kilat', 'Express'),
    ('super', 'Super Express')
]

class VisaSyncProducts(models.TransientModel):
    _name = "visa.sync.product.wizard"
    _description = 'Visa Sync Product Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa').id
        return [('provider_type_id.id', '=', int(domain_id))]

    def update_reference_code_internal(self):
        for idx, rec in enumerate(self.env['tt.reservation.visa.pricelist'].search([]), 1):
            if rec.provider_id == '':
                rec.reference_code = ''
                rec.provider_id = self.env['tt.provider'].search([('code', '=', 'visa_internal')], limit=1).id

    def get_reference_code(self):
        for idx, rec in enumerate(self.env['tt.reservation.visa.pricelist'].search([]),1):
            if rec.reference_code == '' or rec.reference_code == False:
                if rec.provider_id.code:
                    counter = idx
                    while True:
                        if not self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', rec.provider_id.code + rec.name + '_' + str(counter))]):
                            rec.update({
                                "reference_code": rec.provider_id.code + '_' + rec.name + '_' + str(counter),
                                "provider_id": self.env['tt.provider'].search([('code', '=', rec.provider_id.code)], limit=1).id
                            })
                            break
                        counter += 1
                else:
                    raise UserError(
                        _('You have to fill Provider ID in all Visa Pricelist.'))

            for count, requirement in enumerate(rec.requirement_ids):
                requirement.update({
                    "reference_code": '%s_%s' % (rec.reference_code, str(count))
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def actions_get_product_rodextrip(self, data):
        req = {
            'provider': 'rodextrip_visa'
        }
        ## tambah context
        res = self.env['tt.visa.api.con'].get_product_vendor(req)
        if res['error_code'] == 0:
            folder_path = '/var/log/tour_travel/rt_visa_master_data'
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
            file = open('/var/log/tour_travel/rt_visa_master_data/rt_visa_master_data.json', 'w')
            file.write(json.dumps(res['response']))
            file.close()
        else:
            #raise sini
            pass

    def actions_sync_product_rodextrip(self, data):
        provider = 'rodextrip_visa'
        list_product = self.env['tt.reservation.visa.pricelist'].search([('provider_id', '=', self.env['tt.provider'].search([('code', '=', 'rodextrip_visa')], limit=1).id)])
        for rec in list_product:
            rec.active = False
        file = []
        file_dat = open('/var/log/tour_travel/rt_visa_master_data/rt_visa_master_data.json','r')
        file = json.loads(file_dat.read())
        file_dat.close()
        if file:
            self.sync_products(provider, file)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def sync_products(self, provider=None, data=None, page=None):
        file = data
        if file:
            for rec in file:
                product_obj = self.env['tt.reservation.visa.pricelist'].search([('reference_code', '=', rec)], limit=1)
                product_obj = product_obj and product_obj[0] or False
                temp = []
                if provider == 'rodextrip_visa':
                    if product_obj and product_obj.provider_id.code == provider:
                        product_obj.active = False #inactive
                    req = {
                        'provider': provider,
                        'code': rec
                    }
                    ## tambah context
                    res = self.env['tt.visa.api.con'].get_product_detail_vendor(req)
                    #create object
                    if res['error_code'] == 0:
                        master_data = self.env['tt.reservation.visa.pricelist'].search([('reference_code','=',res['response']['reference_code'] + '_rdx')], limit=1)
                        if master_data:
                            master_data.update({
                                'commercial_duration': res['response']['commercial_duration'],
                                'commission_price': res['response']['commission_price'],
                                'cost_price': res['response']['cost_price'],
                                'country_id': self.env['res.country'].search(
                                    [('name', '=', res['response']['country_id'])]).id,
                                'currency_id': self.env['res.currency'].search(
                                    [('name', '=', res['response']['currency_id'])]).id,
                                'delivery_nta_price': res['response']['delivery_nta_price'],
                                'description': res['response']['description'],
                                'duration': res['response']['duration'],
                                'entry_type': res['response']['entry_type'],
                                'immigration_consulate': res['response']['immigration_consulate'],
                                'name': res['response']['name'],
                                'notes': res['response']['notes'],
                                'nta_price': res['response']['nta_price'],
                                'other_additional_price': res['response']['other_additional_price'],
                                'pax_type': res['response']['pax_type'],
                                'process_type': res['response']['process_type'],
                                'reference_code': res['response']['reference_code'] + '_rdx',
                                'provider_id': self.env['tt.provider'].search([('code', '=', res['response']['provider_id'])]).id,
                                'sale_price': res['response']['sale_price'],
                                'visa_nta_price': res['response']['visa_nta_price'],
                                'visa_type': res['response']['visa_type'],
                                'active': True
                            })
                            master_data.requirement_ids.unlink()
                            master_data.attachments_ids.unlink()
                            master_data.visa_location_ids.unlink()
                        else:
                            master_data = self.env['tt.reservation.visa.pricelist'].create({
                                'commercial_duration': res['response']['commercial_duration'],
                                'commission_price': res['response']['commission_price'],
                                'cost_price': res['response']['cost_price'],
                                'country_id': self.env['res.country'].search(
                                    [('name', '=', res['response']['country_id'])]).id,
                                'currency_id': self.env['res.currency'].search(
                                    [('name', '=', res['response']['currency_id'])]).id,
                                'delivery_nta_price': res['response']['delivery_nta_price'],
                                'description': res['response']['description'],
                                'duration': res['response']['duration'],
                                'entry_type': res['response']['entry_type'],
                                'immigration_consulate': res['response']['immigration_consulate'],
                                'name': res['response']['name'],
                                'notes': res['response']['notes'],
                                'nta_price': res['response']['nta_price'],
                                'other_additional_price': res['response']['other_additional_price'],
                                'pax_type': res['response']['pax_type'],
                                'process_type': res['response']['process_type'],
                                'reference_code': res['response']['reference_code'] + '_rdx',
                                'provider_id': self.env['tt.provider'].search([('code', '=', res['response']['provider_id'])]).id,
                                'sale_price': res['response']['sale_price'],
                                'visa_nta_price': res['response']['visa_nta_price'],
                                'visa_type': res['response']['visa_type'],
                                'active': True
                            })
                        for data in res['response']['requirement_ids']:

                            self.env['tt.reservation.visa.requirements'].create({
                                'pricelist_id': master_data.id,
                                'name': data['name'],
                                'reference_code': data['reference_code'] + '_rdx',
                                'type_id': self.env['tt.traveldoc.type'].create(data['type_id']).id
                            })
                        upload = self.env['tt.upload.center.wizard']
                        co_agent_id = self.env.user.agent_id.id
                        co_uid = self.env.user.id
                        context = {
                            'co_agent_id': co_agent_id,
                            'co_uid': co_uid
                        }
                        attachments = []
                        for data in res['response']['attachments_ids']:
                            data['file'] = self.url_to_base64(data['url'])
                            # data['filename'], data['file_reference'], data['file']
                            # KASIH TRY EXCEPT
                            upload = upload.upload_file_api(data, context)
                            attachments.append(self.env['tt.upload.center'].search([('seq_id', '=', upload['response']['seq_id'])],limit=1).id)
                        #     pass
                        #     #tt upload center
                        #     self.env['tt.upload.center'].create({
                        #         'pricelist_id': master_data.id,
                        #     })
                        if attachments:
                            master_data.update({
                                'attachments_ids': [(6, 0, attachments)]
                            })
                        for data in res['response']['visa_location_ids']:
                            self.env['tt.master.visa.locations'].create({
                                'pricelist_id': master_data.id,
                                'name': data['name'],
                                'location_type': data['location_type'],
                                'address': data['address'],
                                'city': data['city']
                            })
                    else:
                        _logger.error('error sync data' + json.dumps(rec))
                    pass

    def url_to_base64(self, url):
        return base64.b64encode(requests.get(url).content)


class VisaPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.visa.pricelist'
    _description = 'Reservation Visa Pricelist'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_visa.tt_provider_type_visa').id
        return [('provider_type_id.id', '=', int(domain_id))]

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type', default='ADT', required=True)
    entry_type = fields.Selection(ENTRY_TYPE, 'Entry Type')
    visa_type = fields.Selection(VISA_TYPE, 'Visa Type')
    process_type = fields.Selection(PROCESS_TYPE, 'Process Type')

    reference_code = fields.Char('Reference Code', required=False, copy=False)
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain)
    active = fields.Boolean('Active', default=True)

    country_id = fields.Many2one('res.country', 'Country')
    immigration_consulate = fields.Char('Immigration Consulate')
    notes = fields.Html('Notes')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    visa_nta_price = fields.Monetary('Visa NTA Price', default=0)
    delivery_nta_price = fields.Monetary('Delivery NTA Price', default=0)
    other_additional_price = fields.Monetary('Other Price', default=0)

    nta_price = fields.Monetary('NTA Price', default=0, compute="_compute_nta_price", store=True)
    cost_price = fields.Monetary('Cost Price', default=0)
    sale_price = fields.Monetary('Sale Price', default=0)
    commission_price = fields.Monetary('Commission Price', store=True, readonly=1, compute="_compute_commission_price")

    requirement_ids = fields.One2many('tt.reservation.visa.requirements', 'pricelist_id', 'Requirements', copy=True)

    attachments_ids = fields.Many2many('tt.upload.center', 'visa_pricelist_attachment_rel', 'visa_pricelist_id',
                                       'attachment_id', string='Attachments')

    visa_location_ids = fields.Many2many('tt.master.visa.locations', 'tt_master_visa_locations_rel',
                                         'master_visa_location_id', 'pricelist_id', 'Visa Locations')

    duration = fields.Integer('Duration (day(s))', help="in day(s)", required=True, default=1)
    commercial_duration = fields.Char('Duration', compute='_compute_duration', readonly=1)

    ho_ids = fields.Many2many('tt.agent', 'tt_master_visa_ho_agent_rel', 'visa_id', 'ho_id', string='Allowed Head Office(s)', domain=[('is_ho_agent', '=', True)])

    owner_ho_id = fields.Many2one('tt.agent', 'Owner Head Office', domain=[('is_ho_agent', '=', True)],default=lambda self: self.env.user.ho_id)

    @api.multi
    @api.depends('cost_price', 'sale_price')
    @api.onchange('cost_price', 'sale_price')
    def _compute_commission_price(self):
        for rec in self:
            rec.commission_price = rec.sale_price - rec.cost_price

    @api.multi
    @api.depends('visa_nta_price', 'delivery_nta_price', 'other_additional_price')
    @api.onchange('visa_nta_price', 'delivery_nta_price', 'other_additional_price')
    def _compute_nta_price(self):
        for rec in self:
            rec.nta_price = rec.visa_nta_price + rec.delivery_nta_price + rec.other_additional_price

    @api.multi
    @api.onchange('duration')
    def _compute_duration(self):
        for rec in self:
            rec.commercial_duration = '%s day(s)' % str(rec.duration)

    @api.model
    def create(self, values):
        if values.get('reference_code'):
            if self.search([('reference_code','=',values['reference_code'])]):
                raise UserError(_('Duplicate reference code, please change or leave blank and update use compute reference code!'))
        values.update({
            "owner_ho_id": self.env.user.agent_id.ho_id.id,
            "ho_ids": [(4, self.env.user.agent_id.ho_id.id)]
        })
        if not values.get('reference_code') and values.get('provider_id'):
            provider_obj = self.env['tt.provider'].browse(values['provider_id'])
            values.update({
                "reference_code": "%s_%s_%s" % (provider_obj.code, values['name'], str(len(self.search([]))))
            })
        res = super(VisaPricelist, self).create(values)
        return res

    @api.multi
    def write(self, values):
        admin_obj_id = self.env.ref('base.user_admin').id
        root_obj_id = self.env.ref('base.user_root').id
        if not self.env.user.has_group('base.group_erp_manager') and not self.env.user.id in [admin_obj_id, root_obj_id] and self.env.user.ho_id.id != self.owner_ho_id.id:
            raise UserError('You do not have permission to edit this record.')
        if values.get('reference_code'):
            if self.search([('reference_code','=',values['reference_code']),('id','not in',self.ids)]):
                raise UserError(_('Duplicate reference code, please change or leave blank and update use compute reference code!'))
        return super(VisaPricelist, self).write(values)

    # @api.onchange('reference_code')
    # def _compute_duration(self):
    #     if self.reference_code:
    #         if self.search(['reference_code','=',self.reference_code]):
    #             raise UserError(_('Duplicate reference code, please change or leave blank and update use compute reference code!'))

    def get_config_api(self, context):
        try:
            visa = {}
            for rec in self.sudo().search([('ho_ids.seq_id','=',context['co_ho_seq_id']), ('active','=',True)]):
                if not visa.get(rec.country_id.name): #kalau ngga ada bikin dict
                    visa[rec.country_id.name] = [] #append country
                count = 0
                for rec1 in visa[rec.country_id.name]:
                    if rec1 == rec.immigration_consulate:
                        count = 1
                if count == 0:
                    visa[rec.country_id.name].append(rec.immigration_consulate)

                # for rec1 in self.search([('name', '=ilike', rec.country_id.id)]):
                #
                # pass
            response = visa
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def get_inventory_api(self):
        try:
            res = []
            for idx, rec in enumerate(self.sudo().search([('provider_id.code','=', 'visa_internal'), ('active','=', True)])):
                res.append(rec.reference_code)
            res = Response().get_no_error(res)
        except Exception as e:
            _logger.error("%s, %s" % (str(e),traceback.format_exc()))
            return ERR.get_error(500)
        return res

    def to_dict(self):
        attachement_ids = []
        requirement_ids = []
        visa_location_ids = []
        for data in self.attachments_ids:
            attachement_ids.append({
                'file_reference': data.file_reference,
                'filename': data.filename,
                'name': data.name,
                'url': data.url
            })
        for data in self.requirement_ids:
            requirement_ids.append({
                'name': data.name,
                'type_id': {
                    'description': data.type_id.description,
                    'name': data.type_id.name
                },
                'reference_code': data.reference_code
            })

        for data in self.visa_location_ids:
            visa_location_ids.append({
                'name': data.name,
                'location_type': data.location_type,
                'address': data.address,
                'city': data.city,
            })

        return {
            'attachments_ids': attachement_ids,
            'requirement_ids': requirement_ids,
            'visa_location_ids': visa_location_ids,
            'commercial_duration': self.commercial_duration,
            'commission_price': self.commission_price,
            'cost_price': self.cost_price,
            'country_id': self.country_id.name,
            'currency_id': self.currency_id.name,
            'delivery_nta_price': self.delivery_nta_price,
            'description': self.description,
            'duration': self.duration,
            'entry_type': self.entry_type,
            'immigration_consulate': self.immigration_consulate,
            'name': self.name,
            'notes': self.notes,
            'nta_price': self.nta_price,
            'pax_type': self.pax_type,
            'process_type': self.process_type,
            'reference_code': self.reference_code,
            'provider_id': self.provider_id.code,
            'sale_price': self.sale_price,
            'visa_nta_price': self.visa_nta_price,
            'visa_type': self.visa_type,
            'other_additional_price': self.other_additional_price
        }

    def get_product_detail_api(self,data):
        try:
            res = []
            res = self.sudo().search([('reference_code', '=', data['code'])], limit=1).to_dict()
            if res:
                res = Response().get_no_error(res)
            else:
                res = Response().get_error(str("Data Doesn't exist!"), 500)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def search_api(self, data, context):
        try:
            list_of_visa = []
            search_params = [('active','=',True), ('country_id.name', '=ilike', data['destination']), ('immigration_consulate', '=ilike', data['consulate']), ('reference_code','!=','')]
            if context.get('co_ho_id'):
                search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
            elif context.get('ho_seq_id'):
                ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['ho_seq_id'])], limit=1)
                search_params += ['|', '|', ('owner_ho_id', '=', int(ho_obj[0].id)), ('ho_ids', '=', int(ho_obj[0].id)), ('ho_ids', '=', False)]
            elif context.get('co_ho_seq_id'):
                ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['co_ho_seq_id'])], limit=1)
                search_params += ['|', '|', ('owner_ho_id', '=', int(ho_obj[0].id)), ('ho_ids', '=', int(ho_obj[0].id)), ('ho_ids', '=', False)]
            else:
                search_params.append(('ho_ids', '=', False))
            for idx, rec in enumerate(self.sudo().search(search_params)): #agar kalau duplicate reference kosong tidak tampil (harus diisi manual / compute reference code)
                requirement = []
                attachments = []
                for rec1 in rec.requirement_ids:
                    requirement.append({
                        'name': rec1.type_id.name,
                        'description': rec1.type_id.description,
                        'required': rec1.required,
                        'id': rec1.reference_code
                    })
                for attach in rec.attachments_ids:
                    attachments.append({
                        'name': attach.file_reference,
                        'url': attach.url,
                    })
                visa_vals = {
                    'sequence': idx,
                    'name': rec.name,
                    'pax_type': rec.pax_type,
                    'entry_type': rec.entry_type,
                    'visa_type': rec.visa_type,
                    'type': {
                        'process_type': rec.process_type,
                        'duration': rec.duration
                    },
                    'consulate': {
                        'city': rec.immigration_consulate,
                        'address': rec.description
                    },
                    'requirements': requirement,
                    'attachments': attachments,
                    'sale_price': {
                        'commission': rec.commission_price,
                        'total_price': rec.sale_price,
                        'currency': rec.currency_id.name
                    },
                    'id': rec.reference_code,
                    'provider': rec.provider_id.code
                }
                if rec.notes:
                    notes_html = BeautifulSoup(rec.notes, features="lxml")
                    notes_html = notes_html.prettify()
                    notes_text = html2text.html2text(notes_html)
                    notes_text2 = notes_text.split('\n')
                    visa_vals.update({
                        'notes': notes_text2
                    })
                else:
                    visa_vals.update({
                        'notes': []
                    })
                list_of_visa.append(visa_vals)
            response = {
                'country': data['destination'],
                'list_of_visa': list_of_visa
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def availability_api(self, data, context):
        try:
            list_of_availability = []
            for idx, rec in enumerate(data['reference_code']):
                search_params = [('reference_code', '=', rec)]
                if context.get('co_ho_id'):
                    search_params += ['|', '|', ('owner_ho_id', '=', int(context['co_ho_id'])), ('ho_ids', '=', int(context['co_ho_id'])), ('ho_ids', '=', False)]
                elif context.get('ho_seq_id'):
                    ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['ho_seq_id'])], limit=1)
                    search_params += ['|', '|', ('owner_ho_id', '=', int(ho_obj[0].id)), ('ho_ids', '=', int(ho_obj[0].id)), ('ho_ids', '=', False)]
                elif context.get('co_ho_seq_id'):
                    ho_obj = self.env['tt.agent'].search([('seq_id', '=', context['co_ho_seq_id'])], limit=1)
                    search_params += ['|', '|', ('owner_ho_id', '=', int(ho_obj[0].id)), ('ho_ids', '=', int(ho_obj[0].id)), ('ho_ids', '=', False)]
                else:
                    search_params.append(('ho_ids', '=', False))
                if self.sudo().search(search_params):
                    list_of_availability.append(True)
                else:
                    list_of_availability.append(False)
            response = {
                'availability': list_of_availability,
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res
