from odoo import models, api


class PrintoutReservation(models.AbstractModel):
    _name = 'report.tt_report_common.printout_resv'

    """Abstract Model for report template.
        for `_name` model, please use `report.` as prefix then add `module_name.report_name`.
    """

    @api.model
    def _get_report_values(self, docids, data=None):
        # print('docids : ' + str(docids))
        return {
            'doc_ids': data['context']['active_ids'],
            'doc_model': data['context']['active_model'],
            'docs': self.env[data['context']['active_model']].browse(data['context']['active_ids']),
        }
