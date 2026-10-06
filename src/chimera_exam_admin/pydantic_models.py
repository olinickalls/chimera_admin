
from pydantic import BaseModel


class RRAnsBare(BaseModel):
    uid: str
    case_n: int

    RR_Normal: bool
    RR_Abnormal: bool
    RR_Desc: str


class RRAnsQuery(BaseModel):
    uid: str
    case_n: int


class RRSet(BaseModel):
    uid: str
    candidateID: str
    device_name: str
    start_time: str
    set_name: str
    set_id: int

    case: dict[int, RRAnsBare]
    type: str


class LCAnsBare(BaseModel):
    uid: str
    case_n: int

    LC_OBS: str
    LC_INT: str
    LC_PDX: str
    LC_DDX: str
    LC_MX: str


class LCSet(BaseModel):
    uid: str
    candidateID: str
    device_name: str
    start_time: str
    set_name: str
    set_id: int

    case: dict[int, LCAnsBare]
    type: str


class Session(BaseModel):
    uid: str
    username: str
    set_name: str
    set_type: str
    device_name: str
    start_dt: str
    finalised: bool
    final_dt: str | None = None
    pdf: bool = False
    pdf_dt: str | None = None


class NewSessionData(BaseModel):
    username: str
    set_name: str
    set_type: str
    device_name: str
    start_dt: str


class FinaliseSessionDetail(BaseModel):
    uid: str
    username: str
    set_name: str
    set_type: str
    device_name: str


# Backwards-compatible aliases for legacy imports.
RR_Ans_bare = RRAnsBare
RR_Ans_Query = RRAnsQuery
RR_Set = RRSet
LC_Ans_bare = LCAnsBare
LC_Set = LCSet
New_Session_Data = NewSessionData
Finalise_Session_Detail = FinaliseSessionDetail


