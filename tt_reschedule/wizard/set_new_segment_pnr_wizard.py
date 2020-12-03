from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR

_logger = logging.getLogger(__name__)


class SetNewSegmentPNRWizard(models.TransientModel):
    _name = "reschedule.set.new.segment.pnr.wizard"
    _description = 'Reschedule Set New Segment PNR Wizard'

    segment_reschedule_id = fields.Many2one('tt.segment.reschedule', 'Reschedule Segment', readonly=True)
    new_pnr = fields.Char('New PNR', required=True)

    def submit_new_pnr(self):
        self.segment_reschedule_id.write({
            'pnr': self.new_pnr
        })
