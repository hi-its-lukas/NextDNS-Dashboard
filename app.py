import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import pytz

st.set_page_config(
    page_title="NextDNS Advanced Analytics",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

GAFAM_DOMAINS = {
    'google': ['google', 'googleapis', 'gstatic', 'youtube', 'googlevideo', 'ggpht', 'googleusercontent', 'gvt1', 'gvt2', 'doubleclick', 'googlesyndication', 'googleadservices'],
    'apple': ['apple', 'icloud', 'mzstatic', 'apple-cloudkit', 'cdn-apple'],
    'meta': ['facebook', 'fbcdn', 'instagram', 'whatsapp', 'fb', 'meta'],
    'amazon': ['amazon', 'amazonaws', 'cloudfront', 'alexa', 'prime'],
    'microsoft': ['microsoft', 'msn', 'bing', 'azure', 'office', 'live', 'outlook', 'skype', 'xbox', 'windows', 'msftconnecttest', 'msedge']
}

def classify_gafam(domain):
    if not domain:
        return 'Others'
    domain_lower = domain.lower()
    for company, patterns in GAFAM_DOMAINS.items():
        for pattern in patterns:
            if pattern in domain_lower:
                return company.capitalize()
    return 'Others'

def extract_root_domain(domain):
    if not domain:
        return ''
    parts = domain.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return domain

@st.cache_data(ttl=300)
def fetch_logs(api_key, profile_id, limit=1000):
    headers = {'X-Api-Key': api_key}
    base_url = f'https://api.nextdns.io/profiles/{profile_id}/logs'
    
    all_logs = []
    cursor = None
    fetched = 0
    
    while fetched < limit:
        batch_size = min(500, limit - fetched)
        params = {'limit': batch_size}
        if cursor:
            params['cursor'] = cursor
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            if response.status_code == 401:
                return None, "Invalid API Key"
            elif response.status_code == 404:
                return None, "Profile not found"
            elif response.status_code != 200:
                return None, f"API Error: {response.status_code}"
            
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/x-ndjson' in content_type or 'text/event-stream' in content_type:
                for line in response.text.strip().split('\n'):
                    if line.strip():
                        try:
                            log_entry = json.loads(line)
                            all_logs.append(log_entry)
                            fetched += 1
                            if fetched >= limit:
                                break
                        except json.JSONDecodeError:
                            continue
                break
            else:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return None, "Invalid response format from API"
                
                if isinstance(data, list):
                    all_logs.extend(data)
                    fetched += len(data)
                    break
                elif isinstance(data, dict):
                    logs = data.get('data', [])
                    if not logs:
                        break
                    
                    all_logs.extend(logs)
                    fetched += len(logs)
                    
                    meta = data.get('meta', {})
                    pagination = meta.get('pagination', {})
                    cursor = pagination.get('cursor')
                    
                    if not cursor:
                        break
                else:
                    return None, "Unexpected API response format"
                
        except requests.exceptions.Timeout:
            return None, "Request timeout"
        except requests.exceptions.RequestException as e:
            return None, f"Connection error: {str(e)}"
    
    return all_logs, None

@st.cache_data(ttl=300)
def fetch_analytics(api_key, profile_id, endpoint, params=None):
    headers = {'X-Api-Key': api_key}
    url = f'https://api.nextdns.io/profiles/{profile_id}/analytics/{endpoint}'
    
    try:
        response = requests.get(url, headers=headers, params=params or {}, timeout=30)
        if response.status_code == 200:
            return response.json().get('data', []), None
        return None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, str(e)

def process_logs(logs, timezone_str='Europe/Berlin'):
    if not logs:
        return pd.DataFrame()
    
    df = pd.DataFrame(logs)
    
    timestamp_col = None
    for col in ['timestamp', 'time', 'date', 'ts']:
        if col in df.columns:
            timestamp_col = col
            break
    
    if timestamp_col:
        df['timestamp'] = pd.to_datetime(df[timestamp_col], errors='coerce')
        try:
            tz = pytz.timezone(timezone_str)
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            df['timestamp'] = df['timestamp'].dt.tz_convert(tz)
        except Exception:
            pass
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['date'] = df['timestamp'].dt.date
    else:
        df['timestamp'] = pd.NaT
        df['hour'] = 0
        df['day_of_week'] = 'Unknown'
        df['date'] = None
    
    if 'status' in df.columns:
        df['is_blocked'] = df['status'].apply(lambda x: 'Blocked' if str(x).lower() == 'blocked' else 'Allowed')
    else:
        df['is_blocked'] = 'Allowed'
    
    domain_col = None
    for col in ['domain', 'name', 'query', 'qname']:
        if col in df.columns:
            domain_col = col
            break
    
    if domain_col:
        df['domain'] = df[domain_col].fillna('')
        df['root_domain'] = df['domain'].apply(extract_root_domain)
        df['gafam'] = df['domain'].apply(classify_gafam)
    else:
        df['domain'] = ''
        df['root_domain'] = ''
        df['gafam'] = 'Others'
    
    if 'device' in df.columns:
        df['device_name'] = df['device'].apply(
            lambda x: x.get('name', 'Unknown') if isinstance(x, dict) else (str(x) if x else 'Unknown')
        )
    elif 'deviceName' in df.columns:
        df['device_name'] = df['deviceName'].fillna('Unknown')
    elif 'client' in df.columns:
        df['device_name'] = df['client'].apply(
            lambda x: x.get('name', 'Unknown') if isinstance(x, dict) else (str(x) if x else 'Unknown')
        )
    else:
        df['device_name'] = 'Unknown'
    
    if 'protocol' in df.columns:
        df['is_encrypted'] = df['protocol'].isin(['DNS-over-HTTPS', 'DNS-over-TLS', 'DOH', 'DOT'])
    else:
        df['protocol'] = 'Unknown'
        df['is_encrypted'] = False
    
    return df

with st.sidebar:
    st.title("🔒 NextDNS Analytics")
    st.markdown("---")
    
    st.subheader("API Configuration")
    api_key = st.text_input("API Key", type="password", help="Find your API key at my.nextdns.io/account")
    profile_id = st.text_input("Profile ID", help="Your NextDNS profile ID (e.g., abc123)")
    
    st.markdown("---")
    
    st.subheader("Settings")
    log_limit = st.selectbox("Logs to fetch", [1000, 2000, 5000, 10000], index=0)
    timezone = st.selectbox("Timezone", ['Europe/Berlin', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'Asia/Tokyo', 'UTC'], index=0)
    
    st.markdown("---")
    
    fetch_button = st.button("📊 Fetch Data", type="primary", use_container_width=True)
    
    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared!")

if 'logs_data' not in st.session_state:
    st.session_state.logs_data = None
if 'error' not in st.session_state:
    st.session_state.error = None

if fetch_button:
    if not api_key or not profile_id:
        st.error("Please enter both API Key and Profile ID")
    else:
        with st.spinner("Fetching data from NextDNS..."):
            logs, error = fetch_logs(api_key, profile_id, log_limit)
            if error:
                st.session_state.error = error
                st.session_state.logs_data = None
            else:
                st.session_state.logs_data = logs
                st.session_state.error = None

if st.session_state.error:
    st.error(f"Error: {st.session_state.error}")
    st.info("Please check your API Key and Profile ID")
    st.stop()

if not st.session_state.logs_data:
    st.title("🔒 NextDNS Advanced Analytics Dashboard")
    st.markdown("""
    ### Welcome! 
    
    This dashboard provides advanced analytics for your NextDNS DNS queries, offering insights beyond the standard NextDNS interface.
    
    **Features:**
    - 📈 Interactive time-series analysis
    - 🔥 Activity heatmaps
    - 🔍 Device forensics
    - 🏢 GAFAM (Big Tech) tracking analysis
    - 📋 Full log explorer with search
    - 💾 CSV export
    
    **Get Started:**
    1. Enter your **API Key** (find it at [my.nextdns.io/account](https://my.nextdns.io/account))
    2. Enter your **Profile ID**
    3. Click **Fetch Data**
    """)
    st.stop()

df = process_logs(st.session_state.logs_data, timezone)

if df.empty:
    st.warning("No log data available")
    st.stop()

st.title("🔒 NextDNS Advanced Analytics")

col1, col2, col3, col4 = st.columns(4)

total_queries = len(df)
blocked_count = len(df[df['is_blocked'] == 'Blocked'])
block_rate = (blocked_count / total_queries * 100) if total_queries > 0 else 0

top_device = df['device_name'].value_counts().index[0] if len(df['device_name'].value_counts()) > 0 else 'N/A'
blocked_df = df[df['is_blocked'] == 'Blocked']
top_blocked = blocked_df['root_domain'].value_counts().index[0] if len(blocked_df) > 0 and len(blocked_df['root_domain'].value_counts()) > 0 else 'N/A'

with col1:
    st.metric("Total Queries", f"{total_queries:,}")
with col2:
    st.metric("Block Rate", f"{block_rate:.1f}%")
with col3:
    st.metric("Top Device", top_device)
with col4:
    st.metric("Top Blocked", top_blocked)

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Time Analysis", "🔥 Heatmap", "📱 Device Forensics", "🏢 GAFAM Analysis", "📋 Log Explorer"])

with tab1:
    st.subheader("Query Volume Over Time")
    
    if 'timestamp' in df.columns:
        df_time = df.copy()
        df_time['time_bucket'] = df_time['timestamp'].dt.floor('H')
        
        time_series = df_time.groupby(['time_bucket', 'is_blocked']).size().reset_index(name='count')
        
        fig = px.line(
            time_series,
            x='time_bucket',
            y='count',
            color='is_blocked',
            color_discrete_map={'Blocked': '#ef4444', 'Allowed': '#22c55e'},
            title='DNS Queries Over Time',
            labels={'time_bucket': 'Time', 'count': 'Number of Queries', 'is_blocked': 'Status'}
        )
        fig.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Allowed Domains")
            allowed_domains = df[df['is_blocked'] == 'Allowed']['root_domain'].value_counts().head(10)
            fig_allowed = px.bar(
                x=allowed_domains.values,
                y=allowed_domains.index,
                orientation='h',
                color_discrete_sequence=['#22c55e']
            )
            fig_allowed.update_layout(template='plotly_dark', yaxis={'categoryorder': 'total ascending'}, showlegend=False)
            fig_allowed.update_xaxes(title='Queries')
            fig_allowed.update_yaxes(title='')
            st.plotly_chart(fig_allowed, use_container_width=True)
        
        with col2:
            st.subheader("Top Blocked Domains")
            blocked_domains = df[df['is_blocked'] == 'Blocked']['root_domain'].value_counts().head(10)
            if len(blocked_domains) > 0:
                fig_blocked = px.bar(
                    x=blocked_domains.values,
                    y=blocked_domains.index,
                    orientation='h',
                    color_discrete_sequence=['#ef4444']
                )
                fig_blocked.update_layout(template='plotly_dark', yaxis={'categoryorder': 'total ascending'}, showlegend=False)
                fig_blocked.update_xaxes(title='Queries')
                fig_blocked.update_yaxes(title='')
                st.plotly_chart(fig_blocked, use_container_width=True)
            else:
                st.info("No blocked queries found")

with tab2:
    st.subheader("Activity Heatmap")
    st.markdown("Identify when your network is most active")
    
    if 'hour' in df.columns and 'day_of_week' in df.columns:
        heatmap_data = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
        
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)
        heatmap_pivot = heatmap_pivot.reindex(day_order)
        
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=[f'{h:02d}:00' for h in range(24)],
            y=heatmap_pivot.index,
            colorscale='RdYlGn_r',
            hoverongaps=False,
            hovertemplate='Day: %{y}<br>Hour: %{x}<br>Queries: %{z}<extra></extra>'
        ))
        
        fig_heatmap.update_layout(
            template='plotly_dark',
            title='Network Activity by Day and Hour',
            xaxis_title='Hour of Day',
            yaxis_title='Day of Week',
            height=400
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Busiest Hours")
            hourly_counts = df.groupby('hour').size().sort_values(ascending=False).head(5)
            for hour, count in hourly_counts.items():
                st.write(f"**{hour:02d}:00** - {count:,} queries")
        
        with col2:
            st.subheader("Busiest Days")
            daily_counts = df.groupby('day_of_week').size().reindex(day_order).dropna().sort_values(ascending=False).head(5)
            for day, count in daily_counts.items():
                st.write(f"**{day}** - {int(count):,} queries")

with tab3:
    st.subheader("Device Forensics")
    st.markdown("Analyze individual device behavior")
    
    devices = ['All Devices'] + sorted(df['device_name'].unique().tolist())
    selected_device = st.selectbox("Select Device", devices)
    
    if selected_device == 'All Devices':
        device_df = df
    else:
        device_df = df[df['device_name'] == selected_device]
    
    if len(device_df) > 0:
        col1, col2, col3 = st.columns(3)
        
        device_total = len(device_df)
        device_blocked = len(device_df[device_df['is_blocked'] == 'Blocked'])
        device_block_rate = (device_blocked / device_total * 100) if device_total > 0 else 0
        
        with col1:
            st.metric("Total Queries", f"{device_total:,}")
        with col2:
            st.metric("Blocked", f"{device_blocked:,}")
        with col3:
            st.metric("Block Rate", f"{device_block_rate:.1f}%")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Domains")
            top_domains = device_df['root_domain'].value_counts().head(10)
            fig_domains = px.pie(
                values=top_domains.values,
                names=top_domains.index,
                hole=0.4
            )
            fig_domains.update_layout(template='plotly_dark')
            st.plotly_chart(fig_domains, use_container_width=True)
        
        with col2:
            st.subheader("Blocked Domains")
            device_blocked_df = device_df[device_df['is_blocked'] == 'Blocked']
            if len(device_blocked_df) > 0:
                blocked_domains = device_blocked_df['root_domain'].value_counts().head(10)
                fig_blocked = px.bar(
                    x=blocked_domains.values,
                    y=blocked_domains.index,
                    orientation='h',
                    color_discrete_sequence=['#ef4444']
                )
                fig_blocked.update_layout(template='plotly_dark', yaxis={'categoryorder': 'total ascending'})
                fig_blocked.update_xaxes(title='Count')
                fig_blocked.update_yaxes(title='')
                st.plotly_chart(fig_blocked, use_container_width=True)
            else:
                st.info("No blocked queries for this device")
        
        if 'protocol' in device_df.columns:
            st.subheader("Protocol Distribution")
            protocol_counts = device_df['protocol'].value_counts()
            fig_protocol = px.pie(
                values=protocol_counts.values,
                names=protocol_counts.index,
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_protocol.update_layout(template='plotly_dark')
            st.plotly_chart(fig_protocol, use_container_width=True)
    else:
        st.info("No data for selected device")

with tab4:
    st.subheader("GAFAM & Big Tech Analysis")
    st.markdown("Breakdown of requests to major tech companies")
    
    gafam_counts = df['gafam'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_gafam_pie = px.pie(
            values=gafam_counts.values,
            names=gafam_counts.index,
            title='Request Distribution by Company',
            hole=0.4,
            color_discrete_map={
                'Google': '#4285F4',
                'Apple': '#A2AAAD',
                'Meta': '#0668E1',
                'Amazon': '#FF9900',
                'Microsoft': '#00A4EF',
                'Others': '#6B7280'
            }
        )
        fig_gafam_pie.update_layout(template='plotly_dark')
        st.plotly_chart(fig_gafam_pie, use_container_width=True)
    
    with col2:
        fig_gafam_bar = px.bar(
            x=gafam_counts.index,
            y=gafam_counts.values,
            title='Total Requests by Company',
            color=gafam_counts.index,
            color_discrete_map={
                'Google': '#4285F4',
                'Apple': '#A2AAAD',
                'Meta': '#0668E1',
                'Amazon': '#FF9900',
                'Microsoft': '#00A4EF',
                'Others': '#6B7280'
            }
        )
        fig_gafam_bar.update_layout(template='plotly_dark', showlegend=False)
        fig_gafam_bar.update_xaxes(title='Company')
        fig_gafam_bar.update_yaxes(title='Queries')
        st.plotly_chart(fig_gafam_bar, use_container_width=True)
    
    if 'timestamp' in df.columns:
        st.subheader("GAFAM Requests Over Time")
        df_gafam_time = df.copy()
        df_gafam_time['time_bucket'] = df_gafam_time['timestamp'].dt.floor('H')
        
        gafam_time_series = df_gafam_time.groupby(['time_bucket', 'gafam']).size().reset_index(name='count')
        
        fig_gafam_time = px.area(
            gafam_time_series,
            x='time_bucket',
            y='count',
            color='gafam',
            color_discrete_map={
                'Google': '#4285F4',
                'Apple': '#A2AAAD',
                'Meta': '#0668E1',
                'Amazon': '#FF9900',
                'Microsoft': '#00A4EF',
                'Others': '#6B7280'
            }
        )
        fig_gafam_time.update_layout(
            template='plotly_dark',
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig_gafam_time, use_container_width=True)
    
    st.subheader("Top Domains by Company")
    for company in ['Google', 'Apple', 'Meta', 'Amazon', 'Microsoft']:
        with st.expander(f"{company}"):
            company_domains = df[df['gafam'] == company]['root_domain'].value_counts().head(10)
            if len(company_domains) > 0:
                display_data = pd.DataFrame({
                    'Domain': company_domains.index,
                    'Queries': company_domains.values
                })
                st.dataframe(display_data, use_container_width=True)
            else:
                st.info(f"No {company} requests found")

with tab5:
    st.subheader("Interactive Log Explorer")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search domains", "")
    
    with col2:
        status_filter = st.selectbox("Status", ['All', 'Allowed', 'Blocked'])
    
    with col3:
        device_filter = st.selectbox("Device", ['All'] + sorted(df['device_name'].unique().tolist()), key='log_device')
    
    filtered_df = df.copy()
    
    if search_term and 'domain' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['domain'].astype(str).str.contains(search_term, case=False, na=False)]
    
    if status_filter != 'All':
        filtered_df = filtered_df[filtered_df['is_blocked'] == status_filter]
    
    if device_filter != 'All':
        filtered_df = filtered_df[filtered_df['device_name'] == device_filter]
    
    st.write(f"Showing {len(filtered_df):,} of {len(df):,} logs")
    
    display_cols = ['timestamp', 'domain', 'device_name', 'protocol', 'is_blocked']
    available_cols = [col for col in display_cols if col in filtered_df.columns]
    
    if available_cols:
        display_df = filtered_df[available_cols].copy()
        display_df.columns = ['Timestamp', 'Domain', 'Device', 'Protocol', 'Status'][:len(available_cols)]
        
        def highlight_status(row):
            if 'Status' in row.index:
                if row['Status'] == 'Blocked':
                    return ['background-color: rgba(239, 68, 68, 0.3)'] * len(row)
            if 'Protocol' in row.index:
                if row['Protocol'] in ['DNS-over-HTTPS', 'DNS-over-TLS', 'DOH', 'DOT']:
                    return ['background-color: rgba(34, 197, 94, 0.2)'] * len(row)
            return [''] * len(row)
        
        styled_df = display_df.head(500).style.apply(highlight_status, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=500)
        
        if len(filtered_df) > 500:
            st.info("Showing first 500 rows. Export to CSV for complete data.")
    
    st.markdown("---")
    
    st.subheader("💾 Export Data")
    
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"nextdns_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6B7280; font-size: 0.8em;'>"
    "NextDNS Advanced Analytics Dashboard | Data cached for 5 minutes"
    "</div>",
    unsafe_allow_html=True
)
