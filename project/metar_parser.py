import re


def degrees_to_cardinal(degrees):
    directions = [
        'North', 'North-Northeast', 'Northeast', 'East-Northeast',
        'East', 'East-Southeast', 'Southeast', 'South-Southeast',
        'South', 'South-Southwest', 'Southwest', 'West-Southwest',
        'West', 'West-Northwest', 'Northwest', 'North-Northwest',
    ]
    idx = round(degrees / 22.5) % 16
    return directions[idx]


def celsius_to_fahrenheit(c):
    return round(c * 9 / 5 + 32)


def knots_to_mph(knots):
    return round(knots * 1.15078)


def parse_temp_str(s):
    if s.startswith('M'):
        return -int(s[1:])
    return int(s)


WEATHER_CODES = {
    'RA': 'rain',
    'SN': 'snow',
    'DZ': 'drizzle',
    'GR': 'hail',
    'GS': 'small hail',
    'SG': 'snow grains',
    'IC': 'ice crystals',
    'PL': 'ice pellets',
    'UP': 'unknown precipitation',
    'FG': 'fog',
    'BR': 'mist',
    'HZ': 'haze',
    'FU': 'smoke',
    'DU': 'dust',
    'SA': 'sand',
    'VA': 'volcanic ash',
    'SQ': 'squalls',
    'SS': 'sandstorm',
    'DS': 'dust storm',
    'FC': 'funnel cloud / tornado',
    'PO': 'dust/sand whirls',
    'TS': 'thunderstorm',
}

DESCRIPTOR_CODES = {
    'MI': 'shallow',
    'PR': 'partial',
    'BC': 'patches of',
    'DR': 'low drifting',
    'BL': 'blowing',
    'SH': 'showers',
    'FZ': 'freezing',
    'TS': 'thunderstorm with',
}

WEATHER_PATTERN = re.compile(
    r'^([-+]|VC)?(MI|PR|BC|DR|BL|SH|FZ|TS)?'
    r'(RA|SN|DZ|GR|GS|SG|IC|PL|UP|FG|BR|HZ|FU|DU|SA|VA|SQ|SS|DS|FC|PO|TS)+'
    r'(CB|TCU)?$'
)


def parse_weather_token(token):
    s = token
    parts = []

    if s.startswith('-'):
        parts.append('light')
        s = s[1:]
    elif s.startswith('+'):
        parts.append('heavy')
        s = s[1:]
    elif s.startswith('VC'):
        parts.append('in the vicinity:')
        s = s[2:]

    if len(s) >= 2 and s[:2] in DESCRIPTOR_CODES:
        parts.append(DESCRIPTOR_CODES[s[:2]])
        s = s[2:]

    while len(s) >= 2:
        code = s[:2]
        if code in WEATHER_CODES:
            parts.append(WEATHER_CODES[code])
        s = s[2:]

    return ' '.join(parts) if parts else token


def parse_sky_token(token):
    sky_map = {
        'SKC': 'Clear skies',
        'CLR': 'Clear skies',
        'CAVOK': 'Clear skies, visibility OK',
        'NSC': 'No significant clouds',
        'NCD': 'No clouds detected',
    }
    if token in sky_map:
        return sky_map[token]

    coverage_map = {
        'FEW': 'Few clouds',
        'SCT': 'Scattered clouds',
        'BKN': 'Broken cloud layer',
        'OVC': 'Overcast',
    }

    for cov, desc in coverage_map.items():
        if token.startswith(cov):
            rest = token[len(cov):]
            suffix = ''
            if rest.endswith('CB'):
                suffix = ' (cumulonimbus — potential thunderstorm)'
                rest = rest[:-2]
            elif rest.endswith('TCU'):
                suffix = ' (towering cumulus — potential storm)'
                rest = rest[:-3]
            try:
                height = int(rest) * 100
                return f"{desc} at {height:,} ft{suffix}"
            except ValueError:
                return f"{desc}{suffix}"

    vv_match = re.match(r'^VV(\d{3})$', token)
    if vv_match:
        height = int(vv_match.group(1)) * 100
        return f"Sky obscured, vertical visibility {height:,} ft"

    return None


def parse_metar(raw_text):
    # Take the first non-empty line
    raw = ''
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            raw = line
            break

    if not raw:
        return None

    tokens = raw.split()
    result = {
        'raw': raw,
        'station': None,
        'time_utc': None,
        'wind': None,
        'visibility': None,
        'weather': [],
        'sky': [],
        'temperature_c': None,
        'temperature_f': None,
        'dewpoint_c': None,
        'dewpoint_f': None,
        'altimeter': None,
        'remarks': None,
        'summary': None,
        'error': None,
    }

    i = 0

    # Optional report type
    if i < len(tokens) and tokens[i] in ('METAR', 'SPECI'):
        i += 1

    # Station ID
    if i < len(tokens):
        result['station'] = tokens[i]
        i += 1

    # Date/time: DDHHMMZ
    if i < len(tokens):
        m = re.match(r'^(\d{2})(\d{2})(\d{2})Z$', tokens[i])
        if m:
            day, hour, minute = m.groups()
            result['time_utc'] = f"Day {int(day)}, {hour}:{minute} UTC"
            i += 1

    # AUTO / COR flags
    if i < len(tokens) and tokens[i] in ('AUTO', 'COR', 'RTD'):
        i += 1

    # Wind: dddssKT or dddssGggKT or VRBssKT
    if i < len(tokens):
        m = re.match(r'^(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?(?:KT|MPS)$', tokens[i])
        if m:
            direction_raw, speed_raw, gust_raw = m.groups()
            speed = int(speed_raw)
            # Convert MPS to knots if needed
            if tokens[i].endswith('MPS'):
                speed = round(speed * 1.944)
                gust_raw = str(round(int(gust_raw) * 1.944)) if gust_raw else None

            speed_mph = knots_to_mph(speed)

            if speed == 0:
                wind_desc = "Calm winds"
            elif direction_raw == 'VRB':
                wind_desc = f"Variable wind at {speed} kt ({speed_mph} mph)"
            else:
                deg = int(direction_raw)
                cardinal = degrees_to_cardinal(deg)
                wind_desc = f"Wind from the {cardinal} ({deg}°) at {speed} kt ({speed_mph} mph)"

            if gust_raw:
                gust = int(gust_raw)
                gust_mph = knots_to_mph(gust)
                wind_desc += f", gusting to {gust} kt ({gust_mph} mph)"

            result['wind'] = wind_desc
            i += 1

        # Variable wind direction e.g. 160V220
        if i < len(tokens) and re.match(r'^\d{3}V\d{3}$', tokens[i]):
            i += 1  # skip, direction already described as variable above

    # Visibility
    if i < len(tokens):
        vis = tokens[i]
        if vis == 'CAVOK':
            result['visibility'] = "10+ miles (CAVOK — ceiling and visibility OK)"
            result['sky'].append('Clear skies, visibility OK')
            i += 1
        elif vis in ('M1/4SM', '0SM', 'M1/4'):
            result['visibility'] = "Less than 1/4 mile (near zero)"
            i += 1
        elif re.match(r'^(\d+)SM$', vis):
            n = int(re.match(r'^(\d+)SM$', vis).group(1))
            quality = 'excellent' if n >= 10 else ('good' if n >= 5 else ('moderate' if n >= 3 else 'poor'))
            result['visibility'] = f"{n} mile{'s' if n != 1 else ''} ({quality})"
            i += 1
        elif re.match(r'^(\d+)/(\d+)SM$', vis):
            result['visibility'] = f"{vis.replace('SM', ' mile')} (very poor)"
            i += 1
        elif re.match(r'^\d+$', vis) and i + 1 < len(tokens) and re.match(r'^\d+/\d+SM$', tokens[i + 1]):
            result['visibility'] = f"{vis} {tokens[i+1].replace('SM', ' miles')}"
            i += 2
        elif re.match(r'^\d{4}$', vis):
            m_val = int(vis)
            result['visibility'] = f"{m_val:,} meters"
            i += 1
        elif vis == '9999':
            result['visibility'] = "10+ km (excellent)"
            i += 1

    # Skip RVR (Runway Visual Range) tokens like R28L/2400FT
    while i < len(tokens) and re.match(r'^R\d+[LCR]?/', tokens[i]):
        i += 1

    # Present weather
    while i < len(tokens) and WEATHER_PATTERN.match(tokens[i]):
        result['weather'].append(parse_weather_token(tokens[i]))
        i += 1

    # Sky conditions
    while i < len(tokens):
        sky = parse_sky_token(tokens[i])
        if sky:
            result['sky'].append(sky)
            i += 1
        else:
            break

    # Temperature / Dewpoint: TT/TT with optional M prefix
    if i < len(tokens):
        m = re.match(r'^(M?\d+)/(M?\d*)$', tokens[i])
        if m:
            temp_c = parse_temp_str(m.group(1))
            result['temperature_c'] = temp_c
            result['temperature_f'] = celsius_to_fahrenheit(temp_c)
            if m.group(2):
                dew_c = parse_temp_str(m.group(2))
                result['dewpoint_c'] = dew_c
                result['dewpoint_f'] = celsius_to_fahrenheit(dew_c)
            i += 1

    # Altimeter: A2992 (inHg) or Q1013 (hPa)
    if i < len(tokens):
        m = re.match(r'^A(\d{4})$', tokens[i])
        if m:
            result['altimeter'] = f"{int(m.group(1)) / 100:.2f} inHg"
            i += 1
        else:
            m = re.match(r'^Q(\d{4})$', tokens[i])
            if m:
                result['altimeter'] = f"{m.group(1)} hPa"
                i += 1

    # Remarks
    if i < len(tokens) and tokens[i] == 'RMK':
        result['remarks'] = ' '.join(tokens[i + 1:])

    result['summary'] = build_summary(result)
    return result


def build_summary(r):
    parts = []

    # Overall sky condition
    sky_lower = [s.lower() for s in r['sky']]
    if any('overcast' in s for s in sky_lower):
        parts.append("Overcast skies")
    elif any('broken' in s for s in sky_lower):
        parts.append("Mostly cloudy")
    elif any('scattered' in s for s in sky_lower):
        parts.append("Partly cloudy")
    elif any('few clouds' in s for s in sky_lower):
        parts.append("Mostly clear with some clouds")
    elif r['sky']:
        parts.append("Clear skies")

    # Weather phenomena
    for w in r['weather']:
        parts.append(w.capitalize())

    # Temperature
    if r['temperature_f'] is not None:
        parts.append(f"{r['temperature_f']}°F ({r['temperature_c']}°C)")

    # Wind
    if r['wind']:
        w = r['wind']
        parts.append(w[0].lower() + w[1:] if w else w)

    # Visibility (only mention if not excellent)
    if r['visibility'] and 'excellent' not in r['visibility']:
        parts.append(f"visibility {r['visibility']}")

    if not parts:
        return "Weather data parsed — see details below."

    return ', '.join(parts) + '.'
