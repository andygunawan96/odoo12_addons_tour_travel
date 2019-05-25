from odoo import api, fields, models, _

TITLE = [
    ('mr', 'Mr.'),
    ('mrs', 'Mrs.'),
    ('ms', 'Ms.'),
    ('miss', 'Miss.'),
    ('mstr', 'Mstr.'),
]

PAX_TYPE = [
    ('infant', 'Infant'),
    ('child', 'Child'),
    ('adult', 'Adult'),
    ('elder', 'Elder'),
]


class TtReservationCustomer(models.Model):
    _name = 'tt.reservation.customer'

    resv_id = fields.Many2one('tt.reservation', 'Reservation ID')  # Many2One -> tt.reservation
    customer_id = fields.Many2one('tt.customer', 'Customer')
    title = fields.Selection(TITLE, 'Title')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    date_of_birth = fields.Datetime('Date of Birth')
    age = fields.Char('Age')
    passport_number = fields.Char('Passport Number')
    passport_expdate = fields.Datetime('Passport Exp. Date')
    nationality_id = fields.Many2one('res.country', 'Nationality')
    country_of_issued_id = fields.Many2one('res.country', 'Country of Issued')
    pax_type = fields.Selection(PAX_TYPE, 'Pax Type')
