from odoo import api, fields, models, _
from ...tools.api import Response

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


class VisaPricelist(models.Model):
    _inherit = ['tt.history']
    _name = 'tt.reservation.visa.pricelist'
    _description = 'Rodex Model'

    name = fields.Char('Name', required=True, default='New')
    description = fields.Char('Description')
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type', default='ADT', required=True)
    entry_type = fields.Selection(ENTRY_TYPE, 'Entry Type')
    visa_type = fields.Selection(VISA_TYPE, 'Visa Type')
    process_type = fields.Selection(PROCESS_TYPE, 'Process Type')

    country_id = fields.Many2one('res.country', 'Country')
    immigration_consulate = fields.Char('Immigration Consulate')
    notes = fields.Html('Notes')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    nta_price = fields.Monetary('NTA Price', default=0)
    cost_price = fields.Monetary('Cost Price', default=0)
    sale_price = fields.Monetary('Sale Price', default=0)
    commission_price = fields.Monetary('Commission Price', store=True, readonly=1, compute="_compute_commission_price")

    requirement_ids = fields.One2many('tt.reservation.visa.requirements', 'pricelist_id', 'Requirements')

    attachments_ids = fields.Many2many('tt.upload.center', 'visa_pricelist_attachment_rel', 'visa_pricelist_id',
                                       'attachment_id', string='Attachments')

    visa_location_ids = fields.Many2many('tt.master.visa.locations', 'tt_master_visa_locations_rel',
                                         'master_visa_location_id', 'pricelist_id', 'Visa Locations')

    duration = fields.Integer('Duration (day(s))', help="in day(s)", required=True, default=1)
    commercial_duration = fields.Char('Duration', compute='_compute_duration', readonly=1)

    @api.multi
    @api.depends('cost_price', 'sale_price')
    @api.onchange('cost_price', 'sale_price')
    def _compute_commission_price(self):
        for rec in self:
            rec.commission_price = rec.sale_price - rec.cost_price

    @api.multi
    @api.onchange('duration')
    def _compute_duration(self):
        for rec in self:
            rec.commercial_duration = '%s day(s)' % str(rec.duration)

    def get_config_api(self):
        try:
            visa = {}
            for rec in self.sudo().search([]):
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
            res = Response().get_error(str(e), 500)
        return res

    def search_api(self, data):
        try:
            list_of_visa = []

            for idx, rec in enumerate(self.sudo().search([('country_id.name', '=ilike', data['destination']), ('immigration_consulate', '=ilike', data['consulate'])])):
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
                list_of_visa.append({
                    'sequence': idx,
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
                    'notes': rec.notes,
                    'id': rec.id
                })

                # for rec1 in self.search([('name', '=ilike', rec.country_id.id)]):
                #
                # pass
            response = {
                'country': data['destination'],
                'list_of_visa': list_of_visa
            }
            res = Response().get_no_error(response)
        except Exception as e:
            res = Response().get_error(str(e), 500)
        return res