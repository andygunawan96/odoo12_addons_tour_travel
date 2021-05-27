{
    'name': 'Tour & Travel - Bank Transaction',
    'version': '2.0',
    'category': 'Tour & Travel',
    'summary': 'Bank Transaction Module',
    'sequence': 97,
    'description': """
Tour & Travel - Bank Transaction
================================
Key Features
------------
    """,
    'author': "PT Roda Express Sukses Mandiri",
    'website': "rodextravel.tours",
    'depends': ['tt_base', 'tt_accounting'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',
        'data/ir_cron_data.xml',
        'views/bank_accounts_views.xml',
        'views/bank_transaction_views.xml',
        'views/bank_transaction_date_views.xml',
        'views/menu_item_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}