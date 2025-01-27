# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Accounting Setup',
    'version': '2.0',
    'category': 'Accounting',
    'summary': 'Accounting Setup Module',
    'sequence': 20,
    'description': """
Tour & Travel - Accounting Setup
================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base','tt_accounting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'views/tt_accounting_setup_views.xml',
        'views/tt_accounting_setup_variables_views.xml',
        'views/tt_accounting_setup_suppliers_views.xml',
        'views/res_users_views.xml',
        'views/tt_customer_parent_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}