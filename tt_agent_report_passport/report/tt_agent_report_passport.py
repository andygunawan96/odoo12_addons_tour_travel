from odoo import models, api, fields, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AgentReportPassportModel(models.AbstractModel):
    _name = 'report.tt_agent_report_passport.agent_report_passport_model'
    _description = 'Passport'

    @api.model
    def _get_report_values(self, docids, data=None):
        print('docids : ' + str(self.env['tt.agent.report.passport'].browse(data['ids'])))
