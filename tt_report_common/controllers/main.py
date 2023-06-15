from odoo import api, http, _
from odoo.http import request


# Default odoo bisa render report via URL cman ada kendala karena yg render mesti login
# Opsi ini dibuat untuk by pass login e odoo (kurang secure)
class Main(http.Controller):
    @http.route(['/orbisway/report/<string:print_type>/<string:model_name>/<string:order_number>',
        '/orbisway/report/<string:print_type>/<string:model_name>/<string:order_number>/<int:report_mode>'], methods=['GET'], csrf=False, type='http', auth="none", website=True)
    def print_id(self, print_type, model_name, order_number, report_mode=False):
        if model_name == 'form.itinerary':
            pdf = request.env.ref('tt_report_common.action_printout_itinerary_from_json')
            data = { 'context': {'json_content': order_number} }
            if print_type.lower() == 'pdf':
                pdf, _ = pdf.sudo().render_qweb_pdf(False, data=data)
                pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
                pdfhttpheaders.append( ('Content-Disposition', 'attachment; filename="Itinerary.pdf"') )
                return request.make_response(pdf, headers=pdfhttpheaders)
            else:
                html = pdf.sudo().render_qweb_html(False, data=data)
                return request.make_response(html)

        model_id = request.env[model_name].search([('name', '=ilike', order_number)], limit=1).ids
        data = {'context': {'active_model': model_name, 'active_ids': model_id}}
        model_obj = request.env[model_name].browse(model_id)
        if model_id and model_obj:
            # TODO VIN: Rapikan URL
            if model_name == 'tt.reservation.airline' and report_mode == 1:
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
            elif model_name == 'tt.reservation.airline' and report_mode == 2:
                data.update({'is_with_price': True})
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
            elif model_name == 'tt.reservation.airline' and report_mode == 3:
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_airline')
            elif model_name == 'tt.reservation.airline' and report_mode == 4:
                line_ids = request.env['tt.agent.invoice.line'].search([('id', 'in', model_obj.invoice_line_ids.ids)])
                model_id = [rec.invoice_id.id for rec in line_ids]
                model_obj = request.env['tt.agent.invoice'].browse(model_id)
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')
                data['context'].update({
                    'active_model': 'tt.agent.invoice',
                    'active_ids': model_id,
                })
            elif model_name == 'tt.reservation.hotel' and report_mode == 1:
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_hotel')
            elif model_name == 'tt.reservation.hotel' and report_mode == 3:
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_hotel')
            elif model_name == 'tt.reservation.hotel' and report_mode == 4:
                line_ids = request.env['tt.agent.invoice.line'].search([('id', 'in', model_obj.invoice_line_ids.ids)])
                model_id = [rec.invoice_id.id for rec in line_ids]
                model_obj = request.env['tt.agent.invoice'].browse(model_id)
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')
                data['context'].update({
                    'active_model': 'tt.agent.invoice',
                    'active_ids': model_id,
                })
            elif model_name == 'tt.reservation.train' and report_mode == 1: # Without Price
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_train')
            elif model_name == 'tt.reservation.train' and report_mode == 2: # With Price
                data.update({'is_with_price': True})
                pdf = request.env.ref('tt_report_common.action_report_printout_reservation_train')
            elif model_name == 'tt.reservation.train' and report_mode == 3:
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_airline')
            elif model_name == 'tt.reservation.train' and report_mode == 4:
                line_ids = request.env['tt.agent.invoice.line'].search([('id', 'in', model_obj.invoice_line_ids.ids)])
                model_id = [rec.invoice_id.id for rec in line_ids]
                model_obj = request.env['tt.agent.invoice'].browse(model_id)
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')
                data['context'].update({
                    'active_model': 'tt.agent.invoice',
                    'active_ids': model_id,
                })

            elif model_name == 'tt.reservation.activity' and report_mode == 1:
                # pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_activity')
            elif model_name == 'tt.reservation.activity' and report_mode == 2:
                data.update({'is_with_price': True})
                # pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_activity')
            elif model_name == 'tt.reservation.activity' and report_mode == 3:
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_activity')
            elif model_name == 'tt.reservation.activity' and report_mode == 4:
                line_ids = request.env['tt.agent.invoice.line'].search([('id', 'in', model_obj.invoice_line_ids.ids)])
                model_id = [rec.invoice_id.id for rec in line_ids]
                model_obj = request.env['tt.agent.invoice'].browse(model_id)
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')
                data['context'].update({
                    'active_model': 'tt.agent.invoice',
                    'active_ids': model_id,
                })
            elif model_name == 'tt.reservation.tour' and report_mode == 1:
                # pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_tour')
            elif model_name == 'tt.reservation.tour' and report_mode == 2:
                data.update({'is_with_price': True})
                # pdf = request.env.ref('tt_report_common.action_report_printout_reservation_airline')
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_tour')
            elif model_name == 'tt.reservation.tour' and report_mode == 3:
                pdf = request.env.ref('tt_report_common.action_printout_itinerary_tour')
            elif model_name == 'tt.reservation.tour' and report_mode == 4:
                line_ids = request.env['tt.agent.invoice.line'].search([('id', 'in', model_obj.invoice_line_ids.ids)])
                model_id = [rec.invoice_id.id for rec in line_ids]
                model_obj = request.env['tt.agent.invoice'].browse(model_id)
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')
                data['context'].update({
                    'active_model': 'tt.agent.invoice',
                    'active_ids': model_id,
                })
            else:
                pdf = request.env.ref('tt_report_common.action_report_printout_invoice')

            if print_type.lower() == 'pdf':
                pdf, _ = pdf.sudo().render_qweb_pdf(model_id, data=data)
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