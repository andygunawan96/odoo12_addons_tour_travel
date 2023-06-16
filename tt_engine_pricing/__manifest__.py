{
    'name': 'Tour & Travel Gateway - Engine Pricing',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 15,
    'summary': 'Engine Pricing Module',
    'description': """
Tour & Travel Gateway - Engine Pricing
======================================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['tt_base'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'views/pricing_provider_views.xml',
        'views/pricing_agent_views.xml',
        'views/pricing_customer_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
