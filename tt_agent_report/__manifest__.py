# -*- coding: utf-8 -*-
{
    'name': "tt_agent_report",

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
    'depends': ['base', 'tt_base', 'tt_accounting', 'tt_reservation', 'tt_agent_sales', 'tt_report_common'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_common_view.xml',
        'wizard/tt_agent_report_ledger_view.xml',
        'wizard/tt_agent_report_excel_output_wizard.xml',
        'report/tt_agent_report_ledger_menu.xml',
        'report/tt_agent_report_ledger_template.xml'
        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}