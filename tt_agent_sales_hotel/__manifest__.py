# -*- coding: utf-8 -*-
{
    'name': "tt_agent_sales_hotel",

    'summary': """
        Agent Invoice for Hotel Reservation
    """,

    'description': """
        Agent Invoice for Hotel Reservation
    """,

    'author': "Skytors",
    'website': "http://www.skytors.id",
    'category': 'Tour and Travel',
    'version': '0.1',

    'depends': [
        'tt_agent_sales',
        'tt_reservation_hotel'
    ],

    'data': [
        'views/tt_reservation_hotel.xml'
    ],
}