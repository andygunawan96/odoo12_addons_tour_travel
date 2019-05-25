from odoo import api, fields, models, _

RESV_TYPE = [
    ('reservation.train','Reservation Train'),
    ('reservation.hotel','Reservation Hotel')
]

class Orang(models.Model):
    _name = "orang.orang"
    _description = "data orang"
    _inherit = "mail.thread"

    name = fields.Char('Name', required=True)
    age = fields.Integer("Age", required=True)
    gender = fields.Selection([
        ('', ''),
        ('m', 'Males'),
        ('f', 'Females'),
    ], required=True, default='')
    note = fields.Text(string='Note')
    country_id = fields.Many2one('res.country', 'Country')
    address_ids = fields.One2many('orang.address', 'orang_id', 'Address')
    country_state_id = fields.Many2one('res.country.state', 'State')
    pet_ids = fields.One2many('testing.animal', 'owner_id', 'Pets')
    invoice_line_ids = fields.One2many('invoice.line', 'invoice_id', 'Reservations')



class OrangAdress(models.Model):
    _name = "orang.address"
    _description = ""

    orang_id = fields.Many2one('orang.orang', 'Orang')
    city_id = fields.Many2one('res.city', 'City')
    address = fields.Char('Address')
