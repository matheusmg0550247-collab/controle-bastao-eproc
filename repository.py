import streamlit as st
from supabase import create_client, Client
import json
from datetime import datetime, timedelta, date, time as dt_time
from utils import CONSULTORES, get_brazil_time

# Conexão Única com Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase: Client = init_connection()

# Serializador para datas (JSON não suporta datetime nativo)
def date_serializer(obj):
    if isinstance(obj, (datetime, date, dt_time)): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    return str(obj)

def load_state_from_db():
    """Baixa o estado completo do Supabase"""
    try:
        response = supabase.table("app_state").select("data").eq("id", 1).execute()
        if response.data:
            data = response.data[0]['data']
            # Reconverte strings ISO para datetime
            if 'current_status_starts' in data:
                for k, v in data['current_status_starts'].items():
                    if isinstance(v, str): data['current_status_starts'][k] = datetime.fromisoformat(v)
            if 'bastao_start_time' in data and data['bastao_start_time']:
                data['bastao_start_time'] = datetime.fromisoformat(data['bastao_start_time'])
            return data
    except Exception as e:
        print(f"Erro ao carregar do DB: {e}")
    
    # Retorna estado padrão se falhar ou estiver vazio
    now_br = get_brazil_time()
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'current_status_starts': {nome: now_br for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'daily_logs': []
    }

def save_state_to_db(state_dict):
    """Salva o estado atual no Supabase"""
    try:
        # Prepara o JSON serializável
        clean_data = json.loads(json.dumps(state_dict, default=date_serializer))
        supabase.table("app_state").update({"data": clean_data, "updated_at": "now()"}).eq("id", 1).execute()
    except Exception as e:
        print(f"Erro ao salvar no DB: {e}")
