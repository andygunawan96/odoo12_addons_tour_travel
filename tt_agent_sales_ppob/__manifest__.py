# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales PPOB',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales PPOB Module',
    'sequence': 28,
    'description': """
Tour & Travel - Agent Sales PPOB
================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_ppob'],

    # always loaded
    'data': [
        'views/tt_reservation_ppob.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}