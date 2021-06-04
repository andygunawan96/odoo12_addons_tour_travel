# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Activity',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Activity Module',
    'sequence': 21,
    'description': """
Tour & Travel - Agent Sales Activity
====================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales', 'tt_reservation_activity'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_activity.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}