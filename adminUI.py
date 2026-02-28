"""
Web-based Admin Frontend for Exam Administration Database
Built with NiceGUI - Compatible with NiceGUI 3.3+
"""

from nicegui import ui
import datetime
import time
import os
from serverdb import chimera_server_db, get_current_dt_str
from pydanticmodels import (
    RR_Ans_bare,
    LC_Ans_bare,
)
from logsystem import logger
import sentry_sdk

sentry_sdk.init(
    dsn="http://a6c87bf3896932238a459148c4d0f87f@192.168.50.177:9000/1", # Replace with your DSN
    traces_sample_rate=1.0, # Capture 100% of traces for performance monitoring
    enable_logs=True,
    # Other options like enable_logs=True can be added here
)

from serverside_report import create_answer_pdf
from serverconstants import (
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

# Initialize database
DB_TARGET = os.getenv('EXAMADMIN_DB_TARGET', r'C:\pycode\examserver\DB\chimera_server.db')
db = chimera_server_db(DB_TARGET, test_on_start=False, clean_start=False)


# ==================== NAVIGATION ====================
def create_header():
    """Create consistent header with navigation"""
    with ui.header().classes('items-center justify-between'):
        ui.label('Exam Admin Dashboard').classes('text-h5')
        with ui.row():
            ui.button('Sessions', on_click=lambda: ui.navigate.to('/')).props('flat')
            ui.button('RR Answers', on_click=lambda: ui.navigate.to('/rr_answers')).props('flat')
            ui.button('LC Answers', on_click=lambda: ui.navigate.to('/lc_answers')).props('flat')


# ==================== SESSIONS PAGE ====================
@ui.page('/')
def sessions_page():
    create_header()
    
    with ui.column().classes('w-full p-4'):
        ui.label('Session Management').classes('text-h4 mb-4')
        ui.label(f'DB: {DB_TARGET}').classes('text-caption text-grey-7 mb-2')
        
        # Filter buttons
        with ui.row().classes('mb-4'):
            filter_state = {
                'session_status': 'all',
                'date_mode': 'all',
                'last_n_days': 7,
                'set_type': None,
                'username': None,
                'set_name': None,
                'device_name': None,
            }

            def parse_session_dt(dt_value):
                if not dt_value:
                    return None
                if isinstance(dt_value, datetime.datetime):
                    return dt_value
                dt_text = str(dt_value).strip()
                try:
                    return datetime.datetime.fromisoformat(dt_text)
                except ValueError:
                    pass
                try:
                    return datetime.datetime.strptime(dt_text, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None

            def passes_date_filter(session):
                mode = filter_state['date_mode']
                if mode == 'all':
                    return True

                session_dt = parse_session_dt(session.get('start_dt'))
                if session_dt is None:
                    return False

                today = datetime.date.today()
                session_date = session_dt.date()

                if mode == 'today':
                    return session_date == today
                if mode == 'yesterday':
                    return session_date == (today - datetime.timedelta(days=1))
                if mode == 'last_n_days':
                    try:
                        n_days = max(1, int(filter_state['last_n_days']))
                    except (TypeError, ValueError):
                        n_days = 1
                    earliest = today - datetime.timedelta(days=n_days - 1)
                    return earliest <= session_date <= today
                return True

            def passes_type_filter(session):
                selected_type = filter_state['set_type']
                if not selected_type:
                    return True
                return str(session.get('set_type', '')).upper() == selected_type

            def passes_detail_filters(session):
                username = filter_state['username']
                if username and str(session.get('username', '')) != username:
                    return False

                set_name = filter_state['set_name']
                if set_name and str(session.get('set_name', '')) != set_name:
                    return False

                device_name = filter_state['device_name']
                if device_name and str(session.get('device_name', '')) != device_name:
                    return False

                return True

            def sync_select_options(select_widget, values, state_key):
                options = sorted({str(v) for v in values if v is not None and str(v) != ''})
                select_widget.options = options
                if filter_state[state_key] not in options:
                    filter_state[state_key] = None
                    if select_widget.value is not None:
                        select_widget.value = None
                select_widget.update()

            def refresh_table():
                table_container.clear()
                with table_container:
                    create_sessions_table(filter_state['session_status'])

            auto_update_state = {
                'enabled': False,
                'interval_seconds': 2,
                'last_refresh_ts': time.monotonic(),
            }

            def update_auto_update_button_style():
                if auto_update_state['enabled']:
                    auto_update_button.style('background-color: var(--q-positive) !important; color: white !important; border: 1px solid var(--q-positive) !important;')
                else:
                    auto_update_button.style('background-color: white !important; color: var(--q-primary) !important; border: 1px solid var(--q-primary) !important;')

            def toggle_auto_update():
                auto_update_state['enabled'] = not auto_update_state['enabled']
                auto_update_state['last_refresh_ts'] = time.monotonic()
                update_auto_update_button_style()

            def auto_update_tick():
                if not auto_update_state['enabled']:
                    return
                now = time.monotonic()
                if now - auto_update_state['last_refresh_ts'] >= auto_update_state['interval_seconds']:
                    auto_update_state['last_refresh_ts'] = now
                    refresh_table()

            def set_session_filter(filter_type):
                filter_state['session_status'] = filter_type
                refresh_table()
                update_quick_final_buttons()

            def on_date_mode_change(e):
                filter_state['date_mode'] = e.value or 'all'
                last_n_days_input.set_visibility(filter_state['date_mode'] == 'last_n_days')
                refresh_table()
                update_quick_range_buttons()

            def on_last_n_days_change(e):
                try:
                    filter_state['last_n_days'] = max(1, int(e.value or 1))
                except (TypeError, ValueError):
                    filter_state['last_n_days'] = 1
                refresh_table()
                update_quick_range_buttons()

            def on_username_change(e):
                filter_state['username'] = e.value or None
                refresh_table()

            def on_set_name_change(e):
                filter_state['set_name'] = e.value or None
                refresh_table()

            def on_device_change(e):
                filter_state['device_name'] = e.value or None
                refresh_table()

            def clear_dropdown_filters():
                filter_state['date_mode'] = 'all'
                filter_state['username'] = None
                filter_state['set_name'] = None
                filter_state['device_name'] = None

                date_mode_select.value = 'all'
                last_n_days_input.set_visibility(False)
                username_select.value = None
                set_name_select.value = None
                device_select.value = None

                refresh_table()
                update_quick_range_buttons()

            ui.button('Update', on_click=refresh_table).props('outline')
            auto_update_button = ui.button('Auto-Update', on_click=toggle_auto_update).props('outline')
            ui.button('New Session', on_click=lambda: show_new_session_dialog()).props('color=positive')
            update_auto_update_button_style()
            ui.timer(1.0, auto_update_tick)

            date_mode_select = ui.select(
                {'all': 'All dates', 'today': 'Today', 'yesterday': 'Yesterday', 'last_n_days': 'Last N days'},
                value='all',
                label='Date filter',
                on_change=on_date_mode_change,
            ).classes('w-44')

            last_n_days_input = ui.number(
                label='Days',
                value=filter_state['last_n_days'],
                min=1,
                step=1,
                on_change=on_last_n_days_change,
            ).classes('w-28')
            last_n_days_input.set_visibility(False)

            username_select = ui.select(
                options=[],
                value=None,
                label='Username',
                on_change=on_username_change,
            ).classes('w-40').props('clearable')

            set_name_select = ui.select(
                options=[],
                value=None,
                label='Set Name',
                on_change=on_set_name_change,
            ).classes('w-40').props('clearable')

            device_select = ui.select(
                options=[],
                value=None,
                label='Device',
                on_change=on_device_change,
            ).classes('w-40').props('clearable')

            ui.button('Clear filters', on_click=clear_dropdown_filters).props('outline')

        quick_final_buttons = {}
        quick_range_buttons = {}
        quick_type_buttons = {}

        def set_quick_button_style(button, active: bool):
            if active:
                button.style('background-color: var(--q-primary) !important; color: white !important; border: 1px solid var(--q-primary) !important;')
            else:
                button.style('background-color: transparent !important; color: var(--q-primary) !important; border: 1px solid var(--q-primary) !important;')

        def update_quick_final_buttons():
            selected_status = filter_state['session_status']
            status_key_map = {
                'closed': 'yes',
                'open': 'no',
                'all': 'all',
            }
            active_key = status_key_map.get(selected_status, 'all')
            for key, button in quick_final_buttons.items():
                set_quick_button_style(button, key == active_key)

        def get_active_quick_range() -> str | None:
            mode = filter_state['date_mode']
            if mode in ('all', 'today', 'yesterday'):
                return mode
            if mode == 'last_n_days':
                n_days = max(1, int(filter_state['last_n_days']))
                if n_days == 7:
                    return '7d'
                if n_days == 30:
                    return '30d'
            return None

        def update_quick_range_buttons():
            active_key = get_active_quick_range()
            for key, button in quick_range_buttons.items():
                set_quick_button_style(button, key == active_key)

        def update_quick_type_buttons():
            selected_type = filter_state['set_type']
            for key, button in quick_type_buttons.items():
                set_quick_button_style(button, key == (selected_type or 'all'))

        def set_date_filter(mode: str, last_n_days: int | None = None):
            filter_state['date_mode'] = mode
            if date_mode_select.value != mode:
                date_mode_select.value = mode
            if last_n_days is not None:
                filter_state['last_n_days'] = max(1, int(last_n_days))
                if last_n_days_input.value != filter_state['last_n_days']:
                    last_n_days_input.value = filter_state['last_n_days']
            last_n_days_input.set_visibility(mode == 'last_n_days')
            refresh_table()
            update_quick_range_buttons()

        def set_type_filter(set_type: str):
            if set_type == 'all':
                filter_state['set_type'] = None
            elif filter_state['set_type'] == set_type:
                filter_state['set_type'] = None
            else:
                filter_state['set_type'] = set_type
            refresh_table()
            update_quick_type_buttons()

        with ui.row().classes('mb-3 items-center gap-2'):
            ui.label('Final').classes('text-grey-7')
            quick_final_buttons['yes'] = ui.button('✓', on_click=lambda: set_session_filter('closed')).props('dense size=sm')
            quick_final_buttons['no'] = ui.button('✗', on_click=lambda: set_session_filter('open')).props('dense size=sm')
            quick_final_buttons['all'] = ui.button('All', on_click=lambda: set_session_filter('all')).props('dense size=sm')
            ui.label('Quick range').classes('text-grey-7 ml-4')
            quick_range_buttons['today'] = ui.button('Today', on_click=lambda: set_date_filter('today')).props('dense size=sm')
            quick_range_buttons['yesterday'] = ui.button('Yesterday', on_click=lambda: set_date_filter('yesterday')).props('dense size=sm')
            quick_range_buttons['7d'] = ui.button('7d', on_click=lambda: set_date_filter('last_n_days', 7)).props('dense size=sm')
            quick_range_buttons['30d'] = ui.button('30d', on_click=lambda: set_date_filter('last_n_days', 30)).props('dense size=sm')
            quick_range_buttons['all'] = ui.button('All', on_click=lambda: set_date_filter('all')).props('dense size=sm')
            ui.label('Type').classes('text-grey-7 ml-4')
            quick_type_buttons['RR'] = ui.button('RR', on_click=lambda: set_type_filter('RR')).props('dense size=sm')
            quick_type_buttons['LC'] = ui.button('LC', on_click=lambda: set_type_filter('LC')).props('dense size=sm')
            quick_type_buttons['all'] = ui.button('All', on_click=lambda: set_type_filter('all')).props('dense size=sm')

        update_quick_final_buttons()
        update_quick_range_buttons()
        update_quick_type_buttons()

        # Table container
        table_container = ui.column().classes('w-full')
        
        def create_sessions_table(filter_type='all'):
            if filter_type == 'open':
                sessions = db.query_open_sessions()
            elif filter_type == 'closed':
                sessions = db.query_closed_sessions()
            else:
                sessions = db.query_all_sessions()

            sessions = [s for s in sessions if passes_date_filter(s) and passes_type_filter(s)]
            sessions = [s for s in sessions if passes_detail_filters(s)]

            sync_select_options(username_select, [s.get('username') for s in sessions], 'username')
            sync_select_options(set_name_select, [s.get('set_name') for s in sessions], 'set_name')
            sync_select_options(device_select, [s.get('device_name') for s in sessions], 'device_name')

            columns = [
                {'name': 'username', 'label': 'Username', 'field': 'username', 'align': 'left', 'sortable': True},
                {'name': 'set_name', 'label': 'Set Name', 'field': 'set_name', 'align': 'left', 'sortable': True},
                {'name': 'set_type', 'label': 'Type', 'field': 'set_type', 'align': 'left', 'sortable': True},
                {'name': 'device_name', 'label': 'Device', 'field': 'device_name', 'align': 'left', 'sortable': True},
                {'name': 'start_dt', 'label': 'Start Time', 'field': 'start_dt', 'align': 'left', 'sortable': True},
                {'name': 'finalised', 'label': 'Finalised', 'field': 'finalised', 'align': 'left', 'sortable': True},
                {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                {'name': 'uid', 'label': 'UID', 'field': 'uid', 'align': 'left', 'sortable': True},
            ]
            
            # Format sessions data
            rows = []
            has_rows = len(sessions) > 0
            if has_rows:
                for s in sessions:
                    rows.append({
                        'uid': s['uid'],
                        'username': s['username'],
                        'set_name': s['set_name'],
                        'set_type': s['set_type'],
                        'device_name': s['device_name'],
                        'start_dt': s['start_dt'],
                        'finalised': '✓' if s['finalised'] else '✗',
                    })
            else:
                rows.append({
                    'uid': '',
                    'username': 'No sessions found matching filters.',
                    'set_name': '',
                    'set_type': '',
                    'device_name': '',
                    'start_dt': '',
                    'finalised': '',
                    'actions': '',
                })
            
            table = ui.table(columns=columns, rows=rows, row_key='uid').classes('w-full')
            if has_rows:
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn size="sm" color="info" flat dense icon="visibility" @click="$parent.$emit('view', props.row)" />
                        <q-btn size="sm" color="primary" flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                        <q-btn size="sm" color="primary" flat dense icon="print" @click="$parent.$emit('generate PDF', props.row)" />
                        <q-btn size="sm" color="negative" flat dense icon="delete" @click="$parent.$emit('delete', props.row)" />
                    </q-td>
                ''')
                
                table.on('view', lambda e: show_view_answers_dialog(e.args))
                table.on('edit', lambda e: show_edit_session_dialog(e.args))
                table.on('generate PDF', lambda e: generate_pdf_for_session(e.args))
                table.on('delete', lambda e: show_delete_session_dialog(e.args))
            else:
                table.add_slot('body-cell-username', '''
                    <q-td :props="props" class="text-grey-6" style="font-style: italic;">
                        {{ props.value }}
                    </q-td>
                ''')
                table.add_slot('body-cell-uid', '''
                    <q-td :props="props"></q-td>
                ''')
        
        # Initial load
        with table_container:
            create_sessions_table(filter_state['session_status'])
        
        def generate_pdf_for_session(session):
            """Generate PDF report for the selected session and download it in the browser"""
            try:
                uid = session['uid']
                username = session['username']
                set_name = session['set_name']

                ui.notify(f'PDF generation started for {username} - {set_name}', type='positive')
                print(f'This is what my session data looks like: \nUID={uid}, Username={username}, Set Name={set_name}')
                print(f'Complete dump of session data: {session}')

                answers = {
                    'type': session['set_type'],
                    'set_name': session['set_name'],
                    'candidateID': session['username'],
                    'device_name': session['device_name'],
                    'start_time': session['start_dt'],
                    'case': {}
                }

                if session['set_type'] == 'RR':
                    cases = db.get_rr_cases_by_uid(uid)

                    for case_n in cases:
                        case_data = db.get_rr_case(uid, case_n)
                        case_dict = {
                            RR_NORMAL: True if case_data[0][1] else False,
                            RR_ABNORMAL: True if case_data[0][2] else False,
                            RR_DESC: case_data[0][3]
                        }
                        answers['case'][case_n] = case_dict

                elif session['set_type'] == 'LC':
                    cases = db.get_lc_cases_by_uid(uid)

                    for case_n in cases:
                        case_data = db.get_lc_case(uid, case_n)
                        print(f'Case_data: {case_data}')
                        case_dict = {
                            LC_OBS: case_data[1],
                            LC_INT: case_data[2],
                            LC_PDX: case_data[3],
                            LC_DDX: case_data[4],
                            LC_MX: case_data[5]
                        }
                        answers['case'][case_n] = case_dict

                else:
                    ui.notify(f'Unknown set type: {session["set_type"]}', type='negative')
                    print(f'Unknown set type for session {uid}: {session["set_type"]}')
                    raise ValueError(f'Unknown set type: {session["set_type"]}')

                print(f'\nComplete dump of ANSWER data: {answers}')

                report_fp = create_answer_pdf(answers, draft_status=False)
                print(f'Generated PDF path: {report_fp}')

                if not report_fp:
                    raise ValueError('PDF generator returned no output path')

                report_path = str(report_fp)
                if not os.path.exists(report_path):
                    raise FileNotFoundError(f'Generated PDF not found: {report_path}')

                ui.download(report_path)
                ui.notify('PDF ready: download started', type='positive')

            except Exception as e:
                ui.notify(f'Error generating PDF: {str(e)}', type='negative')
                print(f'Error generating PDF for session {session.get("uid", "unknown")}: {str(e)}')
        
        def show_view_answers_dialog(session):
            """Display student answers/responses for the selected session"""
            uid = session['uid']
            set_type = session['set_type']

            def as_bool(value) -> bool:
                if isinstance(value, bool):
                    return value
                if value is None:
                    return False
                if isinstance(value, (int, float)):
                    return value == 1
                text = str(value).strip().lower()
                if text in {'1', 'true', 't', 'yes', 'y'}:
                    return True
                if text in {'0', 'false', 'f', 'no', 'n', ''}:
                    return False
                return False
            
            with ui.dialog().props('maximized') as dialog, ui.card().classes('w-full h-full'):
                with ui.column().classes('w-full h-full gap-4 p-4'):
                    # Header with close button
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label('Student Answers').classes('text-h5')
                        ui.button(icon='close', on_click=dialog.close).props('flat round')
                    
                    # Summary information card
                    with ui.card().classes('w-full'):
                        ui.label('Session Summary').classes('text-h6 mb-2')
                        with ui.grid(columns=2).classes('w-full gap-2'):
                            ui.label('Student:').classes('font-bold')
                            ui.label(session['username'])
                            ui.label('Set Type:').classes('font-bold')
                            ui.label(session['set_type'])
                            ui.label('Set Name:').classes('font-bold')
                            ui.label(session['set_name'])
                            ui.label('Start Time:').classes('font-bold')
                            ui.label(session['start_dt'])
                    
                    try:
                        # Get answers from database
                        answers = db.get_answers_obj_by_uid(uid)

                        
                        # Debug output
                        print(f"[DEBUG] Answers returned: {answers}")
                        print(f"[DEBUG] Session UID: {uid}, Type: {set_type}")
                        
                        if not answers or 'case' not in answers:
                            ui.label('No answers found for this session').classes('text-grey-6')
                            print(f"[DEBUG] No answers - answers is: {answers}")
                        else:
                            print(f"[DEBUG] Found {len(answers.get('case', {}))} cases")
                            
                            # Store UI references for saving
                            ui_refs = {}
                            
                            if set_type == 'RR':
                                # Create RR answers table
                                with ui.card().classes('w-full'):
                                    ui.label('Rapid Reporting Answers').classes('text-h6 mb-2')
                                    
                                    def handle_rr_checkbox_change(case_num: int, changed: str, value: bool) -> None:
                                        refs = ui_refs.get(case_num)
                                        if not refs:
                                            return
                                        if changed == 'normal' and value:
                                            refs['abnormal'].set_value(False)
                                        elif changed == 'abnormal' and value:
                                            refs['normal'].set_value(False)
                                    
                                    # Table header
                                    with ui.row().classes('w-full items-center font-bold bg-grey-2 p-2'):
                                        ui.label('Case #').classes('w-20')
                                        ui.label('Normal').classes('w-24')
                                        ui.label('Abnormal').classes('w-24')
                                        ui.label('Description').classes('flex-grow')
                                    
                                    # Scrollable table body
                                    with ui.scroll_area().classes('w-full h-96'):
                                        with ui.column().classes('w-full gap-2'):
                                            for case_num in sorted(answers['case'].keys()):
                                                case_data = answers['case'][case_num]
                                                
                                                with ui.row().classes('w-full items-start p-2 border'):
                                                    # Case number
                                                    ui.label(str(case_num)).classes('w-20 pt-2')
                                                    
                                                    # Normal checkbox
                                                    n_cb = ui.checkbox('',
                                                                            value=as_bool(case_data.get('RR_Normal', 0)),
                                                                            on_change=lambda e, cn=case_num: handle_rr_checkbox_change(cn, 'normal', e.value)
                                                                            ).classes('w-24')
                                                    
                                                    # Abnormal checkbox
                                                    an_cb = ui.checkbox('',
                                                                        value=as_bool(case_data.get('RR_Abnormal', 0)),
                                                                        on_change=lambda e, cn=case_num: handle_rr_checkbox_change(cn, 'abnormal', e.value)
                                                                        ).classes('w-24')
                                                    
                                                    # Description textarea
                                                    desc_input = ui.textarea(value=case_data.get('RR_Desc', '')).classes('flex-grow').props('dense').props('rows=1')
                                                    
                                                    # Store references
                                                    ui_refs[case_num] = {
                                                        'normal': n_cb,
                                                        'abnormal': an_cb,
                                                        'desc': desc_input
                                                    }
                            
                            elif set_type == 'LC':
                                # Create LC answers table
                                with ui.card().classes('w-full'):
                                    ui.label('Long Case Answers').classes('text-h6 mb-2')
                                    
                                    # Scrollable area for LC cases
                                    with ui.scroll_area().classes('w-full h-96'):
                                        with ui.column().classes('w-full gap-4'):
                                            for case_num in sorted(answers['case'].keys()):
                                                case_data = answers['case'][case_num]
                                                
                                                with ui.card().classes('w-full'):
                                                    ui.label(f'Case {case_num}').classes('text-h6 mb-2')
                                                    
                                                    # Editable fields
                                                    obs_input = ui.textarea('Observations', value=case_data.get('LC_OBS', '')).classes('w-full')
                                                    int_input = ui.textarea('Interpretation', value=case_data.get('LC_INT', '')).classes('w-full')
                                                    pdx_input = ui.textarea('Primary Diagnosis', value=case_data.get('LC_PDX', '')).classes('w-full')
                                                    ddx_input = ui.textarea('Differential Diagnosis', value=case_data.get('LC_DDX', '')).classes('w-full')
                                                    mx_input = ui.textarea('Management', value=case_data.get('LC_MX', '')).classes('w-full')
                                                    
                                                    # Store references
                                                    ui_refs[case_num] = {
                                                        'obs': obs_input,
                                                        'int': int_input,
                                                        'pdx': pdx_input,
                                                        'ddx': ddx_input,
                                                        'mx': mx_input
                                                    }
                            
                            # Action buttons at bottom
                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Close', on_click=dialog.close).props('flat')
                                
                                def save_changes():
                                    try:
                                        if set_type == 'RR':
                                            for case_num, refs in ui_refs.items():
                                                rr_case = RR_Ans_bare(
                                                    uid=uid,
                                                    case_n=case_num,
                                                    RR_Normal=bool(refs['normal'].value),
                                                    RR_Abnormal=bool(refs['abnormal'].value),
                                                    RR_Desc=refs['desc'].value or ''
                                                )
                                                db.store_rr_case(rr_case, uid, method='UPDATE')
                                        
                                        elif set_type == 'LC':
                                            for case_num, refs in ui_refs.items():
                                                lc_case = LC_Ans_bare(
                                                    uid=uid,
                                                    case_n=case_num,
                                                    LC_OBS=refs['obs'].value or '',
                                                    LC_INT=refs['int'].value or '',
                                                    LC_PDX=refs['pdx'].value or '',
                                                    LC_DDX=refs['ddx'].value or '',
                                                    LC_MX=refs['mx'].value or ''
                                                )
                                                db.store_lc_case(lc_case, uid, method='UPDATE')
                                        
                                        ui.notify('Changes saved successfully', type='positive')
                                    except Exception as e:
                                        ui.notify(f'Error saving changes: {str(e)}', type='negative')
                                        logger.error(f'Error saving changes for session {uid}: {str(e)}')
                                
                                ui.button('Save Changes', on_click=save_changes).props('color=primary')
                                def generate_pdf_and_close() -> None:
                                    generate_pdf_for_session(session)
                                    dialog.close()

                                ui.button('Generate PDF', on_click=generate_pdf_and_close).props('color=positive')
                    
                    except Exception as e:
                        ui.label(f'Error loading answers: {str(e)}').classes('text-red')
                        logger.error(f'Error loading answers for session {uid}: {str(e)}')
            
            dialog.open()
        
        def show_new_session_dialog():
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('New Session').classes('text-h6')
                username_input = ui.input('Username').classes('w-full')
                set_name_input = ui.input('Set Name').classes('w-full')
                set_type_select = ui.select(['RR', 'LC'], label='Set Type').classes('w-full')
                device_input = ui.input('Device Name').classes('w-full')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def create_session():
                        try:
                            uid = db.create_session(
                                username=username_input.value,
                                set_type=set_type_select.value,
                                set_name=set_name_input.value,
                                device_name=device_input.value,
                                start_dt=get_current_dt_str()
                            )
                            ui.notify(f'Session created: {uid}', type='positive')
                            dialog.close()
                            refresh_table()
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Create', on_click=create_session).props('color=positive')
            
            dialog.open()
        
        def show_edit_session_dialog(session):
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('Edit Session').classes('text-h6')
                ui.label(f'UID: {session["uid"]}').classes('text-sm text-grey-7')
                
                username_input = ui.input('Username', value=session['username']).classes('w-full')
                set_name_input = ui.input('Set Name', value=session['set_name']).classes('w-full')
                set_type_select = ui.select(['RR', 'LC'], label='Set Type', value=session['set_type']).classes('w-full')
                device_input = ui.input('Device Name', value=session['device_name']).classes('w-full')
                finalised_check = ui.checkbox('Finalised', value=session['finalised'] == '✓')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def update_session():
                        try:
                            # Update session in database
                            query = """UPDATE sessions 
                                      SET username=?, set_name=?, set_type=?, device_name=?, finalised=? 
                                      WHERE uid=?"""
                            params = (username_input.value, set_name_input.value, set_type_select.value,
                                     device_input.value, 1 if finalised_check.value else 0, session['uid'])
                            db.execute_param_query(query, params, txt='Update session')
                            
                            ui.notify('Session updated', type='positive')
                            dialog.close()
                            refresh_table()
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Update', on_click=update_session).props('color=positive')
            
            dialog.open()
        
        def show_delete_session_dialog(session):
            with ui.dialog() as dialog, ui.card():
                ui.label('Delete Session?').classes('text-h6')
                ui.label(f'Are you sure you want to delete session {session["uid"]}?').classes('mb-4')
                ui.label('This will also delete all associated RR and LC answers!').classes('text-red mb-4')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def delete_session():
                        try:
                            # Delete associated answers first
                            db.execute_param_query("DELETE FROM rr_answers WHERE uid=?", (session['uid'],), txt='Delete RR answers')
                            db.execute_param_query("DELETE FROM lc_answers WHERE uid=?", (session['uid'],), txt='Delete LC answers')
                            db.execute_param_query("DELETE FROM sessions WHERE uid=?", (session['uid'],), txt='Delete session')
                            
                            ui.notify('Session deleted', type='positive')
                            dialog.close()
                            refresh_table()
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Delete', on_click=delete_session).props('color=negative')
            
            dialog.open()


# ==================== RR ANSWERS PAGE ====================
@ui.page('/rr_answers')
def rr_answers_page():
    create_header()
    
    with ui.column().classes('w-full p-4'):
        ui.label('Rapid Reporting Answers').classes('text-h4 mb-4')
        
        # UID selector
        sessions = db.query_all_sessions()
        rr_sessions = [s for s in sessions if s['set_type'] == 'RR']
        
        if not rr_sessions:
            ui.label('No RR sessions found').classes('text-grey-6')
            return
        
        uid_options = {f"{s['uid']} ({s['username']} - {s['set_name']})": s['uid'] for s in rr_sessions}
        
        selected_uid = {'value': None}
        
        with ui.row().classes('mb-4 items-center'):
            ui.select(
                options=list(uid_options.keys()),
                label='Select Session',
                on_change=lambda e: load_rr_answers(uid_options[e.value])
            ).classes('w-96')
            ui.button('New RR Answer', on_click=lambda: show_new_rr_dialog()).props('color=positive')
        
        table_container = ui.column().classes('w-full')
        
        def load_rr_answers(uid):
            selected_uid['value'] = uid
            table_container.clear()
            with table_container:
                cases = db.get_rr_cases_by_uid(uid)
                
                if not cases:
                    ui.label('No RR answers found for this session').classes('text-grey-6')
                    return
                
                columns = [
                    {'name': 'case_number', 'label': 'Case #', 'field': 'case_number', 'align': 'left'},
                    {'name': 'rr_normal', 'label': 'Normal', 'field': 'rr_normal', 'align': 'center'},
                    {'name': 'rr_abnormal', 'label': 'Abnormal', 'field': 'rr_abnormal', 'align': 'center'},
                    {'name': 'rr_desc', 'label': 'Description', 'field': 'rr_desc', 'align': 'left'},
                    {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                ]
                
                rows = []
                for case_n in cases:
                    case_data = db.get_rr_case(uid, case_n)
                    if case_data:
                        rows.append({
                            'case_number': case_data[0][0],
                            'rr_normal': '✓' if case_data[0][1] else '✗',
                            'rr_abnormal': '✓' if case_data[0][2] else '✗',
                            'rr_desc': case_data[0][3],
                            'uid': uid
                        })
                
                table = ui.table(columns=columns, rows=rows, row_key='case_number').classes('w-full')
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn size="sm" color="primary" flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                        <q-btn size="sm" color="negative" flat dense icon="delete" @click="$parent.$emit('delete', props.row)" />
                    </q-td>
                ''')
                
                table.on('edit', lambda e: show_edit_rr_dialog(e.args))
                table.on('delete', lambda e: show_delete_rr_dialog(e.args))
        
        def show_new_rr_dialog():
            if not selected_uid['value']:
                ui.notify('Please select a session first', type='warning')
                return
                
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('New RR Answer').classes('text-h6')
                case_num_input = ui.number('Case Number', min=1, precision=0).classes('w-full')
                normal_check = ui.checkbox('Normal')
                abnormal_check = ui.checkbox('Abnormal')
                desc_input = ui.textarea('Description').classes('w-full')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def create_rr():
                        try:
                            current_uid = selected_uid['value']
                            if not current_uid:
                                ui.notify('Please select a session first', type='warning')
                                return

                            rr_case = RR_Ans_bare(
                                uid=current_uid,
                                case_n=int(case_num_input.value),
                                RR_Normal=bool(normal_check.value),
                                RR_Abnormal=bool(abnormal_check.value),
                                RR_Desc=desc_input.value or ''
                            )
                            result = db.store_rr_case(rr_case, current_uid, method='INSERT')
                            
                            if result == 'No Error':
                                ui.notify('RR answer created', type='positive')
                                dialog.close()
                                load_rr_answers(current_uid)
                            else:
                                ui.notify(f'Error: {result}', type='negative')
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Create', on_click=create_rr).props('color=positive')
            
            dialog.open()
        
        def show_edit_rr_dialog(rr_answer):
            with ui.dialog() as dialog, ui.card().classes('w-96'):
                ui.label('Edit RR Answer').classes('text-h6')
                ui.label(f'Case #{rr_answer["case_number"]}').classes('text-sm text-grey-7')
                
                normal_check = ui.checkbox('Normal', value=rr_answer['rr_normal'] == '✓')
                abnormal_check = ui.checkbox('Abnormal', value=rr_answer['rr_abnormal'] == '✓')
                desc_input = ui.textarea('Description', value=rr_answer['rr_desc']).classes('w-full')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def update_rr():
                        try:
                            rr_case = RR_Ans_bare(
                                uid=rr_answer['uid'],
                                case_n=rr_answer['case_number'],
                                RR_Normal=bool(normal_check.value),
                                RR_Abnormal=bool(abnormal_check.value),
                                RR_Desc=desc_input.value or ''
                            )
                            result = db.store_rr_case(rr_case, rr_answer['uid'], method='UPDATE')
                            
                            if result == 'No Error':
                                ui.notify('RR answer updated', type='positive')
                                dialog.close()
                                load_rr_answers(rr_answer['uid'])
                            else:
                                ui.notify(f'Error: {result}', type='negative')
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Update', on_click=update_rr).props('color=positive')
            
            dialog.open()
        
        def show_delete_rr_dialog(rr_answer):
            with ui.dialog() as dialog, ui.card():
                ui.label('Delete RR Answer?').classes('text-h6')
                ui.label(f'Delete case #{rr_answer["case_number"]}?').classes('mb-4')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def delete_rr():
                        try:
                            query = "DELETE FROM rr_answers WHERE uid=? AND case_number=?"
                            params = (rr_answer['uid'], rr_answer['case_number'])
                            db.execute_param_query(query, params, txt='Delete RR answer')
                            
                            ui.notify('RR answer deleted', type='positive')
                            dialog.close()
                            load_rr_answers(rr_answer['uid'])
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Delete', on_click=delete_rr).props('color=negative')
            
            dialog.open()


# ==================== LC ANSWERS PAGE ====================
@ui.page('/lc_answers')
def lc_answers_page():
    create_header()
    
    with ui.column().classes('w-full p-4'):
        ui.label('Long Case Answers').classes('text-h4 mb-4')
        
        # UID selector
        sessions = db.query_all_sessions()
        lc_sessions = [s for s in sessions if s['set_type'] == 'LC']
        
        if not lc_sessions:
            ui.label('No LC sessions found').classes('text-grey-6')
            return
        
        uid_options = {f"{s['uid']} ({s['username']} - {s['set_name']})": s['uid'] for s in lc_sessions}
        
        selected_uid = {'value': None}
        
        with ui.row().classes('mb-4 items-center'):
            ui.select(
                options=list(uid_options.keys()),
                label='Select Session',
                on_change=lambda e: load_lc_answers(uid_options[e.value])
            ).classes('w-96')
            ui.button('New LC Answer', on_click=lambda: show_new_lc_dialog()).props('color=positive')
        
        table_container = ui.column().classes('w-full')
        
        def load_lc_answers(uid):
            selected_uid['value'] = uid
            table_container.clear()
            with table_container:
                cases = db.get_lc_cases_by_uid(uid)
                
                if not cases:
                    ui.label('No LC answers found for this session').classes('text-grey-6')
                    return
                
                columns = [
                    {'name': 'case_number', 'label': 'Case #', 'field': 'case_number', 'align': 'left'},
                    {'name': 'LC_OBS', 'label': 'Observations', 'field': 'LC_OBS', 'align': 'left'},
                    {'name': 'LC_INT', 'label': 'Interpretation', 'field': 'LC_INT', 'align': 'left'},
                    {'name': 'LC_PDX', 'label': 'Primary Dx', 'field': 'LC_PDX', 'align': 'left'},
                    {'name': 'LC_DDX', 'label': 'Differential Dx', 'field': 'LC_DDX', 'align': 'left'},
                    {'name': 'LC_MX', 'label': 'Management', 'field': 'LC_MX', 'align': 'left'},
                    {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                ]
                
                rows = []
                for case_n in cases:
                    # Fetch LC case data
                    query = "SELECT case_number, LC_OBS, LC_INT, LC_PDX, LC_DDX, LC_MX FROM lc_answers WHERE uid=? AND case_number=?"
                    result = db.cursor.execute(query, (uid, case_n))
                    case_data = result.fetchone()
                    
                    if case_data:
                        rows.append({
                            'case_number': case_data[0],
                            'LC_OBS': case_data[1][:50] + '...' if len(case_data[1]) > 50 else case_data[1],
                            'LC_INT': case_data[2][:50] + '...' if len(case_data[2]) > 50 else case_data[2],
                            'LC_PDX': case_data[3][:50] + '...' if len(case_data[3]) > 50 else case_data[3],
                            'LC_DDX': case_data[4][:50] + '...' if len(case_data[4]) > 50 else case_data[4],
                            'LC_MX': case_data[5][:50] + '...' if len(case_data[5]) > 50 else case_data[5],
                            'LC_OBS_full': case_data[1],
                            'LC_INT_full': case_data[2],
                            'LC_PDX_full': case_data[3],
                            'LC_DDX_full': case_data[4],
                            'LC_MX_full': case_data[5],
                            'uid': uid
                        })
                
                table = ui.table(columns=columns, rows=rows, row_key='case_number').classes('w-full')
                table.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn size="sm" color="primary" flat dense icon="edit" @click="$parent.$emit('edit', props.row)" />
                        <q-btn size="sm" color="negative" flat dense icon="delete" @click="$parent.$emit('delete', props.row)" />
                    </q-td>
                ''')
                
                table.on('edit', lambda e: show_edit_lc_dialog(e.args))
                table.on('delete', lambda e: show_delete_lc_dialog(e.args))
        
        def show_new_lc_dialog():
            if not selected_uid['value']:
                ui.notify('Please select a session first', type='warning')
                return
                
            with ui.dialog() as dialog, ui.card().classes('w-128'):
                ui.label('New LC Answer').classes('text-h6')
                case_num_input = ui.number('Case Number', min=1, precision=0).classes('w-full')
                obs_input = ui.textarea('Observations').classes('w-full')
                int_input = ui.textarea('Interpretation').classes('w-full')
                pdx_input = ui.textarea('Primary Diagnosis').classes('w-full')
                ddx_input = ui.textarea('Differential Diagnosis').classes('w-full')
                mx_input = ui.textarea('Management').classes('w-full')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def create_lc():
                        try:
                            current_uid = selected_uid['value']
                            if not current_uid:
                                ui.notify('Please select a session first', type='warning')
                                return

                            lc_case = LC_Ans_bare(
                                uid=current_uid,
                                case_n=int(case_num_input.value),
                                LC_OBS=obs_input.value or '',
                                LC_INT=int_input.value or '',
                                LC_PDX=pdx_input.value or '',
                                LC_DDX=ddx_input.value or '',
                                LC_MX=mx_input.value or ''
                            )
                            result = db.store_lc_case(lc_case, current_uid, method='INSERT')
                            
                            if result == 'No Error':
                                ui.notify('LC answer created', type='positive')
                                dialog.close()
                                load_lc_answers(current_uid)
                            else:
                                ui.notify(f'Error: {result}', type='negative')
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Create', on_click=create_lc).props('color=positive')
            
            dialog.open()
        
        def show_edit_lc_dialog(lc_answer):
            with ui.dialog() as dialog, ui.card().classes('w-128'):
                ui.label('Edit LC Answer').classes('text-h6')
                ui.label(f'Case #{lc_answer["case_number"]}').classes('text-sm text-grey-7')
                
                obs_input = ui.textarea('Observations', value=lc_answer['LC_OBS_full']).classes('w-full')
                int_input = ui.textarea('Interpretation', value=lc_answer['LC_INT_full']).classes('w-full')
                pdx_input = ui.textarea('Primary Diagnosis', value=lc_answer['LC_PDX_full']).classes('w-full')
                ddx_input = ui.textarea('Differential Diagnosis', value=lc_answer['LC_DDX_full']).classes('w-full')
                mx_input = ui.textarea('Management', value=lc_answer['LC_MX_full']).classes('w-full')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def update_lc():
                        try:
                            lc_case = LC_Ans_bare(
                                uid=lc_answer['uid'],
                                case_n=lc_answer['case_number'],
                                LC_OBS=obs_input.value or '',
                                LC_INT=int_input.value or '',
                                LC_PDX=pdx_input.value or '',
                                LC_DDX=ddx_input.value or '',
                                LC_MX=mx_input.value or ''
                            )
                            result = db.store_lc_case(lc_case, lc_answer['uid'], method='UPDATE')
                            
                            if result == 'No Error':
                                ui.notify('LC answer updated', type='positive')
                                dialog.close()
                                load_lc_answers(lc_answer['uid'])
                            else:
                                ui.notify(f'Error: {result}', type='negative')
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Update', on_click=update_lc).props('color=positive')
            
            dialog.open()
        
        def show_delete_lc_dialog(lc_answer):
            with ui.dialog() as dialog, ui.card():
                ui.label('Delete LC Answer?').classes('text-h6')
                ui.label(f'Delete case #{lc_answer["case_number"]}?').classes('mb-4')
                
                with ui.row().classes('w-full justify-end'):
                    ui.button('Cancel', on_click=dialog.close).props('flat')
                    
                    def delete_lc():
                        try:
                            query = "DELETE FROM lc_answers WHERE uid=? AND case_number=?"
                            params = (lc_answer['uid'], lc_answer['case_number'])
                            db.execute_param_query(query, params, txt='Delete LC answer')
                            
                            ui.notify('LC answer deleted', type='positive')
                            dialog.close()
                            load_lc_answers(lc_answer['uid'])
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')
                    
                    ui.button('Delete', on_click=delete_lc).props('color=negative')
            
            dialog.open()


# ==================== RUN SERVER ====================
ui.run(
    title='Exam Admin Dashboard',
    port=8080,
    reload=False,
    show=True,
    storage_secret='exam-admin-secret-key-change-in-production'
)
