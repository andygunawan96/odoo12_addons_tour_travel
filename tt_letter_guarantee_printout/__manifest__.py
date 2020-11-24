# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_letter_guarantee',
    'version' : 'beta',
    'summary': 'Letter of Guarantee Printout',
    'sequence': 2,
    'description': """
Letter of Guarantee Printout
""",
    'category': 'billing',
    'website': '',
    'images' : [],
    'depends' : ['tt_base','tt_report_common'],
    'data': [
        'views/tt_letter_guarantee_views.xml'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
