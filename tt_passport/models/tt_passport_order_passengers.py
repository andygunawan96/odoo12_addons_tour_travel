from odoo import models, fields, api


class PassportOrderPassengers(models.Model):
    _name = 'tt.passport.order.passengers'
    _description = 'Tour & Travel - Passport Order Passengers'

    name = fields.Char('Name', related='passenger_id.first_name', readonly=1)
    # to_requirement_ids = fields.Char('')
    passport_id = fields.Many2one('tt.passport', 'Passport', readonly=1)
    passenger_id = fields.Many2one('tt.customer', 'Passenger', readonly=1)
    pricelist_id = fields.Many2one('tt.passport.pricelist', 'Passport Pricelist', readonly=1)
    passenger_type = fields.Selection([('ADT', 'Adult'), ('CHD', 'Child'), ('INF', 'Infant')], 'Pax Type', readonly=1)
    passenger_domicile = fields.Char('Domicile', related='passenger_id.domicile', readonly=1)
    process_status = fields.Selection([('accepted', 'Accepted'), ('rejected', 'Rejected')], string='Process Result',
                                      readonly=1)

    in_process_date = fields.Datetime('In Process Date', readonly=1)
    payment_date = fields.Datetime('Payment Date', readonly=1)
    payment_uid = fields.Many2one('res.users', 'Payment By', readonly=1)
    call_date = fields.Datetime('Call Date', help='Call to interview (visa) or take a photo (passport)')
    out_process_date = fields.Datetime('Out Process Date', readonly=1)
    to_HO_date = fields.Datetime('Send to HO Date', readonly=1)
    to_agent_date = fields.Datetime('Send to Agent Date', readonly=1)
    ready_date = fields.Datetime('Ready Date', readonly=1)

    # use_vendor = fields.Boolean('Use Vendor', readonly=1, related='passport_id.use_vendor')
    notes = fields.Text('Notes (Agent to Customer)')
    notes_HO = fields.Text('Notes (HO to Agent)')

    booking_state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm to HO'), ('validate', 'Validated by HO'),
         ('to_vendor', 'Send to Vendor'), ('vendor_process', 'Proceed by Vendor'), ('cancel', 'Canceled'),
         ('in_process', 'In Process'),
         ('partial_proceed', 'Partial Proceed'), ('proceed', 'Proceed'), ('done', 'Done')], default='draft',
        string='Order State', readonly=1, related='passport_id.state_passport',
        help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                to_vendor = Documents sent to Vendor
                                                vendor_process = Documents proceed by Vendor
                                                in_process = Documents proceed at Consulat or Imigration
                                                to_HO = documents sent to HO
                                                waiting = Documents ready at HO
                                                done = Documents given to customer''')

    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('validate', 'Validated'), ('re_validate', 'Re-Validate'),
         ('re_confirm', 'Re-Confirm'), ('cancel', 'Canceled'), ('in_process', 'In Process'), ('add_payment', 'Payment'),
         ('confirm_payment', 'Confirmed Payment'), ('in_process2', 'Processed by Consulate/Immigration'),
         ('waiting', 'Waiting'),
         ('proceed', 'Proceed'), ('rejected', 'Rejected'), ('accepted', 'Accepted'), ('to_HO', 'To HO'),
         ('to_agent', 'To Agent'),
         ('ready', 'Ready'), ('done', 'Done')], default='draft',
        help='''draft = requested
                                                confirm = HO accepted
                                                validate = if all required documents submitted and documents in progress
                                                cancel = request cancelled
                                                in_process = before payment
                                                in_process2 = process by consulate/immigration
                                                waiting = waiting interview or photo
                                                proceed = Has Finished the requirements
                                                accepted = Accepted by the Consulat
                                                rejected = Rejected by the Consulat
                                                ready = ready to pickup by customer
                                                done = picked up by customer''')
