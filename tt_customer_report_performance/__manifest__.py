# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Customer Report Performance',
    'version': '2.0',
    'category': 'Report',
    'sequence': 87,
    'summary': 'Customer Report Performance',
    'description': """
Tour & Travel - Customer Report Performance
===========================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['base', 'tt_base', 'tt_report_common', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_customer_report_performance_view.xml',
        # 'report/tt_customer_report_performance_menu.xml'
    ],
    # only loaded in demonstration mode
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}