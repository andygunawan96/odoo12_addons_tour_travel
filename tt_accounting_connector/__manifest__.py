# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_accounting_connector',
    'version' : 'beta',
    'summary': 'jasaweb accounting connector',
    'sequence': 2,
    'description': """
TT_ACCOUNTING_CONNECTOR
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['tt_base', 'tt_accounting', 'tt_payment', 'tt_reservation', 'tt_reschedule'],
    'data': [
        'views/accounting_history_views.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
