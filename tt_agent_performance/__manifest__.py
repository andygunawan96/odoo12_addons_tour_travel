# -*- coding: utf-8 -*-
{
    'name' : 'Tour & Travel - Agent Report Performance',
    'version' : '2.0',
    'category': 'Report',
    'summary': 'Agent Performance Report Module',
    'sequence': 85,
    'description': """
Tour & Travel - Agent Report Performance
========================================
Key Features
------------
""",
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['base', 'tt_base', 'tt_report_common', 'tt_agent_report'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_performance_view.xml',
        'report/tt_agent_report_performance_menu.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}