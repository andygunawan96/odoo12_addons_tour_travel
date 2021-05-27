# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tour & Travel - Accounting Connector',
    'version' : '2.0',
    'category': 'Connector',
    'summary': 'Jasaweb Accounting Connector',
    'sequence': 99,
    'description': """
Tour & Travel - Accounting Connector
====================================
Key Features
------------
""",
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends' : ['tt_base', 'tt_accounting', 'tt_payment', 'tt_reservation', 'tt_reschedule'],
    'data': [
        'views/accounting_history_views.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
