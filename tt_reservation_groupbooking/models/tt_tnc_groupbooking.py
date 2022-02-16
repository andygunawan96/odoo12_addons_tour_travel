from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math

class TermNConditions(models.Model):
    _name = 'tt.tnc.groupbooking'
    _description = 'Term & Conditions'

    name = fields.Char('Name', required=True)
    title = fields.Char('Title', required=True, help="""Header in frontend""")
    description_ids = fields.One2many('tt.tnc.description.groupbooking', 'tnc_id', string='Description')
    provider_type_id = fields.Many2one('tt.provider.type', 'Provider Type', required=True)
    carrier_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")], 'Product Access Type', default='all')
    carrier_ids = fields.Many2many('tt.transport.carrier', "tt_search_banner_carrier_rel", "search_banner_id","carrier_id", "Product", domain="[('provider_type_id', '=', provider_type_id)]")
    cabin_class_access_type = fields.Selection([("all", "ALL"), ("allow", "Allowed"), ("restrict", "Restricted")],'Cabin Class Access Type', default='all')
    cabin_class_ids = fields.Many2many('tt.master.cabin.class', "tt_tnc_cabin_class_rel", "tnc_id","cabin_class_id", "Cabin Class")
    active = fields.Boolean('Active', default=True)

    def to_dict(self):
        description = []
        for rec in self.description_ids:
            description.append(rec.to_dict())
        return{
            "name": self.title,
            "description": description
        }

class TermNConditionDescription(models.Model):
    _name = 'tt.tnc.description.groupbooking'
    _description = 'Term & Conditions Description'

    tnc_id = fields.Many2one('tt.tnc.groupbooking', 'Term n Conditions')
    description = fields.Char('Description', required=True)

    def to_dict(self):
        return self.description

