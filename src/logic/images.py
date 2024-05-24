from io import BytesIO
import re
from PIL import Image, ImageDraw, ImageFont
import requests
import settings
from logic.utilities import hex_to_rgba
from database import DatabaseManager


def create_circle(size):
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask


def get_image(url: str):
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert('RGBA')


def get_image_db(db, id: str):
    with db.cursor() as cursor:
        cursor.execute("SELECT image FROM IMAGES WHERE id = %s", (id,))
        image = cursor.fetchone()
        return Image.open(BytesIO(image[0])).convert('RGBA')


def create_circle(diameter):
    """Create a circular mask."""
    mask = Image.new('L', (diameter, diameter), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, diameter, diameter), fill=255)
    return mask


def create_welcome_image(username, user_number, profile: Image.Image, background: Image.Image):
    mask = create_circle(profile.height)
    profile.putalpha(mask)

    # Create an orange circle image slightly larger than the profile picture
    frame_thickness = 10  # Adjust this value to change the thickness of the frame
    # Example orange color, replace with settings.DOURADINHOS_COLOR if needed
    orange_color = hex_to_rgba("#FFA500")
    orange_circle = Image.new(
        'RGBA', (profile.width + frame_thickness, profile.height + frame_thickness), orange_color)
    orange_mask = create_circle(profile.height + frame_thickness)
    orange_circle.putalpha(orange_mask)

    # Calculate the top-left position of the profile picture on the orange circle
    profile_top_left = (frame_thickness // 2, frame_thickness // 2)

    # Paste the profile picture onto the orange circle
    orange_circle.paste(profile, profile_top_left, profile)

    # Calculate the top-left position of the orange circle on the background
    top_left = (int((background.width - orange_circle.width) / 2), 10)

    # Paste the orange circle onto the background
    background.paste(orange_circle, top_left, orange_circle)

    # Add text to the image
    draw = ImageDraw.Draw(background)
    # Specify your font file and size
    font = ImageFont.truetype('fonts/Roboto-Bold.ttf', size=30)
    text1 = f"{username} just joined the server"
    text2 = f"Member #{user_number}"
    font_width, font_height = font.getsize(text1)
    font_width2, _ = font.getsize(text2)

    # # Calculate the position for the text to be centered
    position = ((background.width - font_width) / 2,
                top_left[1] + orange_circle.height + 60)
    position2 = ((background.width - font_width2) / 2,
                 top_left[1] + orange_circle.height + font_height + 60)
    draw.text(position, text1, font=font)
    draw.text(position2, text2, font=font)

    # Save the image to a BytesIO object
    image_bytes = BytesIO()
    background.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return image_bytes
