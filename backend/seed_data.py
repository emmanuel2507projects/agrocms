"""
Seed the AgroCMS SQLite database with synthetic but realistic
Tasmanian pharmaceutical poppy data.
Run:  python backend/seed_data.py
      python backend/seed_data.py --reset   (drops & recreates)
"""

import sys
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import engine, SessionLocal
from backend.models import Base, Grower, Paddock, Contract, SowingRecord, HarvestRecord, PesticideApplication, CropCost

# â”€â”€ reproducible â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RNG = random.Random(42)

# â”€â”€ region centres (Northern Tasmania) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
REGION_CENTRES = {
    "Westbury":  (-41.533, 146.848),
    "Deloraine": (-41.523, 146.648),
    "Longford":  (-41.600, 147.113),
    "Perth":     (-41.571, 147.177),
    "Latrobe":   (-41.242, 146.417),
}

SOIL_TYPES = ["Red Ferrosol", "Brown Dermosol", "Grey Vertosol"]
VARIETIES   = ["Norman", "Latex"]
SEASONS     = ["2022-23", "2023-24", "2024-25"]
SEASON_YEAR = {"2022-23": 2022, "2023-24": 2023, "2024-25": 2024}

CHEMICALS = [
    ("Glyphosate",    2.5, 7),
    ("Chlorpyrifos",  1.2, 28),
    ("Pendimethalin", 3.0, 14),
]

COST_TYPES = ["seed", "fertiliser", "pesticide", "contractor", "irrigation", "harvest_levy", "admin"]

LOSS_REASONS = [
    "Weather damage", "Pest pressure", "Disease",
    "Mechanical loss", "Irrigation failure", None,
]

# â”€â”€ weather per (region, season_year) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
WEATHER = {
    ("Westbury",  2022): {"rainfall_mm": 625, "avg_temp_c": 12.3},
    ("Westbury",  2023): {"rainfall_mm": 695, "avg_temp_c": 13.0},
    ("Westbury",  2024): {"rainfall_mm": 585, "avg_temp_c": 12.7},
    ("Deloraine", 2022): {"rainfall_mm": 680, "avg_temp_c": 11.8},
    ("Deloraine", 2023): {"rainfall_mm": 720, "avg_temp_c": 12.4},
    ("Deloraine", 2024): {"rainfall_mm": 640, "avg_temp_c": 12.1},
    ("Longford",  2022): {"rainfall_mm": 560, "avg_temp_c": 13.2},
    ("Longford",  2023): {"rainfall_mm": 610, "avg_temp_c": 13.8},
    ("Longford",  2024): {"rainfall_mm": 575, "avg_temp_c": 13.5},
    ("Perth",     2022): {"rainfall_mm": 555, "avg_temp_c": 13.5},
    ("Perth",     2023): {"rainfall_mm": 605, "avg_temp_c": 14.1},
    ("Perth",     2024): {"rainfall_mm": 570, "avg_temp_c": 13.9},
    ("Latrobe",   2022): {"rainfall_mm": 740, "avg_temp_c": 11.5},
    ("Latrobe",   2023): {"rainfall_mm": 710, "avg_temp_c": 12.0},
    ("Latrobe",   2024): {"rainfall_mm": 695, "avg_temp_c": 11.8},
}

# â”€â”€ 20 growers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GROWER_DATA = [
    # Westbury (4)
    {"name": "James Henderson",   "region": "Westbury",  "status": "active"},
    {"name": "Sarah Mitchell",    "region": "Westbury",  "status": "active"},
    {"name": "Robert Tanner",     "region": "Westbury",  "status": "active"},
    {"name": "Claire Whitfield",  "region": "Westbury",  "status": "active"},
    # Deloraine (4)
    {"name": "Peter Burgess",     "region": "Deloraine", "status": "active"},
    {"name": "Helen Stokes",      "region": "Deloraine", "status": "active"},
    {"name": "Matthew Crawford",  "region": "Deloraine", "status": "active"},
    {"name": "Amanda Lawson",     "region": "Deloraine", "status": "active"},
    # Longford (4)
    {"name": "David Campbell",    "region": "Longford",  "status": "active"},
    {"name": "Fiona McKenzie",    "region": "Longford",  "status": "active"},
    {"name": "Thomas Walsh",      "region": "Longford",  "status": "active"},
    {"name": "Natalie Pearce",    "region": "Longford",  "status": "active"},
    # Perth (4)
    {"name": "Gregory Barnes",    "region": "Perth",     "status": "active"},
    {"name": "Linda Forsyth",     "region": "Perth",     "status": "active"},
    {"name": "Andrew Nielson",    "region": "Perth",     "status": "active"},
    {"name": "Joanne Carmichael", "region": "Perth",     "status": "active"},
    # Latrobe (4)
    {"name": "Kenneth Rudd",      "region": "Latrobe",   "status": "active"},
    {"name": "Patricia Hollis",   "region": "Latrobe",   "status": "active"},
    {"name": "Stuart Beaumont",   "region": "Latrobe",   "status": "active"},
    {"name": "Wendy Farrell",     "region": "Latrobe",   "status": "suspended"},
]

PADDOCK_NAMES = [
    "North Block", "River Flat", "Hill Paddock", "Main Block",
    "East Paddock", "Creek Flat", "Back Block", "South Run",
    "Top Paddock", "Gully Flat",
]


# â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def make_polygon(centre_lat, centre_lon, area_ha):
    """Return a closed GeoJSON ring [[lon,lat], ...] for a rectangular paddock."""
    side_m  = math.sqrt(area_ha * 10_000)
    half_lat = side_m / 111_000 / 2
    half_lon = side_m /  83_000 / 2
    clon, clat = centre_lon, centre_lat
    ring = [
        [clon - half_lon, clat - half_lat],
        [clon + half_lon, clat - half_lat],
        [clon + half_lon, clat + half_lat],
        [clon - half_lon, clat + half_lat],
        [clon - half_lon, clat - half_lat],
    ]
    return json.dumps(ring)


def calc_yield(variety, soil_type, region, season_year, seed_rate, rainfall, avg_temp):
    base = {"Norman": 10.5, "Latex": 9.8}[variety]
    soil_mod = {"Red Ferrosol": 0.8, "Brown Dermosol": 0.0, "Grey Vertosol": -0.5}[soil_type]
    rain_mod = (rainfall - 650) * 0.003
    temp_mod = -abs(avg_temp - 12.0) * 0.08
    seed_mod = -abs(seed_rate - 1.5) * 0.5
    noise    = RNG.gauss(0, 0.45)
    return round(max(8.0, min(14.0, base + soil_mod + rain_mod + temp_mod + seed_mod + noise)), 2)


def calc_morphine(variety):
    base = {"Norman": 0.45, "Latex": 0.38}[variety]
    return round(max(0.35, min(0.55, base + RNG.gauss(0, 0.025))), 3)


def licence_expiry_for(idx):
    """Spread expiry dates: some expired, some soon, most current."""
    today = date(2026, 6, 21)
    if idx in (18, 19):          # expired
        return today - timedelta(days=RNG.randint(15, 90))
    if idx in (2, 11):           # expiring within 30 days
        return today + timedelta(days=RNG.randint(5, 28))
    # current
    return today + timedelta(days=RNG.randint(60, 730))


# â”€â”€ main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def seed(session):
    # â”€â”€ growers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    growers = []
    for i, g in enumerate(GROWER_DATA):
        grower = Grower(
            name=g["name"],
            licence_no=f"PACB-202{1 + (i % 3)}-{i+1:04d}",
            region=g["region"],
            status=g["status"],
            contact_email=f"{g['name'].lower().replace(' ', '.')}@tasfarm.com.au",
            licence_expiry=licence_expiry_for(i),
        )
        session.add(grower)
        growers.append(grower)
    session.flush()

    # â”€â”€ paddocks (50 total: first 10 growers get 3, rest get 2) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    paddocks_by_grower: dict[int, list] = {}
    paddock_count = 0
    for i, grower in enumerate(growers):
        n_pads = 3 if i < 10 else 2
        clat, clon = REGION_CENTRES[grower.region]
        pads = []
        used_names = set()
        for _ in range(n_pads):
            area = round(RNG.uniform(15, 75), 1)
            offset_lat = RNG.uniform(-0.06, 0.06)
            offset_lon = RNG.uniform(-0.06, 0.06)
            plat = clat + offset_lat
            plon = clon + offset_lon
            name = RNG.choice([n for n in PADDOCK_NAMES if n not in used_names])
            used_names.add(name)
            pad = Paddock(
                grower_id=grower.id,
                name=name,
                area_ha=area,
                soil_type=RNG.choice(SOIL_TYPES),
                geojson_coords=make_polygon(plat, plon, area),
                lat=plat,
                lon=plon,
            )
            session.add(pad)
            pads.append(pad)
            paddock_count += 1
        paddocks_by_grower[grower.id] = pads
    session.flush()

    # â”€â”€ contracts, sowing, harvest, pesticides, costs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    for grower in growers:
        pads = paddocks_by_grower[grower.id]
        for season in SEASONS:
            yr = SEASON_YEAR[season]
            variety = RNG.choice(VARIETIES)
            contracted_ha = round(sum(p.area_ha for p in pads) * RNG.uniform(0.7, 0.95), 1)
            price = round(RNG.uniform(55, 75), 2)

            contract = Contract(
                grower_id=grower.id,
                season=season,
                variety=variety,
                area_contracted_ha=contracted_ha,
                price_per_kg=price,
            )
            session.add(contract)
            session.flush()

            # costs
            for ct in COST_TYPES:
                base_costs = {
                    "seed":          contracted_ha * RNG.uniform(180, 220),
                    "fertiliser":    contracted_ha * RNG.uniform(300, 450),
                    "pesticide":     contracted_ha * RNG.uniform(80,  130),
                    "contractor":    contracted_ha * RNG.uniform(200, 350),
                    "irrigation":    contracted_ha * RNG.uniform(50,  150),
                    "harvest_levy":  contracted_ha * price * 0.03,
                    "admin":         RNG.uniform(800, 1800),
                }
                session.add(CropCost(
                    contract_id=contract.id,
                    cost_type=ct,
                    amount=round(base_costs[ct], 2),
                    recorded_date=date(yr, RNG.randint(10, 12), RNG.randint(1, 28)),
                ))

            # sowing & harvest per paddock
            weather = WEATHER[(grower.region, yr)]
            is_current = season == "2024-25"

            for pad in pads:
                sow_day = date(yr, 11, RNG.randint(1, 30))
                seed_rate = round(RNG.uniform(1.2, 1.8), 2)
                declaration_lodged = 0 if (grower.id % 7 == 0 and is_current) else 1

                sow = SowingRecord(
                    paddock_id=pad.id,
                    contract_id=contract.id,
                    sow_date=sow_day,
                    seed_rate_kg_ha=seed_rate,
                    status="growing" if is_current else "harvested",
                    sowing_declaration_lodged=declaration_lodged,
                )
                session.add(sow)

                # harvest â€” skip ~15 % of 2024-25 paddocks (in progress)
                if not is_current or RNG.random() > 0.15:
                    harv_day = sow_day + timedelta(days=RNG.randint(85, 110))
                    yld      = calc_yield(variety, pad.soil_type, grower.region, yr,
                                         seed_rate, weather["rainfall_mm"], weather["avg_temp_c"])
                    morph    = calc_morphine(variety)
                    loss_pct = RNG.uniform(0.02, 0.08)
                    loss_kg  = round(yld * pad.area_ha * loss_pct, 1)
                    recon_submitted = 0 if (grower.id % 11 == 0 and is_current) else 1

                    session.add(HarvestRecord(
                        paddock_id=pad.id,
                        contract_id=contract.id,
                        harvest_date=harv_day,
                        yield_kg_ha=yld,
                        morphine_content_pct=morph,
                        loss_kg=loss_kg,
                        loss_reason=RNG.choice(LOSS_REASONS),
                        harvest_reconciliation_submitted=recon_submitted,
                    ))

                # pesticide applications (2-4 per paddock per season)
                for _ in range(RNG.randint(2, 4)):
                    chem, rate, wh = RNG.choice(CHEMICALS)
                    app_date = date(yr, RNG.choice([10, 11, 12]), RNG.randint(1, 28))
                    session.add(PesticideApplication(
                        paddock_id=pad.id,
                        applied_date=app_date,
                        chemical_name=chem,
                        rate_L_ha=round(rate * RNG.uniform(0.85, 1.15), 2),
                        withholding_days=wh,
                        applicator_id=f"APP-{RNG.randint(100, 999)}",
                    ))

    session.commit()
    print(f"Seeded: {len(growers)} growers, {paddock_count} paddocks, "
          f"{len(SEASONS)} seasons each.")


def write_geojson(session):
    """Write data/paddocks.geojson from DB for the Folium map."""
    out = Path(__file__).parent.parent / "data" / "paddocks.geojson"
    features = []
    for pad in session.query(Paddock).all():
        if not pad.geojson_coords:
            continue
        ring = json.loads(pad.geojson_coords)
        # Most recent harvest yield for colour
        latest_hr = (
            session.query(HarvestRecord)
            .filter(HarvestRecord.paddock_id == pad.id)
            .order_by(HarvestRecord.harvest_date.desc())
            .first()
        )
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "paddock_id":    pad.id,
                "paddock_name":  pad.name,
                "grower_id":     pad.grower_id,
                "area_ha":       pad.area_ha,
                "soil_type":     pad.soil_type,
                "yield_kg_ha":   latest_hr.yield_kg_ha if latest_hr else None,
                "morphine_pct":  latest_hr.morphine_content_pct if latest_hr else None,
                "lat":           pad.lat,
                "lon":           pad.lon,
            },
        })
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2))
    print(f"Written {len(features)} paddock features â†’ {out}")


if __name__ == "__main__":
    reset = "--reset" in sys.argv

    if reset:
        Base.metadata.drop_all(bind=engine)
        print("Tables dropped.")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        if session.query(Grower).count() > 0 and not reset:
            print("Database already seeded. Use --reset to reseed.")
        else:
            seed(session)
            write_geojson(session)
    finally:
        session.close()

