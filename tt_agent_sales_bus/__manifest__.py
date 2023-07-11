# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Bus',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Bus Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales Bus
===============================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_bus'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_bus.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}