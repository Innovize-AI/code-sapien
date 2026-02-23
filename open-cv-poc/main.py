from pdf_processor import PDFProcessor
from measurement_engine import MeasurementEngine
from yolo_detector import YOLODetector, RoomClassifier
import os

def run_poc(pdf_path):
    # 1. Pre-Processing (PDF -> Images)
    processor = PDFProcessor()
    images = []
    if os.path.exists(pdf_path):
        images = processor.convert_pdf_to_images(pdf_path)
    else:
        print(f"File {pdf_path} not found. Running with dummy logic.")
        return

    # 2. AI Detection Layer (YOLO)
    detector = YOLODetector()
    classifier = RoomClassifier()

    # 3. Measurement Engine (The Ruler)
    engine = MeasurementEngine()
    # Calibrate: 1:100 scale example
    engine.set_scale(1000, 118) 

    for img_path in images:
        print(f"\n--- Analyzing {img_path} ---")
        
        # Step A: Detect Symbols (Walls, Doors, etc.)
        detections = detector.detect_elements(img_path)
        print(f"AI Detected {len(detections)} elements.")

        # Step B: Page Classification
        page_type = classifier.classify_page(detections)
        print(f"Classification: This page is a {page_type}")

        # Step C: Geometric Math (on detected walls/rooms)
        # In production, we loop through YOLO 'Wall' coords and pass them to 'engine.measure_line'
        results = engine.detect_and_measure_contours(img_path)
        for i, res in enumerate(results):
            print(f" - Found Area {i+1}: {res['area_m2']:.2f} m²")

if __name__ == "__main__":
    run_poc("house_plan.pdf")
