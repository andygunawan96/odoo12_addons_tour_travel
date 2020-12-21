from odoo import api, fields, models, _
from ...tools.api import Response
import logging
import traceback
from ...tools.db_connector import GatewayConnector


class TtTemporaryRecord(models.Model):
    _name = 'tt.temporary.record'
    _description = 'Model that use to record newly created object that may need some human action'

    name = fields.Char('Name', required=True)
    provider_id = fields.Many2one('tt.provider', "Provider")
    parent_rec_id = fields.Integer('Res Id', required=False)
    remove_rec_id = fields.Integer('To be Merged Id', required=True, help='record that set to in active after being merged')
    rec_model = fields.Char('Res Model', required=True)

    state = fields.Selection([('new', 'New'), ('confirm', 'Confirmed'), ('need_merge', 'Need to be Merge'), ('merge', 'Merged')],
                             'State', help='This Record are Confirmed as new record or need to merge with old record', default='new')
    active = fields.Boolean('Active', default=True)
    line_ids = fields.One2many('tt.record.move.line', 'temp_rec_id', 'Move Obj')

    def get_obj(self):
        # Tambahkan list object yg mau dicek disini
        # Examp: waktu aku merge city maka sytems juga mesti pindah smua hotel yg reference ke city tsb jadi
        # Jadi waktu di tt_hotel_reservation aku inherit fungsi ini dan tmabahkan tuple (model name, field_name)
        # Example ada di TT Hotel same function name
        return {
            'res.country': [('res.country.state', 'country_id'), ('res.city', 'country_id')],
            'res.country.state': [('res.city', 'state_id')],
        }

    @api.multi
    def action_merge(self):
        for obj in self.get_obj():
            # Todo Check apakah obj yg di self = obj[1] di list tsb
            model_name, field_name = obj
            for rec in self.env[model_name].search([(field_name, '=', self.remove_rec_id)]):
                rec.update({field_name: self.parent_rec_id})

                self.env['tt.record.move.line'].create({
                    'temp_rec_id': self.id,
                    'rec_id': rec.id,
                    'rec_model': model_name,
                })
        parent_obj = self.env[self.rec_model].browse(self.parent_rec_id)
        remove_obj = self.env[self.rec_model].browse(self.remove_rec_id)
        if self.rec_model in ['res.city', 'res.country.state', 'res.country']:
            alias_name_list = []
            # Pindah smua alias name dari object ke target merge nya
            for alias in parent_obj.other_name_ids:
                if alias.name != parent_obj.name:
                    if self.rec_model == 'res.city':
                        alias.city_id = self.parent_rec_id
                    elif self.rec_model == 'res.country':
                        alias.country_id = self.parent_rec_id
                    elif self.rec_model == 'res.country.state':
                        alias.state_id = self.parent_rec_id
                alias_name_list.append(alias.name)
            # Pindah smua nama asli obj yg ingin di remove ke target merge nya
            if remove_obj.name not in alias_name_list:
                self.env['tt.destination.alias'].create({'name': remove_obj.name, 'city_id': self.parent_rec_id, })

            for a in remove_obj.provide_code_ids:
                a.update({field_name: self.parent_rec_id})

        remove_obj.active = False
        remove_obj.other_name_ids = False
        self.state = 'merge'

    @api.multi
    def action_revert(self):
        self.env[self.rec_model].browse(self.remove_rec_id).active = True
        for rec in self.env['tt.record.move.line'].search([('temp_rec_id', '=', self.id)]):
            for obj in self.get_obj():
                model_name, field_name = obj
                if model_name == rec.rec_model:
                    break

            target_obj = self.env[model_name].browse(rec.rec_id)
            target_obj.update({
                field_name: self.remove_rec_id
            })
            rec.sudo().unlink()
        self.state = 'new'

    @api.multi
    def action_confirm(self):
        self.state = 'confirm'

    @api.multi
    def action_set_to_draft(self):
        self.state = 'new'

    def open_record_parent(self):
        return self.open_record(self.parent_rec_id)

    def open_record_remove(self):
        return self.open_record(self.remove_rec_id)

    def open_record(self, rec_id):
        try:
            form_id = self.env[self.rec_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.rec_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.rec_model,
            'res_id': rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }


class TtMoveLine(models.Model):
    _name = 'tt.record.move.line'
    _description = 'Save move relation after action merging. EX: Moving Hotel A from city Bali-Denpasar to city ' \
                   'Denpasar after both record merged'

    temp_rec_id = fields.Many2one('tt.temporary.record', 'Temporary Record')
    rec_id = fields.Integer('Record Id', required=True)
    rec_model = fields.Char('Record Model', required=True)

    def open_record(self):
        try:
            form_id = self.env[self.rec_model].get_form_id()
        except:
            form_id = self.env['ir.ui.view'].search([('type', '=', 'form'), ('model', '=', self.rec_model)], limit=1)
            form_id = form_id[0] if form_id else False

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reservation',
            'res_model': self.rec_model,
            'res_id': self.rec_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': form_id.id,
            'context': {},
            'target': 'current',
        }
