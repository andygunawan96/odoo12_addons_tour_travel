from odoo import api,models,fields,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import base64
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback,pytz

_logger = logging.getLogger(__name__)


class TtReschedulePeriksainChanges(models.Model):
    _name = "tt.reschedule.periksain.changes"
    _inherit = "tt.reschedule.changes"
    _description = "After Sales Model"

    reschedule_id = fields.Many2one('tt.reschedule.periksain', 'After Sales', readonly=True)


class TtRescheduleLine(models.Model):
    _name = "tt.reschedule.periksain.line"
    _inherit = "tt.reschedule.line"
    _description = "After Sales Model"
    _order = 'id DESC'

    reschedule_id = fields.Many2one('tt.reschedule.periksain', 'After Sales', readonly=True)


class TtReschedulePeriksain(models.Model):
    _name = "tt.reschedule.periksain"
    _inherit = "tt.reschedule"
    _description = "After Sales Periksain Model"
    _order = 'id DESC'

    reschedule_line_ids = fields.One2many('tt.reschedule.periksain.line', 'reschedule_id', 'After Sales Line(s)', readonly=True, states={'confirm': [('readonly', False)]})
    old_picked_timeslot_id = fields.Many2one('tt.timeslot.periksain', 'Old Picked Timeslot', readonly=True)
    new_picked_timeslot_id = fields.Many2one('tt.timeslot.periksain', 'New Picked Timeslot', readonly=True, states={'draft': [('readonly', False)]})
    change_ids = fields.One2many('tt.reschedule.periksain.changes', 'reschedule_id', 'Changes', readonly=True)
    passenger_ids = fields.Many2many('tt.reservation.passenger.periksain', 'tt_reschedule_periksain_passenger_rel', 'reschedule_id',
                                     'passenger_id',
                                     readonly=True)

    def generate_changes(self):
        for rec in self.change_ids:
            rec.sudo().unlink()
        if self.new_picked_timeslot_id and self.new_picked_timeslot_id.id != self.old_picked_timeslot_id.id:
            change_vals = {
                'reschedule_id': self.id,
                'seg_sequence': 1,
                'name': 'Picked Timeslot',
                'old_value': str(self.old_picked_timeslot_id.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19],
                'new_value': str(self.new_picked_timeslot_id.datetimeslot.astimezone(pytz.timezone('Asia/Jakarta')))[:19]
            }
            self.env['tt.reschedule.periksain.changes'].sudo().create(change_vals)
