import fitz  # PyMuPDF
import os
from PIL import Image

class PDFProcessor:
    def __init__(self, output_dir="output/pages"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def convert_pdf_to_images(self, pdf_path, dpi=300):
        """Converts each page of a PDF to a high-res image."""
        print(f"Converting {pdf_path} to images...")
        doc = fitz.open(pdf_path)
        image_paths = []

        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            img_path = os.path.join(self.output_dir, f"page_{i+1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
            print(f"Saved: {img_path}")

        return image_paths

if __name__ == "__main__":
    # Example usage
    processor = PDFProcessor()
    # processor.convert_pdf_to_images("sample_plan.pdf")
