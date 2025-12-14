# ./ui/app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuración
ORCHESTRATOR_URL = "http://orchestrator:8000"

# Configuración de la página
st.set_page_config(
    page_title="Asistente Educativo Inteligente",
    page_icon="🎓",
    layout="wide"
)

# Inicializar estado de sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user" not in st.session_state:
    st.session_state.user = "estudiante"

# Función para obtener métricas
def get_system_metrics():
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        return None

# Función para enviar consulta
def send_query_to_orchestrator(query, username):
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/query",
            json={"query": query, "username": username},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

# Título principal
st.title("🎓 Asistente Educativo Inteligente")
st.markdown("Sistema de Asistentes Heterogéneos para Educación")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de usuario
    st.session_state.user = st.selectbox(
        "👤 Tu perfil:",
        ["estudiante", "profesor", "admin", "invitado"]
    )
    
    st.divider()
    
    # Estado del sistema
    st.header("📊 Estado")
    try:
        health_response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=3)
        if health_response.status_code == 200:
            health_data = health_response.json()
            status = health_data.get("status", "unknown")
            
            if status == "healthy":
                st.success("✅ Sistema operativo")
            elif status == "degraded":
                st.warning("⚠️ Sistema degradado")
            else:
                st.error("❌ Sistema no disponible")
        else:
            st.error("❌ No se pudo verificar")
    except:
        st.error("❌ Error de conexión")
    
    st.divider()
    
    # Métricas
    metrics = get_system_metrics()
    if metrics:
        st.header("📈 Métricas")
        st.metric("Consultas Totales", metrics.get("total_queries", 0))
        st.metric("Tasa de Éxito", f"{metrics.get('success_rate_percentage', 0):.1f}%")
        st.metric("Usuarios Activos", metrics.get("active_users_7d", 0))
    
    st.divider()
    
    if st.button("🗑️ Limpiar Chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.caption("Versión 1.0.0")

# Chat principal (SIN PESTAÑAS)
st.header(f"💬 Chat educativo como {st.session_state.user}")

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input de consulta (FUERA de contenedores especiales)
prompt = st.chat_input("Escribe tu pregunta educativa aquí...")

if prompt:
    # Agregar mensaje del usuario
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Obtener respuesta
    with st.chat_message("assistant"):
        with st.spinner("🔄 Procesando..."):
            response_data = send_query_to_orchestrator(prompt, st.session_state.user)
            
            if isinstance(response_data, dict) and "error" in response_data:
                response_text = f"**Error:** {response_data['error']}"
            elif isinstance(response_data, str):
                response_text = response_data
            elif isinstance(response_data, dict) and "response" in response_data:
                response_text = response_data["response"]
            else:
                response_text = str(response_data)
            
            st.markdown(response_text)
            
            # Guardar en historial
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text
            })

# Sección de análisis (debajo del chat)
st.divider()
st.header("📊 Análisis del Sistema")

if st.button("🔄 Actualizar Métricas"):
    st.rerun()

try:
    response = requests.get(f"{ORCHESTRATOR_URL}/metrics?days=7", timeout=10)
    if response.status_code == 200:
        data = response.json()
        
        if data.get("metrics"):
            df = pd.DataFrame(data["metrics"])
            
            # Mostrar resumen
            cols = st.columns(3)
            with cols[0]:
                total = sum(m.get("total_queries", 0) for m in data.get("metrics", []))
                st.metric("Consultas (7d)", total)
            with cols[1]:
                st.metric("Métricas", data.get("total_metrics", 0))
            with cols[2]:
                st.metric("Período", "7 días")
            
            # Gráfico
            if "assistant_type" in df.columns and "total_queries" in df.columns:
                st.subheader("Consultas por Asistente")
                chart_data = df.groupby("assistant_type")["total_queries"].sum()
                st.bar_chart(chart_data)
            
            # Tabla
            st.subheader("Detalles")
            st.dataframe(df)
    else:
        st.info("No hay métricas disponibles todavía")
except:
    st.info("Esperando datos del sistema...")

# Footer
st.divider()
st.caption("Sistema de Asistentes Educativos Heterogéneos • Versión 1.0.0")