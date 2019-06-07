from odoo import models, fields, api, _

STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Request'),
    ('valid', 'Validated'),
    ('final', 'Finalization'),
    ('done', 'Done'),
    ('cancel', 'Cancelled')
]

TRANSACTION_TYPE = [
    ('airline', 'Airline'),
    ('train', 'Train'),
    ('ship', 'Ship'),
    # ('visa', 'Visa'),
    ('cruise', 'Cruise'),
    ('car', 'Car/Rent'),
    ('bus', 'Bus'),
    ('tour', 'Tours'),
    ('merchant', 'Merchandise'),
    ('others', 'Other(s)'),
    # ('passport', 'Passport'),
    ('activity', 'Activity'),
    ('travel_doc', 'Travel Doc.'),
    ('hotel', 'Hotel')
]

CLASS_OF_SERVICE = [
    ('eco', 'Economy'),
    ('pre', 'Premium Economy'),
    ('bus', 'Bussiness')
]


class IssuedOfflineLines(models.Model):
    _name = 'issued.offline.lines'

    iss_off_id = fields.Many2one('issued.offline', 'Issued Offline')
    obj_qty = fields.Integer('Qty', readonly=True, states={'draft': [('readonly', False)]}, default=1)
    state = fields.Selection(STATE, string='State', default='draft', related='iss_off_id.state')
    transaction_type = fields.Selection(TRANSACTION_TYPE, 'Service Type', related='iss_off_id.type')

    # Airplane / Train
    departure_date = fields.Datetime('Departure Date', readonly=True, states={'draft': [('readonly', False)]})
    return_date = fields.Datetime('Return Date', readonly=True, states={'draft': [('readonly', False)]})
    origin_id = fields.Many2one('tt.destinations', 'Origin', readonly=True, states={'draft': [('readonly', False)]})
    destination_id = fields.Many2one('tt.destinations', 'Destination', readonly=True,
                                     states={'draft': [('readonly', False)]})
    carrier_code = fields.Char('Carrier Code', help='or Flight Code', index=True)
    carrier_number = fields.Char('Carrier Number', help='or Flight Number', index=True)
    class_of_service = fields.Selection(CLASS_OF_SERVICE, 'Class')
    subclass = fields.Char('SubClass')

    # Hotel / Activity
    check_in = fields.Date('Check In', readonly=True, states={'draft': [('readonly', False)]})
    check_out = fields.Date('Check Out', readonly=True, states={'draft': [('readonly', False)]})
    obj_name = fields.Char('Name', related='iss_off_id.provider', store=True)
    obj_subname = fields.Char('Room/Package', readonly=True, states={'draft': [('readonly', False)]})

    description = fields.Text('Description')

    # doc_type = fields.Selection([('visa', 'Visa'), ('pass', 'Passport')], default='visa')

    # # Visa
    # country_id = fields.Many2one('res.country', 'Destination')
    # city = fields.Char('Consulate')
    # pax_type = fields.Selection([('ADT', 'Adult'), ('CHD', 'Child'), ('INF', 'Infant')], default='ADT')
    # entry_type = fields.Selection([('single', 'Single'), ('double', 'Double'), ('multiple', 'Multiple')], 'Entry Type')
    # visa_type = fields.Selection([('tourist', 'Tourist'), ('business', 'Business'), ('student', 'Student')],
    #                              'Visa Type')
    # process_type = fields.Selection([('regular', 'Regular'), ('kilat', 'Kilat'), ('super', 'Super Kilat')],
    #                                 'Process Type')
    # # Passport
    # passport_type = fields.Selection([('passport', 'Passport'), ('e-passport', 'E-Passport')], 'Passport Type')
    # apply_type = fields.Selection([('new', 'New'), ('renew', 'Renew'), ('umroh', 'Umroh'), ('add_name', 'Add Name')],
    #                               'Apply Type')
    # description = fields.Text('Description')