"""
Bot Mode Profiles.

Defines preset risk/aggression profiles that the user can switch between
instead of tweaking individual numeric parameters.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Each profile maps a human-friendly name to a full set of numeric trading parameters.
# slug is the stable identifier persisted in SystemSettings as `active_mode_profile`.
MODE_PROFILES: Dict[str, Dict[str, Any]] = {
    "conservative": {
        "slug": "conservative",
        "name": "Konservatif",
        "name_en": "Conservative",
        "tagline": "Modal aman — bot jarang trade, tunggu sinyal sangat kuat",
        "description": (
            "Bot hanya akan masuk pasar saat semua indikator setuju dengan keyakinan tinggi. "
            "Posisi kecil, leverage rendah, dan stop loss ketat. "
            "Cocok untuk pemula atau yang ingin tidur nyenyak."
        ),
        "icon": "Shield",
        "color": "emerald",
        "risk_level": 1,
        "params": {
            "consensus_threshold_strong": "0.80",
            "consensus_threshold_moderate": "0.60",
            "daily_loss_limit": "2.0",
            "max_drawdown_pct": "10.0",
            "weekly_loss_limit": "5.0",
            "max_leverage": "3",
            "max_position_size": "2.0",
            "max_total_exposure": "15.0",
            "consecutive_loss_limit": "3",
            "consecutive_loss_multiplier": "0.3",
            "correlation_guard_enabled": "true",
        },
    },
    "balanced": {
        "slug": "balanced",
        "name": "Seimbang",
        "name_en": "Balanced",
        "tagline": "Keseimbangan antara keamanan modal dan peluang profit",
        "description": (
            "Bot mencari peluang trade yang masuk akal — tidak terlalu hati-hati, tidak terlalu nekat. "
            "Cocok untuk trader yang ingin pertumbuhan modal stabil dengan risiko terkontrol. "
            "Profil paling populer."
        ),
        "icon": "Scale",
        "color": "blue",
        "risk_level": 2,
        "params": {
            "consensus_threshold_strong": "0.65",
            "consensus_threshold_moderate": "0.40",
            "daily_loss_limit": "4.0",
            "max_drawdown_pct": "15.0",
            "weekly_loss_limit": "8.0",
            "max_leverage": "5",
            "max_position_size": "5.0",
            "max_total_exposure": "30.0",
            "consecutive_loss_limit": "5",
            "consecutive_loss_multiplier": "0.5",
            "correlation_guard_enabled": "true",
        },
    },
    "aggressive": {
        "slug": "aggressive",
        "name": "Agresif",
        "name_en": "Aggressive",
        "tagline": "Sering trade — toleransi loss lebih tinggi demi peluang lebih banyak",
        "description": (
            "Bot aktif mencari setiap peluang. Posisi lebih besar, leverage lebih tinggi, "
            "dan threshold sinyal lebih rendah. Cocok untuk yang sudah berpengalaman dan "
            "siap menghadapi volatilitas harian yang lebih besar."
        ),
        "icon": "Zap",
        "color": "amber",
        "risk_level": 3,
        "params": {
            "consensus_threshold_strong": "0.50",
            "consensus_threshold_moderate": "0.25",
            "daily_loss_limit": "8.0",
            "max_drawdown_pct": "22.0",
            "weekly_loss_limit": "14.0",
            "max_leverage": "10",
            "max_position_size": "12.0",
            "max_total_exposure": "50.0",
            "consecutive_loss_limit": "6",
            "consecutive_loss_multiplier": "0.7",
            "correlation_guard_enabled": "false",
        },
    },
    "very_aggressive": {
        "slug": "very_aggressive",
        "name": "Sangat Agresif",
        "name_en": "Very Aggressive",
        "tagline": "Bot hampir selalu di pasar — high frequency, high leverage",
        "description": (
            "Bot bias kuat untuk eksekusi. Bahkan sinyal lemah cukup untuk membuka posisi. "
            "Loss harian besar masih ditoleransi. Hanya untuk trader yang paham risiko leverage "
            "dan siap dengan fluktuasi modal yang besar dalam satu hari."
        ),
        "icon": "Flame",
        "color": "orange",
        "risk_level": 4,
        "params": {
            "consensus_threshold_strong": "0.40",
            "consensus_threshold_moderate": "0.15",
            "daily_loss_limit": "12.0",
            "max_drawdown_pct": "30.0",
            "weekly_loss_limit": "20.0",
            "max_leverage": "15",
            "max_position_size": "20.0",
            "max_total_exposure": "80.0",
            "consecutive_loss_limit": "8",
            "consecutive_loss_multiplier": "0.8",
            "correlation_guard_enabled": "false",
        },
    },
    "yolo": {
        "slug": "yolo",
        "name": "YOLO",
        "name_en": "YOLO",
        "tagline": "⚠️ Maksimum risiko — akun bisa hancur dalam satu hari",
        "description": (
            "Mode ekstrem. Bot eksekusi pada sinyal paling lemah sekalipun, dengan leverage maksimal "
            "dan posisi sangat besar. Tidak ada safety net yang berarti. "
            "JANGAN gunakan dengan modal yang tidak siap Anda kehilangan."
        ),
        "icon": "Skull",
        "color": "red",
        "risk_level": 5,
        "params": {
            "consensus_threshold_strong": "0.30",
            "consensus_threshold_moderate": "0.10",
            "daily_loss_limit": "25.0",
            "max_drawdown_pct": "50.0",
            "weekly_loss_limit": "40.0",
            "max_leverage": "25",
            "max_position_size": "35.0",
            "max_total_exposure": "100.0",
            "consecutive_loss_limit": "12",
            "consecutive_loss_multiplier": "0.9",
            "correlation_guard_enabled": "false",
        },
    },
}


# Parameter friendly metadata used by the UI to render the explainer card on the AI Agents page.
PARAM_META: Dict[str, Dict[str, str]] = {
    "consensus_threshold_strong": {
        "label": "Threshold Sinyal Kuat",
        "explanation": "Seberapa yakin agent harus untuk eksekusi STRONG (LONG/SHORT besar). Skala 0-1. Semakin rendah, semakin sering bot trade.",
        "unit": "score",
    },
    "consensus_threshold_moderate": {
        "label": "Threshold Sinyal Moderat",
        "explanation": "Threshold minimum untuk eksekusi apa pun. Skala 0-1. Semakin rendah, semakin agresif (lebih banyak eksekusi).",
        "unit": "score",
    },
    "daily_loss_limit": {
        "label": "Batas Loss Harian",
        "explanation": "Persentase loss harian yang ditoleransi sebelum bot otomatis pause 24 jam.",
        "unit": "percent",
    },
    "max_drawdown_pct": {
        "label": "Batas Drawdown Maksimum",
        "explanation": "Persentase penurunan dari equity tertinggi sebelum bot emergency stop. Ini adalah safety paling penting.",
        "unit": "percent",
    },
    "weekly_loss_limit": {
        "label": "Batas Loss Mingguan",
        "explanation": "Akumulasi loss mingguan sebelum bot butuh review manual.",
        "unit": "percent",
    },
    "max_leverage": {
        "label": "Leverage Maksimum",
        "explanation": "Berapa kali lipat modal yang dipakai per trade. Lebih tinggi = profit/loss lebih besar.",
        "unit": "x",
    },
    "max_position_size": {
        "label": "Ukuran Posisi Maksimum",
        "explanation": "Persentase modal yang dialokasikan per trade.",
        "unit": "percent",
    },
    "max_total_exposure": {
        "label": "Total Exposure Maksimum",
        "explanation": "Total persentase modal yang boleh terbuka di semua posisi sekaligus.",
        "unit": "percent",
    },
    "consecutive_loss_limit": {
        "label": "Batas Loss Berturut-turut",
        "explanation": "Berapa kali loss berturut-turut sebelum ukuran posisi otomatis dikurangi.",
        "unit": "count",
    },
    "consecutive_loss_multiplier": {
        "label": "Pengurangan Ukuran Setelah Loss",
        "explanation": "Pengali ukuran posisi setelah loss beruntun. 0.5 = ukuran posisi dipotong setengah.",
        "unit": "multiplier",
    },
    "correlation_guard_enabled": {
        "label": "Proteksi Korelasi",
        "explanation": "Cegah bot membuka 2 posisi pada koin yang berkorelasi tinggi (misal BTC + ETH long bersamaan).",
        "unit": "toggle",
    },
}


DEFAULT_PROFILE_SLUG = "very_aggressive"


def get_profile(slug: str) -> Optional[Dict[str, Any]]:
    return MODE_PROFILES.get(slug)


def list_profiles() -> List[Dict[str, Any]]:
    """Returns all profiles sorted by risk_level ascending, with param_details for the UI."""
    profiles = list(MODE_PROFILES.values())
    profiles.sort(key=lambda p: p["risk_level"])
    enriched = []
    for p in profiles:
        enriched.append({
            **p,
            "param_details": _build_param_details(p["params"]),
        })
    return enriched


def get_active_profile(db: Session) -> Dict[str, Any]:
    """Returns the active profile with its slug, name, and param details for UI."""
    slug = SystemSettings.get_value(db, "active_mode_profile", DEFAULT_PROFILE_SLUG)
    profile = MODE_PROFILES.get(slug) or MODE_PROFILES[DEFAULT_PROFILE_SLUG]
    return {
        **profile,
        "param_details": _build_param_details(profile["params"]),
    }


def apply_profile(db: Session, slug: str) -> Dict[str, Any]:
    """Applies the named profile by writing every parameter to SystemSettings.
    Raises ValueError if slug is unknown."""
    profile = MODE_PROFILES.get(slug)
    if not profile:
        raise ValueError(f"Unknown mode profile: {slug}")

    # Persist every numeric parameter
    for key, value in profile["params"].items():
        SystemSettings.set_value(db, key, str(value))

    # Persist the active profile slug itself
    SystemSettings.set_value(db, "active_mode_profile", slug)

    logger.info("mode_profile_applied", slug=slug, name=profile["name"])
    return {
        **profile,
        "param_details": _build_param_details(profile["params"]),
    }


def _build_param_details(params: Dict[str, str]) -> List[Dict[str, Any]]:
    """Combine params + PARAM_META into UI-ready list."""
    out = []
    for key, raw_value in params.items():
        meta = PARAM_META.get(key, {})
        out.append({
            "key": key,
            "value": raw_value,
            "label": meta.get("label", key),
            "explanation": meta.get("explanation", ""),
            "unit": meta.get("unit", ""),
        })
    return out
