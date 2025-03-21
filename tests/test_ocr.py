from src.ocr import extract_text_from_area

# Define the coordinates of the area to capture (e.g., top-left and bottom-right corners)
x1, y1, x2, y2 = 100, 100, 300, 200  # Example coordinates

# Extract text from the specified area
extracted_text = extract_text_from_area(x1, y1, x2, y2)

# Print the extracted text
print("Extracted Text:", extracted_text)