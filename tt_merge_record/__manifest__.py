{
    'name': 'Tour & Travel - Merge Record',
    'version': '1.1',
    'category': 'Tour & Travel',
    'sequence': 1,
    'summary': 'Tour & Travel - Merge Record',
    'description': """
Tour & Travel - Base
====================
Key Features
------------
    """,
    'author': 'PT Roda Express Sukses Mandiri',
    'website': 'rodextravel.tours',
    'depends': ['tt_base'],
    'data': [
        'security/ir.model.access.csv',
        # Wizard dlu karena di views panggil action e wizard
        'wizard/find_similar_views.xml',
        'views/merge_record_views.xml',

    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
