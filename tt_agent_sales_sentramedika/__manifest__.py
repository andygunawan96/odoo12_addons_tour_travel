# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Sentra Medika',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Sentra Medika Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales Sentra Medika
=================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_sentramedika'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_sentramedika.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}