# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Airline',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Airline Module',
    'sequence': 23,
    'description': """
Tour & Travel - Agent Sales Airline
===================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_airline'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_airline.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}