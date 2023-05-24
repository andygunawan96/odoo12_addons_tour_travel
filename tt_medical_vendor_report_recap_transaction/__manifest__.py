# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Medical Vendor Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Medical Vendor Report Recap Transaction Module',
    'sequence': 22,
    'description': """
Tour & Travel - Medical Vendor Report Recap Transaction
=======================================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['base', 'tt_base', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_medical_vendor_report_recap_transaction_view.xml',
        'report/tt_medical_vendor_report_recap_transaction_menu.xml',
        'report/tt_medical_vendor_report_recap_transaction_template.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}