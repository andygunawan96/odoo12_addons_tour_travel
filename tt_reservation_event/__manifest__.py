# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'tt_reservation_event',
    'version' : 'beta',
    'summary': 'transport dummy event',
    'sequence': 2,
    'description': """
TT_TRANSPORT
""",
    'category': 'booking',
    'website': '',
    'images' : [],
    'depends' : ['base_setup','tt_base','tt_reservation','base_address_city','tt_agent_sales'],
    'data': [
        # 'data/ir_sequence_data.xml',
        # 'data/ir_cron_data.xml',
        'data/tt_provider_type_data.xml',
        # 'data/tt_provider_activity.xml',
        # 'data/tt_transport_carrier_activity.xml',
        # 'data/tt_api_webhook_data.xml',
        # 'data/ir_send_email.xml',
        'security/ir.model.access.csv',
        # 'security/ir_rule_data.xml',
        # 'report/printout_invoice_templates.xml',
        'views/menu_item_base.xml',
        # 'views/tt_event_voucher_wizard.xml',
        # 'views/tt_event_sync_product_wizard.xml',
        # 'views/tt_event_sync_to_children_wizard.xml',
        'views/tt_event_category_views.xml',
        # 'views/tt_reservation_event_option_views.xml',
        'views/tt_master_event_views.xml',
        'views/tt_reservation_event_views.xml',
        # 'views/tt_provider_views.xml',
        'views/tt_service_charge_views.xml',
        'views/tt_reservation_passenger_event_form_views.xml'
        # 'views/tt_event_printout_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
