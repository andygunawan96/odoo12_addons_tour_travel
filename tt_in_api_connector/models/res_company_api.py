from odoo import api,models,fields
from ...tools import ERR
from ...tools.ERR import RequestException

class ResCompanyApiCon(models.Model):
    _name = 'res.company.api.con'
    _inherit = 'tt.api.con'

    table_name = 'res.company'

    def action_call(self,table_obj,action,data,context):
        if action == 'get_currency_company':
            company_data = {}
            companies = table_obj.search([], limit=1)
            for company in companies:
                company_data.update({
                    "country": company.country_id.code if company.country_id else '',
                    "website": company.website if company.website else '',
                    "phone": company.phone if company.phone else '',
                    "email": company.email if company.email else '',
                    "tax_id": company.vat if company.vat else '',
                    "company_registry": company.company_registry if company.company_registry else '',
                    "default_incoterm": company.incoterm_id.code if company.incoterm_id else '',
                    "currency": company.currency_id.name if company.currency_id else ''
                })
            return ERR.get_no_error(company_data)
        else:
            raise RequestException(999)
