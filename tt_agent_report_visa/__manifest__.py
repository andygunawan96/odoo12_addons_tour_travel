# -*- coding: utf-8 -*-
{
    'name': "tt_agent_report_visa",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Andre - Rodextrip",
    'website': "http://www.rodextrip.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'report',
    'version': 'beta',

    # any module necessary for this one to work correctly
    'depends': ['base', 'tt_base', 'tt_reservation_visa', 'tt_agent_report'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/tt_agent_report_visa_view.xml',
        # 'report/tt_agent_report_visa_menu.xml',
        'report/tt_agent_report_visa_report.xml',
        'report/tt_agent_report_visa_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}