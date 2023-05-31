from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...tools.api import Response
import html2text
import json,traceback,logging
from ...tools import util,variables,ERR
from bs4 import BeautifulSoup
import base64
import requests
import os

_logger = logging.getLogger(__name__)

PASSPORT_TYPE = [
    ('passport', 'Passport'),
    ('e-passport', 'E-Passport')
]

APPLY_TYPE = [
    ('new', 'New'),
    ('renew', 'Renew'),
    ('umroh', 'Umroh'),
    ('add_name', 'Add Name')
]

PROCESS_TYPE = [
    ('regular', 'Regular'),
    ('express', 'Express'),
    ('super', 'Super Express')
]

class PassportSyncProducts(models.TransientModel):
    _name = "passport.sync.product.wizard"
    _description = 'Passport Sync Product Wizard'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_passport.tt_provider_type_passport').id
        return [('provider_type_id.id', '=', int(domain_id))]

    def update_reference_code_internal(self):
        for idx, rec in enumerate(self.env['tt.reservation.passport.pricelist'].search([]), 1):
            if rec.provider_id == '':
                rec.reference_code = ''
                rec.provider_id = self.env['tt.provider'].search([('code', '=', 'passport_internal')], limit=1).id

    def get_reference_code(self):
        for idx, rec in enumerate(self.env['tt.reservation.passport.pricelist'].search([]),1):
            if rec.reference_code == '' or rec.reference_code == False:
                if rec.provider_id.code:
                    counter = idx
                    while True:
                        if not self.env['tt.reservation.passport.pricelist'].search([('reference_code', '=', rec.provider_id.code + rec.name + '_' + str(counter))]):
                            rec.update({
                                "reference_code": rec.provider_id.code + '_' + rec.name + '_' + str(counter),
                                "provider_id": self.env['tt.provider'].search([('code', '=', rec.provider_id.code)], limit=1).id
                            })
                            break
                        counter += 1
                else:
                    raise UserError(
                        _('You have to fill Provider ID in all Passport Pricelist.'))

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
            'provider': 'rodextrip_passport'
        }
        ## tambah context
        res = self.env['tt.passport.api.con'].get_product_vendor(req)
        if res['error_code'] == 0:
            folder_path = '/var/log/tour_travel/rodextrip_passport_master_data'
            if not os.path.exists(folder_path):
                os.mkdir(folder_path)
            file = open('/var/log/tour_travel/rodextrip_passport_master_data/rodextrip_passport_master_data.json', 'w')
            file.write(json.dumps(res['response']))
            file.close()
        else:
            #raise sini
            pass

    def actions_sync_product_rodextrip(self, data):
        provider = 'rodextrip_passport'
        list_product = self.env['tt.reservation.passport.pricelist'].search([('provider_id', '=', self.env['tt.provider'].search([('code', '=', 'rodextrip_passport')], limit=1).id)])
        for rec in list_product:
            rec.active = False
        file = []
        file_dat = open('/var/log/tour_travel/rodextrip_passport_master_data/rodextrip_passport_master_data.json','r')
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
                product_obj = self.env['tt.reservation.passport.pricelist'].search([('reference_code', '=', rec)], limit=1)
                product_obj = product_obj and product_obj[0] or False
                temp = []
                if provider == 'rodextrip_passport':
                    if product_obj:
                        product_obj.active = False
                    req = {
                        'provider': provider,
                        'code': rec
                    }
                    ## tambah context
                    res = self.env['tt.passport.api.con'].get_product_detail_vendor(req)
                    #create object
                    if res['error_code'] == 0:
                        master_data = self.env['tt.reservation.passport.pricelist'].search([('reference_code','=',res['response']['reference_code'] + '_rdx')], limit=1)
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
                                'apply_type': res['response']['apply_type'],
                                'immigration_consulate': res['response']['immigration_consulate'],
                                'name': res['response']['name'],
                                'notes': res['response']['notes'],
                                'process_type': res['response']['process_type'],
                                'nta_price': res['response']['nta_price'],
                                'passport_type': res['response']['passport_type'],
                                'reference_code': res['response']['reference_code'] + '_rdx',
                                'provider_id': self.env['tt.provider'].search([('code', '=', res['response']['provider_id'])]).id,
                                'sale_price': res['response']['sale_price'],
                                'passport_nta_price': res['response']['passport_nta_price'],
                                'active': True
                            })
                            master_data.requirement_ids.unlink()
                            master_data.attachments_ids.unlink()
                        else:
                            master_data = self.env['tt.reservation.passport.pricelist'].create({
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
                                'apply_type': res['response']['apply_type'],
                                'immigration_consulate': res['response']['immigration_consulate'],
                                'name': res['response']['name'],
                                'notes': res['response']['notes'],
                                'process_type': res['response']['process_type'],
                                'nta_price': res['response']['nta_price'],
                                'passport_type': res['response']['passport_type'],
                                'reference_code': res['response']['reference_code'] + '_rdx',
                                'provider_id': self.env['tt.provider'].search([('code', '=', res['response']['provider_id'])]).id,
                                'sale_price': res['response']['sale_price'],
                                'passport_nta_price': res['response']['passport_nta_price'],
                                'active': True
                            })
                        for data in res['response']['requirement_ids']:

                            self.env['tt.reservation.passport.requirements'].create({
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
                    else:
                        _logger.error('error sync data' + rec)
                    pass

    def url_to_base64(self, url):
        return base64.b64encode(requests.get(url).content)

class PassportPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.passport.pricelist'
    _description = 'Reservation Passport Pricelist'

    def get_domain(self):
        domain_id = self.env.ref('tt_reservation_passport.tt_provider_type_passport').id
        return [('provider_type_id.id', '=', int(domain_id))]

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    passport_type = fields.Selection(PASSPORT_TYPE, 'Passport Type')
    apply_type = fields.Selection(APPLY_TYPE, 'Apply Type')
    process_type = fields.Selection(PROCESS_TYPE, 'Process Type')

    reference_code = fields.Char('Reference Code', required=False)
    provider_id = fields.Many2one('tt.provider', 'Provider', domain=get_domain)
    active = fields.Boolean('Active', default=True)

    country_id = fields.Many2one('res.country', 'Country')
    immigration_consulate = fields.Char('Immigration Consulate')
    notes = fields.Html('Notes')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    passport_nta_price = fields.Monetary('Passport NTA Price', default=0)
    delivery_nta_price = fields.Monetary('Delivery NTA Price', default=0)

    nta_price = fields.Monetary('NTA Price', default=0, compute="_compute_nta_price", store=True)
    cost_price = fields.Monetary('Cost Price', default=0)
    sale_price = fields.Monetary('Sale Price', default=0)
    commission_price = fields.Monetary('Commission Price', store=True, readonly=1, compute="_compute_commission_price")

    requirement_ids = fields.One2many('tt.reservation.passport.requirements', 'pricelist_id', 'Requirements')

    attachments_ids = fields.Many2many('tt.upload.center', 'passport_pricelist_attachment_rel', 'passport_pricelist_id',
                                       'attachment_id', string='Attachments')

    duration = fields.Integer('Duration (day(s))', help="in day(s)", required=True, default=1)
    commercial_duration = fields.Char('Duration', compute='_compute_duration', readonly=1)

    ho_id = fields.Many2one('tt.agent', 'Head Office', domain=[('is_ho_agent', '=', True)])

    @api.multi
    @api.depends('cost_price', 'sale_price')
    @api.onchange('cost_price', 'sale_price')
    def _compute_commission_price(self):
        for rec in self:
            rec.commission_price = rec.sale_price - rec.cost_price

    @api.multi
    @api.depends('passport_nta_price', 'delivery_nta_price')
    @api.onchange('passport_nta_price', 'delivery_nta_price')
    def _compute_nta_price(self):
        for rec in self:
            rec.nta_price = rec.passport_nta_price + rec.delivery_nta_price

    @api.multi
    @api.onchange('duration')
    def _compute_duration(self):
        for rec in self:
            rec.commercial_duration = '%s day(s)' % str(rec.duration)

    # untuk search di halaman home
    def get_config_api(self):
        try:
            passport = {}
            passport_type_list = PASSPORT_TYPE
            apply_type_list = APPLY_TYPE
            immigration_consulate_list = []
            for rec in self.sudo().search([]):
                if rec.immigration_consulate not in immigration_consulate_list:
                    immigration_consulate_list.append(rec.immigration_consulate)

            passport.update({
                'passport_type_list': passport_type_list,
                'apply_type_list': apply_type_list,
                'immigration_consulate_list': immigration_consulate_list
            })
            response = passport
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def search_api(self, data):
        try:
            list_of_passport = []

            for idx, rec in enumerate(self.sudo().search([('immigration_consulate', '=ilike', data['immigration_consulate']),
                                                          ('passport_type', '=ilike', data['passport_type']),
                                                          ('apply_type', '=ilike', data['apply_type'])])):
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
                passport_vals = {
                    'sequence': idx,
                    'name': rec.name,
                    'apply_type': dict(APPLY_TYPE)[rec.apply_type],
                    'type': {
                        'process_type': dict(PROCESS_TYPE)[rec.process_type],
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
                    passport_vals.update({
                        'notes': notes_text2
                    })
                else:
                    passport_vals.update({
                        'notes': []
                    })
                list_of_passport.append(passport_vals)
            response = {
                'list_of_passport': list_of_passport
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def availability_api(self, data):
        try:
            list_of_availability = []
            for idx, rec in enumerate(data['reference_code']):
                if self.sudo().search([('reference_code', '=', rec)]):
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

    def get_inventory_api(self):
        try:
            res = []
            for idx, rec in enumerate(self.sudo().search([])):
                res.append(rec.reference_code)
            res = Response().get_no_error(res)
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
        return res

    def to_dict(self):
        attachement_ids = []
        requirement_ids = []
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

        return {
            'attachments_ids': attachement_ids,
            'requirement_ids': requirement_ids,
            'commercial_duration': self.commercial_duration,
            'commission_price': self.commission_price,
            'process_type': self.process_type,
            'cost_price': self.cost_price,
            'country_id': self.country_id.name,
            'currency_id': self.currency_id.name,
            'delivery_nta_price': self.delivery_nta_price,
            'description': self.description,
            'duration': self.duration,
            'apply_type': self.apply_type,
            'immigration_consulate': self.immigration_consulate,
            'name': self.name,
            'notes': self.notes,
            'nta_price': self.nta_price,
            'passport_type': self.passport_type,
            'reference_code': self.reference_code,
            'provider_id': self.provider_id.code,
            'sale_price': self.sale_price,
            'passport_nta_price': self.passport_nta_price,
        }

    def get_product_detail_api(self,data):
        try:
            res = []
            res = self.sudo().search([('reference_code', '=', data['code'])], limit=1).to_dict()
            if res:
                res = Response().get_no_error(res)
            else:
                res = Response().get_error(str("Data Doesn't exist!"), 500)
            return res
        except Exception as e:
            _logger.error(traceback.format_exc())
            return ERR.get_error(500)
