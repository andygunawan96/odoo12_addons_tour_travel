# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_bitrix_connector',
    'version' : 'beta',
    'summary': 'Bitrix Connector',
    'sequence': 2,
    'description': """
Bitrix Connector
""",
    'category': 'bitrix',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base'],
    'data': [
        'data/config_parameter_data.xml',
        'views/tt_agent_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
