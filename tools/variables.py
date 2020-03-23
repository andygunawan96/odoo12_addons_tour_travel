"""

========================
    Global Variable
========================

"""

ENVIRONMENT = [
    ('test', 'Test'),
    ('prod', 'Production'),
]

ROLE_TYPE = [
    ("admin", "Administrator"),
    ("manager", "Manager"),
    ("operator", "Operator"),
]

DEVICE_TYPE = [
    ("general", "General"),
    ("website", "Website"),
    ("android", "Android"),
    ("ios", "Ios"),
]

ACCESS_TYPE = [
    ("all", "ALL"),
    ("allow", "Allowed"),
    ("restrict", "Restricted"),
]

AMOUNT_TYPE = [
    ("amount", "Amount"),
    ("percentage", "Percentage"),
]

BANK_STATEMENT = [
    ('not_connect', 'Not Connected'),       #Processing
    ('connect', 'connected')                #after Processing
]

BOOKING_STATE = [
    ('draft', 'New'),
    ('confirm', 'Confirmed'),
    ('cancel', 'Cancelled'),
    ('cancel2', 'Expired'),
    ('cancel_pending', 'Cancel Pending'),
    ('fail_cancel', 'Failed (Cancel)'),
    ('error', 'Connection Loss'), #diganti failed issue
    ('fail_booked', 'Failed (Book)'),
    ('booked', 'Booked'),
    ('partial_booked', 'Partial Booked'),
    ('in_progress', 'In Progress'),
    ('fail_issued', 'Failed (Issue)'),
    ('partial_issued', 'Partial Issued'),
    ('sent', 'Sent'),
    ('paid', 'Paid'),
    ('validate', 'Validate'),
    ('issued', 'Issued'),
    ('pending', 'Pending'),
    ('done', 'Done'),
    ('rejected', 'Rejected'),
    ('fail_refunded', 'Failed (REFUNDED)'),
    ('refund', 'Refund'),
    ('refund_pending', 'Refund Pending'),
    ('reissue', 'Reissue'), #diganti reissue
]

BOOKING_STATE_STR = {
    'draft': 'New',
    'confirm': 'Confirmed',
    'cancel': 'Cancelled',
    'cancel2': 'Expired',
    'cancel_pending': 'Cancel Pending',
    'fail_cancel': 'Failed (Cancel)',
    'error': 'Connection Loss', #diganti failed issue
    'fail_booked': 'Failed (Book)',
    'booked': 'Booked',
    'partial_booked': 'Partial Booked',
    'in_progress': 'In Progress',
    'fail_issued': 'Failed (Issue)',
    'partial_issued': 'Partial Issued',
    'sent': 'Sent',
    'paid': 'Paid',
    'validate': 'Validate',
    'issued': 'Issued',
    'pending': 'Pending',
    'done': 'Done',
    'rejected': 'Rejected',
    'fail_refunded': 'Failed (REFUNDED)',
    'refund': 'Refund',
    'refund_pending': 'Refund Pending',
    'reroute': 'Reroute', #diganti reissue
}

JOURNEY_DIRECTION = [
    ('OW', 'One Way'),
    ('RT', 'Return'),
    ('MC','Multi City'),
    ('OTHER','Other')
]

JOURNEY_TYPE = [
    ('DEP', 'Depart'),
    ('RET', 'Return')
]

TITLE = [
    ('MR', 'Mr.'),
    ('MSTR', 'Mstr.'),
    ('MRS', 'Mrs.'),
    ('MS', 'Ms.'),
    ('MISS', 'Miss')
]

GENDER = [
    ('male', 'Male'),
    ('female', 'Female')
]

MARITAL_STATUS = [
    ('single', 'Single'),
    ('married', 'Married'),
    ('divorced', 'Divorced'),
    ('widowed', 'Widowed')
]

RELIGION = [
    ('islam', 'Islam'),
    ('protestantism', 'Protestantism'),
    ('catholicism', 'Catholicism'),
    ('hinduism', 'Hinduism'),
    ('buddhism', 'Buddhism'),
    ('confucianism', 'Confucianism'),
    ('others', 'Others')
]

IDENTITY_TYPE = [
    ('ktp', 'KTP'),
    ('sim', 'SIM'),
    ('passport', 'Passport'),
    ('other', 'Other'),
]

PAX_TYPE = [
    ('YCD', 'Elder'),
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

PROVIDER_TYPE = []##akan di isi saat run oleh tt_provider_type.py

ADJUSTMENT_TYPE = []

ACQUIRER_TYPE = [
    ('cash', 'Cash'),
    ('transfer', 'Transfer'),
    ('debit', 'Debit Card'),
    ('credit', 'Credit Card'),
    ('va', 'Virtual Account')
]

ACC_TRANSPORT_TYPE = {
    'tt.reservation.airline': 'Airline',
    'tt.reservation.train': 'Train',
    'tt.reservation.hotel': 'Hotel',
    'tt.reservation.visa': 'Visa',
    'tt.reservation.tour': 'Tour',
    'tt.reservation.activity': 'Activity',
    'tt.refund': 'Refund',
    'tt.reschedule': 'Airline Reschedule',
    'tt.agent.invoice': 'Invoice Agent',
    'tt.top.up': 'Top Up',
    'tt.adjustment': 'Adjustment',
}

ACC_TRANSPORT_TYPE_REVERSE = {
    'Airline': 'tt.reservation.airline',
    'Train': 'tt.reservation.train',
    'Hotel': 'tt.reservation.hotel',
    'Visa': 'tt.reservation.visa',
    'Tour': 'tt.reservation.tour',
    'Activity': 'tt.reservation.activity',
    'Refund': 'tt.refund',
    'Airline Reschedule': 'tt.reschedule',
    'Invoice Agent': 'tt.agent.invoice',
    'Top Up': 'tt.top.up',
    'Adjustment': 'tt.adjustment',
}

FEE_CHARGE_TYPE = [
    ('parent', 'Parent'),
    ('ho', 'HO')
]
