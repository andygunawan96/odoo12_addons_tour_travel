# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Swab Express Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Swab Express Report Recap Transaction Module',
    'sequence': 22,
    'description': """
Tour & Travel - Swab Express Report Recap Transaction
=======================================================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base', 'tt_medical_vendor_report_recap_transaction', 'tt_reservation_swabexpress'],

    # always loaded
    'data': [
        'views/tt_swabexpress_report_recap_transaction_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}