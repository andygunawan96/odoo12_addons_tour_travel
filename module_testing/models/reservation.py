from odoo import api,models,fields


class InvoiceLine(models.Model):
    _name = "invoice.line"

    name = fields.Char('Name',compute="_compute_display_name")
    res_model = fields.Char(
        'Related Document Model Name', required=True, index=True)
    res_id = fields.Integer(
        'Related Document ID', index=True, help='Id of the followed resource')
    invoice_id = fields.Many2one('orang.orang','Invoice')

    @api.multi
    def _compute_display_name(self):
        for rec in self:
            rec.name = self.env[rec.res_model].browse(rec.res_id).name

    def open_record(self):
        form_id = self.env[self.res_model].get_form_id()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }

class Reservation(models.Model):
    _name = "reservation.reservation"

    name = fields.Char("Reservation Name", default="New")
    book_date = fields.Date("Book Date")
    total_amount = fields.Integer("Total Amount")

    invoice_line_ids = fields.One2many("invoice.line","res_id","Owners",domain=lambda self: [('res_model', '=', self._name)])

    def create_invoice(self):
        self.env['invoice.line'].create({
            'res_model': self._name,
            'res_id': self.id,
            'invoice_id': 1
        })


class ReservationTrain(models.Model):
    _name = "reservation.train"
    _inherit = "reservation.reservation"

    pnr = fields.Char("PNR")


    def get_form_id(self):
            return self.env.ref("module_testing.reservation_train_form_view")



class ReservationHotel(models.Model):
    _name = "reservation.hotel"
    _inherit = "reservation.reservation"

    resv_code = fields.Char("Reservation Code")

    def get_form_id(self):
            return self.env.ref("module_testing.reservation_hotel_form_view")

