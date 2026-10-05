from reportlab.platypus import (
    Table,
    Paragraph,
    SimpleDocTemplate,
    PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from .server_constants import (
    TEMP_REPORT_SUBDIR,
    DEBUG_REPORT,
    RR_NORMAL,
    RR_ABNORMAL,
    RR_DESC,
    LC_OBS,
    LC_INT,
    LC_PDX,
    LC_DDX,
    LC_MX,
    ANS_BLANK,
    LC_OBS_TITLE,
    LC_INT_TITLE,
    LC_PDX_TITLE,
    LC_DDX_TITLE,
    LC_MX_TITLE
)
from pathlib import Path
from .utils import get_safe_filename
from .log_system import logger
from xml.sax.saxutils import escape
import os


def reformat(strtxt: str):
    '''
    Convert the Python '\n' to '<br/>\n' which report lab understands
    '''
    return strtxt.replace('\n', '<br/>\n')


def device_header_line(answers) -> str:
    device_name = escape(str(answers.get('device_name', '')))
    return f'Device: <font name="Courier">{device_name}</font>'


def create_answer_pdf(answers, draft_status=False):
    '''
    Supply the .answers dict from answer sheet widget.
    Prototype (from Answer_sheet_widget() class def.)
        self.answers = {'type': self.parent.current_set_type,
                        'set_id': c_set_id,
                        'set_name': set_name,
                        'candidateID': 'Candidate X',
                        'case': {}
                        }    '''
    if DEBUG_REPORT:
        logger.debug(
            'Creating answer PDF | type={} set_id={} set_name={} candidate={} case_count={}',
            answers.get('type'),
            answers.get('set_id'),
            answers.get('set_name'),
            answers.get('candidateID'),
            len(answers.get('case', {})),
        )

    if answers['type'] == 'RR':
        pathPDF = create_rapids_pdf(answers, draft_status)
    elif answers['type'] == 'LC':
        pathPDF = create_longcase_pdf(answers, draft_status)
    else:
        logger.error('Cannot create answer PDF | unknown type={}', answers['type'])
        return None
    return pathPDF


def get_filename(fname: str = '', draft: bool = False):
    '''
    Adjust filename to make unique draft names to prevent clash'''
    now = datetime.now()
    if draft:
        dt_str = now.strftime("(%Y-%m-%d_%H-%M-%S.%f)")
        new_fname = fname + '_' + dt_str + '_draft.pdf'
        return new_fname

    else:
        dt_str = now.strftime("(%H-%M-%S.%f)")
        new_fname = fname + '_' + dt_str + '.pdf'
        return new_fname


def get_filepath(candID: str,
                 set_name: str,
                 draft: bool
                 ):
    '''
    Generate appropriate report filename for RR/LC and draft/final
    '''
    # ########## Report PATH ##########

    report_path = Path(os.getcwd()).joinpath(TEMP_REPORT_SUBDIR)

    # ########## Report Filename ##########

    base = get_safe_filename(f'{candID}-{set_name}')
    if draft:
        fname = get_filename(base, draft=True)
    else:
        fname = get_filename(base, draft=False)

    report_fp = report_path / Path(fname)
    report_fp.parent.mkdir(parents=True, exist_ok=True)

    return report_fp


def create_rapids_pdf(answers, draft=False, show_PDF=False):
    set_name = answers['set_name']  # string - set number != c_set_id
    candidate_ID = answers['candidateID']  # string

    report_fp = get_filepath(candID=answers['candidateID'],  # string,
                             set_name=answers['set_name'],  # string - set number != c_set_id,
                             draft=draft
                             )

    # DT for in-report use
    now = datetime.now()
    dt_str = now.strftime("%d %B, %Y")

    # Header style
    styleSheet = getSampleStyleSheet()
    h3 = styleSheet['Heading3']
    h3.spaceBefore = 0
    h3.spaceAfter = 0

    # Paragraph style in-table
    PARA_STYLE = styleSheet['Normal']
    PARA_STYLE.spaceBefore = 0
    PARA_STYLE.spaceAfter = 0
    PARA_STYLE.leading = 10
    PARA_STYLE.fontSize = 8

    # Data creation - one row per RR case answer
    data = []
    for i, rr_case_key in enumerate(answers['case'], start=1):
        if rr_case_key in [answers['case']]:
            continue
        row = []
        row.append(f'{i}.')
        rr_case = answers['case'][rr_case_key]
        if rr_case[RR_NORMAL] is True and rr_case[RR_ABNORMAL] is False:
            row.append(Paragraph('<b>N</b>ormal', PARA_STYLE))
        elif rr_case[RR_ABNORMAL] is True and rr_case[RR_NORMAL] is False:
            row.append(Paragraph('<b>Ab</b>normal', PARA_STYLE))
        else:  # both are False
            row.append(Paragraph('Not answered', PARA_STYLE))

        row.append(Paragraph(reformat(rr_case[RR_DESC]), PARA_STYLE))
        row.append(10 * ' ')
        data.append(row)

    # If no asnwer data -ie case started but no answer data sent, 'no data' entry to
    # make the blank table without error.
    if len(answers['case'])<1:
        # No answers in data. Record a 'no response' row.
        row = []
        row.append('-')
        row.append(Paragraph('no data', PARA_STYLE))
        row.append(Paragraph('no data', PARA_STYLE))
        row.append(10 * ' ')
        data.append(row)

    t = Table(data,
              colWidths=[0.3*inch, 0.9*inch, 5.7*inch, 0.5*inch],
              style=[  # ALL cells grey border
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    # case number Align Left
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ]
              )

    story = []
    story.append(Paragraph(f"""Rapids Marksheet {dt_str}<br/>
                            Set: {set_name}\t\tUser: {candidate_ID}<br/>
                            {device_header_line(answers)}""", h3))
    story.append(t)

    SimpleDocTemplate(str(report_fp),
                      pagesize=A4,
                      showBoundary=0
                      ).build(story)
    # Expand this with header/Footer from:
    # https://stackoverflow.com/questions/67702808
    if show_PDF:
        os.system(f'start {report_fp}')

    return report_fp


def create_longcase_pdf(answers, draft=False, show_PDF=False):
    set_name = answers['set_name']  # string - set number != c_set_id
    candidate_ID = answers['candidateID']  # string

    report_fp = get_filepath(candID=answers['candidateID'],  # string,
                             set_name=answers['set_name'],  # string - set number != c_set_id,
                             draft=draft
                             )
    now = datetime.now()
    dt_str = now.strftime("%d %B, %Y")

    # Header style
    styleSheet = getSampleStyleSheet()

    title = styleSheet['title']
    title.spaceBefore = 0
    title.spaceAfter = 6

    subtitle = styleSheet['Heading1']
    subtitle.spaceBefore = 0
    subtitle.spaceAfter = 6
    subtitle.fontSize = 12
    subtitle.alignment = TA_CENTER

    head_sty = styleSheet['Heading3']
    head_sty.spaceBefore = 12
    head_sty.spaceAfter = 8

    # Paragraph styles
    ans_sty = styleSheet['Normal']
    ans_sty.spaceBefore = 6
    ans_sty.spaceAfter = 6
    ans_sty.leftIndent = 10
    ans_sty.leading = 10
    ans_sty.fontSize = 8
    ans_sty.borderColor = '#808080'
    ans_sty.borderPadding = (5, 10, 5, 10)
    ans_sty.borderWidth = 0.5

    story = []

    # Paragraph creation - one Para per LC answer segment.
    # Titles and Section Headers
    top = Paragraph(f'Long Case Answer Sheet {dt_str}', style=title)
    top_data = Paragraph(
        f'Set: {set_name}\t\tUser: {candidate_ID}<br/>{device_header_line(answers)}',
        subtitle,
    )

    for case_n, case_id in enumerate(answers['case'], start=1):
        obs_head = Paragraph(f'{case_n}.1 {LC_OBS_TITLE}', head_sty)
        int_head = Paragraph(f'{case_n}.2 {LC_INT_TITLE}', head_sty)
        pdx_head = Paragraph(f'{case_n}.3 {LC_PDX_TITLE}', head_sty)
        ddx_head = Paragraph(f'{case_n}.4 {LC_DDX_TITLE}', head_sty)
        mx_head = Paragraph(f'{case_n}.5 {LC_MX_TITLE}', head_sty)

        case = answers['case'][case_id]
        case_title = Paragraph(f'Case {case_n}', subtitle)
        obs_ans = Paragraph(reformat(case[LC_OBS]), ans_sty)
        int_ans = Paragraph(reformat(case[LC_INT]), ans_sty)
        pdx_ans = Paragraph(reformat(case[LC_PDX]), ans_sty)
        ddx_ans = Paragraph(reformat(case[LC_DDX]), ans_sty)
        mx_ans = Paragraph(reformat(case[LC_MX]), ans_sty)

        # Answer Title and Demographics
        story.append(top)
        story.append(top_data)
        story.append(case_title)

        # Answer Headers & Text
        story.append(obs_head)
        story.append(obs_ans)

        story.append(int_head)
        story.append(int_ans)

        story.append(pdx_head)
        story.append(pdx_ans)

        story.append(ddx_head)
        story.append(ddx_ans)

        story.append(mx_head)
        story.append(mx_ans)

        story.append(PageBreak())

    SimpleDocTemplate(str(report_fp),
                      pagesize=A4,
                      showBoundary=0
                      ).build(story)
    # Expand this with header/Footer from:
    # https://stackoverflow.com/questions/67702808
    if show_PDF:
        os.system(f'start {report_fp}')
    
    return report_fp


def get_rr_case_answer(norm=None, abn=None, desc=''):
    '''
    # Used only in TESTING (generate_fake_rr_answers)
    answer as defined in displayclasses.py

    ans[RR_NORMAL] = False
    ans[RR_ABNORMAL] = False
    ans[RR_DESC] = ''
    '''
    case_dict = {
        RR_NORMAL: norm,
        RR_ABNORMAL: abn,
        RR_DESC: desc
    }
    return case_dict


def get_lc_case_answer(OBStxt: str | None = None,
                       INTtxt: str | None = None,
                       PDXtxt: str | None = None,
                       DDXtxt: str | None = None,
                       MXtxt: str | None = None):
    '''
    answer as defined in displayclasses.py

    ans[RR_NORMAL] = False
    ans[RR_ABNORMAL] = False
    ans[RR_DESC] = ''
    '''
    if (OBStxt is None) or (OBStxt.strip() == ''):
        OBStxt = ANS_BLANK
    if (INTtxt is None) or (INTtxt.strip() == ''):
        INTtxt = ANS_BLANK
    if (PDXtxt is None) or (PDXtxt.strip() == ''):
        PDXtxt = ANS_BLANK
    if (DDXtxt is None) or (DDXtxt.strip() == ''):
        DDXtxt = ANS_BLANK
    if (MXtxt is None) or (MXtxt.strip() == ''):
        MXtxt = ANS_BLANK

    case_dict = {
        LC_OBS: OBStxt,
        LC_INT: INTtxt,
        LC_PDX: PDXtxt,
        LC_DDX: DDXtxt,
        LC_MX: MXtxt
    }
    return case_dict
