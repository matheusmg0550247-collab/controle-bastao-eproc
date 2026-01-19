import streamlit as st
from supabase import create_client, Client
import json
from datetime import datetime, timedelta, date, time as dt_time

from utils import CONSULTORES, get_brazil_time

# =====================================================
# MULTI-STATE SUPPORT
#
# One Supabase table (app_state), multiple rows.
# Set a different state_id for each Streamlit app/repository in secrets:
#
#   [app]
#   state_id = "1"   # Legados
#   state_id = "2"   # Eproc
#
# If [app].state_id is not provided, it defaults to 1.
# =====================================================


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


supabase: Client = init_connection()


def _get_state_id() -> int:
    sid = 1
    try:
        app_cfg = st.secrets["app"]
        if hasattr(app_cfg, "get"):
            sid = app_cfg.get("state_id", 1)
        else:
            sid = app_cfg["state_id"]
    except Exception:
        sid = 1

    try:
        return int(sid)
    except Exception:
        return 1


STATE_ID: int = _get_state_id()


def date_serializer(obj):
    """Serializer for JSON (datetime/timedelta are not JSON-serializable by default)."""
    if isinstance(obj, (datetime, date, dt_time)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()
    return str(obj)


def load_state_from_db():
    """Downloads the full state from Supabase for the configured STATE_ID."""
    try:
        response = supabase.table("app_state").select("data").eq("id", STATE_ID).execute()
        if response.data:
            data = response.data[0].get("data") or {}

            # Convert ISO strings back to datetime
            if isinstance(data, dict):
                if "current_status_starts" in data and isinstance(data["current_status_starts"], dict):
                    for k, v in list(data["current_status_starts"].items()):
                        if isinstance(v, str):
                            try:
                                data["current_status_starts"][k] = datetime.fromisoformat(v)
                            except Exception:
                                pass

                if data.get("bastao_start_time") and isinstance(data.get("bastao_start_time"), str):
                    try:
                        data["bastao_start_time"] = datetime.fromisoformat(data["bastao_start_time"])
                    except Exception:
                        pass

            return data
    except Exception as e:
        print(f"Erro ao carregar do DB: {e}")

    # Default/fallback state
    now_br = get_brazil_time()
    return {
        "status_texto": {nome: "Indisponível" for nome in CONSULTORES},
        "bastao_queue": [],
        "skip_flags": {},
        "current_status_starts": {nome: now_br for nome in CONSULTORES},
        "bastao_counts": {nome: 0 for nome in CONSULTORES},
        "priority_return_queue": [],
        "daily_logs": [],
    }


def save_state_to_db(state_dict):
    """Saves the current state to Supabase for the configured STATE_ID."""
    try:
        clean_data = json.loads(json.dumps(state_dict, default=date_serializer))
        supabase.table("app_state").update({"data": clean_data, "updated_at": "now()"}).eq("id", STATE_ID).execute()
    except Exception as e:
        print(f"Erro ao salvar no DB: {e}")
