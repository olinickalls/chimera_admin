from serverconstants import (
    DEFAULT_DB_PATH,
    DEBUG,
    DEBUG_RR_CASE,
    DEBUG_RR_SET,
    DEBUG_LC_CASE,
    DEBUG_LC_SET,
    DEBUG_REPORT,
    DEBUG_FINALISE,
    DEBUG_NEW_SESSION,
    RR_NORMAL,
    RR_ABNORMAL,
    RR_DESC
)
from pathlib import Path
import sqlite3
from sqlite3 import Error
import serverreport as report
import uuid
import datetime
import pprint
from typing import Optional

from logsystem import logger

from pydanticmodels import (
    # RR_Ans,  # Can this be removed?
    RR_Ans_bare,
    RR_Set,
    LC_Set,
    LC_Ans_bare,
    Session,
    New_Session_Data,
    Finalise_Session_Detail
)

pp = pprint.PrettyPrinter(indent=4)


# Manage the server DB interactions

class chimera_server_db():
    def __init__(self, db_file,
                 test_on_start=True,
                 clean_start=False):
        # Use SQL DB to store answers
        # 3 tables:
        # 1- Users & instances (start_time & UID)
        # 2- RR answers (key = UID)
        # 3- LC answers (key = UID)

        given_db_fp = Path(db_file)
        if given_db_fp.exists():
            self.db_fp = given_db_fp

        else:
            # Does the DB dir & file exist?
            if not DEFAULT_DB_PATH.exists():
                DEFAULT_DB_PATH.mkdir(parents=True, exist_ok=True)

            self.db_fp = DEFAULT_DB_PATH.joinpath(db_file)

        # Delete the existing DB file if instructed on startup
        if clean_start and self.db_fp.exists():
            self.db_fp.unlink()

        if not self.db_fp.exists():
            logger.info(f'*** Server DB file does not exist: {self.db_fp}')
            logger.info('*** Creating DB file...')
            self.create_new_db(include_test_data=True)
            self.mount_db()

        else:
            logger.info(f'*** Found DB file: {self.db_fp}')
            self.mount_db()

        if test_on_start:
            self.populate_fake_data()


    def create_new_db(self, include_test_data=False):
        try:
            self.connection = sqlite3.connect(self.db_fp)
            self.cursor = self.connection.cursor()
            logger.info(f'***[DB]*** Creating DB {self.db_fp}')

            logger.debug('\t\t *** Creating sessions table')
            # See the pydantic model in pydanticmodels.py
            SQL_create_sessions_table = ("CREATE TABLE sessions ("
                                        "id INTEGER PRIMARY KEY, "
                                        "uid TEXT NOT NULL, "
                                        "username TEXT NOT NULL, "
                                        "set_name INTEGER NOT NULL, "
                                        "set_type TEXT NOT NULL, "
                                        "device_name TEXT NOT NULL, "
                                        "start_dt TEXT NOT NULL,"
                                        "finalised INTEGER NOT NULL,"  # bool
                                        "pdf_filepath STRING"
                                        ");")
            self.cursor.execute(SQL_create_sessions_table)
    
            logger.debug('\t\t *** Creating rr table')
            # See the pydantic model in pydanticmodels.py
            SQL_create_rr_table = ("CREATE TABLE rr_answers ("
                                    "id INTEGER PRIMARY KEY, "
                                    "uid TEXT NOT NULL, "
                                    "case_number INTEGER NOT NULL, "
                                    "rr_normal INTEGER NOT NULL, "  # Bool
                                    "rr_abnormal INTEGER NOT NULL, "  # Bool
                                    "rr_desc TEXT NOT NULL, "
                                    "FOREIGN KEY (uid) REFERENCES sessions (uid)"
                                    ");")
            self.cursor.execute(SQL_create_rr_table)

            logger.debug('\t\t *** Creating lc table')
            # See the pydantic model in pydanticmodels.py
            SQL_create_lc_table = ("CREATE TABLE lc_answers ("
                                    "id INTEGER PRIMARY KEY, "
                                    "uid TEXT NOT NULL, "
                                    "case_number INTEGER NOT NULL, "
                                    "LC_OBS TEXT NOT NULL, "
                                    "LC_INT TEXT NOT NULL, "
                                    "LC_PDX TEXT NOT NULL, "
                                    "LC_DDX TEXT NOT NULL, "
                                    "LC_MX TEXT NOT NULL, "
                                    "FOREIGN KEY (uid) REFERENCES sessions (uid)"
                                    ");")
            self.cursor.execute(SQL_create_lc_table)
            logger.debug('\t\t *** Done creating tables')

        except Error as e:
            logger.error(f"The error '{e}' occurred")


    def mount_db(self):
        try:
            self.connection = sqlite3.connect(self.db_fp)
            self.cursor = self.connection.cursor()
            logger.info(f'***[DB]*** Connected to DB {self.db_fp}')
        except Error as e:
            logger.error(f"The error '{e}' occurred")
        except Exception as e:
            logger.error(f"The Exception '{e}' occurred")


    def populate_fake_data(self, rr_sets=1, lc_sets=1):
        # use the fake data generator in reports.py
        # populate this directly into the DB

        for rr_set in range(rr_sets):
            new_dt = report.get_rnd_dt()
            uid = self.create_session(username='TEST01',
                                      set_type="RR",
                                      set_name='RR SET 99',
                                      device_name='SURAFCE',
                                      start_dt=new_dt
                                      )

            rr_answers = report.generate_fake_rr_answers()
            rr_set_name = rr_answers['set_name']

            for casen in rr_answers['case'].keys():
                txt = f'---[DB Fake RR] set {rr_set} ({rr_set_name}) case {casen}'
                case = rr_answers['case'][casen]
                case['case_n'] = casen
                case['uid'] = uid

                rr_case_answer = RR_Ans_bare.model_validate(case)
                self.store_rr_case(rr_case=rr_case_answer, uid=uid, txt=txt)
                logger.trace('\t-Done creating RR case data.')
            logger.debug('\t-Done creating RR set data.')

    # ###################################################################
    # ########      Base Functions                               ########
    # ###################################################################


    def create_session(self,
                       username,
                       set_type,
                       set_name,
                       device_name,
                       start_dt,
                       uid=None
                       ):
        # Begin a NEW session
        if not uid:
            uid = f'{username}|{set_name}_{uuid.uuid4()}'
        logger.debug(f'\n\t[serverDB create_session] {uid}, {username}, {set_name}, {device_name}, {start_dt}')

        
        SQL_NEW_SESSION = ("INSERT INTO sessions"
                           "(uid, username, set_type, set_name, device_name, start_dt, finalised) "
                           "VALUES "
                           "(?, ?, ?, ?, ?, ?, ?);")
        params = (uid, username, set_type, set_name, device_name, start_dt, 0)

        # self.execute_query(SQL_NEW_SESSION, txt='Creating Session')
        self.execute_param_query(SQL_NEW_SESSION, params, txt='Creating Session')
        return uid


    def finalise_session(self, sess: Finalise_Session_Detail):
        '''
        Take a finalise_session_detail object from the API
        'Close the session by setting the 'finalised' flag in sesions table.
        '''
        logger.debug('finalise_session')
        query = ("UPDATE sessions"
                " SET finalised=True"
                " WHERE uid=?;")
        params = (sess.uid,)
        msg = f'Finalising session uid={sess.uid}'

        db_response = self.execute_param_query(query, params=params, txt=msg)

        if db_response is None:
            return 'No Error'

        elif isinstance(db_response, Exception):
            return db_response.__repr__()

        else:
            return str(db_response)

    # ###################################################################
    # ########      RAPID REPORTING                              ########
    # ###################################################################


    def store_rr_case(self,
                      rr_case,
                      uid:str,
                      txt:str=None,
                      method:str=None
                      ):
        '''
        rr_ans (dict) must include all fields:
        { 'RR_Normal':   bool,
          'RR_Abnormal': bool,
          'RR_Desc':     str,
          'case_n':      INTEGER,
          'uid:          str
        }
        uid is needed to associate with the correct session
        '''
        if method is None:
            logger.trace('[store_rr_case] Checking existing cases')
            existing = self.get_rr_cases_by_uid(uid=uid)
            logger.trace(f'[store_rr_case] Found: {existing}')

            if rr_case.case_n not in existing:
                method = 'INSERT'
            else:
                method = 'UPDATE'
        elif method not in ['UPDATE', 'INSERT']:
            raise(ValueError(f"Unknown method value: {method}"))

        if method == 'INSERT':
            logger.trace('INSERT')
            new_rr_data =  ("INSERT INTO "
                            "rr_answers (uid, case_number, rr_normal, rr_abnormal, rr_desc) "
                            "VALUES (?, ?, ?, ?, ?);")
            params = (uid,
                      rr_case.case_n,
                      1 if bool(rr_case.RR_Normal) else 0,
                      1 if bool(rr_case.RR_Abnormal) else 0,
                      rr_case.RR_Desc
                      )

        elif method == 'UPDATE':
            logger.trace('UPDATE')
            new_rr_data = ("UPDATE rr_answers"
                           " SET rr_normal=?,"
                           "    rr_abnormal=?,"
                           "    rr_desc=?"
                           " WHERE uid=? AND case_number=?"
                        )
            params = (1 if bool(rr_case.RR_Normal) else 0,
                      1 if bool(rr_case.RR_Abnormal) else 0,
                      rr_case.RR_Desc,
                      uid,
                      rr_case.case_n)

        else:
            logger.error(f"Unknown method value: {method}")
            raise(ValueError(f"Unknown method value: {method}"))

        msg = '[Store RR Case]' + str(txt)
        db_response = self.execute_param_query(new_rr_data, params=params, txt=msg)

        logger.trace(f'[store_rr_case] [raw db response] {db_response}')

        if db_response is None:
            logger.debug('[store_rr_case] No error')
            return 'No Error'
        elif type(db_response)is Exception:
            logger.error('[store_rr_case] Exception')
            logger.error(f'[store_rr_case] db_response: {db_response.__repr__()}')
            return db_response.__repr__()
        else:
            logger.trace('[store_rr_case] Other')
            return str(db_response)


    def exists_rr_case(self,
                      rr_case,
                      uid:str,
                      txt:str=None
                      ):
        '''
        Checks for the existance of a single case at a time
        True if exists in te DB
        '''
        cases_in_DB = self.get_rr_casen_by_uid(uid)
        if rr_case.case_n in cases_in_DB:
            return True
        else:
            return False


    def store_rr_set(self, rr_set:RR_Set):
        '''
        the rr set dict should be like this:

        '''
        uid = rr_set.uid
        candidateID = rr_set.candidateID
        device_name = rr_set.device_name
        start_time = rr_set.start_time
        set_name = rr_set.set_name
        cases = rr_set.case
        logger.trace(f'[store_rr_set] {uid}, {candidateID}, {device_name}, {start_time}, {set_name}, {len(cases)} cases')
        # Is there an efficient way to write so many DB
        # In the meantime, I will write one case at a time

        # Pre-check if they exist before writing each 1 by 1
        existing_cases = self.get_rr_cases_by_uid(uid=uid)
        n_cases = len(cases.keys())

        for case in cases.keys():
            if case in existing_cases:
                method = 'UPDATE'
            else:
                method = 'INSERT'
            rr_case= cases[case]
            response = self.store_rr_case(rr_case,
                                          uid=uid,
                                          txt=f' store_rr_set ({case} of {n_cases})',
                                          method=method)
            if not isinstance(response, str):
                logger.error(f'[store_rr_set] Error storing case {case}')
                return response
        return 'Success'

    # ###################################################################
    # ########      LONG CASES                                   ########
    # ###################################################################

    def store_lc_case(self,
                      lc_case,
                      uid:str,
                      txt:str=None,
                      method:str=None
                      ):
        '''
        lc_ans (dict) must include all fields:
        { 
            'uid:          str,
            'case_n':      INTEGER,
            'LC_OBS': str,
            'LC_INT': str,
            'LC_PDX': str,
            'LC_DDX': str,
            'LC_MX': str,
        }
        uid is needed to associate with the correct session
        '''
        if method is None:
            logger.trace('[store_lc_case] Checking existing cases')
            existing = self.get_lc_cases_by_uid(uid=uid)
            logger.trace(f'[store_lc_case] Found: {existing}')

            if lc_case.case_n not in existing:
                method = 'INSERT'
            else:
                method = 'UPDATE'
        elif method not in ['UPDATE', 'INSERT']:
            raise(ValueError(f"Unknown method value: {method}"))

        if method == 'INSERT':
            logger.trace('INSERT')
            new_lc_data =  ("INSERT INTO "
                            "lc_answers (uid, "
                            "case_number, "
                            "LC_OBS, "
                            "LC_INT, "
                            "LC_PDX, "
                            "LC_DDX, "
                            "LC_MX "
                            ") VALUES (?, ?, ?, ?, ?, ?, ?);")
            params = (uid,
                      lc_case.case_n,
                      lc_case.LC_OBS,
                      lc_case.LC_INT,
                      lc_case.LC_PDX,
                      lc_case.LC_DDX,
                      lc_case.LC_MX,
                      )

        elif method == 'UPDATE':
            logger.trace('UPDATE')
            new_lc_data = ("UPDATE lc_answers"
                           " SET "
                            "LC_OBS=?, "
                            "LC_INT=?, "
                            "LC_PDX=?, "
                            "LC_DDX=?, "
                            "LC_MX=? "
                           " WHERE uid=? AND case_number=?"
                        )
            params = (lc_case.LC_OBS,
                      lc_case.LC_INT,
                      lc_case.LC_PDX,
                      lc_case.LC_DDX,
                      lc_case.LC_MX,
                      uid,
                      lc_case.case_n)

        else:
            logger.error(f"Unknown method value: {method}")
            raise(ValueError(f"Unknown method value: {method}"))

        msg = '[Store LC Case] ' + str(txt)

        logger.debug(msg)
        logger.trace(f'SQL Query: {new_lc_data}')
        logger.trace(f'SQL params: {params}')

        db_response = self.execute_param_query(new_lc_data,
                                               params=params,
                                               txt=msg)

        logger.trace(f'[store_lc_case] [raw db response] {db_response}')


        if db_response is None:
            logger.debug('[store_lc_case] No error')
            return 'No Error'
        elif type(db_response)is Exception:
            logger.error('[store_lc_case] Exception')
            logger.error(f'[store_lc_case] db_response: {db_response.__repr__()}')
            return db_response.__repr__()
        else:
            logger.trace('[store_lc_case] db response- Other')
            return str(db_response)


    # ###################################################################

    def store_lc_set(self, lc_set:LC_Set):
        '''
        the lc set dict should be like this (very similar to rr_set):

        '''
        uid = lc_set.uid
        candidateID = lc_set.candidateID
        device_name = lc_set.device_name
        start_time = lc_set.start_time
        set_name = lc_set.set_name
        cases = lc_set.case
        logger.debug(f'[store_lc_set] {uid}, {candidateID}, {device_name}, {start_time}, {set_name}, {len(cases)} cases')

        # Pre-check if they exist before writing each 1 by 1
        existing_cases = self.get_lc_cases_by_uid(uid=uid)
        n_cases = len(cases.keys())

        for case in cases.keys():
            if case in existing_cases:
                method = 'UPDATE'
            else:
                method = 'INSERT'
            lc_case= cases[case]
            logger.debug("[LC_SET] {method} case {case} of {n_cases}",
                         method=method, case=case, n_cases=n_cases)
            response = self.store_lc_case(lc_case,
                                          uid=uid,
                                          txt=f' store_lc_set ({case} of {n_cases})',
                                          method=method)
            if not isinstance(response, str):
                logger.error('[store_rr_set] Error storing case {case}', case=case)
                return response
        return 'Success'


    # ###################################################################
    # ###################################################################
    # ###################################################################

    def _build_session_model(self, record: dict) -> Session:
        payload = {
            'uid': str(record.get('uid', '')),
            'username': str(record.get('username', '')),
            'set_name': str(record.get('set_name', '')),
            'set_type': str(record.get('set_type', '')),
            'device_name': str(record.get('device_name', '')),
            'start_dt': str(record.get('start_dt', '')),
            'finalised': bool(record.get('finalised', False)),
        }
        return Session.model_validate(payload)

    def _build_rr_case_model(self, uid: str, row: tuple) -> RR_Ans_bare:
        payload = {
            'uid': uid,
            'case_n': int(row[0]),
            'RR_Normal': bool(row[1]),
            'RR_Abnormal': bool(row[2]),
            'RR_Desc': str(row[3]),
        }
        return RR_Ans_bare.model_validate(payload)

    def _build_lc_case_model(self, uid: str, row: tuple) -> LC_Ans_bare:
        payload = {
            'uid': uid,
            'case_n': int(row[0]),
            'LC_OBS': str(row[1]),
            'LC_INT': str(row[2]),
            'LC_PDX': str(row[3]),
            'LC_DDX': str(row[4]),
            'LC_MX': str(row[5]),
        }
        return LC_Ans_bare.model_validate(payload)

    def _validate_session_records(self, records: list[dict]) -> list[dict]:
        validated_records = []
        for record in records:
            try:
                session_model = self._build_session_model(record)
                validated_records.append(session_model.model_dump())
            except Exception as exc:
                logger.error(f'Failed to validate session record for uid={record.get("uid")}: {exc}')
        return validated_records

    def query_open_sessions(self):
        '''
        Returns a dict of open sessions
        '''
        query = '''
        SELECT uid, username, set_name, set_type, device_name, start_dt, finalised
        FROM sessions
        WHERE finalised=0
        '''
        reply = self.cursor.execute(query)
        results = self.fetch_all_as_dict(reply)
        return self._validate_session_records(results)

    def query_all_sessions(self):
        '''
        Returns a dict of all sessions
        '''
        query = '''
        SELECT uid, username, set_name, set_type, device_name, start_dt, finalised
        FROM sessions
        '''
        reply = self.cursor.execute(query)
        results = self.fetch_all_as_dict(reply)
        return self._validate_session_records(results)

    def query_closed_sessions(self):
        '''
        Returns a dict of closed sessions
        '''
        query = '''
        SELECT uid, username, set_name, set_type, device_name, start_dt, finalised
        FROM sessions
        WHERE finalised=1
        '''
        reply = self.cursor.execute(query)
        results = self.fetch_all_as_dict(reply)
        return self._validate_session_records(results)

    def get_session_by_uid(self, uid: str) -> Optional[Session]:
        query = '''
        SELECT uid, username, set_name, set_type, device_name, start_dt, finalised
        FROM sessions
        WHERE uid=?
        '''
        try:
            reply = self.cursor.execute(query, (uid,))
            records = self.fetch_all_as_dict(reply)
            if not records:
                return None
            return self._build_session_model(records[0])
        except Exception as exc:
            logger.error(f'Error loading session uid={uid}: {exc}')
            return None

    def get_answers_obj_by_uid(self,
                               uid
                               ):
        '''
        Check type - RR or LC
        get list of answers accordingly and populate the answers object
        '''
        logger.debug(f'starting get_answers_obj_by_uid [uid: {uid}]')
        # ### Query sessions table:
        query = ("SELECT set_type, finalised, set_name, username, device_name, start_dt"
                " FROM sessions"
                " WHERE uid=?"
                )
        params = (uid, )
        msg = f'Extracting session details for {uid}'

        logger.debug('[DEBUG] [get_answers_obj_by_uid] msg: {msg}')
        logger.debug(f'[DEBUG] query: {query}')
        logger.debug(f'[DEBUG] params: {params}')
 
        results = self.execute_param_query_fetch(query,
                                                 params,
                                                 txt=msg,
                                                 fetchall=True
                                                 )
        logger.debug(f'Query result: {pprint.pformat(results)}')

        answers = None
        for i, item in enumerate(results):
            logger.debug(f'\t{i:3}:{item}')

            answers = {'type': item[0],
                'final': item[1],
                'set_id': 'SET-ID',
                'set_name': item[2],
                'candidateID': item[3],
                'device_name:': item[4],
                'start_time': item[5],
                'case': {}
            }
            logger.debug(f'Answers: {pprint.pformat(answers)}')

        logger.debug(f"Answers are for type: {answers['type']}")

        if answers['type'] == 'RR':
            logger.trace(f'Looking for Rapids answers from UID {uid}')

            # ### Query rr_answers table:
            query = ("SELECT case_number, rr_normal, rr_abnormal, rr_desc"
                    " FROM rr_answers"
                    " WHERE uid=?"
                    " ORDER BY case_number ASC")
            params = (uid, )
            msg = f'Extracting rr answers for {uid}'

            logger.debug(f'query: {query}\n\tParams: {params}')
            case_results = self.execute_param_query(query, params, txt=msg)

            for i, item in enumerate(case_results):
                logger.trace(f'\t\t{i}: {item}')
                answers['case'][item[0]] = {
                    RR_NORMAL: item[1],
                    RR_ABNORMAL: item[2],
                    RR_DESC: item[3]
                }

        elif answers['type'] == 'LC':
            logger.trace(f'Looking for Long Case answers from UID {uid}')

            # ### Query lc_answers table:
            query = ("SELECT case_number, LC_OBS, LC_INT, LC_PDX, LC_DDX, LC_MX "
                    "FROM lc_answers "
                    "WHERE uid=?")
            params = (uid, )
            msg = f'Extracting lc answers for {uid}'

            logger.debug(f'query: {query}\n\tParams: {params}')
            case_results = self.execute_param_query(query, params, txt=msg)

            for i, item in enumerate(case_results):
                logger.trace(f'\t\t{i}: {item}')
                answers['case'][item[0]] = {
                    'LC_OBS': item[1],
                    'LC_INT': item[2],
                    'LC_PDX': item[3],
                    'LC_DDX': item[4],
                    'LC_MX': item[5]
                }

        return answers

    def fetch_all_as_dict(self, cursor):
        # Get column names from the cursor description
        column_names = [description[0] for description in cursor.description]
        
        try:
            # Fetch all rows from the cursor
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
        
        # Convert rows to list of dictionaries
        result = [dict(zip(column_names, row)) for row in rows]
        
        return result


    def execute_query(self,
                      query,
                      txt=''
                      ):
        try:
            results = self.cursor.execute(query)
            self.connection.commit()
            logger.debug(f"\t[DB SExecute] '{txt}' Query successful")
        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
        except Error as e:
            logger.error(f"\t[DB SExecute] The error '{e}' occurred during '{txt}'\n{query}")
            return e
        return results


    def execute_param_query(self,
                            query,
                            params,
                            txt=''
                            ):
        try:
            results = self.cursor.execute(query, params)
            self.connection.commit()
            logger.debug(f"\t[DB PExecute] '{txt}' Query successful")
        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
            return e
        except Exception as e:
            logger.error(f"\t[DB PExecute] The error '{e}' occurred during '{txt}'\n{query} | {params}")
            return e
        return results


    def execute_param_query_fetch(self,
                            query,
                            params,
                            txt='',
                            fetchall=False
                            ):
        try:
            results = self.cursor.execute(query, params)
            self.connection.commit()
            logger.debug(f"\t[DB PExecute] '{txt}' Query successful")
        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
        except Exception as e:
            logger.error(f"\t[DB PExecute] The error '{e}' occurred during '{txt}'\n{query} | {params}")
            return e
        return results



    # ######################## HELPER FUNCTIONS  ########################
    def get_unique_uids(self, table='sessions'):
        '''
        Queries 'table' for unique UIDs based on type
        table can only be 'sessions', 'rr_answers' or 'lc_answers'
        '''
        if table not in ['sessions', 'rr_answers' or 'lc_answers']:
            raise(ValueError(f"Unknown table: {table}"))
        query = '''
        SELECT DISTINCT uid FROM ?
        '''
        results = self.cursor.execute(query, (table,))
        uids = []
        for item in results:
            uids.append(item[0])
        return uids

    def get_rr_cases_by_uid(self, uid):
        '''
        Returns a list of existing RR cases for a given UID
        '''
        query = '''
        SELECT case_number FROM rr_answers
        WHERE uid=?'''

        try:
            reply = self.cursor.execute(query, (uid,))
            results = self.fetch_all_as_dict(reply)

        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
            results = []
        except Exception as e:
            logger.error(f"\t[DB] The error '{e}' occurred during get_rr_cases_by_uid")
            results = []

        cases = []
        for item in results:
            cases.append(item['case_number'])

        return cases

    def get_lc_cases_by_uid(self, uid):
        '''
        Returns a list of existing LC cases for a given UID
        '''
        query = '''
        SELECT case_number FROM lc_answers
        WHERE uid=?'''

        try:
            reply = self.cursor.execute(query, (uid,))
            results = self.fetch_all_as_dict(reply)

        except sqlite3.Error as e:
            logger.error(f'A SQL error occurred: {e}')
            results = []
        except Exception as e:
            logger.error(f"\t[DB] The error '{e}' occurred during get_lc_cases_by_uid")
            results = []

        cases = []
        for item in results:
            cases.append(item['case_number'])

        return cases


    def get_rr_case(self, uid, case_n):
        '''
        Specific single RR case lookup
        return the case as json
        '''
        query = '''
        SELECT case_number, rr_normal, rr_abnormal, rr_desc 
        FROM rr_answers
        WHERE uid=? AND case_number=?
        '''
        # params = {
        #     'uid': uid,
        #     'case_number': case_n
        # }
        logger.debug(f'[SQL Query]: {query}')

        dbreply = self.cursor.execute(query, (uid, case_n))
        n_list = []
        for item in dbreply:
            n_list.append(item)
        return n_list

    def get_rr_case_model(self, uid: str, case_n: int) -> Optional[RR_Ans_bare]:
        query = '''
        SELECT case_number, rr_normal, rr_abnormal, rr_desc
        FROM rr_answers
        WHERE uid=? AND case_number=?
        '''
        try:
            result = self.cursor.execute(query, (uid, case_n)).fetchone()
            if not result:
                return None
            return self._build_rr_case_model(uid, result)
        except Exception as exc:
            logger.error(f'Error loading RR case uid={uid} case={case_n}: {exc}')
            return None

    def get_lc_case_model(self, uid: str, case_n: int) -> Optional[LC_Ans_bare]:
        query = '''
        SELECT case_number, LC_OBS, LC_INT, LC_PDX, LC_DDX, LC_MX
        FROM lc_answers
        WHERE uid=? AND case_number=?
        '''
        try:
            result = self.cursor.execute(query, (uid, case_n)).fetchone()
            if not result:
                return None
            return self._build_lc_case_model(uid, result)
        except Exception as exc:
            logger.error(f'Error loading LC case uid={uid} case={case_n}: {exc}')
            return None


def random_uid():
    return str(uuid.uuid4())


def get_current_dt_dict():
    dt = datetime.datetime.now()
    dt_dict = {
    'yyyy': dt.year,
    'mm': dt.month,
    'dd': dt.day,
    'HH': dt.hour,
    'MM': dt.minute,
    'SS': dt.second
    }
    return dt_dict


def get_current_dt_str():
    dt = datetime.datetime.now()
    dt_str = f'{dt.year:04}-{dt.month:02}-{dt.day:02} {dt.hour:02}:{dt.minute:02}:{dt.second:02}'
    return dt_str
