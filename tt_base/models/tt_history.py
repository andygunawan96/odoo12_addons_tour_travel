from odoo import models, api, _
import html


class TtHistory(models.Model):
    _name = 'tt.history'
    _inherit = ['mail.thread']

    @api.multi
    def write(self, value):
        self_dict = self.read()
        key_list = [key for key in value.keys()]
        for key in key_list:
            # print(self.fields_get())
            # print(self.fields_get().get(key))
            # print(key)
            # print(self.fields_get().get(key))
            if self.fields_get().get(key) is not None:
                # One2Many Relation Field
                if self.fields_get().get(key)['type'] == 'one2many' or self.fields_get().get(key)['type'] == 'many2many':
                    self.message_post(body=_("%s Changed.") %
                                            (self.fields_get().get(key)['string']))  # Model String / Label

                # Many2One Relation Field
                else:
                    # start : kode ini masih beresiko (hard coded). dapat diubah kapan saja
                    if self.fields_get().get(key)['type'] == 'many2one':
                        old_value = self_dict[0].get(key)
                        # print(old_value)
                        if old_value is False:
                            old_value = 'None'
                        else:
                            old_value = self_dict[0].get(key)[1]
                        new_val = self.env[self.fields_get().get(key)['relation']].search([('id', 'in', [value[key]])]).name_get()
                        if not new_val:
                            if str(self.env[self.fields_get().get(key)['relation']]) == 'res.users()':  # masih rawan
                                new_value = self.env.user.name
                            else:
                                new_value = old_value  # sementara
                        else:
                            new_value = self.env[self.fields_get().get(key)['relation']] \
                                        .search([('id', 'in', [value[key]])]).name_get()[0][1]
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
