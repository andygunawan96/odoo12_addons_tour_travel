# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tour Travel Public Holiday',
    'version' : 'beta',
    'summary': 'Public Holiday',
    'sequence': 2,
    'description': """
TT_PUBLIC_HOLIDAY
""",
    'category': 'tour_travel',
    'website': '',
    'images': [],
    'depends': ['base_setup', 'tt_base'],
    'data': [
        'views/menu_item_base.xml',
        'views/tt_public_holiday_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
