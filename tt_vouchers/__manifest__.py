{
    'name': 'Tour & Travel - Voucher',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 70,
    'summary': 'Voucher Module',
    'description': """
Tour & Travel - Voucher
=======================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['tt_base'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_send_email.xml',
        'views/voucher_views.xml',
        'views/voucher_detail_views.xml',
        'views/voucher_blackout_views.xml',
        'views/voucher_use_views.xml',
        'views/menu_item_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}