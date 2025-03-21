from src.overlay import ScreenOverlay

# Create an instance of the ScreenOverlay class
overlay = ScreenOverlay()

# Start the overlay and wait for the user to select an area
overlay.start()

# Get the coordinates of the selected rectangle
coordinates = overlay.get_selection_coordinates()
print("Selected Area Coordinates:", coordinates)