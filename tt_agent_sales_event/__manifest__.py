# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Event',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Event Module',
    'sequence': 24,
    'description': """
Tour & Travel - Agent Sales Event
=================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': [
        'tt_agent_sales',
        'tt_reservation_event'
    ],

    'data': [
        'views/tt_reservation_event.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}