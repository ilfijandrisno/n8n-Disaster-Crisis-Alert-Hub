# n8n Code node (Python) — BMKG Quake Alert (polished + time-window dedup, safe quotes)

import math, re
from datetime import datetime, timezone

# -------- helpers --------
def to_float(x):
    if x is None:
        return None
    s = str(x).replace(",", ".")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else None

def fmt_num(x, digits=1, fallback="-"):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return fallback

def mag_bucket(m):
    if m is None:
        return "⚪", "Unknown"
    m = float(m)
    if m >= 6.0:  return "🔴", "Strong"
    if m >= 5.0:  return "🟠", "Moderate"
    if m >= 3.5:  return "🟡", "Light"
    return "🟢", "Minor"

def parse_lat_lon_from_lb(g):
    lat = lon = None
    L = g.get("Lintang")
    B = g.get("Bujur")
    if L:
        v = to_float(L)
        hemi = str(L).strip().split()[-1].upper() if isinstance(L, str) else ""
        lat = -abs(v) if hemi in ("LS", "S") else abs(v)
    if B:
        v = to_float(B)
        hemi = str(B).strip().split()[-1].upper() if isinstance(B, str) else ""
        lon = -abs(v) if hemi in ("BB", "W") else abs(v)   # BB=West(-), BT/E=East(+)
    return lat, lon

def parse_lat_lon(g):
    lat, lon = parse_lat_lon_from_lb(g)
    c = g.get("Coordinates")
    if (lat is None or lon is None) and isinstance(c, str) and "," in c:
        a, b = [to_float(p) for p in c.split(",")[:2]]
        if a is not None and b is not None:
            if abs(a) <= 90 and abs(b) <= 180:
                lat = lat if lat is not None else a
                lon = lon if lon is not None else b
            else:
                lon = lon if lon is not None else a
                lat = lat if lat is not None else b
    return lat, lon

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    from math import radians, sin, cos, asin, sqrt
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

def parse_event_dt(g):
    # 1) ISO 'DateTime'
    if g.get("DateTime"):
        try:
            dt = datetime.fromisoformat(str(g["DateTime"]))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    # 2) 'Tanggal' + 'Jam' (WIB/WITA/WIT)
    tanggal = (g.get("Tanggal") or "").strip()
    jam_raw = (g.get("Jam") or "").strip()
    if not tanggal or not jam_raw:
        return None
    tz = 7
    up = jam_raw.upper()
    if "WITA" in up: tz = 8
    if "WIT" in up and "WITA" not in up: tz = 9
    jam_clean = up.replace("WIB","").replace("WITA","").replace("WIT","").strip()
    bulan_map = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04","MEI":"05","MAY":"05","JUN":"06",
        "JUL":"07","AGU":"08","AGS":"08","AGUSTUS":"08","AUG":"08","SEP":"09",
        "OKT":"10","OCT":"10","NOV":"11","DES":"12","DEC":"12"
    }
    try:
        parts = tanggal.replace(",", "").split()
        if len(parts) >= 3:
            d = int(parts[0]); m = bulan_map.get(parts[1].upper()[:3], parts[1]); y = parts[2]
            iso = f"{y}-{m}-{d:02d}T{jam_clean}+{int(tz):02d}:00"
            return datetime.fromisoformat(iso).astimezone(timezone.utc)
    except Exception:
        return None
    return None

# -------- main --------
inp = _input.item.json
g = (inp.get("Infogempa", {}).get("gempa") or inp.get("gempa") or inp)

home_lat = float(inp.get("HOME_LAT"))
home_lon = float(inp.get("HOME_LON"))
max_dist = float(inp.get("MAX_DISTANCE_KM"))
min_mag  = float(inp.get("MIN_MAGNITUDE") or 0)
max_age  = float(inp.get("MAX_EVENT_AGE_MINUTES") or 6)  # minutes

evt_dt = parse_event_dt(g)

lat, lon = parse_lat_lon(g)
mag = to_float(g.get("Magnitude") or g.get("magnitude") or 0)
kedalaman = g.get("Kedalaman") or "-"
tanggal = g.get("Tanggal") or ""
jam = g.get("Jam") or ""
wilayah = g.get("Wilayah") or "-"
potensi = g.get("Potensi") or ""
dirasakan = g.get("Dirasakan") or ""

distance_km = None
if all(v is not None for v in (home_lat, home_lon, lat, lon)):
    distance_km = haversine_km(home_lat, home_lon, lat, lon)

event_id = g.get("Shakemap") or g.get("DateTime") or f"{tanggal} {jam} {g.get('Coordinates','')}".strip()
shakemap_url = f"https://data.bmkg.go.id/DataMKG/TEWS/{g['Shakemap']}" if g.get("Shakemap") else None

# filters
within = True if distance_km is None else (distance_km <= max_dist)
age_ok = True
age_min = None
if evt_dt is not None:
    age_min = (datetime.now(timezone.utc) - evt_dt).total_seconds() / 60.0
    age_ok = (age_min >= 0) and (age_min <= max_age)

pass_filters = (mag or 0) >= min_mag and within and age_ok

# -------- message (HTML) --------
emoji, label = mag_bucket(mag)
maps_url = f"https://www.google.com/maps?q={lat},{lon}" if (lat is not None and lon is not None) else None
mag_str = fmt_num(mag, 1)
dist_str = f"{fmt_num(distance_km,1)} km" if distance_km is not None else "-"

lines = []
lines.append(f'<b>⚠️ GEMPA BMKG {emoji} {label}</b>')
lines.append(f'<b>Magnitudo</b> <code>{mag_str}</code> • <b>Kedalaman</b> <code>{kedalaman}</code>')
lines.append(f'<b>Lokasi</b> {wilayah}')
if maps_url:
    lines.append(f'<b>Koordinat</b> <code>{fmt_num(lat,2)},{fmt_num(lon,2)}</code> - <a href="{maps_url}">Lihat peta</a>')
if distance_km is not None:
    lines.append(f'<b>Jarak ke rumah</b> <code>{dist_str}</code>')
lines.append(f'<b>Waktu</b> {tanggal} {jam}')
if potensi:
    lines.append(f'<b>Potensi</b> {potensi}')
if dirasakan:
    lines.append(f'<b>Dirasakan</b> {dirasakan}')
if shakemap_url:
    lines.append(f'<a href="{shakemap_url}">Shakemap</a>')
lines.append('<i>Auto-alert via n8n</i>')

out = {
    "pass": bool(pass_filters),
    "text": "\n".join(lines),
    "shakemapUrl": shakemap_url,
    "eventId": event_id,
    "mag": mag,
    "distanceKm": round(distance_km, 1) if distance_km is not None else None,
    "lat": lat, "lon": lon,
    "eventAgeMinutes": round(age_min, 2) if age_min is not None else None
}
return [{ "json": out }]
