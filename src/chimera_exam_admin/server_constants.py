"""
Server constants for exam administration system
"""
from pathlib import Path

# Database path
DEFAULT_DB_PATH = Path.cwd() / 'data'

# Debug flags
DEBUG = False
DEBUG_RR_CASE = False
DEBUG_RR_SET = False
DEBUG_LC_CASE = False
DEBUG_LC_SET = False
DEBUG_REPORT = False
DEBUG_FINALISE = False
DEBUG_NEW_SESSION = False

# RR Answer field names
RR_NORMAL = 'RR_Normal'
RR_ABNORMAL = 'RR_Abnormal'
RR_DESC = 'RR_Desc'

# For report generation
DEBUG_REPORT = False
TEMP_REPORT_SUBDIR = 'temp_report_pdfs'

RR_NORMAL = "RR_Normal"
RR_ABNORMAL = "RR_Abnormal"
RR_DESC = "RR_Desc"
LC_OBS = "LC_OBS"
LC_INT = "LC_INT"
LC_PDX = "LC_PDX"
LC_DDX = "LC_DDX"
LC_MX = "LC_MX"

LC_OBS_TITLE = "Observations"
LC_INT_TITLE = "Interpretation"
LC_PDX_TITLE = "Primary Differential Diagnosis"
LC_DDX_TITLE = "Differential Diagnoses"
LC_MX_TITLE = "Management"

ANS_BLANK = "-- left blank --"
