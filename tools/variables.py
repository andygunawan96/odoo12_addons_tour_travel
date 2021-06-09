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
    ('booked', 'Booked'),
    ('cancel', 'Cancelled'),
    ('cancel2', 'Expired'),
    ('cancel_pending', 'Cancel Pending'),
    ('fail_cancel', 'Failed (Cancel)'),
    ('fail_refunded', 'Failed (Refunded)'),
    ('fail_paid', 'Failed (Paid)'),
    ('error', 'Connection Loss'), #diganti failed issue
    ('in_progress', 'In Progress'),
    ('sent', 'Sent'),
    ('paid', 'Paid'),
    ('validate', 'Validate'),
    ('pending', 'Pending'),
    ('issued', 'Issued'),
    ('done', 'Done'),
    ('rejected', 'Rejected'),
    ('reissue', 'Reissue'), #diganti reissue
    # April 21, 2020 - SAM
    ('fail_booked', 'Booking Failed'),
    ('halt_booked', 'Booking Halt'),
    ('booked_pending', 'Booking Pending'),
    ('partial_booked', 'Partial Booked'),
    ('fail_issued', 'Issued Failed'),
    ('halt_issued', 'Issued Halt'),
    ('issued_pending', 'Issued Pending'),
    ('partial_issued', 'Partial Issued'),
    ('void_failed', 'Void Failed'),
    ('void_pending', 'Void Pending'),
    ('void', 'Void'),
    ('partial_void', 'Partial Void'),
    ('refund_failed', 'Refund Failed'),
    ('refund_pending', 'Refund Pending'),
    ('refund', 'Refund'),
    ('partial_refund', 'Partial Refund'),
    ('rescheduled_failed', 'Rescheduled Failed'),
    ('rescheduled_pending', 'Rescheduled Pending'),
    ('rescheduled', 'Rescheduled'),
    ('partial_rescheduled', 'Partial Rescheduled'),
    # END
]

BOOKING_STATE_STR = {
    'draft': 'New',
    'confirm': 'Confirmed',
    'cancel': 'Cancelled',
    'cancel2': 'Expired',
    'cancel_pending': 'Cancel Pending',
    'fail_cancel': 'Failed (Cancel)',
    'fail_paid': 'Failed (Paid)',
    'fail_refunded': 'Failed (Refund)',
    'error': 'Connection Loss', #diganti failed issue
    'in_progress': 'In Progress',
    'sent': 'Sent',
    'paid': 'Paid',
    'validate': 'Validate',
    'pending': 'Pending',
    'done': 'Done',
    'rejected': 'Rejected',
    'reroute': 'Reroute', #diganti reissue
    'reissue': 'Reissue', #diganti reissue
    # April 21, 2020
    'fail_booked': 'Booking Failed',
    'halt_booked': 'Booking Halt',
    'booked_pending': 'Booking Pending',
    'booked': 'Booked',
    'partial_booked': 'Partial Booked',
    'fail_issued': 'Issued Failed',
    'halt_issued': 'Issued Halt',
    'issued_pending': 'Issued Pending',
    'issued': 'Issued',
    'partial_issued': 'Partial Issued',
    'rescheduled_failed': 'Rescheduled Failed',
    'rescheduled_pending': 'Rescheduled Pending',
    'rescheduled': 'Rescheduled',
    'partial_rescheduled': 'Partial Rescheduled',
    'void_failed': 'Void Failed',
    'void_pending': 'Void Pending',
    'void': 'Void',
    'partial_void': 'Partial Void',
    'refund_failed': 'Refund Failed',
    'refund_pending': 'Refund Pending',
    'refund': 'Refund',
    'partial_refund': 'Partial Refund',
    # END
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
    ('va', 'Virtual Account'),##open
    ('payment_gateway', 'Payment Gateway')##closed
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

COMMISSION_CHARGE_TYPE = [
    ('pricing', 'Pricing'),
    ('fare', 'Basic Fare'),
    ('total', 'Total Fare and Tax'),
]

ROUNDING_AMOUNT_TYPE = (
    ('none', 'None'),
    ('ceil', 'Ceil'),
    ('floor', 'Floor'),
    ('round', 'Round'),
)

PROVIDER_TYPE_PREFIX = {
    'AL': 'airline',
    'TN': 'train',
    'PS': 'passport',
    'VS': 'visa',
    'AT': 'activity',
    'TR': 'tour',
    'RESV': 'hotel',
    'BT': 'ppob',
    'VT': 'event',
    'PK': 'periksain',
    'PH': 'phc'
}

PRODUCT_STATE = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('cancel', 'Cancel'),
    ('postpone', 'Postpone'),
    ('sold-out', 'Sold Out'),
    ('expired', 'Expired')
]
RESV_RECONCILE_STATE = [
    ('not_reconciled','Not Reconciled'),
    ('partial','Partially Reconciled'),
    ('reconciled','Reconciled'),
    ('cancel','Cancelled')
]

PRICING_PROVIDER_TYPE = [
    ('main','Main'),
    ('append','Append'),
]
