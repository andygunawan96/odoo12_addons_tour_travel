from odoo import api, http, _
from odoo.http import request


# Default odoo bisa render report via URL cman ada kendala karena yg render mesti login
# Opsi ini dibuat untuk by pass login e odoo (kurang secure)
class Main(http.Controller):
    @http.route('/rodextrip/report/<string:print_type>/<string:model_name>/<string:order_number>', methods=['GET'], csrf=False, type='http', auth="public", website=True)
    def print_id(self, print_type, model_name, order_number):
        model_id = request.env[model_name].search([('name', '=ilike', order_number)], limit=1).ids
        data = {'context': {'active_model': model_name, 'active_ids': model_id}}
        model_obj = request.env[model_name].browse(model_id)
        if model_id and model_obj:
            if model_name == 'tt.reservation.airline':
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
            elif model_name == 'tt.reservation.hotel':
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_hotel')
            elif model_name == 'tt.reservation.train':
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_hotel')
            else:
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')

            if print_type.lower() == 'pdf':
                pdf, _ = pdf.sudo().render_qweb_pdf([model_id], data=data)
                pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
                # Fungsi untuk buat PDF jadi ke download + filename
                # Jika tidak ingin download maka akan tampil di web browser
                pdfhttpheaders.append( ('Content-Disposition', 'attachment; filename="' + model_obj.name + '.pdf"') )
                return request.make_response(pdf, headers=pdfhttpheaders)
            else:
                html = pdf.sudo().render_qweb_html(model_id, data=data)
                return request.make_response(html)
        else:
            return request.redirect('/')