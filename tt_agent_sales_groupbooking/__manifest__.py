# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Group Booking',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Group Booking Module',
    'sequence': 29,
    'description': """
Tour & Travel - Agent Sales Group Booking
================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_groupbooking'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_groupbooking.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}