from odoo import models, api, fields, _
import html


class SkippedKeys(models.Model):
    _name = 'tt.skipped.keys'
    _description = 'Rodex Model'

    model_name = fields.Char('Model Name')
    field_name = fields.Char('Field Name')
    active = fields.Boolean('Active', default=True)

    SKIPPED_KEYS = {}

    @api.model
    def create(self, vals_list):
        new_record = super(SkippedKeys, self).create(vals_list)
        self._register_hook()
        return new_record

    @api.model
    def write(self, vals):
        super(SkippedKeys, self).write(vals)
        self._register_hook()

    @api.multi
    def unlink(self):
        deleted_record = super(SkippedKeys, self).unlink()
        self._register_hook()
        return deleted_record

    def fill_skipped_keys(self):
        self.SKIPPED_KEYS.clear()
        for rec in self.search([]):
            if not rec.model_name in self.SKIPPED_KEYS:
                self.SKIPPED_KEYS[rec.model_name] = []
            self.SKIPPED_KEYS[rec.model_name].append(rec.field_name)

    def _register_hook(self):
        self.fill_skipped_keys()
        print(self.SKIPPED_KEYS)


class TtHistory(models.Model):
    _name = 'tt.history'
    _inherit = ['mail.thread']
    _description = 'Rodex Model'

    def update_ids_only(self, target_objs, key_list):
        for obj in target_objs:
            for key in key_list:
                if isinstance(obj[key], list):
                    a = [self.env[self.fields_get().get(key)['relation']].browse(par_rec).name_get()[0][1] for par_rec in obj[key]]
                    obj[key] = a
        return target_objs


    @api.multi
    def write(self, value):
        key_list = value.keys()
        # tempat hardcode skip key
        skipped_keys = self.env['tt.skipped.keys'].SKIPPED_KEYS

        for rec in self:
            old_self = self.update_ids_only(rec.read(), key_list)
            return super(TtHistory, rec).write(value)
            new_self = self.update_ids_only(rec.read(), key_list)
            # rec_dict = rec.read()

            for key in key_list:
                # skipped key
                if rec._name in skipped_keys:
                    if key in skipped_keys[rec._name]:
                        continue

                # Todo: Selection
                # One2Many Relation Field
                # Many2one, Non-Relation Field
                old_value = old_self[0].get(key) and (isinstance(old_self[0].get(key), tuple) and old_self[0].get(key)[1] or old_self[0].get(key)) or 'None'
                new_value = new_self[0].get(key) and (isinstance(new_self[0].get(key), tuple) and new_self[0].get(key)[1] or new_self[0].get(key)) or 'None'
                # print(key + ' : ' + str(new_value))

                #kalau value sama skip tidak usah di print
                if old_value == new_value:
                    continue

                # Print History
                if rec.fields_get().get(key)['type'] == 'binary':
                    rec.message_post(body=_("%s has been changed.") %
                                           (rec.fields_get().get(key)['string']))  # Model String / Label
                elif rec.fields_get().get(key)['type'] == 'html':
                    # Un-escape HTML
                    old_value = html.unescape(old_value)
                    new_value = html.unescape(new_value)

                    # " to '
                    old_value = old_value.replace('"', '\'')
                    new_value = new_value.replace('"', '\'')

                    if old_value != new_value:
                        # print('test')
                        rec.message_post(body=_("%s has been changed from %s to %s by %s.") %
                                                (rec.fields_get().get(key)['string'],  # Model String / Label
                                                 old_value,  # Old Value
                                                 # value[key],  # New Value
                                                 new_value,  # new value
                                                 rec.env.user.name))  # User that Changed the Value
                else:
                    rec.message_post(body=_("{ %s } changed from [ %s ] to [ %s ] by < %s >.") %
                                           (rec.fields_get().get(key)['string'],  # Model String / Label
                                            old_value,  # Old Value
                                            # value[key],  # New Value
                                            new_value,  # new value
                                            rec.env.user.name))  # User that Changed the Value

# For Debug Purposes
# print(key)
# print(self.fields_get().get(key))

# many2one debug :
    # print(value)
    # print(self.fields_get().get(key))
    # print(self.env[self.fields_get().get(key)['relation']])
    # print(self.env[self.fields_get().get(key)['relation']]
    #       .search([('id', 'in', [value[key]])]).name_get())
    # print(new_value)

# html debug :
    # print(old_value)
    # print(' ')
    # print(new_value)
    # print(',,,,,,,,,,,,,,,,,,,,,,,')

# print(self.fields_get().get(key)['string'])
# print(self_dict[0].get(key)[1])
# print(self.env[self.fields_get().get(key)['relation']].fields_get().get('name'))
# print(self.fields_get().get(key)['relation'])
# print(self.env[value[key]])
# print(self.pool.get(self.fields_get().get(key)['relation']).search(self._cr, self._uid, []))
# print(self.env['tt.agent.type'].search([('id', 'in', [value[key]])]).name_get())
# print(self.env[self.fields_get().get(key)['relation']].search([('id', 'in', [value[key]])]).name_get())
# print(key)
