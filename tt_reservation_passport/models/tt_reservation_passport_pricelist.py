from odoo import api, fields, models, _
from ...tools.api import Response
import html2text
import json,traceback,logging
from bs4 import BeautifulSoup

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


class PassportPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.passport.pricelist'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    passport_type = fields.Selection(PASSPORT_TYPE, 'Passport Type')
    apply_type = fields.Selection(APPLY_TYPE, 'Apply Type')
    process_type = fields.Selection(PROCESS_TYPE, 'Process Type')

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
            print(response)
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res

    def search_api(self):
        data = {
            'passport_type': 'passport',
            'apply_type': 'new',
            'immigration_consulate': 'Surabaya',
            'departure_date': '03-03-2020'
        }
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
                        'id': rec1.id
                    })
                for attach in rec.attachments_ids:
                    attachments.append({
                        'name': attach.file_reference,
                        'url': attach.url,
                    })
                passport_vals = {
                    'sequence': idx,
                    'name': rec.name,
                    'apply_type': rec.apply_type,
                    'process_type': rec.process_type,
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
                    'id': rec.id
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
            print(list_of_passport)
            response = {
                'list_of_passport': list_of_passport
            }
            res = Response().get_no_error(response)
        except Exception as e:
            _logger.error(traceback.format_exc())
            res = Response().get_error(str(e), 500)
        return res
