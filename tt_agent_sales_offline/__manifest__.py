# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Offline',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Offline Module',
    'sequence': 26,
    'description': """
Tour & Travel - Agent Sales Offline
===================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_agent_sales', 'tt_reservation_offline'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_offline_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}