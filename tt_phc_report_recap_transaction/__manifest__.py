# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - PHC Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'PHC Report Recap Transaction Module',
    'sequence': 22,
    'description': """
Tour & Travel - PHC Report Recap Transaction
=============================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_medical_vendor_report_recap_transaction', 'tt_reservation_phc'],

    # always loaded
    'data': [
        'views/tt_phc_report_recap_transaction_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}