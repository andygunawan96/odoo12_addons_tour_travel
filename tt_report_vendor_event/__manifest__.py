# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Report Vendor Event',
    'version': '2.0',
    'category': 'Report',
    'sequence': 83,
    'summary': 'Report Vendor Event Module',
    'description': """
Tour & Travel - Report Vendor Event
===================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_agent_report', 'tt_reservation_event'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'wizard/tt_report_vendor_event_view.xml',
        'report/tt_report_vendor_event_menu.xml',
        'views/temporary_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}