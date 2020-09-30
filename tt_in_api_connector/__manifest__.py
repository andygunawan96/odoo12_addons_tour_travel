# -*- coding: utf-8 -*-
{
    'name': "tt_in_api_connector",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'API',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'tt_base'],

    # always loaded
    'data': [
        'wizard/create_customer_parent_wizard_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}