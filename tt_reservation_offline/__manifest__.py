# -*- coding: utf-8 -*-
{
    'name': "tt_reservation_offline",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_agent_sales', 'tt_reservation'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/tt_reservation_offline_security.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
        'data/ir_sequence_data.xml',
        'views/issued_offline_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}