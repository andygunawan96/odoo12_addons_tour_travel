from odoo import api, fields, models, _
from datetime import datetime


class VisaOrderRequirements(models.Model):
    _name = 'tt.reservation.visa.order.requirements'
    _description = 'Reservation Visa Order Requirements'

    requirement_id = fields.Many2one('tt.reservation.visa.requirements', 'Requirement', readonly=1)
    to_passenger_id = fields.Many2one('tt.reservation.visa.order.passengers', 'Passenger', readonly=1)
    passenger_state = fields.Selection('Passenger State', related='to_passenger_id.state')
    is_ori = fields.Boolean('Original', default=False)
    is_copy = fields.Boolean('Copy', default=False)
    notes = fields.Text('Notes')
    check_uid = fields.Many2one('res.users', 'Check By')
    check_date = fields.Datetime('Check Date')
    # is_ori_HO = fields.Boolean('Original HO', default=False)
    # is_copy_HO = fields.Boolean('Copy HO', default=False)
    validate_HO = fields.Boolean('Validate HO')
    check_uid_HO = fields.Many2one('res.users', 'Check By HO')
    check_date_HO = fields.Datetime('Check Date HO')
    is_checked_by_agent = fields.Boolean('Agent Checked', default=False)
    is_checked_by_HO = fields.Boolean('HO Checked', default=False)

    @api.onchange('is_ori', 'is_copy')
    def _document_check_by(self):
        for rec in self:
            if rec.is_ori or rec.is_copy:
                rec.check_uid = self.env.user.id
                rec.check_date = datetime.now()
            elif not rec.is_ori or not rec.is_copy:
                rec.check_uid = False
                rec.check_date = False

    @api.onchange('validate_HO')
    def _document_validate_by_HO(self):
        for rec in self:
            if rec.validate_HO:
                rec.check_uid_HO = self.env.user.id
                rec.check_date_HO = datetime.now()
            elif not rec.validate_HO:
                rec.check_uid_HO = False
                rec.check_date_HO = False
