# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Customer Report Birthday',
    'version': '2.0',
    'category': 'Report',
    'sequence': 85,
    'summary': 'Customer Report Birthday',
    'description': """
Tour & Travel - Customer Report Birthday
========================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_customer_report_birthday_view.xml',
        'report/tt_customer_report_birthday_menu.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}