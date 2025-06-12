# dashboard.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from PIL import Image
import io
import base64
from streamlit_autorefresh import st_autorefresh

# Configuración de página
st.set_page_config(
    page_title="🍓 Raspberry Pi Monitor",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL del API
API_URL = "https://backend-3q27.onrender.com"

# CSS personalizado
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .raspberry-card {
        border: 2px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
        background: #f8f9fa;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        color: #333333;
    }
    .image-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .detection-badge {
        background: #28a745;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
    .refresh-indicator {
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0,0,0,0.7);
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.title("🦟 Monitor de Aedes Aegypti 🦟")
st.markdown("---")

# Funciones para obtener datos
@st.cache_data(ttl=10)
def get_raspberry_locations():
    try:
        response = requests.get(f"{API_URL}/api/raspberry-locations", timeout=5)
        if response.status_code == 200:
            return response.json()["raspberry_locations"]
    except Exception as e:
        st.error(f"Error conectando con API: {e}")
    return []

@st.cache_data(ttl=5)
def get_raspberry_images(raspberry_id, limit=20):
    try:
        response = requests.get(f"{API_URL}/api/raspberry-images/{raspberry_id}?limit={limit}", timeout=5)
        if response.status_code == 200:
            return response.json()["images"]
    except Exception as e:
        st.error(f"Error obteniendo imágenes: {e}")
    return []

@st.cache_data(ttl=15)
def get_statistics():
    try:
        response = requests.get(f"{API_URL}/api/statistics", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {e}")
    return {}

# Sidebar para controles
st.sidebar.header("🎛️ Panel de Control")

# Control de auto-refresh
auto_refresh_enabled = st.sidebar.checkbox("🔄 Auto-refresh", value=True)
refresh_interval = st.sidebar.selectbox(
    "⏱️ Intervalo de actualización", 
    options=[5, 10, 15, 30, 60], 
    index=1,  # 10 segundos por defecto
    format_func=lambda x: f"{x} segundos"
)

show_images = st.sidebar.checkbox("🖼️ Mostrar imágenes", value=True)
map_style = st.sidebar.selectbox("🗺️ Estilo de mapa", ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"])

# Auto-refresh usando st_autorefresh
if auto_refresh_enabled:
    # Configurar auto-refresh
    count = st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")
    
    # Mostrar indicador de refresh
    st.sidebar.success(f"🔄 Actualización #{count}")
    st.sidebar.info(f"⏰ Cada {refresh_interval} segundos")
    
    # Limpiar cache periódicamente
    if count % 10 == 0 and count > 0:
        st.cache_data.clear()
        st.sidebar.info("🧹 Cache limpiado")
else:
    st.sidebar.info("🔄 Auto-refresh desactivado")

# Estado del session_state para manejar selección
if 'selected_raspberry' not in st.session_state:
    st.session_state.selected_raspberry = None

# Función principal del dashboard
def main_dashboard():
    # Obtener datos
    locations = get_raspberry_locations()
    stats = get_statistics()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🍓 Raspberry Pi Activos",
            len([r for r in locations if r['status'] == 'online']),
            delta=None
        )
    
    with col2:
        total_detections = stats.get('total_detections', 0)
        st.metric(
            "🎯 Total Detecciones",
            total_detections,
            delta=None
        )
    
    with col3:
        avg_temp = stats.get('avg_temperature', 0)
        st.metric(
            "🌡️ Temperatura Promedio",
            f"{avg_temp}°C",
            delta=None
        )
    
    with col4:
        avg_humidity = stats.get('avg_humidity', 0)
        st.metric(
            "💧 Humedad Promedio", 
            f"{avg_humidity}%",
            delta=None
        )
    
    st.markdown("---")
    
    # Crear mapa interactivo
    st.subheader("🗺️ Ubicaciones de Raspberry Pi")
    
    # Crear DataFrame para el mapa
    if locations:
        # Alertas de detección
        for r in locations:
            if r['total_detections'] & r['total_detections']> 0:
                st.error(f"ALERTA!! AEDES DETECTADO EN {r['location']}", icon="🚨")
                
        df_locations = pd.DataFrame(locations)
        
        # Centro del mapa (Huánuco)
        center_lat = df_locations['latitude'].mean()
        center_lon = df_locations['longitude'].mean()
        
        # Crear mapa con Folium
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles=map_style
        )
        
        # Agregar marcadores
        for _, row in df_locations.iterrows():
            # Color del marcador según estado
            if row['total_detections'] > 0:
                color = 'black' 
            elif row['status'] == 'online':
                color = 'green' 
            else:
                color = 'red' 
            
            # Información del popup
            popup_html = f"""
            <div style="width:200px">
                <h4>{row['name']}</h4>
                <p><strong>ID:</strong> {row['raspberry_id']}</p>
                <p><strong>Ubicación:</strong> {row['location']}</p>
                <p><strong>Detecciones:</strong> {row['total_detections']}</p>
                <p><strong>Última conexión:</strong> {row['last_seen'][:16] if row['last_seen'] else 'N/A'}</p>
                <p><strong>Estado:</strong> {"🟢 Activo" if row['status'] == 'online' else "🔴 Inactivo"}</p>
            </div>
            """
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"Click para ver {row['name']}",
                icon=folium.Icon(color=color, icon='camera')
            ).add_to(m)
        
        # Mostrar mapa y capturar clics
        map_data = st_folium(m, width=700, height=500, returned_objects=["last_object_clicked"])
        
        # Manejar selección del mapa
        if map_data['last_object_clicked']:
            clicked_lat = map_data['last_object_clicked']['lat']
            clicked_lng = map_data['last_object_clicked']['lng']
            
            # Encontrar el Raspberry Pi más cercano al clic
            for location in locations:
                if (abs(location['latitude'] - clicked_lat) < 0.001 and 
                    abs(location['longitude'] - clicked_lng) < 0.001):
                    st.session_state.selected_raspberry = location['raspberry_id']
                    break
    
    # Mostrar información del Raspberry Pi seleccionado
    if st.session_state.selected_raspberry:
        st.markdown("---")
        
        # Encontrar información del Raspberry Pi seleccionado
        selected_info = next((r for r in locations if r['raspberry_id'] == st.session_state.selected_raspberry), None)
        
        if selected_info:
            st.subheader(f"📱 {selected_info['name']}")
            
            # Información del dispositivo
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"""
                **ID:** {selected_info['raspberry_id']}  
                **Ubicación:** {selected_info['location']}  
                **Estado:** {"🟢 Activo" if selected_info['status'] == 'online' else "🔴 Inactivo"}
                """)
            
            with col2:
                st.info(f"""
                **Total Detecciones:** {selected_info['total_detections']}  
                **Última Conexión:** {selected_info['last_seen'][:16] if selected_info['last_seen'] else 'N/A'}  
                **Última Detección:** {selected_info['last_detection'][:16] if selected_info['last_detection'] else 'N/A'}
                """)
            
            # Mostrar imágenes si está habilitado
            if show_images:
                st.subheader("📸 Imágenes Recientes")
                
                images = get_raspberry_images(st.session_state.selected_raspberry, 3)
            
                if images:
                    # Crear grid de imágenes
                    cols = st.columns(3)
                    
                    for idx, img_data in enumerate(images):
                        col_idx = idx % 3
                        
                        with cols[col_idx]:
                            try:
                                # Mostrar imagen
                                image_url = f"{img_data['image_url']}"
                                
                                # Información de la imagen
                                st.markdown(f"""
                                <div class="raspberry-card">
                                    <h5>📅 {img_data['timestamp'][:16]}</h5>
                                    <span class="detection-badge">🎯 {img_data['detection_count']} detecciones</span>
                                    <p><strong>Confianza:</strong> {img_data['confidence']:.2f}</p>
                                    <p><strong>Temp:</strong> {img_data['temperature']:.1f}°C | <strong>Humedad:</strong> {img_data['humidity']:.1f}%</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Intentar cargar y mostrar la imagen
                                try:
                                    response = requests.get(image_url, timeout=5)
                                    if response.status_code == 200:
                                        image = Image.open(io.BytesIO(response.content))
                                        st.image(image, caption=f"Detección {img_data['timestamp'][:10]}", use_container_width=True)
                                    else:
                                        st.error(f"No se pudo cargar la imagen")
                                except Exception as e:
                                    st.warning(f"Imagen no disponible")
                                
                            except Exception as e:
                                st.error(f"Error mostrando imagen: {e}")
                else:
                    st.info("📷 No hay imágenes disponibles para este Raspberry Pi")
        
        # Botón para limpiar selección
        if st.button("🔄 Limpiar Selección"):
            st.session_state.selected_raspberry = None
            st.rerun()
    
    # Gráfico de actividad
    st.markdown("---")
    st.subheader("📊 Actividad por Dispositivo")
    
    if locations:
        # Crear gráfico de barras
        df_activity = pd.DataFrame(locations)
        fig = px.bar(
            df_activity, 
            x='name', 
            y='total_detections',
            color='status',
            title="Detecciones por Raspberry Pi",
            color_discrete_map={'online': '#28a745', 'offline': '#dc3545'}
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# Ejecutar dashboard principal
main_dashboard()

# Información adicional
st.sidebar.markdown("---")
st.sidebar.info("""
**ℹ️ Información:**
- Los datos se actualizan automáticamente
- Haz clic en los marcadores del mapa para ver detalles
- Las alertas aparecen cuando hay detecciones
""")

# Mostrar tiempo de última actualización
if auto_refresh_enabled:
    st.sidebar.caption(f"⏰ Última actualización: {datetime.now().strftime('%H:%M:%S')}")
