# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tour & Travel - Bitrix Connector',
    'version': '2.0',
    'category': 'Connector',
    'sequence': 98,
    'summary': 'Bitrix Connector Module',
    'description': """
Tour & Travel - Bitrix Connector
================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends' : ['base_setup','tt_base'],
    'data': [
        'data/config_parameter_data.xml',
        'views/tt_agent_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
