# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Periksain Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Periksain Report Recap Transaction Module',
    'sequence': 22,
    'description': """
Tour & Travel - Periksain Report Recap Transaction
=======================================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_medical_vendor_report_recap_transaction', 'tt_reservation_periksain'],

    # always loaded
    'data': [
        'views/tt_periksain_report_recap_transaction_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}