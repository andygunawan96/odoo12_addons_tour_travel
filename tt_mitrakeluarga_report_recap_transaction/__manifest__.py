# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Mitra Keluarga Report Recap Transaction',
    'version': '2.0',
    'category': 'Report',
    'summary': 'Mitra Keluarga Report Recap Transaction Module',
    'sequence': 22,
    'description': """
Tour & Travel - Mitra Keluarga Report Recap Transaction
=======================================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_medical_vendor_report_recap_transaction', 'tt_reservation_mitrakeluarga'],

    # always loaded
    'data': [
        'views/tt_mitrakeluarga_report_recap_transaction_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}