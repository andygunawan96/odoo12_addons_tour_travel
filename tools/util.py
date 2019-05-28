import base64
from datetime import datetime

def encode_authorization(_id, _username, _password):
    credential = '%s:%s:%s' % (_id, _username, _password)
    res = base64.b64encode(credential.encode())
    return res


def decode_authorization(_code):
    credential = base64.b64decode(_code).decode()
    cred = credential.split(':')
    if len(cred) != 3:
        return ()
    res = {
        'uid': int(cred[0]),
        'username': cred[1],
        'password': cred[2],
    }
    return res


def get_request_data(request):
    host_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '')
    if not host_ip:
        host_ip = request.httprequest.environ.get('REMOTE_ADDR', '')

    res = {
        'host_ip': host_ip,
        'data': request.jsonrequest,
        'sid': request.session.sid,
        'action': request.httprequest.environ.get('HTTP_ACTION', False),
    }
    return res


def make_dict_from_tree(element_tree):
    """Traverse the given XML element tree to convert it into a dictionary.
    :param element_tree: An XML element tree
    :type element_tree: xml.etree.ElementTree
    :rtype: dict
    """

    def internal_iter(tree, accum):
        """Recursively iterate through the elements of the tree accumulating
        a dictionary result.

        :param tree: The XML element tree
        :type tree: xml.etree.ElementTree
        :param accum: Dictionary into which data is accumulated
        :type accum: dict
        :rtype: dict
        """
        if tree is None:
            return accum

        if tree.getchildren():
            accum[tree.tag] = {}
            for each in tree.getchildren():
                result = internal_iter(each, {})
                if each.tag in accum[tree.tag]:
                    if not isinstance(accum[tree.tag][each.tag], list):
                        accum[tree.tag][each.tag] = [
                            accum[tree.tag][each.tag]
                        ]
                    accum[tree.tag][each.tag].append(result[each.tag])
                else:
                    accum[tree.tag].update(result)
        else:
            accum[tree.tag] = tree.text

        return accum

    return internal_iter(element_tree, {})


def get_logger(sub_folder):
    my_logger = logging.getLogger('MyLogger')
    my_logger.setLevel(logging.DEBUG)

    dirname = '/var/log/tour_travel/'
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    dirname = dirname + sub_folder + '/'
    handler = logging.StreamHandler()

    try:
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname)
        logf = dirname + '/' + sub_folder + '.log'
        handler = logging.handlers.TimedRotatingFileHandler(filename=logf, when='D', interval=1, backupCount=30)
    except Exception:
        sys.stderr.write("ERROR: couldn't create the logfile directory %s. Logging to the standard output.\n" % sub_folder)

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    # add formatter to ch
    handler.setFormatter(formatter)

    my_logger.addHandler(handler)

    try:
        dirname = os.path.dirname(logf)
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname)

        handler = logging.handlers.TimedRotatingFileHandler(filename=logf, when='D', interval=1, backupCount=30)
    except Exception:
        sys.stderr.write("ERROR: couldn't create the logfile directory. Logging to the standard output.\n")

    return my_logger

import random
from uuid import uuid4


def gen_id(prefix='', limit=6):
    s = list(str(int(uuid4())))
    random.shuffle(s)
    return u"%s%s" % (prefix, ''.join(s[:limit]))


def gen_uuid():
    return str(uuid4())

def calculate_transit_duration(arrival_1, depature_2):
    """
    get interval time
    :param date1:
    :param date2:
    :return: '1d 2h 3m'
    """
    intr = datetime.strptime(depature_2[:16], '%Y-%m-%d %H:%M') - datetime.strptime(arrival_1[:16], '%Y-%m-%d %H:%M')
    hours = intr.seconds // 3600
    # minutes
    minutes = (intr.seconds - (hours * 3600)) // 60
    if intr.days < 1:
        return "%sh %sm" % (hours, minutes)
    return "%sd %sh %sm" % (intr.days, hours, minutes)

def navitare_key_to_code(SegmentKey):
    seg = SegmentKey.split('~')
    # seg = ['QG', ' 155', ' ', '', 'DPS', '05/29/2017 12:15', 'HLP', '05/29/2017 13:10', '']
    # QG,155,DPS,HLP,2017-05-29 12:15,2017-05-29 13:00, [provider]
    dept_date = datetime.strptime(seg[5], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
    arr_date = datetime.strptime(seg[7], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
    return segment_attr_to_code(seg[0], seg[1], seg[4], seg[6], dept_date, arr_date)

def navitare_keys_to_codes(JourneySellKey):
    segs = JourneySellKey.split('^')
    # seg = ['QG', ' 155', ' ', '', 'DPS', '05/29/2017 12:15', 'HLP', '05/29/2017 13:10', '']
    # QG,155,DPS,HLP,2017-05-29 12:15,2017-05-29 13:00, [provider]
    jkey = ''
    for seg in segs:
        s = seg.split('~')
        dept_date = datetime.strptime(s[5], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
        arr_date = datetime.strptime(s[7], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
        jkey += segment_attr_to_code(s[0], s[1], s[4], s[6], dept_date, arr_date) + ';'
    return jkey[:-1]

def navitare_code_to_key(segment_code):
    seg = segment_code.split(',')
    # QG~ 103~ ~~JOG~06/10/2017 06:00~HLP~06/10/2017 07:00~
    # seg = ['QG', ' 155', ' ', '', 'DPS', '05/29/2017 12:15', 'HLP', '05/29/2017 13:10', '']
    # QG,155,DPS,HLP,2017-05-29 12:15,2017-05-29 13:00
    dept_date = datetime.strptime(seg[4], '%Y-%m-%d %H:%M').strftime('%m/%d/%Y %H:%M')
    arr_date = datetime.strptime(seg[5], '%Y-%m-%d %H:%M').strftime('%m/%d/%Y %H:%M')
    return '%s~%s~ ~~%s~%s~%s~%s~' % (seg[0], seg[1], seg[2], dept_date, seg[3], arr_date)

    dept_date = datetime.strptime(seg[5], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
    arr_date = datetime.strptime(seg[7], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M')
    return segment_attr_to_code(seg[0], seg[1], seg[4], seg[6], dept_date, arr_date)

def journey_codes_to_segments(journey_codes):
    # Extract Journey Key menjadi Segment key
    journey_codes_tmp = []
    for j in journey_codes:
        seg_codes = j['segment_codes'].split(';')
        fare_codes = j['fare_codes'].split(';')
        for i in range(0, len(seg_codes)):
            tmp = {
                'segment_code': seg_codes[i],
                'fare_code': fare_codes[i]
            }
            journey_codes_tmp.append(tmp)
    return journey_codes_tmp

def segment_code_to_dict(segment_code):
    # seg = segment_code.split('~')
    # if len(seg) > 1:  # Navitare
    #     # QG~ 720~ ~~SUB~11/30/2017 13:40~MDC~11/30/2017 18:20~
    #     return {
    #         'segment_code': segment_code,
    #         'carrier_code': seg[0],
    #         'carrier_number': seg[1],
    #         'origin': seg[4],
    #         'destination': seg[6],
    #         'departure_date': datetime.strptime(seg[5], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S'),
    #         'arrival_date': datetime.strptime(seg[7], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S'),
    #         'carrier_name': seg[0] + ' ' + seg[1],
    #     }
    seg = segment_code.split(',')
    if len(seg) == 1:  # Lionair
        return {
            'segment_code': segment_code,
        }
    return {
        'segment_code': segment_code,
        'carrier_code': seg[0],
        'carrier_number': seg[1],
        'carrier_name': seg[0] + ' ' + seg[1],
        'origin': seg[2],
        'destination': seg[3],
        'departure_date': seg[4],
        'arrival_date': seg[5],
        'provider': seg[10],
    }

def segment_attr_to_code(flight_code, flight_number, origin, dest, departure_date, arrival_date):
    #datetime format MUST : yyyy-mm-dd hh:nn  == %Y-%m-%d %H:%M
    return "%s,%s,%s,%s,%s,%s" % (flight_code, flight_number, origin, dest, departure_date[:16], arrival_date[:16])

def navitare_journeys_parser(response, pop_Journeys=True):
    journeys = response.pop('Journeys') if pop_Journeys else response['Journeys']
    journeys = journeys['Journey']
    res = []
    if type(journeys) != list:
        journeys = [journeys]

    for j in journeys:
        journey_tmp = {
            'journey_code': navitare_keys_to_codes(j['JourneySellKey']),
            'segments': []
        }
        res.append(journey_tmp)

        # ==== Segments ====
        segments = j['Segments']['Segment']
        if type(segments) != list:
            segments = [segments]

        for s in segments:
            seg_tmp = {
                'segment_code': navitare_key_to_code(s['SegmentSellKey']),
                'segment_code2': s['DepartureStation'] + s['ArrivalStation'],
                # key2 use for _get_prices_itinerary_SSR
                'pax_fares': []
            }
            journey_tmp['segments'].append(seg_tmp)

            # ==== FARES====
            fares = s['Fares']['Fare']
            if type(fares) != list:
                fares = [fares]
            for fs in fares:

                # ==== PaxFares ====
                pax_fares = fs['PaxFares']['PaxFare']
                if type(pax_fares) != list:
                    pax_fares = [pax_fares]
                for pf in pax_fares:
                    PaxFare_tmp = {
                        'pax_type': pf['PaxType'],
                        'fare_code': fs['FareSellKey'],
                        'subclass': fs['ClassOfService'],
                        'product_class': fs['ProductClass'],
                        'rule_number': fs['RuleNumber'],
                        'service_charges': []
                    }
                    seg_tmp['pax_fares'].append(PaxFare_tmp)

                    # ==== ServiceCharges ====
                    ServiceCharges = pf['ServiceCharges']['BookingServiceCharge']
                    if type(ServiceCharges) != list:
                        ServiceCharges = [ServiceCharges]
                    total = 0
                    for sc in ServiceCharges:
                        sc_tmp = {
                            'pax_type': pf['PaxType'],
                            # 'charge_code': sc['ChargeType'],
                            'charge_code': 'fare' if sc['ChargeType'] == 'FarePrice' else sc['ChargeCode'].lower(),
                            'passanger_count': 0,
                            'ticket_code': sc['TicketCode'],
                            'currency': sc['CurrencyCode'],
                            'amount': float(sc['Amount']),
                            'charge_code': sc['ChargeType'],
                            'foreign_currency': sc['ForeignCurrencyCode'],
                            'foreign_amount': float(sc['ForeignAmount'])
                        }
                        total += sc_tmp['amount']
                        PaxFare_tmp['service_charges'].append(sc_tmp)
                    PaxFare_tmp['total'] = total
    return res

def _jouneys_booking_groupby_provider(journey_codes):
    # j_provider_tmp = dict, provider_sequence, check pastikan destination-0 == origin-1,
    # jika tidak sama maka provider_sequence di tambahkan
    # setiap satu provider_sequence = satu ROUND TRIP, akan menghasilkan satu PNR

    # journeys_provider = {
    #     'citilink': {
    #         1 : [
    #             {segment},
    #             {segment}
    #         ],
    #         2: [
    #             {segment},
    #             {segment}
    #         ]
    #
    #     },
    #     'airaisa': {
    #         1: [
    #             {segment},
    #             {segment}
    #         ]
    #     }
    # }

    j_provider_tmp = {}
    seg_seq = 0
    provider_sequence = {}
    for j in journey_codes:
        for s in j['segments']:
            seg_seq += 1
            seg = segment_code_to_dict(s['segment_code'])
            seg.update({
                # 'provider_sequence': provider_sequence,
                'sequence': seg_seq,
                'segment_code': s['segment_code'],
                'journey_type': j['journey_type'],
                'fare_code': s['fare_code'],
                'subclass': s.get('subclass', ''),
                'class_of_service': s.get('class_of_service', ''),
                'cabin_class': s.get('cabin_class', ''),
            })
            if j_provider_tmp.get(s['provider']):
                # Cek Open-Jaw Trip, jika iya, buat provider_sequence baru, ini akan menyebabkan request PNR BARU
                if s['provider'] not in ['sabre', 'altea'] and j_provider_tmp[s['provider']][-1]['destination'] != seg['origin']:
                    provider_sequence[s['provider']] += 1
                seg['provider_sequence'] = provider_sequence[s['provider']]
                j_provider_tmp[s['provider']].append(seg)
            else:
                provider_sequence[s['provider']] = 1
                seg['provider_sequence'] = 1
                j_provider_tmp[s['provider']] = [seg]

    journeys_provider = {}
    for provider in j_provider_tmp.keys():
        for seg in j_provider_tmp[provider]:
            if journeys_provider.has_key(provider):
                if journeys_provider[provider].has_key(seg['provider_sequence']):
                    journeys_provider[provider][seg['provider_sequence']].append(seg)
                else:
                    journeys_provider[provider][seg['provider_sequence']] = [seg]
            else:
                journeys_provider[provider] = {
                    seg['provider_sequence']: [seg]
                }
    return journeys_provider

def _jouneys_booking_groupby_provider_2(journey_codes):
    # j_provider_tmp = dict, provider_sequence, check pastikan destination-0 == origin-1,
    # jika tidak sama maka provider_sequence di tambahkan
    # setiap satu provider_sequence = satu ROUND TRIP, akan menghasilkan satu PNR

    # journeys_provider = {
    #     'citilink': {
    #         1 : [
    #             {segment},
    #             {segment}
    #         ],
    #         2: [
    #             {segment},
    #             {segment}
    #         ]
    #
    #     },
    #     'airaisa': {
    #         1: [
    #             {segment},
    #             {segment}
    #         ]
    #     }
    # }

    j_provider_tmp = {}
    seg_seq = 0
    provider_sequence = {}
    for j in journey_codes:
        for s in j['segments']:
            seg_seq += 1
            seg = segment_code_to_dict(s['segment_code'])
            s['departure_date'] = datetime.strptime(seg['departure_date'], '%Y-%m-%d %H:%M:%S')
            # leg_codes bisa berisi '', apabila False diisi segment_code
            leg_codes = s.get('leg_codes', s['segment_code']) and s.get('leg_codes', s['segment_code']) or s['segment_code']
            leg_codes = leg_codes.split(';')
            legs = []
            for leg_code in leg_codes:
                leg = segment_code_to_dict(leg_code)
                leg.update({
                    'leg_code': leg_code,
                    'journey_type': j['journey_type']
                })
                legs.append(leg)

            seg.update({
                # 'provider_sequence': provider_sequence,
                'sequence': seg_seq,
                'segment_code': s['segment_code'],
                'journey_type': j['journey_type'],
                'fare_code': s['fare_code'],
                'subclass': s.get('subclass', ''),
                'class_of_service': s.get('class_of_service', ''),
                'cabin_class': s.get('cabin_class', ''),
                'legs': legs,
            })
            if j_provider_tmp.get(s['provider']):
                # Cek Open-Jaw Trip, jika iya, buat provider_sequence baru, ini akan menyebabkan request PNR BARU
                if s['provider'] not in ['sabre', 'altea'] and j_provider_tmp[s['provider']][-1]['destination'] != seg['origin']:
                    provider_sequence[s['provider']] += 1
                seg['provider_sequence'] = provider_sequence[s['provider']]
                j_provider_tmp[s['provider']].append(seg)
            else:
                provider_sequence[s['provider']] = 1
                seg['provider_sequence'] = 1
                j_provider_tmp[s['provider']] = [seg]

    ### ### ### ### ### ###

    # provider_ids = set()
    # book_providers = sorted(journey_codes, key=lambda r: r['segments'][0]['departure_date'])
    # for rec in book_providers:
    #     for seg in rec['segments']:
    #         provider_ids = provider_ids.union(seg['provider'])
    # provider_ids = list(provider_ids)

    book_providers = sorted(journey_codes, key=lambda r: r['segments'][0]['departure_date'])
    provider_ids = []
    [provider_ids.append(seg['provider']) for rec in book_providers for seg in rec['segments'] if seg['provider'] not in provider_ids]

    ### ### ### ### ### ###

    journeys_provider = {}
    for provider in j_provider_tmp.keys():
        for seg in j_provider_tmp[provider]:
            if provider in journeys_provider:
                if seg['provider_sequence'] in journeys_provider[provider]:
                    journeys_provider[provider][seg['provider_sequence']].append(seg)
                else:
                    journeys_provider[provider][seg['provider_sequence']] = [seg]
            else:
                journeys_provider[provider] = {
                    seg['provider_sequence']: [seg]
                }
    return journeys_provider, provider_ids

def _navitary_create_journey_summary_price(journey_dict, adult, child, infant):
    tmp = {}
    for s in journey_dict['segments']:
        for p in s['pax_fares']:
            for sc in p['service_charges']:
                key = p['pax_type'] + ';' + sc['charge_code']
                if key not in tmp.keys():
                    tmp[key] = {
                        'amount': 0,
                        'foreign_amount': 0,
                        'currency': sc['currency'],
                        'foreign_currency': sc['foreign_currency']
                    }
                tmp[key]['amount'] += sc['amount']
                tmp[key]['foreign_amount'] += sc['foreign_amount']
    pass_count = {
        'ADT': adult,
        'CHD': child,
        'INF': infant
    }
    summary_tmp = {}
    for key in tmp.keys():
        keys = key.split(';')
        pax_type = keys[0]
        if pax_type not in summary_tmp.keys():
            summary_tmp[pax_type] = {
                'pax_type': keys[0],
                'service_charges': []
            }

        sc_tmp = {
            # 'charge_code': keys[1],
            'charge_code': keys[1],
            'pax_type': pax_type,
            'passanger_count': pass_count[pax_type] if pax_type in ['ADT', 'CHD', 'INF'] else 1
        }
        sc_tmp.update(tmp[key])
        summary_tmp[pax_type]['service_charges'].append(sc_tmp)

    journey_dict['summary_service_charges'] = []
    for key in summary_tmp.keys():
        journey_dict['summary_service_charges'].append(summary_tmp[key])
    return summary_tmp


def _navitary_get_prices_itinerary_marriage_segment(response, journeys_booking_by_provider, adult, child, infant):
    journeys = response['prices_itinerary'].pop('journeys')
    journey_DP = {}
    journey_RT = {}
    seg_RT = []

    for key in journeys_booking_by_provider.keys():

        if key == 'RT':
            seg_RT = [seg['segment_code'] for seg in journeys_booking_by_provider[key]]
            journey_RT = {
                'direction': 'RT',
                'journey_code': ';'.join(seg_RT),
                'segments': []
            }
        else:
            # seg_DP = j['journey_code'].split(';')
            journey_DP = {
                'direction': 'DP',
                'journey_code': ';'.join([seg['segment_code'] for seg in journeys_booking_by_provider[key]]),
                'segments': []
            }

    for j in journeys:
        if j['journey_code'] in seg_RT:
            for s in j['segments']:
                journey_RT['segments'].append(s)
        else:
            for s in j['segments']:
                journey_DP['segments'].append(s)

    response['prices_itinerary']['journeys'] = []
    if journey_DP:
        _navitary_create_journey_summary_price(journey_DP, adult, child, infant)
        response['prices_itinerary']['journeys'].append(journey_DP)
    if journey_RT:
        _navitary_create_journey_summary_price(journey_RT, adult, child, infant)
        response['prices_itinerary']['journeys'].append(journey_RT)
    return response
