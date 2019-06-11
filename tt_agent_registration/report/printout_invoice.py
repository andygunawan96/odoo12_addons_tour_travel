from odoo import models, api


class PrintoutInvoice(models.AbstractModel):

    _name = 'report.printout_invoice_model'

    @api.model
    def get_report_values(self, docids, data=None):
        agent_registration = self.env["tt.agent.registration"].browse(docids)
        # fare_detail = self._get_fare_details(transport_booking)
        # sum_comisi = self._sum_comisi(transport_booking)
        # segment_desc = self._get_segments_description(transport_booking)

        docargs = {
            'doc_ids': docids,
            'doc_model': data['model'],
            'docs': agent_registration,
            # 'fare_detail': fare_detail,
            # 'sum_comisi': sum_comisi,
        }

        return docargs
