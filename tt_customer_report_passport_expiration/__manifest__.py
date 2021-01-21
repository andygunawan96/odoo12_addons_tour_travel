# -*- coding: utf-8 -*-
{
    'name': "tt_customer_report_passport_expiration",

    'summary': """
        Generate Report of Customer Passport Expiration
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_customer_report_passport_expiration_view.xml',
        'report/tt_customer_report_passport_expiration_menu.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}