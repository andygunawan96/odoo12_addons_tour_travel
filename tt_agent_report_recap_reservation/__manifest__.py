# -*- coding: utf-8 -*-
{
    'name': "tt_agent_report_recap_reservation",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_recap_reservation_view.xml',
        'report/tt_agent_report_recap_reservation_menu.xml',
        'report/tt_agent_report_recap_reservation_template.xml'
    ],
    # only loaded in demonstration mode
    'demo': [],
}