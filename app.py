import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import uuid
from streamlit_calendar import calendar
import pytz

# Page configuration
st.set_page_config(
    page_title="Google Calendar Manager",
    page_icon="📅",
    layout="wide"
)

# Initialize session state
if 'events' not in st.session_state:
    st.session_state.events = []
if 'selected_event' not in st.session_state:
    st.session_state.selected_event = None

def load_events_from_json(uploaded_file):
    """Load events from uploaded JSON file"""
    try:
        content = json.load(uploaded_file)
        
        # Handle different JSON structures
        if isinstance(content, list):
            events = content
        elif 'items' in content:
            events = content['items']
        elif 'events' in content:
            events = content['events']
        else:
            events = [content]
        
        # Normalize event format
        normalized_events = []
        for event in events:
            normalized_event = {
                'id': event.get('id', str(uuid.uuid4())),
                'title': event.get('summary', event.get('title', 'Untitled Event')),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', datetime.now().isoformat())),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', (datetime.now() + timedelta(hours=1)).isoformat())),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'color': event.get('colorId', '#3788d8')
            }
            
            # Ensure datetime format
            if 'T' not in normalized_event['start']:
                normalized_event['start'] += 'T00:00:00'
            if 'T' not in normalized_event['end']:
                normalized_event['end'] += 'T23:59:59'
                
            normalized_events.append(normalized_event)
        
        return normalized_events
    except Exception as e:
        st.error(f"Error loading JSON file: {str(e)}")
        return []

def format_events_for_calendar(events):
    """Format events for streamlit-calendar component"""
    calendar_events = []
    for event in events:
        calendar_event = {
            'id': event['id'],
            'title': event['title'],
            'start': event['start'],
            'end': event['end'],
            'color': event.get('color', '#3788d8'),
            'description': event.get('description', ''),
            'location': event.get('location', '')
        }
        calendar_events.append(calendar_event)
    return calendar_events

def add_event(title, start_date, start_time, end_date, end_time, description="", location="", color="#3788d8"):
    """Add a new event"""
    start_datetime = datetime.combine(start_date, start_time).isoformat()
    end_datetime = datetime.combine(end_date, end_time).isoformat()
    
    new_event = {
        'id': str(uuid.uuid4()),
        'title': title,
        'start': start_datetime,
        'end': end_datetime,
        'description': description,
        'location': location,
        'color': color
    }
    
    st.session_state.events.append(new_event)
    st.success("Event added successfully!")

def update_event(event_id, title, start_date, start_time, end_date, end_time, description="", location="", color="#3788d8"):
    """Update an existing event"""
    start_datetime = datetime.combine(start_date, start_time).isoformat()
    end_datetime = datetime.combine(end_date, end_time).isoformat()
    
    for i, event in enumerate(st.session_state.events):
        if event['id'] == event_id:
            st.session_state.events[i].update({
                'title': title,
                'start': start_datetime,
                'end': end_datetime,
                'description': description,
                'location': location,
                'color': color
            })
            st.success("Event updated successfully!")
            break

def delete_event(event_id):
    """Delete an event"""
    st.session_state.events = [event for event in st.session_state.events if event['id'] != event_id]
    st.success("Event deleted successfully!")

def export_events_to_json():
    """Export events to JSON format"""
    return json.dumps(st.session_state.events, indent=2)

# Main app layout
st.title("📅 Google Calendar Manager")
st.markdown("---")

# Sidebar for file upload and event management
with st.sidebar:
    st.header("📁 File Upload")
    uploaded_file = st.file_uploader(
        "Upload Google Calendar JSON",
        type=['json'],
        help="Upload your Google Calendar export or any JSON file with calendar events"
    )
    
    if uploaded_file is not None:
        if st.button("Load Events"):
            new_events = load_events_from_json(uploaded_file)
            if new_events:
                st.session_state.events.extend(new_events)
                st.success(f"Loaded {len(new_events)} events!")
                st.rerun()
    
    st.markdown("---")
    
    # Export functionality
    st.header("📤 Export Events")
    if st.session_state.events:
        json_data = export_events_to_json()
        st.download_button(
            label="Download Events as JSON",
            data=json_data,
            file_name=f"calendar_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    
    # Quick stats
    st.header("📊 Statistics")
    st.metric("Total Events", len(st.session_state.events))
    
    if st.session_state.events:
        upcoming_events = [
            event for event in st.session_state.events 
            if datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', '')) > datetime.now()
        ]
        st.metric("Upcoming Events", len(upcoming_events))

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📅 Calendar View")
    
    if st.session_state.events:
        calendar_events = format_events_for_calendar(st.session_state.events)
        
        calendar_options = {
            "editable": True,
            "selectable": True,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay"
            },
            "initialView": "dayGridMonth",
            "height": 600
        }
        
        calendar_result = calendar(
            events=calendar_events,
            options=calendar_options,
            custom_css="""
            .fc-event-past {
                opacity: 0.8;
            }
            .fc-event-time {
                font-weight: bold;
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
        st.info("No events to display. Upload a JSON file or add a new event to get started!")

with col2:
    st.header("⚙️ Event Management")
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["➕ Add", "✏️ Edit", "📋 List"])
    
    with tab1:
        st.subheader("Add New Event")
        with st.form("add_event_form"):
            title = st.text_input("Event Title*", placeholder="Enter event title")
            
            col_date1, col_date2 = st.columns(2)
            with col_date1:
                start_date = st.date_input("Start Date", value=datetime.now().date())
                start_time = st.time_input("Start Time", value=datetime.now().time())
            with col_date2:
                end_date = st.date_input("End Date", value=datetime.now().date())
                end_time = st.time_input("End Time", value=(datetime.now() + timedelta(hours=1)).time())
            
            description = st.text_area("Description", placeholder="Event description (optional)")
            location = st.text_input("Location", placeholder="Event location (optional)")
            
            color_options = {
                "Blue": "#3788d8",
                "Green": "#33b679",
                "Red": "#e74c3c",
                "Orange": "#f39c12",
                "Purple": "#9b59b6",
                "Pink": "#e91e63"
            }
            color_name = st.selectbox("Color", list(color_options.keys()))
            color = color_options[color_name]
            
            submitted = st.form_submit_button("Add Event")
            
            if submitted:
                if title:
                    add_event(title, start_date, start_time, end_date, end_time, description, location, color)
                    st.rerun()
                else:
                    st.error("Please enter an event title")
    
    with tab2:
        st.subheader("Edit Event")
        
        if st.session_state.selected_event:
            event = st.session_state.selected_event
            
            with st.form("edit_event_form"):
                title = st.text_input("Event Title*", value=event['title'])
                
                # Parse existing datetime
                start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', ''))
                end_dt = datetime.fromisoformat(event['end'].replace('Z', '+00:00').replace('+00:00', ''))
                
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input("Start Date", value=start_dt.date())
                    start_time = st.time_input("Start Time", value=start_dt.time())
                with col_date2:
                    end_date = st.date_input("End Date", value=end_dt.date())
                    end_time = st.time_input("End Time", value=end_dt.time())
                
                description = st.text_area("Description", value=event.get('description', ''))
                location = st.text_input("Location", value=event.get('location', ''))
                
                color_options = {
                    "Blue": "#3788d8",
                    "Green": "#33b679",
                    "Red": "#e74c3c",
                    "Orange": "#f39c12",
                    "Purple": "#9b59b6",
                    "Pink": "#e91e63"
                }
                
                current_color = event.get('color', '#3788d8')
                current_color_name = next((name for name, code in color_options.items() if code == current_color), "Blue")
                color_name = st.selectbox("Color", list(color_options.keys()), index=list(color_options.keys()).index(current_color_name))
                color = color_options[color_name]
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    update_submitted = st.form_submit_button("Update Event", use_container_width=True)
                with col_btn2:
                    delete_submitted = st.form_submit_button("Delete Event", use_container_width=True, type="secondary")
                
                if update_submitted:
                    if title:
                        update_event(event['id'], title, start_date, start_time, end_date, end_time, description, location, color)
                        st.session_state.selected_event = None
                        st.rerun()
                    else:
                        st.error("Please enter an event title")
                
                if delete_submitted:
                    delete_event(event['id'])
                    st.session_state.selected_event = None
                    st.rerun()
        else:
            st.info("Click on an event in the calendar to edit it, or select from the list below.")
    
    with tab3:
        st.subheader("All Events")
        
        if st.session_state.events:
            # Sort events by start date
            sorted_events = sorted(st.session_state.events, key=lambda x: x['start'])
            
            for event in sorted_events:
                start_dt = datetime.fromisoformat(event['start'].replace('Z', '+00:00').replace('+00:00', ''))
                
                with st.container():
                    col_info, col_action = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**{event['title']}**")
                        st.write(f"📅 {start_dt.strftime('%Y-%m-%d %H:%M')}")
                        if event.get('location'):
                            st.write(f"📍 {event['location']}")
                    
                    with col_action:
                        if st.button("Edit", key=f"edit_{event['id']}", use_container_width=True):
                            st.session_state.selected_event = event
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No events found. Add some events to see them here!")

# Clear all events button
if st.session_state.events:
    st.markdown("---")
    if st.button("🗑️ Clear All Events", type="secondary"):
        if st.button("Confirm Clear All", type="secondary"):
            st.session_state.events = []
            st.session_state.selected_event = None
            st.success("All events cleared!")
            st.rerun()
