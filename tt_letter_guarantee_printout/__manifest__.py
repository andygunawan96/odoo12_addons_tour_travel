# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Letter of Guarantee Printout',
    'version': '2.0',
    'category': 'Printout',
    'sequence': 2,
    'summary': 'Letter of Guarantee Printout Module',
    'description': """
Tour & Travel - Letter of Guarantee Printout
============================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends' : ['tt_base','tt_report_common'],
    'data': [
        'views/tt_letter_guarantee_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
