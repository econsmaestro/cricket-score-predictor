"""
Latitude / longitude for major cricket venues worldwide.
Used by the weather scraper to fetch Open-Meteo data.

Coordinates are city-centre or stadium-precise where known.
"""

VENUE_COORDS: dict[str, tuple[float, float]] = {
    # ── India ──────────────────────────────────────────────────────────────
    "Wankhede Stadium, Mumbai":                  (18.9388, 72.8258),
    "Eden Gardens, Kolkata":                     (22.5645, 88.3433),
    "M Chinnaswamy Stadium, Bengaluru":          (12.9789, 77.5998),
    "Arun Jaitley Stadium, Delhi":               (28.6364, 77.2243),
    "MA Chidambaram Stadium, Chennai":           (13.0629, 80.2791),
    "Rajiv Gandhi International Stadium, Hyderabad": (17.4040, 78.5437),
    "Sawai Mansingh Stadium, Jaipur":            (26.8943, 75.8038),
    "Punjab Cricket Association IS Bindra Stadium, Mohali": (30.6991, 76.7155),
    "Narendra Modi Stadium, Ahmedabad":          (23.0902, 72.5950),
    "Dr DY Patil Sports Academy, Mumbai":        (19.0637, 72.9998),
    "Brabourne Stadium, Mumbai":                 (18.9364, 72.8263),
    "JSCA International Stadium Complex, Ranchi":(23.3434, 85.3348),
    "Greenfield International Stadium, Thiruvananthapuram": (8.5241, 76.9366),
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": (32.2196, 76.3234),
    "Vidarbha Cricket Association Stadium, Nagpur": (21.1069, 79.0615),
    "Holkar Cricket Stadium, Indore":            (22.7196, 75.8577),
    "BRSABV Ekana Cricket Stadium, Lucknow":     (26.8467, 80.9462),
    "Barabati Stadium, Cuttack":                 (20.4781, 85.8830),
    "Saurashtra Cricket Association Stadium, Rajkot": (22.2948, 70.7827),
    "ACA-VDCA Cricket Stadium, Visakhapatnam":   (17.8124, 83.2308),
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow": (26.8467, 80.9462),
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam": (17.8124, 83.2308),
    "Subrata Roy Sahara Stadium, Pune":          (18.5204, 73.8567),
    "Maharashtra Cricket Association Stadium, Pune": (18.5679, 73.9143),

    # ── Australia ──────────────────────────────────────────────────────────
    "Melbourne Cricket Ground, Melbourne":       (-37.8200, 144.9834),
    "Sydney Cricket Ground, Sydney":             (-33.8914, 151.2249),
    "Adelaide Oval, Adelaide":                   (-34.9158, 138.5962),
    "WACA Ground, Perth":                        (-31.9609, 115.8858),
    "Optus Stadium, Perth":                      (-31.9514, 115.8871),
    "The Gabba, Brisbane":                       (-27.4858, 153.0381),
    "Bellerive Oval, Hobart":                    (-42.8794, 147.3295),
    "Manuka Oval, Canberra":                     (-35.3200, 149.1280),
    "Cazalys Stadium, Cairns":                   (-16.9186, 145.7781),
    "Darwin Cricket Ground, Darwin":             (-12.4634, 130.8456),

    # ── England ────────────────────────────────────────────────────────────
    "Lord's Cricket Ground, London":             (51.5297, -0.1727),
    "The Oval, London":                          (51.4833, -0.1147),
    "Edgbaston, Birmingham":                     (52.4557, -1.9025),
    "Headingley, Leeds":                         (53.8183, -1.5774),
    "Old Trafford, Manchester":                  (53.4567, -2.2878),
    "Trent Bridge, Nottingham":                  (52.9363, -1.1327),
    "Rose Bowl, Southampton":                    (50.9245, -1.3224),
    "County Ground, Bristol":                    (51.4520, -2.5970),
    "Sophia Gardens, Cardiff":                   (51.4882, -3.1878),
    "Chester-le-Street, Durham":                 (54.8585, -1.5739),
    "Riverside Ground, Chester-le-Street":       (54.8585, -1.5739),
    "Kia Oval, London":                          (51.4833, -0.1147),
    "Emirates Old Trafford, Manchester":         (53.4567, -2.2878),

    # ── South Africa ───────────────────────────────────────────────────────
    "Newlands Cricket Ground, Cape Town":        (-33.9258, 18.4167),
    "Wanderers Stadium, Johannesburg":           (-26.1474, 28.0568),
    "SuperSport Park, Centurion":                (-25.7643, 28.1543),
    "St George's Park, Port Elizabeth":          (-33.9636, 25.6122),
    "Kingsmead, Durban":                         (-29.8555, 31.0237),
    "Buffalo Park, East London":                 (-32.9829, 27.9007),
    "Diamond Oval, Kimberley":                   (-28.7282, 24.7499),
    "Boland Park, Paarl":                        (-33.7233, 18.9575),

    # ── West Indies ────────────────────────────────────────────────────────
    "Kensington Oval, Bridgetown, Barbados":     (13.0833, -59.6167),
    "Sabina Park, Kingston, Jamaica":            (17.9994, -76.7918),
    "Queen's Park Oval, Port of Spain, Trinidad":(10.6524, -61.5148),
    "Sir Vivian Richards Stadium, Antigua":      (17.1274, -61.8456),
    "National Stadium, Providence, Guyana":      (6.8326, -58.1090),
    "Daren Sammy National Cricket Stadium, St Lucia": (14.0723, -60.9570),
    "Warner Park, Basseterre, St Kitts":         (17.3011, -62.7297),
    "Central Broward Regional Park, Florida":    (26.1420, -80.2456),
    "Brian Lara Cricket Academy, Trinidad":      (10.6524, -61.5148),
    "Arnos Vale Ground, St Vincent":             (13.1579, -61.2248),

    # ── New Zealand ────────────────────────────────────────────────────────
    "Eden Park, Auckland":                       (-36.8756, 174.7454),
    "Basin Reserve, Wellington":                 (-41.3078, 174.7778),
    "Hagley Oval, Christchurch":                 (-43.5320, 172.6147),
    "Seddon Park, Hamilton":                     (-37.7873, 175.2793),
    "Bay Oval, Tauranga":                        (-37.6847, 176.1653),
    "University Oval, Dunedin":                  (-45.8670, 170.5004),
    "Saxton Oval, Nelson":                       (-41.2650, 173.2764),
    "McLean Park, Napier":                       (-39.4814, 176.9199),

    # ── Pakistan ───────────────────────────────────────────────────────────
    "Gaddafi Stadium, Lahore":                   (31.5204, 74.3587),
    "National Stadium, Karachi":                 (24.8929, 67.0595),
    "Rawalpindi Cricket Stadium, Rawalpindi":    (33.5651, 73.0169),
    "Multan Cricket Stadium, Multan":            (30.1575, 71.5249),
    "Iqbal Stadium, Faisalabad":                 (31.4168, 73.0798),
    "Arbab Niaz Stadium, Peshawar":              (34.0095, 71.5805),

    # ── Sri Lanka ──────────────────────────────────────────────────────────
    "R Premadasa Stadium, Colombo":              (6.9219, 79.8601),
    "Sinhalese Sports Club Ground, Colombo":     (6.9022, 79.8590),
    "Pallekele International Cricket Stadium":   (7.3540, 80.6350),
    "Galle International Stadium, Galle":        (6.0328, 80.2170),
    "Mahinda Rajapaksa International Cricket Stadium, Hambantota": (6.1246, 81.1185),

    # ── Bangladesh ─────────────────────────────────────────────────────────
    "Shere Bangla National Stadium, Dhaka":      (23.7808, 90.3536),
    "Zahur Ahmed Chowdhury Stadium, Chittagong": (22.3397, 91.8225),
    "Sylhet International Cricket Stadium, Sylhet": (24.8949, 91.8687),

    # ── UAE / Asia ─────────────────────────────────────────────────────────
    "Dubai International Cricket Stadium, Dubai":(25.1972, 55.2744),
    "Sheikh Zayed Cricket Stadium, Abu Dhabi":   (24.4539, 54.3773),
    "Sharjah Cricket Stadium, Sharjah":          (25.3463, 55.4209),

    # ── USA ────────────────────────────────────────────────────────────────
    "Nassau County International Cricket Stadium, New York": (40.6501, -73.5994),
    "Grand Prairie Cricket Stadium, Dallas":     (32.7767, -97.0647),

    # ── Zimbabwe ───────────────────────────────────────────────────────────
    "Harare Sports Club, Harare":                (-17.8292, 31.0522),
    "Queens Sports Club, Bulawayo":              (-20.1594, 28.5667),

    # ── Ireland ────────────────────────────────────────────────────────────
    "The Village, Dublin":                       (53.3498, -6.2603),

    # ── Scotland ───────────────────────────────────────────────────────────
    "Grange Cricket Club, Edinburgh":            (55.9443, -3.2396),

    # ── Afghanistan ────────────────────────────────────────────────────────
    "Arun Jaitley Stadium, Delhi":               (28.6364, 77.2243),  # used as neutral
    "Greater Noida Sports Complex Ground":       (28.5355, 77.3910),
}


def get_venue_coords(venue_name: str) -> tuple[float, float] | None:
    """
    Return (lat, lon) for a venue name, or None if unknown.
    Does fuzzy matching — tries exact, then partial word overlap.
    """
    if not venue_name:
        return None

    # Exact match
    if venue_name in VENUE_COORDS:
        return VENUE_COORDS[venue_name]

    # Case-insensitive exact
    vl = venue_name.lower()
    for k, v in VENUE_COORDS.items():
        if k.lower() == vl:
            return v

    # Partial match — any significant word overlap
    v_words = set(w for w in vl.replace(',', '').split() if len(w) > 3)
    best_score, best_coords = 0, None
    for k, coords in VENUE_COORDS.items():
        k_words = set(w for w in k.lower().replace(',', '').split() if len(w) > 3)
        score = len(v_words & k_words)
        if score > best_score:
            best_score = score
            best_coords = coords

    return best_coords if best_score >= 2 else None
