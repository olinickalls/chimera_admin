from pydantic import BaseModel
from typing import Dict, Optional

# # For when a single RR case is sent
# class RR_Ans(BaseModel):
#     candidateID: str
#     device_name: str
#     start_time: str
#     set_name: str
#     case_n: int
#     RR_Normal: bool
#     RR_Abnormal: bool
#     RR_Desc: str
#     uid: str


# Sub-part of the whole RR_SET
class RR_Ans_bare(BaseModel):
    uid: str
    case_n: int

    RR_Normal: bool
    RR_Abnormal: bool
    RR_Desc: str


# RR_Ans query for single answer
class RR_Ans_Query(BaseModel):
    uid: str
    case_n: int


# A whole RR SET answer in one
class RR_Set(BaseModel):
    uid: str
    candidateID: str
    device_name: str
    start_time: str
    set_name: str
    set_id: int

    case: Dict[int, RR_Ans_bare]
    type: str


# Sub-part of the whole LC_SET
class LC_Ans_bare(BaseModel):
    uid: str
    case_n: int

    LC_OBS: str
    LC_INT: str
    LC_PDX: str
    LC_DDX: str
    LC_MX: str


# A whole LC SET answer in one
class LC_Set(BaseModel):
    uid: str
    candidateID: str
    device_name: str
    start_time: str
    set_name: str
    set_id: int

    case: Dict[int, LC_Ans_bare]
    type: str

# session model- one per started exam session
class Session(BaseModel):
    uid: str
    username: str
    set_name: str
    set_type: str
    device_name: str
    start_dt: str
    finalised: bool
    final_dt: Optional[str] = None
    pdf: bool = False
    pdf_dt: Optional[str] = None

class New_Session_Data(BaseModel):
    username: str
    set_name: str
    set_type: str
    device_name: str
    start_dt: str

class Finalise_Session_Detail(BaseModel):
    uid: str
    username: str
    set_name: str
    set_type: str
    device_name: str


