# -*- coding: utf-8 -*-
{
    'name': "tt_agent_sales_event",

    'summary': """
        Agent Invoice for Event Reservation
    """,

    'description': """
        Agent Invoice for Event Reservation
    """,

    'author': "Skytors",
    'website': "http://www.skytors.id",
    'category': 'Tour and Travel',
    'version': '0.1',

    'depends': [
        'tt_agent_sales',
        'tt_reservation_event'
    ],

    'data': [
        'views/tt_reservation_event.xml'
    ],
}