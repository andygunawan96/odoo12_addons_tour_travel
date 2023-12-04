{
    'name': 'Tour & Travel - Point Reward',
    'version': '2.0',
    'category': 'Tour & Travel',
    'sequence': 70,
    'summary': 'Point Reward Module',
    'description': """
Tour & Travel - Point Reward
=============================
Key Features
------------
    """,
    'author': 'PT Orbis Daya Asia',
    'website': 'orbisway.com',
    'depends': ['tt_base', 'tt_reservation', 'tt_accounting'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/tt_agent_views.xml',
        'views/tt_point_reward_rules_views.xml',
        'views/tt_point_reward_views.xml',
        'views/menu_item_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}