{
    'name': 'Tour & Travel - Merge Record',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 95,
    'summary': 'Merge Record Module',
    'description': """
Tour & Travel - Merge Record
============================
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
    'application': False,
    'auto_install': False,
}
