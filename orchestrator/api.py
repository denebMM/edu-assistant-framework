# orchestrator/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
from main import orchestrate 
from db_utils import get_db_connection
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Edu Assistant Orchestrator",
    description="Orquestador para asistentes educativos heterogéneos",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    username: str = "anonymous"

@app.get("/")
async def root():
    return {
        "message": "Orchestrator funcionando!",
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Procesar consulta",
            "GET /health": "Estado del sistema",
            "GET /metrics": "Obtener métricas",
            "GET /stats": "Estadísticas generales"
        }
    }

@app.get("/health")
async def health_check():
    """Health check simple pero funcional"""
    try:
        # Verificar servicios básicos
        services_status = {}
        
        # Verificar rule_based
        try:
            rule_response = requests.get("http://rule_based:5001/", timeout=2)
            services_status["rule_based"] = "healthy" if rule_response.status_code == 200 else "unhealthy"
        except:
            services_status["rule_based"] = "unreachable"
        
        # Verificar deeppavlov
        try:
            dp_response = requests.get("http://deeppavlov_nlu:5002/", timeout=2)
            services_status["deeppavlov"] = "healthy" if dp_response.status_code == 200 else "unhealthy"
        except:
            services_status["deeppavlov"] = "unreachable"
        
        # Verificar ollama
        try:
            ollama_response = requests.get("http://ollama:11434/api/tags", timeout=2)
            services_status["ollama"] = "healthy" if ollama_response.status_code == 200 else "unhealthy"
        except:
            services_status["ollama"] = "unreachable"
        
        # Verificar base de datos
        try:
            conn = get_db_connection()
            conn.close()
            db_status = "healthy"
        except:
            db_status = "unhealthy"
        
        # Determinar estado general
        all_healthy = all("healthy" in status for status in services_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": services_status,
            "database": db_status
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
}
@app.post("/query")
async def process_query(request: QueryRequest):
    """Endpoint principal para procesar consultas"""
    try:
        logger.info(f"📥 Consulta de '{request.username}': {request.query}")
        result = orchestrate(request.query, request.username)
        return result
    except Exception as e:
        logger.error(f"❌ Error en endpoint /query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics(days: int = 7):
    """Obtener métricas detalladas"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                assistant_type,
                COUNT(*) as total_queries,
                AVG(latency) as avg_latency,
                AVG(error_rate) as avg_error_rate,
                COUNT(CASE WHEN error_rate > 0 THEN 1 END) as failed_queries,
                COUNT(DISTINCT user_id) as unique_users,
                DATE(timestamp) as date
            FROM metrics
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY assistant_type, DATE(timestamp)
            ORDER BY date DESC, assistant_type
        """, (days,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir a diccionarios
        metrics = []
        for row in rows:
            metrics.append({
                "assistant_type": row[0],
                "total_queries": row[1],
                "avg_latency_ms": float(row[2]) if row[2] else 0,
                "avg_error_rate": float(row[3]) if row[3] else 0,
                "failed_queries": row[4],
                "unique_users": row[5],
                "date": str(row[6]) if row[6] else None
            })
        
        return {
            "period_days": days,
            "total_metrics": len(metrics),
            "metrics": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Obtener estadísticas generales"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Total de consultas
        cur.execute("SELECT COUNT(*) as total FROM metrics")
        total_result = cur.fetchone()
        total = total_result[0] if total_result else 0
        
        # Distribución por asistente (protegido contra división por cero)
        cur.execute("""
            SELECT 
                assistant_type,
                COUNT(*) as count,
                CASE 
                    WHEN (SELECT COUNT(*) FROM metrics) = 0 THEN 0
                    ELSE ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM metrics), 0), 2)
                END as percentage
            FROM metrics
            GROUP BY assistant_type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()
        by_assistant = [
            {"assistant": row[0], "count": row[1], "percentage": float(row[2]) if row[2] else 0}
            for row in rows
        ]
        
        # Latencia promedio
        cur.execute("SELECT AVG(latency) as avg_latency FROM metrics")
        avg_result = cur.fetchone()
        avg_latency = float(avg_result[0]) if avg_result and avg_result[0] else 0
        
        # Usuarios activos
        cur.execute("""
            SELECT COUNT(DISTINCT user_id) as active_users 
            FROM metrics 
            WHERE timestamp >= NOW() - INTERVAL '7 days'
        """)
        active_result = cur.fetchone()
        active_users = active_result[0] if active_result else 0
        
        # Tasa de éxito (protegido contra división por cero)
        cur.execute("""
            SELECT 
                CASE 
                    WHEN COUNT(*) = 0 THEN 0 
                    ELSE COUNT(CASE WHEN error_rate = 0 THEN 1 END) * 100.0 / COUNT(*) 
                END as success_rate
            FROM metrics
        """)
        success_result = cur.fetchone()
        success_rate = float(success_result[0]) if success_result and success_result[0] else 0
        
        cur.close()
        conn.close()
        
        return {
            "total_queries": total,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate_percentage": round(success_rate, 2),
            "active_users_7d": active_users,
            "distribution_by_assistant": by_assistant
        }
        
    except Exception as e:
        logger.error(f"Error en /stats: {e}")
        return {
            "total_queries": 0,
            "avg_latency_ms": 0,
            "success_rate_percentage": 0,
            "active_users_7d": 0,
            "distribution_by_assistant": [],
            "error": str(e)
        }