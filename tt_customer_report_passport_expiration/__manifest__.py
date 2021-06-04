# -*- coding: utf-8 -*-
{
    'name': 'Tour & Travel - Customer Report Passport Expiration',
    'version': '2.0',
    'category': 'Report',
    'sequence': 86,
    'summary': 'Customer Report Passport Expiration',
    'description': """
Tour & Travel - Customer Report Passport Expiration
===================================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['base', 'tt_base', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_customer_report_passport_expiration_view.xml',
        'report/tt_customer_report_passport_expiration_menu.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}