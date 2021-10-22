{
    'name': 'Tour & Travel Gateway - Engine Pricing V2',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 16,
    'summary': 'Engine Pricing Module V2',
    'description': """
Tour & Travel Gateway - Engine Pricing V2
======================================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_base'],
    'data': [
        'security/ir.model.access.csv',

        'views/menu_item_base.xml',
        'views/tt_provider_pricing_views.xml',
        'views/tt_agent_pricing_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
