{
    'name': 'Tour & Travel - API Management',
    'version': '2.0',
    'category': 'Tour & Travel',
    'summary': 'API Management Module',
    'sequence': 5,
    'description': """
Tour & Travel - API Management
==============================
Key Features
------------
    """,
    'author': "PT Orbis Daya Asia",
    'website': "orbisway.com",
    'depends': ['tt_base','tt_engine_pricing'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'views/menu.xml',
        'views/api_credential_views.xml',
        'views/api_host_views.xml',
        'views/api_config_views.xml',
        'views/api_provider_views.xml',
        'views/api_carrier_views.xml',
        'views/api_monitor_views.xml',
        'views/api_webhook_views.xml',
        'views/api_blackout_views.xml',
        'wizard/user_encrypt_views.xml',

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
