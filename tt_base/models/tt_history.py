from odoo import models, api, fields, _
import html


class SkippedKeys(models.Model):
    _name = 'tt.skipped.keys'

    model_name = fields.Char('Model Name')
    field_name = fields.Char('Field Name')
    active = fields.Boolean('Active', default=True)

    SKIPPED_KEYS = {}

    @api.model
    def create(self, vals_list):
        new_record = super(SkippedKeys, self).create(vals_list)
        self._register_hook()
        return  new_record

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

    @api.multi
    def write(self, value):
        self_dict = self.read()
        key_list = [key for key in value.keys()]

        #tempat hardcode skip key
        skipped_keys = self.env['tt.skipped.keys'].SKIPPED_KEYS

        for key in key_list:
            #skipped key
            if self._name in skipped_keys:
                if key in skipped_keys[self._name]:
                    continue

            # One2Many Relation Field
            if self.fields_get().get(key)['type'] == 'one2many':
                self.message_post(body=_("%s Changed.") %
                                       (self.fields_get().get(key)['string']))  # Model String / Label
            # Many2One Relation Field
            # start : kode ini masih beresiko (hard coded). dapat diubah kapan saja
            else:
                if self.fields_get().get(key)['type'] == 'many2one':
                    old_value = self_dict[0].get(key)
                    if old_value is False:
                        old_value = 'None'
                    else:
                        old_value = self_dict[0].get(key)[1]
                    new_value = self.env[self.fields_get().get(key)['relation']].search([('id', 'in', [value[key]])]).name_get()[0][1]
                    # end

                # Non-Relation Field
                else:
                    old_value = self_dict[0].get(key)
                    new_value = value[key]
                # print(key + ' : ' + str(new_value))

                # Print History
                if self.fields_get().get(key)['type'] == 'binary':
                    self.message_post(body=_("%s has been changed.") %
                                           (self.fields_get().get(key)['string']))  # Model String / Label
                elif self.fields_get().get(key)['type'] == 'html':
                    # Un-escape HTML
                    old_value = html.unescape(old_value)
                    new_value = html.unescape(new_value)

                    # " to '
                    old_value = old_value.replace('"', '\'')
                    new_value = new_value.replace('"', '\'')

                    if old_value != new_value:
                        # print('test')
                        self.message_post(body=_("%s has been changed from %s to %s by %s.") %
                                                (self.fields_get().get(key)['string'],  # Model String / Label
                                                 old_value,  # Old Value
                                                 # value[key],  # New Value
                                                 new_value,  # new value
                                                 self.env.user.name))  # User that Changed the Value
                else:
                    self.message_post(body=_("%s has been changed from %s to %s by %s.") %
                                           (self.fields_get().get(key)['string'],  # Model String / Label
                                            old_value,  # Old Value
                                            # value[key],  # New Value
                                            new_value,  # new value
                                            self.env.user.name))  # User that Changed the Value
        return super(TtHistory, self).write(value)

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
