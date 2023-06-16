# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Visa',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Visa Module',
    'sequence': 31,
    'description': """
Tour & Travel - Agent Sales Visa
================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_visa'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_visa_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}