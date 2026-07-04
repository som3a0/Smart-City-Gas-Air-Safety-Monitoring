"""
metadata_config.py  v3 — Realistic IoT Values
Smart City Gas & Air Safety Monitoring Platform
"""

GOVERNORATES = {
    "Cairo":        {"center": (30.0444, 31.2357), "zones": ["Nasr City","Heliopolis","Maadi","Shubra","Zamalek","Moqattam","New Cairo","Ain Shams","Matareyya","Shorouk City","Badr City","Obour City"]},
    "Giza":         {"center": (29.9870, 31.2118), "zones": ["Dokki","Mohandessin","Agouza","Haram","Faisal","6th of October","Sheikh Zayed","Imbaba","Bulaq Dakrour"]},
    "Alexandria":   {"center": (31.2001, 29.9187), "zones": ["Smouha","Stanley","Sidi Gaber","Roushdy","Miami","Montaza","Agami","Borg El Arab","Mandara"]},
    "Qalyubia":     {"center": (30.3292, 31.2170), "zones": ["Banha","Qalyub","Shubra El Kheima","Khanka","Toukh","Kafr Shukr"]},
    "Sharqia":      {"center": (30.7444, 31.7000), "zones": ["Zagazig","10th of Ramadan","Bilbeis","Minya El Qamh","Kafr Saqr","Abu Kabir"]},
    "Dakahlia":     {"center": (31.0364, 31.3807), "zones": ["Mansoura","Talkha","Mit Ghamr","Belbeis","Aga","Sherbin","Matay"]},
    "Gharbia":      {"center": (30.8748, 31.0326), "zones": ["Tanta","Mahalla El Kubra","Kafr El Zayat","Zefta","Basyoun","Samannoud"]},
    "Monufia":      {"center": (30.5972, 30.9876), "zones": ["Shibin El Kom","Menouf","Ashmoun","Quesna","Berket El Sab","Sadat City"]},
    "Beheira":      {"center": (30.8480, 30.3436), "zones": ["Damanhour","Kafr El Dawwar","Rashid","Edku","Abu El Matamir","Hosh Issa"]},
    "Kafr El Sheikh":{"center":(31.1107, 30.9388), "zones": ["Kafr El Sheikh","Desouk","Fuwwah","Baltim","Qallin","Biella"]},
    "Damietta":     {"center": (31.4165, 31.8133), "zones": ["Damietta","New Damietta","Faraskour","Kafr Saad","Ras El Bar"]},
    "Port Said":    {"center": (31.2653, 32.3019), "zones": ["Port Fouad","El Arab","El Manakh","El Zohour","El Sharq","El Dawahy"]},
    "Ismailia":     {"center": (30.5965, 32.2715), "zones": ["Ismailia City","Fayed","Qantara Sharq","Qantara Gharb","Abu Sweir","Tel El Kebir"]},
    "Suez":         {"center": (29.9668, 32.5498), "zones": ["Suez City","Ataka","Ain Sokhna","El Salam"]},
    "South Sinai":  {"center": (28.2134, 33.9000), "zones": ["Sharm El Sheikh","Dahab","Nuweiba","Taba","El Tor","Ras Sidr"]},
    "North Sinai":  {"center": (30.9117, 33.7722), "zones": ["Arish","Sheikh Zuweid","Rafah","Bir El Abd","Hasana","Nakhl"]},
    "Fayoum":       {"center": (29.3084, 30.8428), "zones": ["Fayoum City","Sinnuris","Ibsheway","Tamiya","Yusuf El Seddiq"]},
    "Beni Suef":    {"center": (29.0661, 31.0994), "zones": ["Beni Suef City","Nasser","El Fashn","Beba","Somosta","Ihnasya El Madina"]},
    "Minya":        {"center": (28.0871, 30.7618), "zones": ["Minya City","Mallawi","Dairut","Abu Qurqas","Maghaghah","Beni Mazar","Samalut"]},
    "Asyut":        {"center": (27.1783, 31.1859), "zones": ["Asyut City","Dairut","Manfalut","Qusiya","Sahel Selim","El Badari","Abnoub"]},
    "Sohag":        {"center": (26.5569, 31.6948), "zones": ["Sohag City","Akhmim","Girga","Tahta","Tima","El Maragha","El Balyana"]},
    "Qena":         {"center": (26.1551, 32.7160), "zones": ["Qena City","Nag Hammadi","Luxor","Qift","Deshna","Abu Tesht"]},
    "Luxor":        {"center": (25.6872, 32.6396), "zones": ["Luxor City","Karnak","East Bank","West Bank","Armant","Esna"]},
    "Aswan":        {"center": (24.0889, 32.8998), "zones": ["Aswan City","Kom Ombo","Edfu","Daraw","Abu Simbel","Nasr El Nuba"]},
    "Red Sea":      {"center": (26.9670, 33.8000), "zones": ["Hurghada","Safaga","El Quseir","Marsa Alam","Shalatin","Ras Gharib"]},
    "New Valley":   {"center": (25.4473, 30.5580), "zones": ["Kharga","Dakhla","Farafra","Bawiti","Siwa"]},
    "Matruh":       {"center": (31.3543, 27.2373), "zones": ["Mersa Matruh","Sallum","Siwa","El Hamam","El Alamein"]},
}

BUILDING_TYPES = {
    "apartment":    {"weight": 0.55},
    "villa":        {"weight": 0.15},
    "commercial":   {"weight": 0.15},
    "factory":      {"weight": 0.05},
    "governmental": {"weight": 0.10},
}

HIGH_RISK_ZONES = {
    "Shubra","Imbaba","Matareyya","Ain Shams","Bulaq Dakrour",
    "Haram","Faisal","Mahalla El Kubra","Shubra El Kheima",
    "10th of Ramadan","Kafr El Dawwar","Borg El Arab",
    "Tel El Kebir","Ataka","Suez City",
}
MEDIUM_RISK_ZONES = {
    "Nasr City","Dokki","Mohandessin","Tanta","Mansoura",
    "Zagazig","Banha","Damanhour","Kafr El Sheikh",
    "Ismailia City","Port Fouad","Fayoum City",
    "Asyut City","Sohag City","Qena City","Minya City",
}

MONTHLY_TEMP = {
    1:{"min":9,"max":19},  2:{"min":10,"max":21}, 3:{"min":13,"max":24},
    4:{"min":17,"max":29}, 5:{"min":21,"max":33}, 6:{"min":23,"max":36},
    7:{"min":25,"max":38}, 8:{"min":25,"max":38}, 9:{"min":23,"max":35},
    10:{"min":19,"max":30},11:{"min":14,"max":24},12:{"min":10,"max":20},
}

HOURLY_ACTIVITY = {
    0:0.10, 1:0.08, 2:0.07, 3:0.07, 4:0.08,
    5:0.15, 6:0.35, 7:0.65, 8:0.70, 9:0.55,
    10:0.50,11:0.55,12:0.80,13:0.85,14:0.60,
    15:0.45,16:0.50,17:0.60,18:0.75,19:0.85,
    20:0.90,21:0.80,22:0.55,23:0.30,
}

# ── Realistic thresholds ──────────────────────────────────────
# Methane: atmospheric ~1.8 ppm, warning 50 ppm (LEL ~5%), critical 150 ppm
THRESHOLDS = {
    "methane":     {"warning": 50,   "critical": 150},
    "lpg":         {"warning": 80,   "critical": 200},
    "co2":         {"warning": 1000, "critical": 2000},
    "smoke":       {"warning": 20,   "critical": 45},
    "aqi":         {"warning": 100,  "critical": 150},
    "co":          {"warning": 9,    "critical": 35},
    "temperature": {"warning": 42,   "critical": 55},
}

# ── Normal baseline — realistic IoT indoor readings ───────────
NORMAL_RANGES = {
    "temperature_c":    {"min": 18,  "max": 35},
    "humidity_pct":     {"min": 30,  "max": 70},
    "methane_ppm":      {"min": 1.0, "max": 6.0},   # atmospheric background
    "lpg_ppm":          {"min": 1.0, "max": 12.0},
    "gas_pressure_kpa": {"min": 1.0, "max": 1.8},
    "co_ppm":           {"min": 0.1, "max": 2.5},
    "smoke_level":      {"min": 0.0, "max": 6.0},
    "aqi":              {"min": 40,  "max": 90},
    "co2_ppm":          {"min": 400, "max": 620},
    "pm25_ugm3":        {"min": 5,   "max": 28},
    "pm10_ugm3":        {"min": 10,  "max": 50},
}

# ── Small deltas — gradual change every 10 seconds ────────────
WALK_DELTA = {
    "temperature_c":    0.15,
    "humidity_pct":     0.6,
    "methane_ppm":      0.2,    # very slow — realistic gas sensor
    "lpg_ppm":          0.15,
    "gas_pressure_kpa": 0.015,
    "co_ppm":           0.08,
    "smoke_level":      0.2,
    "aqi":              1.5,
    "co2_ppm":          8.0,
    "pm25_ugm3":        0.8,
    "pm10_ugm3":        1.2,
}

# ── Anomaly escalation — gradual incident growth ──────────────
ANOMALY_ESCALATION = {
    "gas_leak": {
        "methane_ppm":      +12.0,   # +12/batch → WARNING after ~4 batches
        "lpg_ppm":          +8.0,
        "gas_pressure_kpa": +0.08,
        "co_ppm":           +1.2,
    },
    "fire": {
        "temperature_c":    +2.5,
        "smoke_level":      +5.0,
        "co_ppm":           +4.0,
        "aqi":              +12.0,
    },
    "pollution": {
        "aqi":              +10.0,
        "pm25_ugm3":        +7.0,
        "pm10_ugm3":        +10.0,
        "co2_ppm":          +35.0,
    },
}

ANOMALY_PEAKS = {
    "methane_ppm":      350,
    "lpg_ppm":          280,
    "gas_pressure_kpa": 2.8,
    "temperature_c":    60,
    "smoke_level":      75,
    "co_ppm":           45,
    "aqi":              280,
    "pm25_ugm3":        120,
    "pm10_ugm3":        200,
    "co2_ppm":          1800,
}

ANOMALY_DURATION = {"min": 4, "max": 10}


GOV_BOUNDS = {
    "Cairo":          {"lat_min": 29.70, "lat_max": 30.30, "lon_min": 31.10, "lon_max": 31.85},
    "Giza":           {"lat_min": 29.20, "lat_max": 30.20, "lon_min": 30.70, "lon_max": 31.40},
    "Alexandria":     {"lat_min": 30.80, "lat_max": 31.40, "lon_min": 29.40, "lon_max": 30.20},
    "Qalyubia":       {"lat_min": 30.15, "lat_max": 30.35, "lon_min": 31.15, "lon_max": 31.30},
    "Sharqia":        {"lat_min": 30.50, "lat_max": 30.75, "lon_min": 31.50, "lon_max": 31.80},
    "Dakahlia":       {"lat_min": 30.90, "lat_max": 31.15, "lon_min": 31.30, "lon_max": 31.60},
    "Gharbia":        {"lat_min": 30.75, "lat_max": 30.95, "lon_min": 30.90, "lon_max": 31.10},
    "Monufia":        {"lat_min": 30.40, "lat_max": 30.65, "lon_min": 30.85, "lon_max": 31.10},
    "Beheira":        {"lat_min": 30.70, "lat_max": 31.00, "lon_min": 30.10, "lon_max": 30.50},
    "Kafr El Sheikh": {"lat_min": 31.00, "lat_max": 31.20, "lon_min": 30.80, "lon_max": 31.00},
    "Damietta":       {"lat_min": 31.35, "lat_max": 31.45, "lon_min": 31.75, "lon_max": 31.85},
    "Port Said":      {"lat_min": 31.20, "lat_max": 31.25, "lon_min": 32.25, "lon_max": 32.33},
    "Ismailia":       {"lat_min": 30.50, "lat_max": 30.65, "lon_min": 32.20, "lon_max": 32.35},
    "Suez":           {"lat_min": 29.90, "lat_max": 30.00, "lon_min": 32.45, "lon_max": 32.55},
    "South Sinai":    {"lat_min": 27.90, "lat_max": 29.00, "lon_min": 33.40, "lon_max": 34.50},
    "North Sinai":    {"lat_min": 30.50, "lat_max": 31.30, "lon_min": 32.60, "lon_max": 34.20},
    "Fayoum":         {"lat_min": 29.10, "lat_max": 29.50, "lon_min": 30.40, "lon_max": 31.00},
    "Beni Suef":      {"lat_min": 28.90, "lat_max": 29.20, "lon_min": 30.80, "lon_max": 31.20},
    "Minya":          {"lat_min": 27.90, "lat_max": 28.30, "lon_min": 30.50, "lon_max": 31.00},
    "Asyut":          {"lat_min": 27.00, "lat_max": 27.40, "lon_min": 31.00, "lon_max": 31.40},
    "Sohag":          {"lat_min": 26.30, "lat_max": 26.80, "lon_min": 31.40, "lon_max": 31.90},
    "Qena":           {"lat_min": 25.90, "lat_max": 26.30, "lon_min": 32.40, "lon_max": 32.90},
    "Luxor":          {"lat_min": 25.50, "lat_max": 25.80, "lon_min": 32.50, "lon_max": 32.80},
    "Aswan":          {"lat_min": 23.90, "lat_max": 24.30, "lon_min": 32.70, "lon_max": 33.10},
    "Red Sea":        {"lat_min": 25.00, "lat_max": 27.20, "lon_min": 33.50, "lon_max": 34.90},
    "New Valley":     {"lat_min": 24.00, "lat_max": 26.00, "lon_min": 29.90, "lon_max": 31.00},
    "Matruh":         {"lat_min": 30.50, "lat_max": 31.40, "lon_min": 26.50, "lon_max": 28.50},
}

# ─── الإحداثيات الجغرافية الدقيقة لكل المناطق والمدن ───
ZONE_COORDS = {
    # ─── Cairo ───
    "Nasr City": (30.0626, 31.3242),
    "Heliopolis": (30.0911, 31.3256),
    "Maadi": (29.9602, 31.2569),
    "Shubra": (30.0827, 31.2443),
    "Zamalek": (30.0618, 31.2185),
    "Moqattam": (30.0210, 31.2982),
    "New Cairo": (30.0238, 31.4727),
    "Ain Shams": (30.1293, 31.3129),
    "Matareyya": (30.1226, 31.3045),
    "Shorouk City": (30.1459, 31.6214),
    "Badr City": (30.1423, 31.7455),
    "Obour City": (30.2227, 31.4646),

    # ─── Giza ───
    "Dokki": (30.0384, 31.2111),
    "Mohandessin": (30.0519, 31.2001),
    "Agouza": (30.0469, 31.2115),
    "Haram": (29.9950, 31.1444),
    "Faisal": (29.9982, 31.1437),
    "6th of October": (29.9705, 30.9416),
    "Sheikh Zayed": (30.0441, 30.9760),
    "Imbaba": (30.0768, 31.2120),
    "Bulaq Dakrour": (30.0381, 31.1963),

    # ─── Alexandria ───
    "Smouha": (31.2156, 29.9461),
    "Stanley": (31.2366, 29.9497),
    "Sidi Gaber": (31.2267, 29.9405),
    "Roushdy": (31.2384, 29.9576),
    "Miami": (31.2652, 29.9984),
    "Montaza": (31.2844, 30.0210),
    "Agami": (31.1218, 29.7711),
    "Borg El Arab": (30.9023, 29.5441),
    "Mandara": (31.2721, 30.0076),

    # ─── Qalyubia ───
    "Banha": (30.4667, 31.1833),
    "Qalyub": (30.1833, 31.2000),
    "Shubra El Kheima": (30.1286, 31.2422),
    "Khanka": (30.2181, 31.3650),
    "Toukh": (30.3533, 31.1969),
    "Kafr Shukr": (30.5511, 31.2698),

    # ─── Sharqia ───
    "Zagazig": (30.5877, 31.5167),
    "10th of Ramadan": (30.3060, 31.7402),
    "Bilbeis": (30.4184, 31.5645),
    "Minya El Qamh": (30.5186, 31.3168),
    "Kafr Saqr": (30.7712, 31.6373),
    "Abu Kabir": (30.7297, 31.6828),

    # ─── Dakahlia ───
    "Mansoura": (31.0364, 31.3807),
    "Talkha": (31.0537, 31.3779),
    "Mit Ghamr": (30.7186, 31.2547),
    "Belbeis": (30.4184, 31.5645), # مكرر كاسم في الشرقية
    "Aga": (30.9419, 31.2917),
    "Sherbin": (31.1931, 31.5169),
    "Matay": (28.4161, 30.7797), # يتبع إدارياً للمنيا

    # ─── Gharbia ───
    "Tanta": (30.8748, 31.0326),
    "Mahalla El Kubra": (30.9686, 31.1706),
    "Kafr El Zayat": (30.8222, 30.8164),
    "Zefta": (30.7136, 31.2403),
    "Basyoun": (30.9392, 30.8139),
    "Samannoud": (30.9608, 31.2433),

    # ─── Monufia ───
    "Shibin El Kom": (30.5544, 31.0097),
    "Menouf": (30.4633, 30.9297),
    "Ashmoun": (30.2981, 30.9767),
    "Quesna": (30.5606, 31.1444),
    "Berket El Sab": (30.6375, 31.0772),
    "Sadat City": (30.3789, 30.5239),

    # ─── Beheira ───
    "Damanhour": (31.0361, 30.4683),
    "Kafr El Dawwar": (31.1342, 30.1297),
    "Rashid": (31.4014, 30.4211),
    "Edku": (31.3061, 30.2989),
    "Abu El Matamir": (30.9103, 30.1742),
    "Hosh Issa": (30.9069, 30.2942),

    # ─── Kafr El Sheikh ───
    "Kafr El Sheikh": (31.1107, 30.9388),
    "Desouk": (31.1308, 30.6475),
    "Fuwwah": (31.2033, 30.5489),
    "Baltim": (31.5975, 31.0825),
    "Qallin": (31.0558, 30.9344),
    "Biella": (31.1683, 31.2386),

    # ─── Damietta ───
    "Damietta": (31.4165, 31.8133),
    "New Damietta": (31.4372, 31.6706),
    "Faraskour": (31.3283, 31.7161),
    "Kafr Saad": (31.3653, 31.6681),
    "Ras El Bar": (31.5144, 31.8211),

    # ─── Port Said ───
    "Port Fouad": (31.2506, 32.3217),
    "El Arab": (31.2650, 32.2961),
    "El Manakh": (31.2683, 32.2858),
    "El Zohour": (31.2589, 32.2711),
    "El Sharq": (31.2619, 32.3047),
    "El Dawahy": (31.2483, 32.2831),

    # ─── Ismailia ───
    "Ismailia City": (30.6043, 32.2723),
    "Fayed": (30.3289, 32.2964),
    "Qantara Sharq": (30.8525, 32.3211),
    "Qantara Gharb": (30.8553, 32.3081),
    "Abu Sweir": (30.5517, 32.1461),
    "Tel El Kebir": (30.5481, 31.7892),

    # ─── Suez ───
    "Suez City": (29.9668, 32.5498),
    "Ataka": (29.9483, 32.4822),
    "Ain Sokhna": (29.6011, 32.3169),
    "El Salam": (30.0075, 32.5208),

    # ─── South Sinai ───
    "Sharm El Sheikh": (27.9158, 34.3299),
    "Dahab": (28.5000, 34.5167),
    "Nuweiba": (29.0333, 34.6667),
    "Taba": (29.4931, 34.8972),
    "El Tor": (28.2392, 33.6214),
    "Ras Sidr": (29.5933, 32.7169),

    # ─── North Sinai ───
    "Arish": (31.1316, 33.7984),
    "Sheikh Zuweid": (31.2133, 34.1108),
    "Rafah": (31.2806, 34.2417),
    "Bir El Abd": (31.0092, 33.0119),
    "Hasana": (30.4789, 33.7719),
    "Nakhl": (29.9022, 33.7547),

    # ─── Fayoum ───
    "Fayoum City": (29.3084, 30.8428),
    "Sinnuris": (29.4069, 30.8653),
    "Ibsheway": (29.3561, 30.6869),
    "Tamiya": (29.4750, 30.9389),
    "Yusuf El Seddiq": (29.2272, 30.5969),

    # ─── Beni Suef ───
    "Beni Suef City": (29.0661, 31.0994),
    "Nasser": (29.1769, 31.1158),
    "El Fashn": (28.8258, 30.8986),
    "Beba": (28.9328, 31.0069),
    "Somosta": (28.9242, 30.8447),
    "Ihnasya El Madina": (29.0831, 30.9333),

    # ─── Minya & Asyut ───
    "Minya City": (28.0871, 30.7618),
    "Mallawi": (27.7314, 30.8422),
    "Dairut": (27.5564, 30.8067),
    "Abu Qurqas": (27.9300, 30.7711),
    "Maghaghah": (28.6483, 30.8436),
    "Beni Mazar": (28.5008, 30.7981),
    "Samalut": (28.3094, 30.7103),
    "Asyut City": (27.1783, 31.1859),
    "Manfalut": (27.3117, 30.9706),
    "Qusiya": (27.4419, 30.8183),
    "Sahel Selim": (27.0633, 31.3114),
    "El Badari": (26.9925, 31.4158),
    "Abnoub": (27.2661, 31.1517),

    # ─── Sohag ───
    "Sohag City": (26.5569, 31.6948),
    "Akhmim": (26.5622, 31.7450),
    "Girga": (26.3383, 31.8906),
    "Tahta": (26.7694, 31.5022),
    "Tima": (26.9039, 31.4397),
    "El Maragha": (26.7028, 31.6022),
    "El Balyana": (26.2300, 32.0006),

    # ─── Qena & Luxor ───
    "Qena City": (26.1551, 32.7160),
    "Nag Hammadi": (26.0494, 32.2414),
    "Qift": (25.9861, 32.8094),
    "Deshna": (26.1219, 32.4764),
    "Abu Tesht": (26.1172, 32.1000),
    "Luxor City": (25.6872, 32.6396),
    "Karnak": (25.7186, 32.6586),
    "East Bank": (25.6989, 32.6422),
    "West Bank": (25.7267, 32.6078),
    "Armant": (25.6214, 32.5350),
    "Esna": (25.2933, 32.5539),

    # ─── Aswan ───
    "Aswan City": (24.0889, 32.8998),
    "Kom Ombo": (24.4753, 32.9469),
    "Edfu": (24.9781, 32.8736),
    "Daraw": (24.4072, 32.9297),
    "Abu Simbel": (22.3364, 31.6256),
    "Nasr El Nuba": (24.4828, 33.0033),

    # ─── Red Sea ───
    "Hurghada": (27.2574, 33.8129),
    "Safaga": (26.7350, 33.9358),
    "El Quseir": (26.1081, 34.2789),
    "Marsa Alam": (25.0717, 34.8911),
    "Shalatin": (23.1256, 35.5861),
    "Ras Gharib": (28.3581, 33.0772),

    # ─── New Valley & Matruh ───
    "Kharga": (25.4473, 30.5580),
    "Dakhla": (25.5167, 28.9667),
    "Farafra": (27.0569, 27.9714),
    "Bawiti": (28.3494, 28.8653),
    "Mersa Matruh": (31.3543, 27.2373),
    "Sallum": (31.5475, 25.1561),
    "Siwa": (29.2033, 25.5194),
    "El Hamam": (30.8419, 29.3950),
    "El Alamein": (30.8306, 28.9567)
}