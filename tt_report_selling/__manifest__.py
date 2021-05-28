# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Report Selling',
    'version': '2.0',
    'category': 'Report',
    'sequence': 82,
    'summary': 'Report Selling Module',
    'description': """
Tour & Travel - Report Selling
==============================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_report_common', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_report_selling_view.xml',
        'report/tt_report_selling_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}