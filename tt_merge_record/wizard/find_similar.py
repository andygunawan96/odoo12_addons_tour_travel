# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class FindSimilar(models.TransientModel):
    _name = 'find.similar'
    _description = 'Finding similar record as selected'

    rec_id = fields.Integer('Record id')
    rec_model = fields.Char('Record Model')
    rec_name = fields.Char('Record Name')

    similar_ids = fields.One2many('find.similar.line', 'similar_id', 'Line(s)')

    def count_mark(self, params, marker='|'):
        search_mark = []
        for a in params[1:]:
            search_mark.append(marker)
        return search_mark + params

    def find_similar(self, rec_model, obj_str, rec_id, is_allow_partial=True):
        obj_str_no_space = obj_str.replace(' ', '')
        obj_str_remark = obj_str.replace('-', '')

        search_params = [('name', 'ilike', obj_str),]
        if obj_str != obj_str_no_space:
            search_params.append(('name', 'ilike', obj_str_no_space))
        if obj_str != obj_str_remark:
            search_params.append(('name', 'ilike', obj_str_remark))
        if is_allow_partial and len(obj_str.split(' ')) > 1:
            search_params += [('name', 'ilike', rec) for rec in obj_str.split(' ')]
        search_params = self.count_mark(search_params, '|')

        # mandatory_search_params = [('name', 'ilike', obj_str_no_space[:3]), ('name', 'ilike', obj_str_remark[-3:])]
        mandatory_search_params = [('id', '!=', int(rec_id)),]
        mandatory_search_params = self.count_mark(mandatory_search_params, '&')
        search_params = search_params + mandatory_search_params
        rec_ids = self.env[rec_model].search(search_params)
        # new_ids = []
        # rec_ids += self.env[rec_model].browse(new_ids)
        return rec_ids

    @api.model
    def default_get(self, fields_list):
        rec_obj = self.env[self._context['active_model']].browse(self._context['active_id'])
        target_obj = self.env[rec_obj.rec_model].browse(rec_obj.remove_rec_id)

        line_ids = []
        for similar_rec in self.find_similar(rec_obj.rec_model, target_obj.name, rec_obj.remove_rec_id):
            similar_obj = self.env['find.similar.line'].create({'rec_id': similar_rec.id, 'name':similar_rec.name})
            line_ids.append(similar_obj.id)
        self = self.with_context(
            default_rec_id=rec_obj.remove_rec_id,
            default_rec_model=rec_obj.rec_model,
            default_rec_name=target_obj.name,
            default_similar_ids=[(6, 0, line_ids)],
        )
        return super(FindSimilar, self).default_get(fields_list)

    def open_table(self):
        selected = self.similar_ids.filtered(lambda x: x.is_selected)
        if selected:
            if len(selected) == 1:
                rec_obj = self.env[self._context['active_model']].browse(self._context['active_id'])
                rec_obj.parent_rec_id = selected[0].rec_id
            else:
                raise Exception('You can only Select 1 Record')
        else:
            raise Exception('Select 1 Record, Press cancel if you dont want to proceed')
        return True


class FindSimilarLine(models.TransientModel):
    _name = 'find.similar.line'
    _description = 'Finding similar record as selected'

    name = fields.Char('Record Name')
    similar_id = fields.Many2one('find.similar', 'Similar')
    rec_id = fields.Integer('Record id')
    is_selected = fields.Boolean('Is Selected')


