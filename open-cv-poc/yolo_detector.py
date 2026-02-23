from ultralytics import YOLO
import os

class YOLODetector:
    def __init__(self, model_path=None):
        """
        Initializes the YOLO model. 
        If no path is provided, it uses a generic 'yolov8n.pt' for the POC.
        In production, we use the custom weights trained on CubiCasa5K/NZ plans.
        """
        self.model_path = model_path if model_path else "yolov8n.pt"
        self.model = YOLO(self.model_path)

    def detect_elements(self, image_path):
        """
        Detects walls, doors, windows, and room labels.
        Returns a structured list of detections.
        """
        print(f"Running YOLO Detection on {image_path}...")
        
        # This performs the inference. 
        # For the POC, this will look for standard COCO objects unless 
        # we have the custom weights.
        results = self.model(image_path)
        
        detections = []
        for result in results:
            for box in result.boxes:
                # box.cls: class index
                # box.xyxy: bounding box coordinates
                # box.conf: confidence score
                detections.append({
                    "class": result.names[int(box.cls)],
                    "coords": box.xyxy[0].tolist(),
                    "confidence": float(box.conf)
                })
        
        return detections

class RoomClassifier:
    """
    Categorizes the page or specific zones.
    """
    def classify_page(self, detections):
        """
        Logic: If we see many 'Wall' detections and 'Furniture', 
        it's likely a Floor Plan.
        """
        classes_found = [d['class'] for d in detections]
        
        if "wall" in classes_found or "door" in classes_found:
            return "FLOOR_PLAN"
        elif "roof" in classes_found:
            return "ROOF_PLAN"
        else:
            return "UNKNOWN_SECTION"

if __name__ == "__main__":
    # POC Usage
    detector = YOLODetector()
    # print(detector.detect_elements("output/pages/page_1.png"))
