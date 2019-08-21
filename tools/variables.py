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

ACCESS_TYPE = [
    ("all", "ALL"),
    ("allow", "Allowed"),
    ("restrict", "Restricted"),
]

AMOUNT_TYPE = [
    ("amount", "Amount"),
    ("percentage", "Percentage"),
    ]
BOOKING_STATE = [
    ('draft', 'New'),
    ('cancel', 'Cancelled'),
    ('cancel2', 'Expired'),
    ('error', 'Connection Loss'), #diganti failed issue
    ('fail_booked', 'Failed (Book)'),
    ('booked', 'Booked'),
    ('partial_booked', 'Partial Booked'),
    ('in_progress', 'In Progress'),
    ('fail_issued', 'Failed (Issue)'),
    ('partial_issued', 'Partial Issued'),
    ('issued', 'Issued'),
    ('done', 'Done'),
    ('rejected', 'Rejected'),
    ('fail_refunded', 'Failed (REFUNDED)'),
    ('refund', 'Refund'),
    ('reissue', 'Reissue'), #diganti reissue
]

BOOKING_STATE_STR = {
    'draft': 'New',
    'confirm': 'Confirmed',
    'cancel': 'Cancelled',
    'cancel2': 'Expired',
    'error': 'Connection Loss', #diganti failed issue
    'fail_booked': 'Failed (Book)',
    'booked': 'Booked',
    'partial_booked': 'Partial Booked',
    'in_progress': 'In Progress',
    'fail_issued': 'Failed (Issue)',
    'partial_issued': 'Partial Issued',
    'issued': 'Issued',
    'done': 'Done',
    'fail_refunded': 'Failed (REFUNDED)',
    'refund': 'Refund',
    'reroute': 'Reroute', #diganti reissue
}

JOURNEY_DIRECTION = [
    ('OW', 'One Way'),
    ('RT', 'Return'),
    ('MC','Multi City')
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
    ('passport', 'Passport'),
]

PAX_TYPE = [
    ('YCD', 'Elder'),
    ('ADT', 'Adult'),
    ('CHD', 'Child'),
    ('INF', 'Infant')
]

PROVIDER_TYPE = []##akan di isi saat run oleh tt_provider_type.py