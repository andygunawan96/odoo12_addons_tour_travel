# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Agent Sales Swab Express',
    'version': '2.0',
    'category': 'Billing',
    'summary': 'Agent Sales Swab Express Module',
    'sequence': 30,
    'description': """
Tour & Travel - Agent Sales Swab Express
=================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'base_setup', 'tt_agent_sales','tt_reservation_swabexpress'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/tt_reservation_swabexpress.xml'

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}