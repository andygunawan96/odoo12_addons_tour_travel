from odoo import api, fields, models


class ImageBanner(models.Model):
    _name = 'tt.image.banner'
    _description = 'Promotion Banner for web page (Promotion in Surabaya city, Promotion hotel JW Marriot)'

    name = fields.Char('Name', required=True)
    image_url = fields.Char('Image Url', default=True, help='Size 750px X 250px')
    redirect_url = fields.Char('Redirect Url')
    width = fields.Integer('Block Width', default=3, help='Range 1-12')
    height = fields.Integer('Block Height', default=2, help='Range 1-3')
    city_id = fields.Many2one('res.city', 'City')
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
