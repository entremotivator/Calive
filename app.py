import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import uuid
from streamlit_calendar import calendar
import pytz
import re
from typing import List, Dict, Any, Optional

# Page configuration
st.set_page_config(
    page_title="Enhanced Google Calendar Manager",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced session state management
def initialize_session_state():
    """Initialize all session state variables with defaults"""
    default_states = {
        'events': [],
        'selected_event': None,
        'calendars': {'entremotivator@gmail.com': {'name': 'Default Calendar', 'color': '#3788d8', 'visible': True}},
        'active_calendar': 'entremotivator@gmail.com',
        'timezone': 'UTC',
        'view_mode': 'dayGridMonth',
        'filter_date_range': None,
        'search_term': '',
        'event_categories': [],
        'last_backup': None,
        'app_settings': {
            'auto_save': True,
            'show_weekends': True,
            'default_event_duration': 1,
            'theme': 'light'
        }
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def extract_calendar_info_from_json(content: Dict) -> Dict[str, Any]:
    """Extract calendar information from JSON content"""
    calendar_info = {
        'email': 'entremotivator@gmail.com',  # Default fallback
        'name': 'Imported Calendar',
        'timezone': 'UTC'
    }
    
    # Try to extract calendar email from various JSON structures
    if 'kind' in content and content.get('kind') == 'calendar#calendar':
        calendar_info['email'] = content.get('id', 'entremotivator@gmail.com')
        calendar_info['name'] = content.get('summary', 'Imported Calendar')
        calendar_info['timezone'] = content.get('timeZone', 'UTC')
    elif 'calendarId' in content:
        calendar_info['email'] = content.get('calendarId', 'entremotivator@gmail.com')
    elif 'calendar' in content:
        cal_data = content['calendar']
        calendar_info['email'] = cal_data.get('id', cal_data.get('email', 'entremotivator@gmail.com'))
        calendar_info['name'] = cal_data.get('summary', cal_data.get('name', 'Imported Calendar'))
    
    # Validate extracted email
    if not validate_email(calendar_info['email']):
        calendar_info['email'] = 'entremotivator@gmail.com'
    
    return calendar_info

def load_events_from_json(uploaded_file) -> tuple[List[Dict], Dict[str, Any]]:
    """Load events from uploaded JSON file with enhanced error handling and calendar detection"""
    try:
        content = json.load(uploaded_file)
        
        # Extract calendar information
        calendar_info = extract_calendar_info_from_json(content)
        
        # Handle different JSON structures for events
        events = []
        if isinstance(content, list):
            events = content
        elif 'items' in content:
            events = content['items']
        elif 'events' in content:
            events = content['events']
        elif 'event' in content:
            events = [content['event']]
        else:
            # Check if the content itself is an event
            if 'summary' in content or 'title' in content:
                events = [content]
        
        # Normalize event format with enhanced handling
        normalized_events = []
        for event in events:
            try:
                # Handle various date formats
                start_info = event.get('start', {})
                end_info = event.get('end', {})
                
                # Extract start datetime
                start_dt = None
                if isinstance(start_info, dict):
                    start_dt = start_info.get('dateTime', start_info.get('date'))
                elif isinstance(start_info, str):
                    start_dt = start_info
                
                # Extract end datetime
                end_dt = None
                if isinstance(end_info, dict):
                    end_dt = end_info.get('dateTime', end_info.get('date'))
                elif isinstance(end_info, str):
                    end_dt = end_info
                
                # Default to current time if no start time
                if not start_dt:
                    start_dt = datetime.now().isoformat()
                
                # Default end time to 1 hour after start if no end time
                if not end_dt:
                    try:
                        start_parsed = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                        end_dt = (start_parsed + timedelta(hours=1)).isoformat()
                    except:
                        end_dt = (datetime.now() + timedelta(hours=1)).isoformat()
                
                # Ensure proper datetime format
                if 'T' not in str(start_dt):
                    start_dt = f"{start_dt}T00:00:00"
                if 'T' not in str(end_dt):
                    end_dt = f"{end_dt}T23:59:59"
                
                normalized_event = {
                    'id': event.get('id', event.get('iCalUID', str(uuid.uuid4()))),
                    'title': event.get('summary', event.get('title', 'Untitled Event')),
                    'start': start_dt,
                    'end': end_dt,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'color': get_color_from_id(event.get('colorId', '1')),
                    'calendar_email': calendar_info['email'],
                    'status': event.get('status', 'confirmed'),
                    'created': event.get('created', datetime.now().isoformat()),
                    'updated': event.get('updated', datetime.now().isoformat()),
                    'attendees': event.get('attendees', []),
                    'recurrence': event.get('recurrence', []),
                    'category': extract_category_from_event(event)
                }
                
                normalized_events.append(normalized_event)
                
            except Exception as e:
                st.warning(f"Skipped malformed event: {str(e)}")
                continue
        
        return normalized_events, calendar_info
        
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON file: {str(e)}")
        return [], {}
    except Exception as e:
        st.error(f"Error loading JSON file: {str(e)}")
        return [], {}

def get_color_from_id(color_id: str) -> str:
    """Convert Google Calendar color ID to hex color"""
    color_map = {
        '1': '#a4bdfc',  # Lavender
        '2': '#7ae7bf',  # Sage
        '3': '#dbadff',  # Grape
        '4': '#ff887c',  # Flamingo
        '5': '#fbd75b',  # Banana
        '6': '#ffb878',  # Tangerine
        '7': '#46d6db',  # Peacock
        '8': '#e1e1e1',  # Graphite
        '9': '#5484ed',  # Blueberry
        '10': '#51b749', # Basil
        '11': '#dc2127', # Tomato
    }
    return color_map.get(str(color_id), '#3788d8')

def extract_category_from_event(event: Dict) -> str:
    """Extract category from event data"""
    # Try to determine category from various fields
    title = event.get('summary', event.get('title', '')).lower()
    description = event.get('description', '').lower()
    location = event.get('location', '').lower()
    
    categories = {
        'meeting': ['meeting', 'call', 'conference', 'sync', 'standup'],
        'personal': ['personal', 'appointment', 'doctor', 'dentist'],
        'work': ['work', 'project', 'deadline', 'review'],
        'travel': ['flight', 'travel', 'trip', 'vacation'],
        'social': ['dinner', 'party', 'birthday', 'celebration'],
        'health': ['gym', 'workout', 'exercise', 'fitness'],
        'education': ['class', 'course', 'training', 'workshop']
    }
    
    for category, keywords in categories.items():
        if any(keyword in title or keyword in description or keyword in location for keyword in keywords):
            return category
    
    return 'general'

def format_events_for_calendar(events: List[Dict], active_calendar: str = None) -> List[Dict]:
    """Format events for streamlit-calendar component with filtering"""
    calendar_events = []
    
    for event in events:
        # Filter by active calendar if specified
        if active_calendar and event.get('calendar_email') != active_calendar:
            continue
        
        # Apply search filter
        if st.session_state.search_term:
            search_term = st.session_state.search_term.lower()
            if not any(search_term in str(event.get(field, '')).lower() 
                      for field in ['title', 'description', 'location']):
                continue
        
        calendar_event = {
            'id': event['id'],
            'title': event['title'],
            'start': event['start'],
            'end': event['end'],
            'color': event.get('color', '#3788d8'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'textColor': '#ffffff' if event.get('color', '#3788d8') != '#e1e1e1' else '#000000'
        }
        calendar_events.append(calendar_event)
    
    return calendar_events

def add_event(title: str, start_date, start_time, end_date, end_time, 
              description: str = "", location: str = "", color: str = "#3788d8", 
              category: str = "general", calendar_email: str = None) -> bool:
    """Add a new event with enhanced validation"""
    try:
        if not calendar_email:
            calendar_email = st.session_state.active_calendar
        
        start_datetime = datetime.combine(start_date, start_time).isoformat()
        end_datetime = datetime.combine(end_date, end_time).isoformat()
        
        # Validate that end time is after start time
        if end_datetime <= start_datetime:
            st.error("End time must be after start time")
            return False
        
        new_event = {
            'id': str(uuid.uuid4()),
            'title': title,
            'start': start_datetime,
            'end': end_datetime,
            'description': description,
            'location': location,
            'color': color,
            'calendar_email': calendar_email,
            'status': 'confirmed',
            'created': datetime.now().isoformat(),
            'updated': datetime.now().isoformat(),
            'attendees': [],
            'recurrence': [],
            'category': category
        }
        
        st.session_state.events.append(new_event)
        
        # Auto-backup if enabled
        if st.session_state.app_settings.get('auto_save', True):
            st.session_state.last_backup = datetime.now().isoformat()
        
        return True
        
    except Exception as e:
        st.error(f"Error adding event: {str(e)}")
        return False

def update_event(event_id: str, title: str, start_date, start_time, end_date, end_time,
                description: str = "", location: str = "", color: str = "#3788d8",
                category: str = "general") -> bool:
    """Update an existing event with validation"""
    try:
        start_datetime = datetime.combine(start_date, start_time).isoformat()
        end_datetime = datetime.combine(end_date, end_time).isoformat()
        
        # Validate that end time is after start time
        if end_datetime <= start_datetime:
            st.error("End time must be after start time")
            return False
        
        for i, event in enumerate(st.session_state.events):
            if event['id'] == event_id:
                st.session_state.events[i].update({
                    'title': title,
                    'start': start_datetime,
                    'end': end_datetime,
                    'description': description,
                    'location': location,
                    'color': color,
                    'category': category,
                    'updated': datetime.now().isoformat()
                })
                return True
        
        st.error("Event not found")
        return False
        
    except Exception as e:
        st.error(f"Error updating event: {str(e)}")
        return False

def delete_event(event_id: str) -> bool:
    """Delete an event"""
    try:
        initial_count = len(st.session_state.events)
        st.session_state.events = [event for event in st.session_state.events if event['id'] != event_id]
        
        if len(st.session_state.events) < initial_count:
            return True
        else:
            st.error("Event not found")
            return False
            
    except Exception as e:
        st.error(f"Error deleting event: {str(e)}")
        return False

def export_events_to_json(calendar_email: str = None) -> str:
    """Export events to JSON format with calendar metadata"""
    events_to_export = st.session_state.events
    
    if calendar_email:
        events_to_export = [e for e in events_to_export if e.get('calendar_email') == calendar_email]
    
    export_data = {
        'kind': 'calendar#events',
        'etag': f'"{uuid.uuid4()}"',
        'summary': st.session_state.calendars.get(calendar_email or st.session_state.active_calendar, {}).get('name', 'Exported Calendar'),
        'updated': datetime.now().isoformat(),
        'timeZone': st.session_state.timezone,
        'calendar': {
            'id': calendar_email or st.session_state.active_calendar,
            'summary': st.session_state.calendars.get(calendar_email or st.session_state.active_calendar, {}).get('name', 'Exported Calendar')
        },
        'items': events_to_export
    }
    
    return json.dumps(export_data, indent=2, default=str)

def get_event_statistics() -> Dict[str, Any]:
    """Calculate comprehensive event statistics"""
    events = st.session_state.events
    now = datetime.now()
    
    stats = {
        'total': len(events),
        'upcoming': 0,
        'past': 0,
        'today': 0,
        'this_week': 0,
        'this_month': 0,
        'by_calendar': {},
        'by_category': {},
        'by_status': {}
    }
    
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    for event in events:
        try:
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', ''))
            
            # Time-based stats
            if event_start > now:
                stats['upcoming'] += 1
            else:
                stats['past'] += 1
            
            if today_start <= event_start < today_end:
                stats['today'] += 1
            
            if event_start >= week_start:
                stats['this_week'] += 1
            
            if event_start >= month_start:
                stats['this_month'] += 1
            
            # Calendar stats
            calendar_email = event.get('calendar_email', 'unknown')
            stats['by_calendar'][calendar_email] = stats['by_calendar'].get(calendar_email, 0) + 1
            
            # Category stats
            category = event.get('category', 'general')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Status stats
            status = event.get('status', 'confirmed')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
        except Exception:
            continue
    
    return stats

# Initialize session state
initialize_session_state()

# Enhanced main app layout
st.title("📅 Enhanced Google Calendar Manager")
st.markdown("**Multi-calendar support with advanced features**")

# Enhanced sidebar
with st.sidebar:
    st.header("📧 Calendar Management")
    
    # Calendar selector with email display
    calendar_options = list(st.session_state.calendars.keys())
    if calendar_options:
        selected_calendar = st.selectbox(
            "Active Calendar",
            options=calendar_options,
            index=calendar_options.index(st.session_state.active_calendar) if st.session_state.active_calendar in calendar_options else 0,
            format_func=lambda x: f"{st.session_state.calendars[x]['name']} ({x})"
        )
        st.session_state.active_calendar = selected_calendar
        
        # Display current calendar info
        st.info(f"📧 **Active:** {st.session_state.active_calendar}")
    
    # Add new calendar
    with st.expander("➕ Add Calendar"):
        new_email = st.text_input("Calendar Email", placeholder="user@gmail.com")
        new_name = st.text_input("Calendar Name", placeholder="My Calendar")
        
        if st.button("Add Calendar"):
            if new_email and validate_email(new_email):
                st.session_state.calendars[new_email] = {
                    'name': new_name or new_email,
                    'color': '#3788d8',
                    'visible': True
                }
                st.session_state.active_calendar = new_email
                st.success(f"Added calendar: {new_email}")
                st.rerun()
            else:
                st.error("Please enter a valid email address")
    
    st.markdown("---")
    
    # Enhanced file upload
    st.header("📁 Import Events")
    uploaded_file = st.file_uploader(
        "Upload Calendar JSON",
        type=['json'],
        help="Upload Google Calendar export, Outlook export, or any compatible JSON file"
    )
    
    if uploaded_file is not None:
        if st.button("📥 Import Events"):
            new_events, calendar_info = load_events_from_json(uploaded_file)
            if new_events:
                # Add calendar if it doesn't exist
                cal_email = calendar_info.get('email', 'entremotivator@gmail.com')
                if cal_email not in st.session_state.calendars:
                    st.session_state.calendars[cal_email] = {
                        'name': calendar_info.get('name', 'Imported Calendar'),
                        'color': '#3788d8',
                        'visible': True
                    }
                
                # Add events
                st.session_state.events.extend(new_events)
                st.success(f"✅ Imported {len(new_events)} events to {cal_email}")
                st.rerun()
    
    st.markdown("---")
    
    # Enhanced export functionality
    st.header("📤 Export Events")
    
    export_calendar = st.selectbox(
        "Export Calendar",
        options=["All Calendars"] + list(st.session_state.calendars.keys()),
        format_func=lambda x: x if x == "All Calendars" else f"{st.session_state.calendars[x]['name']} ({x})"
    )
    
    if st.session_state.events:
        export_email = None if export_calendar == "All Calendars" else export_calendar
        json_data = export_events_to_json(export_email)
        
        filename_suffix = "all_calendars" if export_calendar == "All Calendars" else export_calendar.split('@')[0]
        
        st.download_button(
            label="💾 Download as JSON",
            data=json_data,
            file_name=f"calendar_{filename_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Enhanced statistics
    st.header("📊 Statistics")
    stats = get_event_statistics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Events", stats['total'])
        st.metric("Today", stats['today'])
    with col2:
        st.metric("Upcoming", stats['upcoming'])
        st.metric("This Week", stats['this_week'])
    
    # Calendar breakdown
    if stats['by_calendar']:
        st.subheader("By Calendar")
        for email, count in stats['by_calendar'].items():
            cal_name = st.session_state.calendars.get(email, {}).get('name', email)
            st.write(f"📧 {cal_name}: {count}")
    
    # Category breakdown
    if stats['by_category']:
        st.subheader("By Category")
        for category, count in stats['by_category'].items():
            st.write(f"🏷️ {category.title()}: {count}")

# Enhanced main content area
col1, col2 = st.columns([2.5, 1.5])

with col1:
    # Calendar header with controls
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    
    with header_col1:
        st.header("📅 Calendar View")
    
    with header_col2:
        view_mode = st.selectbox(
            "View",
            options=['dayGridMonth', 'timeGridWeek', 'timeGridDay', 'listWeek'],
            index=['dayGridMonth', 'timeGridWeek', 'timeGridDay', 'listWeek'].index(st.session_state.view_mode)
        )
        st.session_state.view_mode = view_mode
    
    with header_col3:
        st.session_state.search_term = st.text_input("🔍 Search", placeholder="Search events...")
    
    # Calendar display
    if st.session_state.events:
        calendar_events = format_events_for_calendar(
            st.session_state.events, 
            st.session_state.active_calendar if len(st.session_state.calendars) > 1 else None
        )
        
        calendar_options = {
            "editable": True,
            "selectable": True,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay,listWeek"
            },
            "initialView": st.session_state.view_mode,
            "height": 650,
            "timeZone": st.session_state.timezone,
            "weekends": st.session_state.app_settings.get('show_weekends', True),
            "eventDisplay": "block",
            "dayMaxEvents": True,
            "moreLinkClick": "popover"
        }
        
        calendar_result = calendar(
            events=calendar_events,
            options=calendar_options,
            custom_css="""
            .fc-event {
                border-radius: 4px;
                border: none;
                font-size: 12px;
            }
            .fc-event-title {
                font-weight: 600;
            }
            .fc-daygrid-event {
                margin: 1px;
            }
            .fc-event-past {
                opacity: 0.7;
            }
            """
        )
        
        # Handle calendar interactions
        if calendar_result.get('eventClick'):
            event_id = calendar_result['eventClick']['event']['id']
            selected_event = next((event for event in st.session_state.events if event['id'] == event_id), None)
            if selected_event:
                st.session_state.selected_event = selected_event
                st.rerun()
    else:
        st.info("📭 No events to display. Import events or add new ones to get started!")
        st.markdown("""
        **Quick Start:**
        1. 📥 Upload a Google Calendar JSON export, or
        2. ➕ Create a new event using the panel on the right
        3. 📧 Default calendar: `entremotivator@gmail.com`
        """)

with col2:
    st.header("⚙️ Event Management")
    
    # Enhanced tabs
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add", "✏️ Edit", "📋 List", "⚙️ Settings"])
    
    with tab1:
        st.subheader("Add New Event")
        with st.form("add_event_form", clear_on_submit=True):
            title = st.text_input("Event Title*", placeholder="Enter event title")
            
            # Date and time inputs
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("Start Date", value=datetime.now().date())
                start_time = st.time_input("Start Time", value=datetime.now().replace(minute=0, second=0))
            with col_date2:
                default_end = datetime.now() + timedelta(hours=st.session_state.app_settings.get('default_event_duration', 1))
                end_date = st.date_input("End Date", value=start_date)
                end_time = st.time_input("End Time", value=default_end.time())
            
            description = st.text_area("Description", placeholder="Event description (optional)")
            location = st.text_input("Location", placeholder="Event location (optional)")
            
            # Enhanced color and category selection
            col_color, col_category = st.columns(2)
            with col_color:
                color_options = {
                    "Blue": "#3788d8",
                    "Green": "#33b679",
                    "Red": "#e74c3c",
                    "Orange": "#f39c12",
                    "Purple": "#9b59b6",
                    "Pink": "#e91e63",
                    "Teal": "#1abc9c",
                    "Yellow": "#f1c40f"
                }
                color_name = st.selectbox("Color", list(color_options.keys()))
                color = color_options[color_name]
            
            with col_category:
                categories = ["general", "meeting", "personal", "work", "travel", "social", "health", "education"]
                category = st.selectbox("Category", categories)
            
            # Calendar assignment
            if len(st.session_state.calendars) > 1:
                event_calendar = st.selectbox(
                    "Assign to Calendar",
                    options=list(st.session_state.calendars.keys()),
                    index=list(st.session_state.calendars.keys()).index(st.session_state.active_calendar),
                    format_func=lambda x: f"{st.session_state.calendars[x]['name']} ({x})"
                )
            else:
                event_calendar = st.session_state.active_calendar
            
            submitted = st.form_submit_button("✅ Add Event", use_container_width=True)
            
            if submitted:
                if title.strip():
                    if add_event(title.strip(), start_date, start_time, end_date, end_time, 
                               description, location, color, category, event_calendar):
                        st.success("✅ Event added successfully!")
                        st.rerun()
                else:
                    st.error("❌ Please enter an event title")
    
    with tab2:
        st.subheader("Edit Event")
        
        if st.session_state.selected_event:
            event = st.session_state.selected_event
            
            # Display event info
            st.info(f"📧 Calendar: {event.get('calendar_email', 'Unknown')}")
            
            with st.form("edit_event_form"):
                title = st.text_input("Event Title*", value=event['title'])
                
                # Parse existing datetime with better error handling
                try:
                    start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', ''))
                    end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00').replace('+00:00', ''))
                except:
                    start_dt = datetime.now()
                    end_dt = start_dt + timedelta(hours=1)
                
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input("Start Date", value=start_dt.date())
                    start_time = st.time_input("Start Time", value=start_dt.time())
                with col_date2:
                    end_date = st.date_input("End Date", value=end_dt.date())
                    end_time = st.time_input("End Time", value=end_dt.time())
                
                description = st.text_area("Description", value=event.get('description', ''))
                location = st.text_input("Location", value=event.get('location', ''))
                
                # Enhanced editing options
                col_color, col_category = st.columns(2)
                with col_color:
                    color_options = {
                        "Blue": "#3788d8",
                        "Green": "#33b679",
                        "Red": "#e74c3c",
                        "Orange": "#f39c12",
                        "Purple": "#9b59b6",
                        "Pink": "#e91e63",
                        "Teal": "#1abc9c",
                        "Yellow": "#f1c40f"
                    }
                    
                    current_color = event.get('color', '#3788d8')
                    current_color_name = next((name for name, code in color_options.items() if code == current_color), "Blue")
                    color_name = st.selectbox("Color", list(color_options.keys()), 
                                            index=list(color_options.keys()).index(current_color_name))
                    color = color_options[color_name]
                
                with col_category:
                    categories = ["general", "meeting", "personal", "work", "travel", "social", "health", "education"]
                    current_category = event.get('category', 'general')
                    category = st.selectbox("Category", categories, 
                                          index=categories.index(current_category) if current_category in categories else 0)
                
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    update_submitted = st.form_submit_button("✅ Update", use_container_width=True)
                with col_btn2:
                    duplicate_submitted = st.form_submit_button("📋 Duplicate", use_container_width=True, type="secondary")
                with col_btn3:
                    delete_submitted = st.form_submit_button("🗑️ Delete", use_container_width=True, type="secondary")
                
                if update_submitted:
                    if title.strip():
                        if update_event(event['id'], title.strip(), start_date, start_time, end_date, end_time, 
                                      description, location, color, category):
                            st.success("✅ Event updated successfully!")
                            st.session_state.selected_event = None
                            st.rerun()
                    else:
                        st.error("❌ Please enter an event title")
                
                if duplicate_submitted:
                    if title.strip():
                        # Create duplicate with new ID
                        if add_event(f"{title.strip()} (Copy)", start_date, start_time, end_date, end_time, 
                                   description, location, color, category, event.get('calendar_email')):
                            st.success("✅ Event duplicated successfully!")
                            st.rerun()
                
                if delete_submitted:
                    if delete_event(event['id']):
                        st.success("✅ Event deleted successfully!")
                        st.session_state.selected_event = None
                        st.rerun()
        else:
            st.info("👆 Click on an event in the calendar to edit it, or select from the list below.")
    
    with tab3:
        st.subheader("All Events")
        
        # Enhanced filtering
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            filter_calendar = st.selectbox(
                "Filter by Calendar",
                options=["All"] + list(st.session_state.calendars.keys()),
                format_func=lambda x: x if x == "All" else st.session_state.calendars[x]['name']
            )
        
        with filter_col2:
            filter_category = st.selectbox(
                "Filter by Category",
                options=["All"] + ["general", "meeting", "personal", "work", "travel", "social", "health", "education"]
            )
        
        if st.session_state.events:
            # Apply filters
            filtered_events = st.session_state.events
            
            if filter_calendar != "All":
                filtered_events = [e for e in filtered_events if e.get('calendar_email') == filter_calendar]
            
            if filter_category != "All":
                filtered_events = [e for e in filtered_events if e.get('category') == filter_category]
            
            # Sort events by start date
            sorted_events = sorted(filtered_events, key=lambda x: x['start'], reverse=True)
            
            # Pagination
            events_per_page = 10
            total_pages = (len(sorted_events) - 1) // events_per_page + 1 if sorted_events else 1
            
            if total_pages > 1:
                page = st.selectbox(f"Page (Total: {len(sorted_events)} events)", 
                                  range(1, total_pages + 1), index=0)
                start_idx = (page - 1) * events_per_page
                end_idx = start_idx + events_per_page
                page_events = sorted_events[start_idx:end_idx]
            else:
                page_events = sorted_events
            
            for event in page_events:
                try:
                    start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', ''))
                    
                    with st.container():
                        # Event card with enhanced info
                        col_info, col_meta, col_action = st.columns([2, 1, 1])
                        
                        with col_info:
                            st.write(f"**{event['title']}**")
                            st.write(f"📅 {start_dt.strftime('%Y-%m-%d %H:%M')}")
                            if event.get('location'):
                                st.write(f"📍 {event['location']}")
                        
                        with col_meta:
                            st.write(f"📧 {event.get('calendar_email', 'Unknown')[:20]}...")
                            st.write(f"🏷️ {event.get('category', 'general').title()}")
                            if event.get('description'):
                                st.write(f"📝 {event['description'][:30]}...")
                        
                        with col_action:
                            if st.button("✏️ Edit", key=f"edit_{event['id']}", use_container_width=True):
                                st.session_state.selected_event = event
                                st.rerun()
                        
                        # Color indicator
                        st.markdown(f"""
                        <div style="height: 3px; background-color: {event.get('color', '#3788d8')}; 
                        border-radius: 1px; margin: 5px 0;"></div>
                        """, unsafe_allow_html=True)
                
                except Exception as e:
                    st.warning(f"Error displaying event: {event.get('title', 'Unknown')}")
                    continue
            
            if not page_events:
                st.info("No events match the current filters.")
        else:
            st.info("📭 No events found. Add some events to see them here!")
    
    with tab4:
        st.subheader("Settings")
        
        # App settings
        st.write("**Application Settings**")
        
        st.session_state.app_settings['auto_save'] = st.checkbox(
            "Auto-save events", 
            value=st.session_state.app_settings.get('auto_save', True),
            help="Automatically backup events when changes are made"
        )
        
        st.session_state.app_settings['show_weekends'] = st.checkbox(
            "Show weekends in calendar", 
            value=st.session_state.app_settings.get('show_weekends', True)
        )
        
        st.session_state.app_settings['default_event_duration'] = st.number_input(
            "Default event duration (hours)", 
            min_value=0.5, max_value=24.0, step=0.5,
            value=st.session_state.app_settings.get('default_event_duration', 1.0)
        )
        
        # Timezone settings
        st.write("**Timezone Settings**")
        common_timezones = [
            'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 
            'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo'
        ]
        
        if st.session_state.timezone in common_timezones:
            tz_index = common_timezones.index(st.session_state.timezone)
        else:
            tz_index = 0
            
        st.session_state.timezone = st.selectbox(
            "Timezone", 
            options=common_timezones,
            index=tz_index
        )
        
        st.markdown("---")
        
        # Data management
        st.write("**Data Management**")
        
        if st.session_state.last_backup:
            backup_time = datetime.fromisoformat(st.session_state.last_backup)
            st.write(f"Last backup: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        col_backup1, col_backup2 = st.columns(2)
        
        with col_backup1:
            if st.button("💾 Backup Now", use_container_width=True):
                st.session_state.last_backup = datetime.now().isoformat()
                st.success("✅ Backup completed!")
        
        with col_backup2:
            if st.button("🔄 Reset All", use_container_width=True, type="secondary"):
                if st.button("⚠️ Confirm Reset", use_container_width=True, type="secondary"):
                    st.session_state.events = []
                    st.session_state.selected_event = None
                    st.session_state.calendars = {'entremotivator@gmail.com': {'name': 'Default Calendar', 'color': '#3788d8', 'visible': True}}
                    st.session_state.active_calendar = 'entremotivator@gmail.com'
                    st.success("✅ All data reset!")
                    st.rerun()
        
        # Calendar management
        st.markdown("---")
        st.write("**Calendar Management**")
        
        for email, cal_info in st.session_state.calendars.items():
            col_cal1, col_cal2, col_cal3 = st.columns([2, 1, 1])
            
            with col_cal1:
                st.write(f"📧 {email}")
                st.write(f"📛 {cal_info['name']}")
            
            with col_cal2:
                # Show event count for this calendar
                event_count = len([e for e in st.session_state.events if e.get('calendar_email') == email])
                st.metric("Events", event_count)
            
            with col_cal3:
                if len(st.session_state.calendars) > 1 and email != 'entremotivator@gmail.com':
                    if st.button("🗑️", key=f"delete_cal_{email}", help="Delete calendar"):
                        # Remove calendar and its events
                        st.session_state.events = [e for e in st.session_state.events if e.get('calendar_email') != email]
                        del st.session_state.calendars[email]
                        if st.session_state.active_calendar == email:
                            st.session_state.active_calendar = list(st.session_state.calendars.keys())[0]
                        st.rerun()

# Enhanced footer with quick actions
st.markdown("---")

footer_col1, footer_col2, footer_col3, footer_col4 = st.columns(4)

with footer_col1:
    if st.button("🔄 Refresh Calendar", use_container_width=True):
        st.rerun()

with footer_col2:
    upcoming_count = len([e for e in st.session_state.events 
                         if datetime.fromisoformat(e['start'].replace('Z', '+00:00').replace('+00:00', '')) > datetime.now()])
    st.metric("Upcoming Events", upcoming_count)

with footer_col3:
    active_cal_events = len([e for e in st.session_state.events 
                           if e.get('calendar_email') == st.session_state.active_calendar])
    st.metric("Active Calendar Events", active_cal_events)

with footer_col4:
    total_calendars = len(st.session_state.calendars)
    st.metric("Total Calendars", total_calendars)

# Enhanced help section
with st.expander("ℹ️ Help & Tips"):
    st.markdown("""
    ### 📧 Email & Calendar Management
    - **Default Calendar**: `entremotivator@gmail.com` is always available
    - **Add Calendars**: Use the sidebar to add multiple calendar accounts
    - **Import Events**: Upload Google Calendar JSON exports or compatible formats
    - **Multi-Calendar**: Switch between calendars or view all events together
    
    ### 🚀 Features
    - **Smart Import**: Automatically detects calendar email from JSON files
    - **Event Categories**: Organize events by type (meeting, personal, work, etc.)
    - **Advanced Search**: Search across titles, descriptions, and locations
    - **Duplicate Events**: Easily copy events with one click
    - **Export Options**: Export individual calendars or all events
    - **Statistics**: Track events by calendar, category, and time period
    
    ### 💡 Tips
    - Click on calendar events to quickly edit them
    - Use color coding to visually organize your events
    - Set default event duration in settings for faster event creation
    - Enable auto-save to automatically backup your changes
    - Use the search feature to quickly find specific events
    
    ### 📱 Keyboard Shortcuts
    - **Ctrl+S**: Quick save (when auto-save is enabled)
    - **Escape**: Clear selection
    - **Tab**: Navigate between form fields
    """)

# Status bar
if st.session_state.events:
    st.caption(f"📊 Showing {len(st.session_state.events)} total events across {len(st.session_state.calendars)} calendars | Active: {st.session_state.active_calendar}")
else:
    st.caption("📭 No events loaded | Ready to import or create events")
