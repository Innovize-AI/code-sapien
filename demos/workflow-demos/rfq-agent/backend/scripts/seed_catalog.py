"""
Seed the products catalog table.

Usage:
    python scripts/seed_catalog.py
    python scripts/seed_catalog.py --csv scripts/catalog_sample.csv
    python scripts/seed_catalog.py --dry-run
"""
import sys, os, argparse, csv, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
_local = Path(__file__).resolve().parent.parent / ".env"
if _local.exists():
    load_dotenv(_local, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = [
    {"product_id": "BOLT-M8-SS-001",   "name": "M8 Stainless Steel Hex Bolt 50mm",           "unit_price": 8.50,     "available": True,  "lead_time_days": 3,  "category": "fasteners",       "unit": "pcs",  "description": "M8 x 50mm SS 316 hex bolt DIN 931"},
    {"product_id": "BOLT-M10-GI-002",  "name": "M10 GI Hex Bolt 75mm",                        "unit_price": 6.00,     "available": True,  "lead_time_days": 3,  "category": "fasteners",       "unit": "pcs",  "description": "M10 x 75mm galvanised iron hex bolt DIN 933"},
    {"product_id": "NUT-M8-SS-003",    "name": "M8 Stainless Steel Hex Nut",                   "unit_price": 3.50,     "available": True,  "lead_time_days": 3,  "category": "fasteners",       "unit": "pcs",  "description": "M8 SS 316 hex nut DIN 934"},
    {"product_id": "NUT-M10-GI-004",   "name": "M10 GI Hex Nut",                               "unit_price": 2.80,     "available": True,  "lead_time_days": 3,  "category": "fasteners",       "unit": "pcs",  "description": "M10 galvanised iron hex nut DIN 934"},
    {"product_id": "WASH-M8-SS-005",   "name": "M8 Stainless Steel Flat Washer",               "unit_price": 1.50,     "available": True,  "lead_time_days": 3,  "category": "fasteners",       "unit": "pcs",  "description": "M8 SS 304 flat washer DIN 125"},
    {"product_id": "SCREW-ST-006",     "name": "Self-Tapping Screw 4.2x25mm Box 100",          "unit_price": 95.00,    "available": True,  "lead_time_days": 5,  "category": "fasteners",       "unit": "box",  "description": "4.2x25mm zinc plated self-tapping Phillips head screw"},
    {"product_id": "STL-MS-PLATE-007", "name": "MS Plate 6mm 2500x1250mm",                    "unit_price": 4200.00,  "available": True,  "lead_time_days": 7,  "category": "steel",           "unit": "sheet","description": "Mild steel plate IS 2062 E250 Grade 6mm thick"},
    {"product_id": "STL-HR-COIL-008",  "name": "HR Steel Coil 2mm 1000mm width per MT",       "unit_price": 62000.00, "available": True,  "lead_time_days": 10, "category": "steel",           "unit": "MT",   "description": "Hot rolled steel coil IS 10748 2mm thick 1000mm wide"},
    {"product_id": "STL-SS-PIPE-009",  "name": "SS 304 Pipe 2 inch SCH40 per meter",           "unit_price": 850.00,   "available": True,  "lead_time_days": 7,  "category": "steel",           "unit": "mtr",  "description": "Stainless steel 304 seamless pipe 2 inch schedule 40"},
    {"product_id": "ALU-SHEET-010",    "name": "Aluminium Sheet 3mm 2438x1219mm",              "unit_price": 3800.00,  "available": True,  "lead_time_days": 7,  "category": "metals",          "unit": "sheet","description": "Aluminium alloy 5052 sheet 3mm thick"},
    {"product_id": "STL-ANGLE-011",    "name": "MS Angle 50x50x6mm per meter",                 "unit_price": 220.00,   "available": True,  "lead_time_days": 5,  "category": "steel",           "unit": "mtr",  "description": "Mild steel equal angle 50x50x6mm IS 2062"},
    {"product_id": "STL-CHANNEL-012",  "name": "MS Channel ISMC 100 per meter",                "unit_price": 420.00,   "available": True,  "lead_time_days": 5,  "category": "steel",           "unit": "mtr",  "description": "Mild steel C-channel ISMC 100 100x50mm IS 2062"},
    {"product_id": "ELEC-CU-WIRE-013", "name": "Copper Wire 2.5 sqmm 100m roll",              "unit_price": 1850.00,  "available": True,  "lead_time_days": 5,  "category": "electrical",      "unit": "roll", "description": "FR PVC insulated copper conductor 2.5 sqmm 100m"},
    {"product_id": "ELEC-CU-WIRE-014", "name": "Copper Wire 6 sqmm 100m roll",                "unit_price": 4200.00,  "available": True,  "lead_time_days": 5,  "category": "electrical",      "unit": "roll", "description": "FR PVC insulated copper conductor 6 sqmm 100m"},
    {"product_id": "ELEC-MCB-015",     "name": "MCB 32A Single Pole C-Curve",                  "unit_price": 380.00,   "available": True,  "lead_time_days": 3,  "category": "electrical",      "unit": "pcs",  "description": "Miniature circuit breaker 32A 1P C-curve 10kA"},
    {"product_id": "ELEC-CONT-016",    "name": "AC Contactor 32A 3P 230V Coil",                "unit_price": 1200.00,  "available": True,  "lead_time_days": 5,  "category": "electrical",      "unit": "pcs",  "description": "AC magnetic contactor 32A 3 pole 230V AC coil"},
    {"product_id": "ELEC-TRAY-017",    "name": "Perforated Cable Tray 150x50mm per meter",     "unit_price": 320.00,   "available": True,  "lead_time_days": 7,  "category": "electrical",      "unit": "mtr",  "description": "GI perforated cable tray 150mm wide 50mm deep"},
    {"product_id": "BRG-6205-018",     "name": "Deep Groove Ball Bearing 6205-2RS",             "unit_price": 180.00,   "available": True,  "lead_time_days": 5,  "category": "bearings",        "unit": "pcs",  "description": "6205-2RS bearing 25x52x15mm rubber sealed"},
    {"product_id": "BRG-6305-019",     "name": "Deep Groove Ball Bearing 6305-ZZ",              "unit_price": 220.00,   "available": True,  "lead_time_days": 5,  "category": "bearings",        "unit": "pcs",  "description": "6305-ZZ bearing 25x62x17mm metal shielded"},
    {"product_id": "BRG-UCF-020",      "name": "Pillow Block Bearing UCF205",                   "unit_price": 450.00,   "available": True,  "lead_time_days": 7,  "category": "bearings",        "unit": "pcs",  "description": "UCF205 square flange pillow block bearing unit 25mm bore"},
    {"product_id": "BELT-VBELT-021",   "name": "V-Belt A-Section A50",                         "unit_price": 220.00,   "available": True,  "lead_time_days": 5,  "category": "mechanical",      "unit": "pcs",  "description": "Classical V-belt A section A50 length 1270mm"},
    {"product_id": "PKG-CBOX-022",     "name": "Corrugated Box 30x20x20cm 5-ply Bundle 25",    "unit_price": 1100.00,  "available": True,  "lead_time_days": 5,  "category": "packaging",       "unit": "bundle","description": "5-ply corrugated carton box 300x200x200mm bundle of 25"},
    {"product_id": "PKG-SWRAP-023",    "name": "Stretch Wrap Film 500mm 300m roll",             "unit_price": 380.00,   "available": True,  "lead_time_days": 3,  "category": "packaging",       "unit": "roll", "description": "LLDPE stretch wrap film 500mm wide 300m 23 micron"},
    {"product_id": "PKG-STRAP-024",    "name": "PP Strapping Roll 12mm 1000m",                  "unit_price": 950.00,   "available": True,  "lead_time_days": 5,  "category": "packaging",       "unit": "roll", "description": "Polypropylene strapping 12mm wide 1000m box strapping"},
    {"product_id": "PKG-TAPE-025",     "name": "BOPP Packing Tape 48mm 66m Box 36",             "unit_price": 1100.00,  "available": True,  "lead_time_days": 3,  "category": "packaging",       "unit": "box",  "description": "Brown BOPP packing tape 48mm 66m box of 36 rolls"},
    {"product_id": "SAF-HELM-026",     "name": "Safety Helmet ISI Marked Ratchet",              "unit_price": 320.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "pcs",  "description": "Industrial safety helmet IS 2925 ratchet HDPE shell"},
    {"product_id": "SAF-GLOVE-027",    "name": "Nitrile Safety Gloves Size L Box 100",          "unit_price": 680.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "box",  "description": "Nitrile powder-free gloves size large box of 100"},
    {"product_id": "SAF-SHOE-028",     "name": "Safety Shoe Steel Toe Cap Size 8",              "unit_price": 1200.00,  "available": True,  "lead_time_days": 7,  "category": "safety",          "unit": "pair", "description": "Steel toe safety shoe IS 15298 leather upper"},
    {"product_id": "SAF-VEST-029",     "name": "Hi-Vis Reflective Safety Vest Size L",          "unit_price": 180.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "pcs",  "description": "High visibility yellow safety vest 2-band reflective"},
    {"product_id": "WLD-ELEC-030",     "name": "Welding Electrode E6013 3.15mm 5kg",            "unit_price": 650.00,   "available": True,  "lead_time_days": 3,  "category": "welding",         "unit": "pack", "description": "E6013 rutile welding electrode 3.15mm 5kg pack"},
    {"product_id": "WLD-WIRE-031",     "name": "MIG Welding Wire ER70S-6 0.8mm 15kg",          "unit_price": 2800.00,  "available": True,  "lead_time_days": 5,  "category": "welding",         "unit": "spool","description": "ER70S-6 MIG wire 0.8mm 15kg spool CO2 welding"},
    {"product_id": "TOOL-DISC-032",    "name": "Cutting Disc 230x3x22.2mm Box 25",              "unit_price": 900.00,   "available": True,  "lead_time_days": 3,  "category": "tools",           "unit": "box",  "description": "Resinoid cutting disc 230mm for steel box 25"},
    {"product_id": "TOOL-DISC-033",    "name": "Grinding Disc 125x6x22.2mm Box 25",             "unit_price": 850.00,   "available": True,  "lead_time_days": 3,  "category": "tools",           "unit": "box",  "description": "Depressed centre grinding wheel 125mm for mild steel box 25"},
    {"product_id": "TOOL-DRILL-034",   "name": "HSS Drill Bit 10mm",                            "unit_price": 85.00,    "available": True,  "lead_time_days": 3,  "category": "tools",           "unit": "pcs",  "description": "HSS-Co high speed steel twist drill bit 10mm DIN 338"},
    {"product_id": "IT-LAP-035",       "name": "Laptop Core i5 13th Gen 8GB 512GB SSD",        "unit_price": 52000.00, "available": True,  "lead_time_days": 7,  "category": "it_hardware",     "unit": "pcs",  "description": "Business laptop Intel Core i5 13th gen 8GB 512GB 15.6 inch"},
    {"product_id": "IT-UPS-036",       "name": "UPS 1KVA Line Interactive",                     "unit_price": 7500.00,  "available": True,  "lead_time_days": 5,  "category": "it_hardware",     "unit": "pcs",  "description": "1KVA 800W line interactive UPS with AVR"},
    {"product_id": "IT-SWITCH-037",    "name": "Managed Switch 24-Port Gigabit",                "unit_price": 18000.00, "available": False, "lead_time_days": 14, "category": "it_hardware",     "unit": "pcs",  "description": "24-port gigabit managed ethernet switch VLAN QoS 1U"},
    {"product_id": "IT-ROUTER-038",    "name": "WiFi 6 Router Dual Band",                       "unit_price": 6500.00,  "available": True,  "lead_time_days": 5,  "category": "it_hardware",     "unit": "pcs",  "description": "WiFi 6 AX1800 dual band wireless router office use"},
    {"product_id": "LUB-OIL-039",      "name": "Hydraulic Oil ISO VG 46 20L",                  "unit_price": 2800.00,  "available": True,  "lead_time_days": 5,  "category": "lubricants",      "unit": "can",  "description": "Anti-wear hydraulic oil ISO VG 46 20 litre"},
    {"product_id": "LUB-GREASE-040",   "name": "Lithium Grease EP-2 1kg",                      "unit_price": 320.00,   "available": True,  "lead_time_days": 3,  "category": "lubricants",      "unit": "tin",  "description": "Lithium complex EP NLGI 2 bearing grease 1kg"},
    
    # Electrical Panel Components (GEI)
    {"product_id": "ELEC-MCCB-250",  "name": "MCCB 250A 3P 36kA",                         "unit_price": 8500.00,  "available": True,  "lead_time_days": 5,  "category": "electrical",      "unit": "pcs",  "description": "Schneider EasyPact 250A 3-pole MCCB 36kA"},
    {"product_id": "ELEC-ELCB-40",   "name": "Earth Leakage Circuit Breaker 40A 30mA",     "unit_price": 1450.00,  "available": False, "lead_time_days": 7,  "category": "electrical",      "unit": "pcs",  "description": "ELCB 40A 30mA sensitivity 4 pole"},
    {"product_id": "ELEC-BUSBAR-100", "name": "Busbar Copper 100A 3-Phase",                 "unit_price": 950.00,   "available": True,  "lead_time_days": 3,  "category": "electrical",      "unit": "mtr",  "description": "3-phase copper busbar rated at 100A"},
    {"product_id": "ELEC-DINRAIL-35", "name": "DIN Rail 35mm Top Hat 1000mm",               "unit_price": 75.00,    "available": True,  "lead_time_days": 2,  "category": "electrical",      "unit": "pcs",  "description": "Galvanised steel DIN rail 35mm standard 1m length"},
    {"product_id": "ELEC-TERM-4",    "name": "Terminal Block 4mm² Grey",                   "unit_price": 15.00,    "available": True,  "lead_time_days": 2,  "category": "electrical",      "unit": "pcs",  "description": "Grey feed-through terminal block 4sqmm screw connection"},
    {"product_id": "ELEC-SPD-T2",    "name": "Surge Protection Device Type 2",             "unit_price": 2800.00,  "available": True,  "lead_time_days": 5,  "category": "electrical",      "unit": "pcs",  "description": "Type 2 surge protection device for power lines"},
    {"product_id": "ELEC-ENC-862",   "name": "Panel Enclosure 800×600×200 IP65",           "unit_price": 9500.00,  "available": True,  "lead_time_days": 7,  "category": "electrical",      "unit": "pcs",  "description": "Wall-mounted sheet steel IP65 electrical enclosure"},

    # Marine Supplies (MV Sea Phoenix)
    {"product_id": "LUB-ENG-OIL40",  "name": "Engine Oil SAE 40 CD/CF (Drum 208L)",         "unit_price": 38000.00, "available": True,  "lead_time_days": 5,  "category": "lubricants",      "unit": "drum", "description": "Marine engine lubrication oil SAE 40 CD/CF grade"},
    {"product_id": "LUB-HYD-OIL46",  "name": "Hydraulic Oil ISO VG 46 (Drum 208L)",         "unit_price": 35000.00, "available": True,  "lead_time_days": 5,  "category": "lubricants",      "unit": "drum", "description": "Premium anti-wear hydraulic fluid ISO VG 46"},
    {"product_id": "LUB-GRS-EP2-18", "name": "Grease Multipurpose NLGI 2 (18kg Pail)",       "unit_price": 7500.00,  "available": True,  "lead_time_days": 3,  "category": "lubricants",      "unit": "pcs",  "description": "Multipurpose extreme pressure lithium grease EP2 18kg pail"},
    {"product_id": "SAF-HELM-WHITE", "name": "Safety Helmet White EN 397",                  "unit_price": 280.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "pcs",  "description": "Industrial safety helmet white colour EN 397 certified"},
    {"product_id": "SAF-SHOE-S3-42", "name": "Safety Boots Steel Toe S3 (Size 42)",         "unit_price": 1800.00,  "available": True,  "lead_time_days": 4,  "category": "safety",          "unit": "pair", "description": "Steel toe safety boots S3 protection grade size 42"},
    {"product_id": "PNT-PRMER-RED",  "name": "Paint Anti-Corrosive Primer Red (20L)",       "unit_price": 6800.00,  "available": True,  "lead_time_days": 3,  "category": "paint",           "unit": "tin",  "description": "Red oxide anti-corrosive primer paint 20L tin"},
    {"product_id": "PNT-FOUL-20L",   "name": "Paint Anti-Fouling (20L)",                    "unit_price": 18000.00, "available": False, "lead_time_days": 10, "category": "paint",           "unit": "tin",  "description": "Marine anti-fouling paint for ship hulls 20L tin"},
    {"product_id": "WLD-ELEC-6013B", "name": "Welding Electrode E6013 3.2mm (5kg box)",       "unit_price": 650.00,   "available": True,  "lead_time_days": 2,  "category": "welding",         "unit": "box",  "description": "Mild steel welding electrode E6013 size 3.2mm"},
    {"product_id": "GEN-TISSUE-48",  "name": "Toilet Paper 2-ply Roll (48 pack)",          "unit_price": 950.00,   "available": True,  "lead_time_days": 2,  "category": "general",         "unit": "pack", "description": "Soft 2-ply toilet paper rolls pack of 48"},
    {"product_id": "GEN-SOAP-5L",    "name": "Liquid Dish Soap 5L Can",                     "unit_price": 450.00,   "available": True,  "lead_time_days": 2,  "category": "general",         "unit": "can",  "description": "Concentrated liquid dishwashing soap 5L can"},

    # HVAC (Mall Expansion)
    {"product_id": "HVAC-AHU-20K",   "name": "Air Handling Unit 20,000 CFM",                "unit_price": 850000.00,"available": True,  "lead_time_days": 30, "category": "hvac",            "unit": "pcs",  "description": "Double skin air handling unit 20,000 CFM Carrier/Trane/York"},
    {"product_id": "HVAC-FCU-1200",  "name": "Fan Coil Unit 4-pipe 1200 CFM",               "unit_price": 45000.00, "available": True,  "lead_time_days": 15, "category": "hvac",            "unit": "pcs",  "description": "Concealed ceiling fan coil unit 4-pipe 1200 CFM"},
    {"product_id": "HVAC-PUMP-150",  "name": "Chilled Water Pump 150 GPM 30m head",         "unit_price": 120000.00,"available": False, "lead_time_days": 20, "category": "hvac",            "unit": "pcs",  "description": "Chilled water circulation pump 150 GPM 30m head Grundfos"},
    {"product_id": "HVAC-VAV-DDC",   "name": "VAV Box with DDC Controller",                 "unit_price": 18000.00, "available": True,  "lead_time_days": 10, "category": "hvac",            "unit": "pcs",  "description": "Variable air volume box with integrated Siemens DDC controller"},
    {"product_id": "HVAC-INS-ARM25", "name": "Duct Insulation Armaflex 25mm",               "unit_price": 450.00,   "available": True,  "lead_time_days": 5,  "category": "hvac",            "unit": "sqm",  "description": "Armaflex class O nitrile rubber sheet insulation 25mm thick"},
    {"product_id": "HVAC-DUCT-GI",   "name": "GI Ductwork Medium Pressure",                 "unit_price": 280.00,   "available": True,  "lead_time_days": 7,  "category": "hvac",            "unit": "kg",   "description": "Galvanised iron ductwork medium pressure SMACNA standards"},
    {"product_id": "HVAC-R410A-11",  "name": "Refrigerant R410A (11.3kg cylinder)",         "unit_price": 4200.00,  "available": True,  "lead_time_days": 3,  "category": "hvac",            "unit": "cyl",  "description": "Refrigerant gas R410A 11.3kg disposable cylinder"},

    # Safety PPE (Pune Fabrication Yard)
    {"product_id": "SAF-GOGGLE-CS",  "name": "Safety Goggles (clear lens, anti-scratch)",   "unit_price": 120.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "pcs",  "description": "Anti-scratch anti-fog clear safety glasses"},
    {"product_id": "SAF-GLOVE-LTHR", "name": "Leather Welding Gloves",                     "unit_price": 280.00,   "available": True,  "lead_time_days": 3,  "category": "safety",          "unit": "pair", "description": "Heavy duty cowhide leather welding gloves"},
    {"product_id": "SAF-PLUG-NRR33", "name": "Ear Plugs (disposable, NRR 33) Pair",          "unit_price": 5.00,     "available": True,  "lead_time_days": 2,  "category": "safety",          "unit": "pair", "description": "Soft disposable foam earplugs NRR 33 rating"},
    {"product_id": "SAF-HARN-EN361", "name": "Safety Harness Full Body (EN 361)",            "unit_price": 2500.00,  "available": False, "lead_time_days": 5,  "category": "safety",          "unit": "pcs",  "description": "Full body fall arrest safety harness EN 361 certified"},

    # IT Hardware (MENA Tech Solutions)
    {"product_id": "IT-LAP-I7",      "name": "Business Laptop 14\" i7/16GB/512GB",          "unit_price": 85000.00, "available": True,  "lead_time_days": 7,  "category": "it_hardware",     "unit": "pcs",  "description": "Business Laptop 14 inch Intel Core i7 16GB RAM 512GB SSD"},
    {"product_id": "IT-MON-27-4K",   "name": "27\" 4K IPS Monitor USB-C",                   "unit_price": 32000.00, "available": True,  "lead_time_days": 5,  "category": "it_hardware",     "unit": "pcs",  "description": "27 inch 4K UHD IPS display USB-C power delivery"},
    {"product_id": "IT-DOCK-TB4",    "name": "Docking Station Thunderbolt 4",              "unit_price": 14500.00, "available": False, "lead_time_days": 7,  "category": "it_hardware",     "unit": "pcs",  "description": "Universal Thunderbolt 4 docking station Dell WD22"},
    {"product_id": "IT-KBD-COMBO",   "name": "Wireless Keyboard & Mouse Combo",             "unit_price": 4200.00,  "available": True,  "lead_time_days": 3,  "category": "it_hardware",     "unit": "set",  "description": "Logitech wireless keyboard and mouse combo"},
    {"product_id": "IT-CHGR-65W",    "name": "USB-C 65W Travel Charger",                    "unit_price": 1800.00,  "available": True,  "lead_time_days": 3,  "category": "it_hardware",     "unit": "pcs",  "description": "65W USB-C PD travel charger wall plug"},
    {"product_id": "IT-BAG-14",      "name": "Laptop Bag 14\" Padded",                      "unit_price": 1200.00,  "available": True,  "lead_time_days": 3,  "category": "it_hardware",     "unit": "pcs",  "description": "Padded notebook carrying case bag for 14 inch laptops"},
]


def load_from_csv(path: str) -> list[dict]:
    products = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                "product_id":     row["product_id"].strip(),
                "name":           row["name"].strip(),
                "description":    row.get("description", "").strip(),
                "unit_price":     float(row["unit_price"]),
                "available":      row["available"].strip().lower() in ("true", "1", "yes"),
                "lead_time_days": int(row["lead_time_days"]),
                "category":       row.get("category", "").strip() or None,
                "unit":           row.get("unit", "").strip() or None,
            })
    return products


def main():
    parser = argparse.ArgumentParser(description="Seed RFQ product catalog")
    parser.add_argument("--csv",     type=str, help="Path to CSV file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    products = load_from_csv(args.csv) if args.csv else SAMPLE_PRODUCTS

    if args.dry_run:
        print(f"\nDRY RUN — {len(products)} products\n")
        for p in products:
            avail = "✓" if p["available"] else "✗"
            print(f"  [{avail}] {p['product_id']:<25} {p['name']:<55} ₹{p['unit_price']:>10,.2f}  {p['lead_time_days']}d")
        return

    from services.catalog_service import upsert_products_batch
    upsert_products_batch(products)
    print(f"\nDone. {len(products)} products seeded into rfq.products table.")


if __name__ == "__main__":
    main()
