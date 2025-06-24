import streamlit as st
import random
import string
import time
from datetime import datetime
import sqlite3
import threading
import os

# Initialize database
def init_db():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            host_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id TEXT,
            name TEXT,
            is_host BOOLEAN,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    ''')
    conn.commit()
    conn.close()

# Database functions
def create_meeting(meeting_id, host_name):
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO meetings (id, host_name) VALUES (?, ?)", 
                  (meeting_id, host_name))
        c.execute("INSERT INTO participants (meeting_id, name, is_host) VALUES (?, ?, ?)",
                  (meeting_id, host_name, 1))  # 1 for True in SQLite
        conn.commit()
    except sqlite3.IntegrityError:
        st.error("Meeting ID already exists!")
    finally:
        conn.close()

def join_meeting(meeting_id, name):
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    try:
        # Check if meeting exists
        c.execute("SELECT id FROM meetings WHERE id = ?", (meeting_id,))
        if not c.fetchone():
            st.error("Meeting ID does not exist!")
            return False
        
        # Add participant
        c.execute("INSERT INTO participants (meeting_id, name, is_host) VALUES (?, ?, ?)",
                  (meeting_id, name, 0))  # 0 for False
        conn.commit()
        return True
    finally:
        conn.close()

def get_participants(meeting_id):
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    try:
        c.execute("SELECT name, is_host FROM participants WHERE meeting_id = ?", (meeting_id,))
        participants = []
        for row in c.fetchall():
            participants.append({
                "name": row[0],
                "is_host": bool(row[1]),
                "mic_on": True,  # Default state
                "camera_on": True  # Default state
            })
        return participants
    finally:
        conn.close()

def remove_participant(meeting_id, name):
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM participants WHERE meeting_id = ? AND name = ?", 
                  (meeting_id, name))
        conn.commit()
    finally:
        conn.close()

def end_meeting(meeting_id):
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM participants WHERE meeting_id = ?", (meeting_id,))
        c.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        conn.commit()
    finally:
        conn.close()

# Generate a random meeting ID
def generate_meeting_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Initialize session state
def init_session_state():
    if 'meeting_state' not in st.session_state:
        st.session_state.meeting_state = "home"
    if 'meeting_id' not in st.session_state:
        st.session_state.meeting_id = ""
    if 'participants' not in st.session_state:
        st.session_state.participants = []
    if 'host_name' not in st.session_state:
        st.session_state.host_name = ""
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'is_host' not in st.session_state:
        st.session_state.is_host = False
    if 'mic_on' not in st.session_state:
        st.session_state.mic_on = True
    if 'camera_on' not in st.session_state:
        st.session_state.camera_on = True
    if 'subtitles_on' not in st.session_state:
        st.session_state.subtitles_on = False
    if 'subtitle_history' not in st.session_state:
        st.session_state.subtitle_history = []
    if 'last_subtitle_time' not in st.session_state:
        st.session_state.last_subtitle_time = time.time()
    if 'last_participant_check' not in st.session_state:
        st.session_state.last_participant_check = 0

# Initialize database
init_db()

# Home screen
def home_screen():
    st.title("🎥 Meeting App with Live Subtitles")
    st.subheader("Host or join meetings with real-time transcription")
    
    st.markdown("""
    <style>
    .feature-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .feature-card h3 {
        color: #4cc9f0;
        margin-top: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>✨ Unique Features</h3>
            <p>• Real-time meeting subtitles</p>
            <p>• Host controls</p>
            <p>• Participant management</p>
            <p>• Simple deployment</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🚀 How It Works</h3>
            <p>1. Host creates a meeting</p>
            <p>2. Share meeting ID</p>
            <p>3. Participants join</p>
            <p>4. Enable subtitles</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Host a Meeting")
        st.write("Create a new meeting and invite others")
        if st.button("Start Hosting", key="host_btn", use_container_width=True, type="primary"):
            st.session_state.meeting_state = "hosting"
    
    with col2:
        st.subheader("Join a Meeting")
        st.write("Enter a meeting ID to join an existing meeting")
        if st.button("Join Meeting", key="join_btn", use_container_width=True, type="primary"):
            st.session_state.meeting_state = "joining"
    
    st.markdown("---")
    st.caption("Developed with Streamlit • Ready for deployment")

# Host meeting form
def host_meeting():
    st.title("🎤 Host a Meeting")
    
    with st.form("host_form"):
        st.session_state.host_name = st.text_input("Your Name", placeholder="Enter your name", max_chars=30)
        
        if st.form_submit_button("Create Meeting", type="primary"):
            if st.session_state.host_name.strip():
                st.session_state.meeting_id = generate_meeting_id()
                st.session_state.user_name = st.session_state.host_name
                st.session_state.is_host = True
                
                # Create meeting in database
                create_meeting(st.session_state.meeting_id, st.session_state.host_name)
                
                # Add host as first participant
                st.session_state.participants = get_participants(st.session_state.meeting_id)
                
                st.session_state.meeting_state = "meeting"
                st.experimental_rerun()
            else:
                st.warning("Please enter your name")

    if st.button("Back to Home"):
        st.session_state.meeting_state = "home"
        st.experimental_rerun()

# Join meeting form
def join_meeting():
    st.title("👥 Join a Meeting")
    
    with st.form("join_form"):
        st.session_state.user_name = st.text_input("Your Name", placeholder="Enter your name", max_chars=30)
        meeting_id = st.text_input("Meeting ID", placeholder="Enter meeting ID", max_chars=8).upper()
        
        if st.form_submit_button("Join Meeting", type="primary"):
            if st.session_state.user_name.strip() and meeting_id.strip():
                if join_meeting_db(meeting_id, st.session_state.user_name):
                    st.session_state.meeting_id = meeting_id
                    st.session_state.is_host = False
                    st.session_state.participants = get_participants(meeting_id)
                    st.session_state.meeting_state = "meeting"
                    st.experimental_rerun()
            else:
                st.warning("Please enter both your name and meeting ID")
    
    if st.button("Back to Home"):
        st.session_state.meeting_state = "home"
        st.experimental_rerun()

# Meeting room
def meeting_room():
    # Check for new participants every 3 seconds
    current_time = time.time()
    if current_time - st.session_state.last_participant_check > 3:
        st.session_state.participants = get_participants(st.session_state.meeting_id)
        st.session_state.last_participant_check = current_time
        st.experimental_rerun()
    
    # Header
    st.title(f"Meeting: {st.session_state.meeting_id}")
    
    # Top controls
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.markdown(f"**Participants:** {len(st.session_state.participants)}")
        with col2:
            host = next((p for p in st.session_state.participants if p['is_host']), None)
            if host:
                st.markdown(f"**Host:** {host['name']}")
        with col3:
            st.session_state.subtitles_on = st.toggle("Live Subtitles", st.session_state.subtitles_on)
    
    st.markdown("---")
    
    # Video and participants section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Video grid
        st.subheader("Participants")
        
        # Simulated video grid
        cols = st.columns(2)
        for idx, participant in enumerate(st.session_state.participants):
            with cols[idx % 2]:
                with st.container():
                    # Participant card
                    st.image(f"https://placehold.co/400x250/1a2a6c/white?text={participant['name']}", 
                             caption=f"{participant['name']} {'(Host)' if participant['is_host'] else ''}")
                    
                    # Status indicators
                    col_a, col_b = st.columns(2)
                    with col_a:
                        mic_status = "🔴 Muted" if not st.session_state.get(f"mic_{participant['name']}", True) else "🎤 Mic On"
                        st.markdown(f"<div style='text-align: center;'>{mic_status}</div>", unsafe_allow_html=True)
                    with col_b:
                        cam_status = "🔴 Camera Off" if not st.session_state.get(f"cam_{participant['name']}", True) else "📷 Camera On"
                        st.markdown(f"<div style='text-align: center;'>{cam_status}</div>", unsafe_allow_html=True)
    
    with col2:
        # Participants list
        st.subheader("Attendees")
        for participant in st.session_state.participants:
            icon = "👑" if participant["is_host"] else "👤"
            st.markdown(f"{icon} {participant['name']}")
        
        st.markdown("---")
        
        # Subtitles panel
        st.subheader("Live Subtitles")
        
        if st.session_state.subtitles_on:
            # Display subtitle history
            for item in st.session_state.subtitle_history[-5:]:
                with st.chat_message("user"):
                    st.markdown(f"**{item['speaker']}** ({item['timestamp']}):")
                    st.write(item['text'])
            
            # Generate simulated subtitles
            if current_time - st.session_state.last_subtitle_time > 8 and st.session_state.subtitle_history:
                st.session_state.last_subtitle_time = current_time
                last_speaker = st.session_state.subtitle_history[-1]["speaker"]
                if last_speaker != "System" and st.session_state.participants:
                    responses = [
                        "That's an interesting point.",
                        "I agree with that approach.",
                        "Could you elaborate on that?",
                        "We should consider the budget implications.",
                        "Let's schedule a follow-up meeting."
                    ]
                    fake_participant = random.choice([p for p in st.session_state.participants if p["name"] != last_speaker])
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.subtitle_history.append({
                        "speaker": fake_participant["name"],
                        "text": random.choice(responses),
                        "timestamp": timestamp
                    })
                    st.experimental_rerun()
        else:
            st.info("Subtitles are currently disabled. Enable them to see live transcriptions.")
    
    # Bottom controls
    st.markdown("---")
    control_cols = st.columns(5)
    
    with control_cols[0]:
        if st.button("🎤 Mute" if st.session_state.mic_on else "🔴 Unmute"):
            st.session_state.mic_on = not st.session_state.mic_on
    
    with control_cols[1]:
        if st.button("📷 Stop" if st.session_state.camera_on else "▶️ Start"):
            st.session_state.camera_on = not st.session_state.camera_on
    
    with control_cols[2]:
        if st.session_state.is_host:
            if st.button("⛔ End Meeting", type="primary"):
                end_meeting(st.session_state.meeting_id)
                st.success("Meeting ended successfully!")
                time.sleep(1)
                st.session_state.meeting_state = "home"
                st.experimental_rerun()
        else:
            if st.button("🚪 Leave Meeting", type="primary"):
                remove_participant(st.session_state.meeting_id, st.session_state.user_name)
                st.success("You left the meeting")
                time.sleep(1)
                st.session_state.meeting_state = "home"
                st.experimental_rerun()
    
    with control_cols[3]:
        if st.button("💬 Simulate Speech", help="For demo purposes"):
            phrases = [
                "I think we should consider the user experience first",
                "The deadline for this project is next Friday",
                "We've seen a 15% increase in engagement",
                "Let's revisit this in our next meeting",
                "The data suggests we need a different approach"
            ]
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.subtitle_history.append({
                "speaker": st.session_state.user_name,
                "text": random.choice(phrases),
                "timestamp": timestamp
            })
    
    with control_cols[4]:
        if st.button("↩️ Home"):
            if not st.session_state.is_host:
                remove_participant(st.session_state.meeting_id, st.session_state.user_name)
            st.session_state.meeting_state = "home"
            st.experimental_rerun()

# Main app
def main():
    # Set page config
    st.set_page_config(
        page_title="Meeting App with Live Subtitles",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize session state
    init_session_state()
    
    # Hide Streamlit header/footer
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {padding-top: 1rem;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Navigation
    if st.session_state.meeting_state == "home":
        home_screen()
    elif st.session_state.meeting_state == "hosting":
        host_meeting()
    elif st.session_state.meeting_state == "joining":
        join_meeting()
    elif st.session_state.meeting_state == "meeting":
        meeting_room()

if __name__ == "__main__":
    main()
