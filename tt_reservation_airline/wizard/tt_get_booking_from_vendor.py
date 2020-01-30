from odoo import api, fields, models, _

class TtBookingFromVendor(models.TransientModel):
    _name = "tt.booking.from.vendor"
    _description = "Booking from Vendor"

    pnr = fields.Char('PNR', required=True)
    provider = fields.Selection([
        # ('sabre', 'Sabre'),
        ('amadeus', 'Amadeus'),
        # ('altea', 'Garuda Altea'),
        # ('lionair', 'Lion Air'),
    ], string='Provider', required=True)

    parent_agent_id = fields.Many2one('res.partner', 'Parent Agent', readonly=True, compute='_compute_parent_agent_id')
    agent_id = fields.Many2one('res.partner', 'Agent', required=True, domain="[('is_agent', '=', True)]")
    sub_agent_id = fields.Many2one('res.partner', 'Sub Agent', readonly=True, compute='_compute_sub_agent_id')
    user_id = fields.Many2one('res.users', 'User', required=True)

    is_database_contact = fields.Boolean('Is Database Contact', default=True)
    contact_id = fields.Many2one('tt.customer.details', 'Contact/Booker')
    contact_title = fields.Selection([('MR', 'Mr.'), ('MSTR', 'Mstr.'), ('MRS', 'Mrs.'), ('MS', 'Ms.'), ('MISS', 'Miss')], string='Title')
    contact_first_name = fields.Char('First Name')
    contact_last_name = fields.Char('Last Name')
    contact_mobile = fields.Char('Mobile')
    contact_email = fields.Char('Email')