import copy

class ToDict():

    def to_dict(self, something = False, depth = 0):
        dict = copy.deepcopy(self.read()[0])

        dict.pop('id')
        dict.pop('create_uid')
        dict.pop('write_uid')
        dict.pop('write_date')
        dict.pop('create_date')
        dict.pop('__last_update')

        for key, item in dict.items():
            field_type = self._fields[key].type
            comodel_name = self._fields[key].comodel_name

            if field_type == 'char' and not item:
                dict[key] = ''

            elif field_type == 'many2one':
                dict[key] = self.process_many2one(item,comodel_name,depth)

            elif field_type == 'datetime':
                dict[key] = item and item.strftime("%Y-%m-%d, %H:%M:%S") or ''

            elif field_type == 'date':
                dict[key] = item and item.strftime('%Y-%m-%d')

            elif field_type == 'one2many' or field_type == 'many2many':
                dict[key] = self.process_one2many(item,comodel_name,depth)
        if depth==0:
            print(dict)
        return dict


    def process_many2one(self, item, comodel_name, depth):
        if item:
            object = self.env[comodel_name].browse(item[0])
            if (hasattr(object, 'to_dict')) and (depth < 1):
                return object.to_dict(depth=depth + 1)
            elif item:
                return item[1]
        else:
            return ''

    def process_one2many(self, item, comodel_name, depth):
        list = []
        if item:
            for rec in item:
                object = self.env[comodel_name].browse(rec)
                if depth < 1:
                    list.append(object.to_dict(depth=depth+1))
                else:
                    list.append(object.display_name)
        else:
            return False

        return list