"""
Server reporting module
"""
import datetime
import random


def generate_fake_rr_answers():
    """Generate fake RR answers for testing"""
    set_name = f'RR SET {random.randint(1, 99)}'
    n_cases = random.randint(5, 10)
    
    cases = {}
    for i in range(1, n_cases + 1):
        cases[i] = {
            'RR_Normal': random.choice([True, False]),
            'RR_Abnormal': random.choice([True, False]),
            'RR_Desc': f'Test description for case {i}'
        }
    
    return {
        'set_name': set_name,
        'case': cases
    }

def get_rnd_dt():
    """Generate random datetime string"""
    dt = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 365))
    return f'{dt.year:04}-{dt.month:02}-{dt.day:02} {dt.hour:02}:{dt.minute:02}:{dt.second:02}'
