import streamlit as st
import hashlib
import datetime
import pandas as pd
import json
import plotly.express as px
import time
import uuid
from io import BytesIO
from typing import Dict, List, Optional

# ============
# PAGE CONFIG (должен быть САМЫМ ПЕРВЫМ вызовом Streamlit)
# ============
st.set_page_config(
    page_title="PatentChain - Advanced Patent Management System",
    page_icon="⛓️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------
# Enhanced Blockchain Classes
# ---------------

class Block:
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        # ISO 8601 — удобно для парсинга/сортировки
        self.timestamp = timestamp if isinstance(timestamp, str) else timestamp.isoformat()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
        self.merkle_root = self.calculate_merkle_root()

    def calculate_hash(self):
        block_string = (
            str(self.index) +
            str(self.timestamp) +
            json.dumps(self.data, sort_keys=True) +
            str(self.previous_hash) +
            str(self.nonce)
        )
        return hashlib.sha256(block_string.encode()).hexdigest()

    def calculate_merkle_root(self):
        """Simplified Merkle root calculation"""
        data_string = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()

    def mine_block(self, difficulty=2):
        """Simple proof of work mining"""
        target = "0" * difficulty
        # Важно: пересчитать hash после изменения previous_hash выше по стеку
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    def __init__(self):
        self.difficulty = 2
        self.pending_transactions = []
        self.mining_reward = 100
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        genesis_block = Block(
            index=0,
            timestamp=datetime.datetime.now().isoformat(),
            data={
                "title": "Genesis Block",
                "description": "First block in the patent blockchain",
                "doc_hash": "",
                "patent_type": "Genesis",
                "is_on_blockchain": True,
                "patent_id": "GENESIS-000",
                "inventor": "System",
                "status": "Active",
                "priority": "Normal",
                "timestamp": datetime.datetime.now().isoformat()
            },
            previous_hash="0"
        )
        genesis_block.mine_block(self.difficulty)
        return genesis_block

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, new_block: Block):
        # корректно проставляем previous_hash, затем майним
        new_block.previous_hash = self.get_latest_block().hash
        # сброс nonce на всякий случай
        new_block.nonce = 0
        new_block.hash = new_block.calculate_hash()
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)

    def is_chain_valid(self):
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            # пересчитать и сравнить
            if current_block.hash != current_block.calculate_hash():
                return False
            if current_block.previous_hash != previous_block.hash:
                return False
        return True

# ---------------
# Data Models
# ---------------

class Patent:
    def __init__(self, title, description, inventor, patent_type, priority="Normal"):
        self.id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
        self.title = title
        self.description = description
        self.inventor = inventor
        self.patent_type = patent_type
        self.priority = priority
        self.created_at = datetime.datetime.now()
        self.status = "Pending"
        self.file_hash = None
        self.verification_score = 0

class User:
    def __init__(self, username, role="Inventor"):
        self.username = username
        self.role = role  # Inventor, Examiner, Admin
        self.created_at = datetime.datetime.now()
        self.patents_submitted = 0
        self.last_login = datetime.datetime.now()

# ---------------
# Utility Functions
# ---------------

def hash_file_bytes(file_bytes: bytes) -> str:
    """Return a SHA-256 hex digest for file bytes."""
    return hashlib.sha256(file_bytes).hexdigest()

def generate_patent_id():
    """Generate a unique patent ID"""
    return f"PAT-{str(uuid.uuid4())[:8].upper()}"

def verify_patent_authenticity(patent_data):
    """Simulate patent verification process"""
    score = 50  # Base score
    if len(patent_data.get("title", "")) > 10:
        score += 10
    if len(patent_data.get("description", "")) > 50:
        score += 15
    if patent_data.get("doc_hash"):
        score += 20
    import random
    score += random.randint(-5, 15)
    return min(100, max(0, score))

def get_file_size_str(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def initialize_session_state():
    """Initialize all session state variables"""
    if "toy_chain" not in st.session_state:
        st.session_state.toy_chain = Blockchain()
    if "off_chain_list" not in st.session_state:
        st.session_state.off_chain_list = []

    patent_types_list = [
        "Utility Patent", "Design Patent", "Plant Patent",
        "Provisional Patent", "Software Patent", "Business Method Patent",
        "Biotechnology Patent", "Chemical Patent", "Mechanical Patent",
        "Certificate of Amendment", "Other"
    ]
    if "patent_types" not in st.session_state:
        st.session_state.patent_types = patent_types_list

    if "current_user" not in st.session_state:
        st.session_state.current_user = User("demo_user", "Inventor")
    if "users" not in st.session_state:
        st.session_state.users = {
            "demo_user": User("demo_user", "Inventor"),
            "examiner1": User("examiner1", "Examiner"),
            "admin": User("admin", "Admin")
        }

    if "counts_on_chain" not in st.session_state:
        st.session_state.counts_on_chain = {ptype: 0 for ptype in patent_types_list}
    if "counts_off_chain" not in st.session_state:
        st.session_state.counts_off_chain = {ptype: 0 for ptype in patent_types_list}

    if "notifications" not in st.session_state:
        st.session_state.notifications = []

    if "search_term" not in st.session_state:
        st.session_state.search_term = ""
    if "filter_type" not in st.session_state:
        st.session_state.filter_type = "All"

def add_notification(message, type="info"):
    notification = {
        "id": str(uuid.uuid4())[:8],
        "message": message,
        "type": type,  # info, success, warning, error
        "timestamp": datetime.datetime.now(),
        "read": False
    }
    st.session_state.notifications.insert(0, notification)

def _parse_iso(ts: str) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(ts)
    except Exception:
        # на всякий случай поддержим "YYYY-MM-DD HH:MM:SS.mmmmmm"
        return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")

def get_blockchain_stats():
    """Get comprehensive blockchain statistics"""
    chain = st.session_state.toy_chain.chain
    stats = {
        "total_blocks": len(chain),
        "total_patents": max(0, len(chain) - 1),  # Exclude genesis
        "chain_valid": st.session_state.toy_chain.is_chain_valid(),
        "average_block_time": 0.0,
        "total_hash_power": sum(block.nonce for block in chain),
        "latest_block_hash": chain[-1].hash if chain else "N/A"
    }
    if len(chain) > 1:
        timestamps = [_parse_iso(block.timestamp) for block in chain]
        # среднее по интервалам между ВСЕМИ блоками
        if len(timestamps) > 1:
            diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
            stats["average_block_time"] = sum(diffs) / len(diffs)
    return stats

# ---------------
# UI Components
# ---------------

def render_sidebar():
    """Render the enhanced sidebar"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/2E86AB/FFFFFF?text=PatentChain", width=200)

        st.markdown("---")
        st.markdown(f"**👤 User:** {st.session_state.current_user.username}")
        st.markdown(f"**🎭 Role:** {st.session_state.current_user.role}")
        st.markdown(f"**📅 Member since:** {st.session_state.current_user.created_at.strftime('%Y-%m-%d')}")

        st.markdown("---")
        st.markdown("**📊 Quick Stats**")
        stats = get_blockchain_stats()
        st.metric("Total Patents", stats["total_patents"])
        st.metric("Blockchain Health", "✅ Valid" if stats["chain_valid"] else "❌ Invalid")

        st.markdown("---")
        unread_count = sum(1 for n in st.session_state.notifications if not n["read"])
        st.button(f"🔔 Notifications ({unread_count})")

        st.markdown("---")
        st.markdown("**🧭 Quick Navigation**")
        st.button("📝 Submit Patent", use_container_width=True)
        st.button("🔍 Search Patents", use_container_width=True)
        st.button("📈 Analytics", use_container_width=True)

def render_notification_panel():
    if st.session_state.notifications:
        with st.expander(f"🔔 Notifications ({len(st.session_state.notifications)})", expanded=False):
            for notification in st.session_state.notifications[:5]:
                icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(notification["type"], "ℹ️")
                st.markdown(f"{icon} **{notification['timestamp'].strftime('%H:%M')}** - {notification['message']}")

def render_advanced_search():
    st.subheader("🔍 Advanced Patent Search")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input(
            "Search patents...",
            placeholder="Enter keywords, patent ID, or inventor name",
            value=st.session_state.search_term
        )
    with col2:
        filter_type = st.selectbox(
            "Filter by Type",
            ["All"] + st.session_state.patent_types,
            index=0 if st.session_state.filter_type == "All" else
            st.session_state.patent_types.index(st.session_state.filter_type) + 1
        )
    with col3:
        filter_status = st.selectbox("Filter by Status", ["All", "Active", "Pending", "Approved", "Rejected"])

    with st.expander("🔧 Advanced Filters"):
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("From Date", value=datetime.date.today() - datetime.timedelta(days=30))
            priority_filter = st.multiselect("Priority", ["Low", "Normal", "High", "Critical"])
        with col2:
            date_to = st.date_input("To Date", value=datetime.date.today())
            storage_filter = st.selectbox("Storage", ["All", "On-Chain", "Off-Chain"])

    return {
        "search_term": search_term,
        "filter_type": filter_type,
        "filter_status": filter_status,
        "date_from": date_from,
        "date_to": date_to,
        "priority_filter": priority_filter,
        "storage_filter": storage_filter
    }

def _block_card(block: Block):
    """Презентабельная карточка блока"""
    # Верхние метрики
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Block #", block.index)
    colB.metric("Nonce", block.nonce)
    colC.metric("Time", _parse_iso(block.timestamp).strftime("%Y-%m-%d %H:%M:%S"))
    colD.metric("Prev…", f"{block.previous_hash[:8]}…")

    st.markdown(
        f"""
        <div style="background-color:#f7f9fc;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-top:8px;">
          <div style="font-family:monospace;">
            <div><b>Hash:</b> <code>{block.hash}</code></div>
            <div><b>Merkle Root:</b> <code>{block.merkle_root}</code></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Краткое резюме данных
    data = block.data or {}
    summary_cols = st.columns(4)
    summary_cols[0].write(f"**Patent ID**\n{data.get('patent_id','—')}")
    summary_cols[1].write(f"**Type**\n{data.get('patent_type','—')}")
    summary_cols[2].write(f"**Priority**\n{data.get('priority','—')}")
    summary_cols[3].write(f"**Status**\n{data.get('status','—')}")

    with st.expander("📦 Full Block Data"):
        st.json(block.data)

def render_analytics_dashboard():
    st.header("📈 Patent Analytics Dashboard")

    stats = get_blockchain_stats()
    total_on_chain = sum(st.session_state.counts_on_chain.values())
    total_off_chain = sum(st.session_state.counts_off_chain.values())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Patents", total_on_chain + total_off_chain)
    c2.metric("On-Chain Patents", total_on_chain)
    c3.metric("Off-Chain Patents", total_off_chain)
    c4.metric("Blockchain Blocks", stats["total_blocks"])

    # Distribution: аккуратно, без дублирования labels
    dist_rows = []
    for k, v in st.session_state.counts_on_chain.items():
        dist_rows.append({"Type": k, "Storage": "On-Chain", "Count": v})
    for k, v in st.session_state.counts_off_chain.items():
        dist_rows.append({"Type": k, "Storage": "Off-Chain", "Count": v})
    dist_df = pd.DataFrame(dist_rows)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(dist_df, x="Type", y="Count", color="Storage", barmode="group", title="Patent Distribution by Type & Storage")
        fig.update_layout(xaxis_title="", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        dates = pd.date_range(start=datetime.date.today() - datetime.timedelta(days=30),
                              end=datetime.date.today(), freq='D')
        values = [abs(hash(str(date)) % 10) for date in dates]
        fig_line = px.line(x=dates, y=values, title="Patent Submissions Over Time")
        fig_line.update_layout(xaxis_title="Date", yaxis_title="Number of Patents")
        st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("⛓️ Blockchain Health Metrics")
    h1, h2, h3 = st.columns(3)
    h1.metric("Chain Validity", "✅ Valid" if stats["chain_valid"] else "❌ Invalid")
    h2.metric("Average Block Time", f"{stats['average_block_time']:.2f}s")
    h3.metric("Total Mining Power", f"{stats['total_hash_power']:,}")

def render_blockchain_explorer():
    st.subheader("⛓️ Blockchain Explorer")
    chain = st.session_state.toy_chain.chain

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Blocks", len(chain))
    c2.metric("Latest Block", f"#{len(chain)-1}")
    c3.metric("Latest Hash", chain[-1].hash[:16] + "..." if chain else "N/A")

    if chain:
        block_index = st.selectbox(
            "Select Block to Explore",
            range(len(chain)),
            format_func=lambda x: f"Block #{x}" + (" (Genesis)" if x == 0 else "")
        )
        _block_card(chain[block_index])

def export_data():
    st.subheader("📤 Export Patent Data")

    export_format = st.selectbox("Select Export Format", ["CSV", "JSON", "Excel"])
    include_blockchain = st.checkbox("Include Blockchain Data", value=True)
    include_offchain = st.checkbox("Include Off-Chain Data", value=True)

    if st.button("Generate Export"):
        data = []

        # On-chain
        if include_blockchain:
            for block in st.session_state.toy_chain.chain[1:]:  # Skip genesis
                row = {
                    "source": "blockchain",
                    "block_index": block.index,
                    "timestamp": block.timestamp,  # добавили для сортировки/фильтров
                    "block_hash": block.hash,
                }
                # плоское объединение
                row.update(block.data or {})
                data.append(row)

        # Off-chain
        if include_offchain:
            for i, record in enumerate(st.session_state.off_chain_list):
                row = {
                    "source": "off-chain",
                    "record_index": i,
                    "timestamp": record.get("timestamp"),
                    "block_hash": None
                }
                row.update(record.get("data", {}))
                data.append(row)

        if not data:
            st.info("Nothing to export with selected options.")
            return

        df = pd.DataFrame(data)

        ts_fname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if export_format == "CSV":
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                csv,
                file_name=f"patents_{ts_fname}.csv",
                mime="text/csv"
            )
        elif export_format == "JSON":
            json_str = df.to_json(orient="records", indent=2, date_format="iso")
            st.download_button(
                "Download JSON",
                json_str,
                file_name=f"patents_{ts_fname}.json",
                mime="application/json"
            )
        else:  # Excel
            buffer = BytesIO()
            try:
                # Попытка через openpyxl (по умолчанию)
                df.to_excel(buffer, index=False)
            except Exception:
                # Фолбэк на xlsxwriter, если доступен
                df.to_excel(buffer, index=False, engine="xlsxwriter")
            buffer.seek(0)
            st.download_button(
                "Download Excel",
                buffer.getvalue(),
                file_name=f"patents_{ts_fname}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# ---------------
# Main Application
# ---------------

def main():
    # Инициализируем состояние (после page_config)
    initialize_session_state()

    # Лёгкий CSS
    st.markdown("""
    <style>
    .main > div { padding-top: 2rem; }
    .stApp > header { background-color: transparent; }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .main .block-container {
        background-color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .patent-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-active { color: #28a745; font-weight: bold; }
    .status-pending { color: #ffc107; font-weight: bold; }
    .status-approved { color: #17a2b8; font-weight: bold; }
    .status-rejected { color: #dc3545; font-weight: bold; }
    .priority-high { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; }
    .priority-critical { background-color: #b30000; color: white; padding: 2px 8px; border-radius: 4px; }
    .priority-normal { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; }
    .priority-low { background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    render_sidebar()

    # Header
    st.title("⛓️ PatentChain - Advanced Patent Management System")
    st.markdown("*Secure, transparent, and efficient patent registration on blockchain*")

    # Notification panel
    render_notification_panel()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Submit Patent",
        "🔍 Search & Browse",
        "⛓️ Blockchain Explorer",
        "📈 Analytics",
        "📤 Export Data",
        "⚙️ System Info"
    ])

    with tab1:
        st.header("📝 Submit New Patent")
        
        # Add debug information
        if st.checkbox("Show Debug Info", value=False):
            st.write("**Debug Information:**")
            st.write(f"Current user: {st.session_state.current_user.username}")
            st.write(f"Session state keys: {list(st.session_state.keys())}")
            st.write(f"Patent types available: {len(st.session_state.patent_types)}")
        
        with st.form("enhanced_patent_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                patent_title = st.text_input("Patent Title *", max_chars=100,
                                             help="Enter a descriptive title for your invention")
                inventor_name = st.text_input("Inventor Name *",
                                              value=st.session_state.current_user.username,
                                              help="Primary inventor or applicant name")
                patent_type = st.selectbox("Patent Type *",
                                           options=st.session_state.patent_types,
                                           help="Select the most appropriate patent category")
            with col2:
                priority = st.selectbox("Priority Level", ["Low", "Normal", "High", "Critical"])
                store_option = st.radio("Storage Option",
                                        ("On Blockchain", "Off Blockchain"),
                                        help="Blockchain storage provides immutability but costs more")
                estimated_value = st.number_input("Estimated Value ($)", min_value=0, value=10000,
                                                  help="Estimated commercial value of the patent")

            patent_description = st.text_area("Detailed Description *", height=150,
                                              help="Provide a comprehensive description of your invention")

            col1, col2 = st.columns([2, 1])
            with col1:
                uploaded_file = st.file_uploader(
                    "Attach Supporting Documents",
                    type=["pdf", "txt", "png", "jpg", "docx", "xlsx"],
                    help="Upload relevant documents, diagrams, or specifications"
                )
            with col2:
                if uploaded_file is not None:
                    file_size_h = get_file_size_str(getattr(uploaded_file, "size", 0))
                    st.success(f"File: {uploaded_file.name}")
                    st.info(f"Size: {file_size_h}")

            with st.expander("📋 Additional Information"):
                col1, col2 = st.columns(2)
                with col1:
                    keywords = st.text_input("Keywords (comma-separated)",
                                             help="Enter relevant keywords for searchability")
                    related_patents = st.text_input("Related Patent IDs",
                                                    help="Reference any related or prior patents")
                with col2:
                    collaboration = st.text_input("Co-inventors",
                                                  help="List any co-inventors or collaborators")
                    funding_source = st.text_input("Funding Source",
                                                   help="Grant number, company, or funding organization")

            # Make the checkbox more prominent
            st.markdown("---")
            agree_terms = st.checkbox(
                "✅ I agree to the terms and conditions and confirm the originality of this work *",
                help="You must agree to the terms to submit your patent application"
            )
            
            # Show button status
            if not agree_terms:
                st.warning("⚠️ Please check the agreement checkbox above to enable the submit button.")

            # Form submission
            submitted = st.form_submit_button(
                "🚀 Submit Patent Application",
                disabled=not agree_terms,
                use_container_width=True,
                type="primary"
            )

            # Enhanced form processing with better error handling
            if submitted:
                try:
                    # Validation
                    required_fields = [
                        (patent_title.strip(), "Patent Title"),
                        (inventor_name.strip(), "Inventor Name"), 
                        (patent_description.strip(), "Patent Description")
                    ]
                    
                    missing_fields = [field_name for field_value, field_name in required_fields if not field_value]
                    
                    if missing_fields:
                        st.error(f"❌ Please fill in the following required fields: {', '.join(missing_fields)}")
                        st.stop()
                    
                    if not agree_terms:
                        st.error("❌ Please agree to the terms and conditions.")
                        st.stop()
                    
                    # Show processing message
                    with st.spinner("Processing your patent application..."):
                        # File processing
                        doc_hash = ""
                        file_name = None
                        file_size = 0
                        
                        if uploaded_file is not None:
                            try:
                                file_bytes = uploaded_file.getvalue()
                                doc_hash = hash_file_bytes(file_bytes)
                                file_name = uploaded_file.name
                                file_size = getattr(uploaded_file, "size", len(file_bytes))
                                st.info(f"✅ File processed: {file_name} ({get_file_size_str(file_size)})")
                            except Exception as e:
                                st.error(f"❌ Error processing file: {str(e)}")
                                st.stop()
                        elif patent_description.strip():
                            doc_hash = hashlib.sha256(patent_description.encode()).hexdigest()

                        # Generate patent data
                        patent_id = generate_patent_id()
                        now_iso = datetime.datetime.now().isoformat()

                        patent_data = {
                            "patent_id": patent_id,
                            "title": patent_title,
                            "description": patent_description,
                            "inventor": inventor_name,
                            "patent_type": patent_type,
                            "priority": priority,
                            "doc_hash": doc_hash,
                            "estimated_value": estimated_value,
                            "keywords": keywords,
                            "related_patents": related_patents,
                            "collaboration": collaboration,
                            "funding_source": funding_source,
                            "is_on_blockchain": (store_option == "On Blockchain"),
                            "status": "Pending",
                            "verification_score": verify_patent_authenticity({
                                "title": patent_title,
                                "description": patent_description,
                                "doc_hash": doc_hash
                            }),
                            "created_by": st.session_state.current_user.username,
                            "file_name": file_name,
                            "file_size": file_size,
                            "timestamp": now_iso
                        }

                        # Store patent
                        if patent_data["is_on_blockchain"]:
                            try:
                                new_block = Block(
                                    index=len(st.session_state.toy_chain.chain),
                                    timestamp=now_iso,
                                    data=patent_data,
                                    previous_hash=""
                                )
                                
                                st.info("⛏️ Mining block on blockchain...")
                                time.sleep(0.5)  # Simulate mining time
                                st.session_state.toy_chain.add_block(new_block)

                                st.session_state.counts_on_chain[patent_type] += 1
                                add_notification(f"Patent {patent_id} successfully recorded on blockchain!", "success")
                                
                                st.success(f"🎉 Patent {patent_id} successfully recorded on the blockchain!")
                                st.info(f"🔗 Block #{new_block.index} created with hash: {new_block.hash[:16]}...")
                                
                            except Exception as e:
                                st.error(f"❌ Error adding to blockchain: {str(e)}")
                                st.error("Falling back to off-chain storage...")
                                # Fallback to off-chain
                                patent_data["is_on_blockchain"] = False
                                st.session_state.off_chain_list.append({
                                    "timestamp": now_iso,
                                    "data": patent_data
                                })
                                st.session_state.counts_off_chain[patent_type] += 1
                                
                        else:
                            try:
                                st.session_state.off_chain_list.append({
                                    "timestamp": now_iso,
                                    "data": patent_data
                                })
                                st.session_state.counts_off_chain[patent_type] += 1
                                add_notification(f"Patent {patent_id} stored off-chain", "info")
                                st.success(f"📄 Patent {patent_id} stored off-chain successfully!")
                                
                            except Exception as e:
                                st.error(f"❌ Error storing patent: {str(e)}")
                                st.stop()

                        # Update user stats
                        st.session_state.current_user.patents_submitted += 1

                        # Show verification score
                        score = patent_data["verification_score"]
                        if score >= 80:
                            st.success(f"🏆 High verification score: {score}/100")
                        elif score >= 60:
                            st.info(f"✅ Good verification score: {score}/100")
                        else:
                            st.warning(f"⚠️ Low verification score: {score}/100 - Consider adding more details")

                        # Show summary
                        with st.expander("📋 Submission Summary", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Patent ID:** {patent_id}")
                                st.write(f"**Title:** {patent_title}")
                                st.write(f"**Type:** {patent_type}")
                                st.write(f"**Priority:** {priority}")
                            with col2:
                                st.write(f"**Storage:** {'Blockchain' if patent_data['is_on_blockchain'] else 'Off-Chain'}")
                                st.write(f"**Status:** {patent_data['status']}")
                                st.write(f"**Verification Score:** {score}/100")
                                st.write(f"**Submitted:** {now_iso[:19]}")

                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Unexpected error during submission: {str(e)}")
                    st.error("Please try again or contact system administrator.")
                    # Optional: Show technical details for debugging
                    if st.checkbox("Show technical details"):
                        st.exception(e)

    with tab2:
        filters = render_advanced_search()

        # Собираем все патенты
        all_patents = []

        # Ончейн
        for block in st.session_state.toy_chain.chain[1:]:  # Skip genesis
            patent = dict(block.data or {})
            patent["source"] = "blockchain"
            patent["block_index"] = block.index
            patent["hash"] = block.hash
            # ВАЖНО: timestamp берём из блока, если в data нет
            patent["timestamp"] = patent.get("timestamp", block.timestamp)
            all_patents.append(patent)

        # Оффчейн
        for i, record in enumerate(st.session_state.off_chain_list):
            patent = dict(record["data"] or {})
            patent["source"] = "off-chain"
            patent["record_index"] = i
            patent["timestamp"] = record["timestamp"]
            all_patents.append(patent)

        # Фильтры
        filtered = all_patents

        if filters["search_term"]:
            q = filters["search_term"].lower()
            filtered = [
                p for p in filtered
                if q in p.get("title", "").lower()
                or q in p.get("description", "").lower()
                or q in p.get("inventor", "").lower()
                or q in p.get("patent_id", "").lower()
            ]

        if filters["filter_type"] != "All":
            filtered = [p for p in filtered if p.get("patent_type") == filters["filter_type"]]

        if filters["filter_status"] != "All":
            filtered = [p for p in filtered if p.get("status") == filters["filter_status"]]

        if filters["priority_filter"]:
            filtered = [p for p in filtered if p.get("priority") in filters["priority_filter"]]

        if filters["storage_filter"] == "On-Chain":
            filtered = [p for p in filtered if p.get("is_on_blockchain") is True]
        elif filters["storage_filter"] == "Off-Chain":
            filtered = [p for p in filtered if p.get("is_on_blockchain") is False]

        # Даты
        df_dates = []
        for p in filtered:
            try:
                dt = _parse_iso(p.get("timestamp", datetime.datetime.min.isoformat())).date()
            except Exception:
                dt = datetime.date.min
            df_dates.append((p, dt))
        filtered = [
            p for (p, dt) in df_dates
            if filters["date_from"] <= dt <= filters["date_to"]
        ]

        # Вывод
        st.subheader(f"📋 Patent Results ({len(filtered)} found)")

        if filtered:
            sort_by = st.selectbox("Sort by", ["Newest First", "Oldest First", "Title A-Z", "Verification Score"])
            if sort_by == "Newest First":
                filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            elif sort_by == "Oldest First":
                filtered.sort(key=lambda x: x.get("timestamp", ""))
            elif sort_by == "Title A-Z":
                filtered.sort(key=lambda x: x.get("title", ""))
            elif sort_by == "Verification Score":
                filtered.sort(key=lambda x: x.get("verification_score", 0), reverse=True)

            for patent in filtered:
                created = patent.get('timestamp', '')
                created_short = created.replace("T", " ")[:19] if created else "Unknown"
                st.markdown(f"""
                <div class="patent-card">
                    <div style="display:flex;justify-content:space-between;align-items:start;gap:16px;">
                        <div style="flex:1;">
                            <h4 style="margin:0;">{patent.get('title','Untitled')}</h4>
                            <p style="margin:4px 0 6px 0;"><strong>ID:</strong> {patent.get('patent_id','N/A')} &nbsp;|&nbsp;
                               <strong>Type:</strong> {patent.get('patent_type','Unknown')} &nbsp;|&nbsp;
                               <strong>Inventor:</strong> {patent.get('inventor','Unknown')}</p>
                            <p style="margin:4px 0 6px 0;"><strong>Description:</strong> {patent.get('description','No description')[:200]}{'...' if len(patent.get('description',''))>200 else ''}</p>
                            <p style="margin:4px 0 0 0;"><strong>Storage:</strong> {'🔗 Blockchain' if patent.get('is_on_blockchain') else '📁 Off-Chain'} &nbsp;|&nbsp;
                               <strong>Created:</strong> {created_short}</p>
                        </div>
                        <div style="text-align:right;min-width:120px;">
                            <span class="priority-{patent.get('priority','normal').lower()}">{patent.get('priority','Normal')}</span><br>
                            <span class="status-{patent.get('status','pending').lower()}">{patent.get('status','Pending')}</span><br>
                            <small>Score: {patent.get('verification_score',0)}/100</small>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No patents found matching your search criteria.")

    with tab3:
        render_blockchain_explorer()

    with tab4:
        render_analytics_dashboard()

    with tab5:
        export_data()

    with tab6:
        st.header("⚙️ System Information")

        # Презентабельные системные метрики
        stats = get_blockchain_stats()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Blocks", stats["total_blocks"])
        m2.metric("Chain Valid", "Yes" if stats["chain_valid"] else "No")
        m3.metric("Avg Block Time", f"{stats['average_block_time']:.2f}s")
        m4.metric("Hash Power (Σ nonce)", f"{stats['total_hash_power']}")

        # Табличка «как JSON, но красиво»
        table_data = [
            ("Blockchain Status", "Active"),
            ("Total Blocks", stats["total_blocks"]),
            ("Chain Validity", stats["chain_valid"]),
            ("Mining Difficulty", st.session_state.toy_chain.difficulty),
            ("Total Hash Power", stats["total_hash_power"]),
            ("Average Block Time", f"{stats['average_block_time']:.2f}s"),
            ("Total Users", len(st.session_state.users)),
            ("Current User", st.session_state.current_user.username),
            ("Total Notifications", len(st.session_state.notifications)),
        ]
        st.table(pd.DataFrame(table_data, columns=["Metric", "Value"]))

        st.subheader("🔧 System Tools")
        colA, colB, colC = st.columns(3)

        with colA:
            if st.button("🔄 Validate Blockchain"):
                with st.spinner("Validating blockchain integrity..."):
                    time.sleep(0.3)
                    is_valid = st.session_state.toy_chain.is_chain_valid()
                    if is_valid:
                        st.success("✅ Blockchain is valid!")
                    else:
                        st.error("❌ Blockchain validation failed!")

        with colB:
            if st.button("🧹 Clear Notifications"):
                st.session_state.notifications = []
                st.success("Notifications cleared!")

        with colC:
            if st.button("📊 Generate System Report"):
                report = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "system_stats": get_blockchain_stats(),
                    "user_count": len(st.session_state.users),
                    "patent_counts": {
                        "on_chain": sum(st.session_state.counts_on_chain.values()),
                        "off_chain": sum(st.session_state.counts_off_chain.values())
                    }
                }
                st.json(report)
                st.download_button(
                    "Download Report",
                    json.dumps(report, indent=2),
                    file_name=f"system_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

if __name__ == "__main__":
    main()

