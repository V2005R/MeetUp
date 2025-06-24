import streamlit as st
import random
import string
import time
from datetime import datetime
import threading
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase, AudioProcessorBase
import speech_recognition as sr
from queue import Queue

# Generate a random meeting ID
def generate_meeting_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Initialize session state
def init_session_state():
    if 'meeting_state' not in st.session_state:
        st.session_state.meeting_state = "home"  # home, hosting, joining, meeting
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
    if 'subtitle_queue' not in st.session_state:
        st.session_state.subtitle_queue = Queue()
    if 'subtitle_history' not in st.session_state:
        st.session_state.subtitle_history = []
    if 'recognition_active' not in st.session_state:
        st.session_state.recognition_active = False
    if 'recognition_thread' not in st.session_state:
        st.session_state.recognition_thread = None

# Audio processor for speech recognition
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        self.audio_queue = Queue()
        self.running = True
        
    def recv(self, frame):
        # Placeholder for audio processing
        return frame
    
    def start_recognition(self):
        def recognize_worker():
            while self.running:
                try:
                    audio = self.audio_queue.get(timeout=1)
                    if audio is None:
                        break
                    text = self.recognizer.recognize_google(audio)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.subtitle_queue.put({
                        "speaker": st.session_state.user_name,
                        "text": text,
                        "timestamp": timestamp
                    })
                except (sr.UnknownValueError, sr.RequestError):
                    pass
                except Exception as e:
                    print(f"Recognition error: {e}")
        
        threading.Thread(target=recognize_worker, daemon=True).start()
    
    def stop_recognition(self):
        self.running = False

# Home screen
def home_screen():
    st.title("🎥 Meeting App with Live Subtitles")
    st.subheader("Host or join meetings with real-time transcription")
    
    st.write("""
    Welcome to our innovative meeting platform! This app allows you to:
    - Host meetings with unique IDs
    - Join existing meetings
    - See who's speaking with live subtitles
    - Control your microphone and camera
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Host a Meeting")
        st.write("Create a new meeting and invite others")
        if st.button("Start Hosting", key="host_btn", use_container_width=True):
            st.session_state.meeting_state = "hosting"
    
    with col2:
        st.subheader("Join a Meeting")
        st.write("Enter a meeting ID to join an existing meeting")
        if st.button("Join Meeting", key="join_btn", use_container_width=True):
            st.session_state.meeting_state = "joining"
    
    st.markdown("---")
    st.caption("Developed with Streamlit • Features real-time speech recognition")

# Host meeting form
def host_meeting():
    st.title("🎤 Host a Meeting")
    
    with st.form("host_form"):
        st.session_state.host_name = st.text_input("Your Name", placeholder="Enter your name", max_chars=30)
        
        if st.form_submit_button("Create Meeting"):
            if st.session_state.host_name.strip():
                st.session_state.meeting_id = generate_meeting_id()
                st.session_state.user_name = st.session_state.host_name
                st.session_state.is_host = True
                
                # Add host as first participant
                st.session_state.participants.append({
                    "id": "host",
                    "name": st.session_state.host_name,
                    "is_host": True,
                    "mic_on": True,
                    "camera_on": True
                })
                
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
        
        if st.form_submit_button("Join Meeting"):
            if st.session_state.user_name.strip() and meeting_id.strip():
                st.session_state.meeting_id = meeting_id
                st.session_state.is_host = False
                
                # Add participant
                st.session_state.participants.append({
                    "id": str(len(st.session_state.participants) + 1),
                    "name": st.session_state.user_name,
                    "is_host": False,
                    "mic_on": True,
                    "camera_on": True
                })
                
                # Add simulated participants for demo
                if len(st.session_state.participants) == 1:
                    st.session_state.participants.append({
                        "id": "host",
                        "name": "Meeting Host",
                        "is_host": True,
                        "mic_on": True,
                        "camera_on": True
                    })
                    st.session_state.participants.append({
                        "id": "p2",
                        "name": "Alex Johnson",
                        "is_host": False,
                        "mic_on": True,
                        "camera_on": True
                    })
                
                st.session_state.meeting_state = "meeting"
                st.experimental_rerun()
            else:
                st.warning("Please enter both your name and meeting ID")
    
    if st.button("Back to Home"):
        st.session_state.meeting_state = "home"
        st.experimental_rerun()

# Meeting room
def meeting_room():
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
        
        # User's own video
        webrtc_ctx = webrtc_streamer(
            key="meeting",
            mode=WebRtcMode.SENDRECV,
            audio_receiver_size=256,
            video_processor_factory=None,
            media_stream_constraints={
                "video": st.session_state.camera_on,
                "audio": st.session_state.mic_on
            },
        )
        
        # Simulated participant videos
        cols = st.columns(2)
        for idx, participant in enumerate(st.session_state.participants):
            if participant["name"] != st.session_state.user_name:  # Skip current user
                with cols[idx % 2]:
                    with st.container():
                        st.image("https://placehold.co/400x250/1a2a6c/white?text=" + participant["name"], 
                                 caption=f"{participant['name']} {'(Host)' if participant['is_host'] else ''}")
                        
                        # Status indicators
                        status_cols = st.columns([1,1])
                        with status_cols[0]:
                            mic_status = "🔴" if not participant["mic_on"] else "🎤"
                            st.markdown(f"{mic_status} Mic")
                        with status_cols[1]:
                            cam_status = "🔴" if not participant["camera_on"] else "📷"
                            st.markdown(f"{cam_status} Camera")
    
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
            for item in st.session_state.subtitle_history[-5:]:  # Show last 5
                with st.chat_message("user"):
                    st.markdown(f"**{item['speaker']}** ({item['timestamp']}):")
                    st.write(item['text'])
            
            # Add simulated subtitles for demo
            if random.random() > 0.8 and st.session_state.subtitle_history:
                last_speaker = st.session_state.subtitle_history[-1]["speaker"]
                if last_speaker != "System":
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
            st.experimental_rerun()
    
    with control_cols[1]:
        if st.button("📷 Stop" if st.session_state.camera_on else "▶️ Start"):
            st.session_state.camera_on = not st.session_state.camera_on
            st.experimental_rerun()
    
    with control_cols[2]:
        if st.session_state.is_host:
            if st.button("⛔ End Meeting"):
                st.success("Meeting ended successfully!")
                time.sleep(1)
                st.session_state.meeting_state = "home"
                st.experimental_rerun()
        else:
            if st.button("🚪 Leave Meeting"):
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
            st.experimental_rerun()
    
    with control_cols[4]:
        if st.button("↩️ Home"):
            st.session_state.meeting_state = "home"
            st.experimental_rerun()
    
    # Simulate automatic subtitles
    if st.session_state.subtitles_on and webrtc_ctx.audio_receiver:
        try:
            # This is a placeholder for actual speech recognition
            # In a real app, you would process the audio frames here
            if random.random() > 0.9:  # Randomly simulate speech detection
                phrases = [
                    "Moving on to the next agenda item",
                    "We need to consider all options",
                    "The data supports this conclusion",
                    "Let's summarize the action items",
                    "I'd like to hear other opinions"
                ]
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.subtitle_history.append({
                    "speaker": st.session_state.user_name,
                    "text": random.choice(phrases),
                    "timestamp": timestamp
                })
                st.experimental_rerun()
        except Exception as e:
            st.error(f"Speech recognition error: {str(e)}")

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
