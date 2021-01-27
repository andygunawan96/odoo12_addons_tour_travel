from odoo import api, fields, models
from datetime import datetime, date, timedelta
import base64,pytz


class TtLetterGuarantee(models.Model):
    _inherit = 'tt.letter.guarantee'

    printout_lg_id = fields.Many2one('tt.upload.center', 'Printout Letter of Guarantee', readonly=True)

    def print_letter_of_guarantee(self):
        datas = {
            'ids': self.env.context.get('active_ids', []),
            'model': self._name
        }
        res = self.read()
        res = res and res[0] or {}
        datas['form'] = res
        lg_printout_action = self.env.ref('tt_report_common.action_report_printout_letter_guarantee')
        if not self.printout_lg_id:
            co_agent_id = self.env.user.agent_id.id

            co_uid = self.env.user.id

            pdf_report = lg_printout_action.report_action(self, data=datas)
            pdf_report['context'].update({
                'active_model': self._name,
                'active_id': self.id
            })
            pdf_report_bytes = lg_printout_action.render_qweb_pdf(data=pdf_report)
            res = self.env['tt.upload.center.wizard'].upload_file_api(
                {
                    'filename': 'Letter of Guarantee %s.pdf' % self.name,
                    'file_reference': 'Letter of Guarantee Printout',
                    'file': base64.b64encode(pdf_report_bytes[0]),
                    'delete_date': datetime.today() + timedelta(minutes=10)
                },
                {
                    'co_agent_id': co_agent_id,
                    'co_uid': co_uid,
                }
            )
            upc_id = self.env['tt.upload.center'].search([('seq_id', '=', res['response']['seq_id'])], limit=1)
            self.printout_lg_id = upc_id.id
        url = {
            'type': 'ir.actions.act_url',
            'name': "Printout",
            'target': 'new',
            'url': self.printout_lg_id.url,
        }
        return url
