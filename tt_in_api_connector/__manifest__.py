# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - In API Connector',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 6,
    'summary': 'In API Connector Module',
    'description': """
Tour & Travel - In API Connector
================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'base_setup', 'tt_base'],

    # always loaded
    'data': [
        'wizard/create_customer_parent_wizard_view.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}