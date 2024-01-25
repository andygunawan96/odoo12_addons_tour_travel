from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ArchiveDupeCustomerWizard(models.TransientModel):
    _name = "archive.dupe.customer.wizard"
    _description = 'Archive Dupe Customer Wizard'

    customer_id = fields.Many2one('tt.customer', 'Customer (Selected one will be kept)', required=True)
    is_search_birthdate = fields.Boolean('Search by Birth Date', default=True)
    is_search_email = fields.Boolean('Search by Email', default=True)
    is_search_phone = fields.Boolean('Search by Phone', default=True)
    is_search_identity = fields.Boolean('Search by Identity Number', default=True)

    def archive_dupe_customer(self):
        if not self.env.user.has_group('tt_base.group_customer_level_3'):
            raise UserError('Error: Insufficient permission. Please contact your system administrator if you believe this is a mistake. Code: 467')
        search_params = [('id', '!=', self.customer_id.id), ('agent_id', '=', self.customer_id.agent_id.id),
                        ('first_name', '=', self.customer_id.first_name), ('last_name', '=', self.customer_id.last_name)]
        if self.is_search_birthdate:
            search_params.append(('birth_date', '=', self.customer_id.birth_date))
        if self.is_search_email:
            search_params.append(('email', '=', self.customer_id.email))
        phone_cust_filtered_ids = []
        if self.is_search_phone:
            for pho in self.customer_id.phone_ids:
                phone_list = self.env['phone.detail'].search([('phone_number', '=', pho.phone_number), ('customer_id', '!=', False)])
                for pho2 in phone_list:
                    if pho2.customer_id.id not in phone_cust_filtered_ids and pho2.customer_id.agent_id.id == self.customer_id.agent_id.id:
                        phone_cust_filtered_ids.append(pho2.customer_id.id)
        id_cust_filtered_ids = []
        if self.is_search_identity:
            for idt in self.customer_id.identity_ids:
                identity_list = self.env['tt.customer.identity'].search([('identity_type', '=', idt.identity_type), ('identity_number', '=', idt.identity_number), ('customer_id', '!=', False)])
                for idt2 in identity_list:
                    if idt2.customer_id.id not in id_cust_filtered_ids and idt2.customer_id.agent_id.id == self.customer_id.agent_id.id:
                        id_cust_filtered_ids.append(idt2.customer_id.id)

        def intersection(lst1, lst2):
            temp_set = set(lst2)
            lst3 = [value for value in lst1 if value in temp_set]
            return lst3

        if len(id_cust_filtered_ids) > len(phone_cust_filtered_ids):
            cust_filtered_ids = intersection(phone_cust_filtered_ids, id_cust_filtered_ids)
        else:
            cust_filtered_ids = intersection(id_cust_filtered_ids, phone_cust_filtered_ids)
        if cust_filtered_ids:
            search_params.append(('id', 'in', cust_filtered_ids))
        cust_list = self.env['tt.customer'].search(search_params)
        if not cust_list:
            raise UserError("No Duplicate User Found.")
        sql_query = """
                    update tt_customer set active = False where id in %s;
                    """ % (str(cust_list.ids).replace('[', '(').replace(']', ')'))
        self.env.cr.execute(sql_query)
