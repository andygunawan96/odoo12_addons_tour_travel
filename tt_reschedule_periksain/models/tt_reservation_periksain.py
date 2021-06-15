from odoo import api,models,fields, _
from ...tools.ERR import RequestException
from ...tools import util,variables,ERR
import logging,traceback
import json

_logger = logging.getLogger(__name__)


class ReservationPeriksain(models.Model):

    _inherit = "tt.reservation.periksain"

    reschedule_ids = fields.One2many('tt.reschedule', 'res_id', 'After Sales', readonly=True)

    def to_dict_reschedule(self):
        reschedule_list = []
        for rsch in self.reschedule_ids:
            rsch_values = rsch.get_reschedule_data()
            reschedule_list.append(rsch_values)
        return  reschedule_list
