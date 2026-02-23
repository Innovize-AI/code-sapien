import cv2
import numpy as np

class MeasurementEngine:
    def __init__(self, pixel_to_mm_ratio=None):
        self.pixel_to_mm_ratio = pixel_to_mm_ratio

    def set_scale(self, known_distance_mm, pixel_length):
        """Calibrates the engine based on a known distance (e.g., scale bar)."""
        self.pixel_to_mm_ratio = known_distance_mm / pixel_length
        print(f"Scale calibrated: 1px = {self.pixel_to_mm_ratio:.2f}mm")

    def measure_line(self, p1, p2):
        """Measures the real-world distance between two points (x, y)."""
        if not self.pixel_to_mm_ratio:
            raise ValueError("Scale not calibrated. Call set_scale first.")
        
        pixel_dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        return pixel_dist * self.pixel_to_mm_ratio

    def detect_and_measure_contours(self, image_path):
        """POC: Detects simple shapes and calculates their area."""
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        for cnt in contours:
            area_px = cv2.contourArea(cnt)
            if area_px > 1000:  # Filter noise
                real_area_m2 = (area_px * (self.pixel_to_mm_ratio**2)) / 1_000_000
                results.append({
                    "contour": cnt,
                    "area_px": area_px,
                    "area_m2": real_area_m2
                })
        
        return results

if __name__ == "__main__":
    # Example usage logic
    engine = MeasurementEngine()
    engine.set_scale(1000, 100) # 1000mm = 100px
    print(f"500px distance = {engine.measure_line((0,0), (500,0))}mm")
