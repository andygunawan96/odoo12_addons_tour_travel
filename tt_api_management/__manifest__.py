{
    'name': 'Tour & Travel - API Management',
    'version': '1.1',
    'category': 'Tour & Travel',
    'sequence': 19,
    'summary': 'Tour & Travel - API Management',
    'description': """
Tour & Travel - API Management
====================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_base','tt_engine_pricing'],
    'data': [
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
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
