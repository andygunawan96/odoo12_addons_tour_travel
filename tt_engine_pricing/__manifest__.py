{
    'name': 'Tour & Travel Gateway - Engine Pricing',
    'version': '1.1',
    'category': 'Tour & Travel',
    'sequence': 19,
    'summary': 'Tour & Travel Gateway - Engine Pricing',
    'description': """
Tour & Travel Gateway - []
====================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_base'],
    'data': [
        'security/ir.model.access.csv',

        'views/pricing_provider_views.xml',
        'views/pricing_agent_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
