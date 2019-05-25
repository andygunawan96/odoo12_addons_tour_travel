# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Modul Testing',
    'version' : 'beta',
    'summary': 'Testing my first modul',
    'sequence': 1,
    'description': """
Invoicing & Payments
====================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your vendors and customers.

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. This module also offers you an easy method of registering payments, without having to encode complete abstracts of account.
    """,
    'category': 'testing',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','base_address_city'],
    'data': [
        'security/ir.model.access.csv',
        'views/orang_view.xml',
        'views/animal_views.xml',
        'views/reservation_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
