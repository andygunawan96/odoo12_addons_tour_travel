from odoo import models, fields, api, _

LOCATION_TYPE = [
    ('interview', 'Interview'),
    ('biometrics', 'Biometrics')
]


class MasterVisaLocations(models.Model):
    _name = 'tt.master.visa.locations'
    _description = 'Tour & Travel - Visa Master Locations'

    name = fields.Char('Name')
    pricelist_ids = fields.Many2many('tt.reservation.visa.pricelist', 'tt_master_visa_locations_rel',
                                     'pricelist_id', 'master_visa_location_id', 'Visa Pricelist')  # readonly=1
    location_type = fields.Selection(LOCATION_TYPE, 'Type')
    address = fields.Char('Location Address')
    city = fields.Char('Location City')
