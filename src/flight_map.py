import staticmaps
from flight_static_maps.markers import get_shape_from_marker, generate_modded_sprite
from flight_static_maps.image_stream import save_image_to_stream

RENDER_SIZE = 1080
MARKER_SHAPE = "jet_swept"
MARKER_COLOR = "#000000"


def create_flight_map(origin: tuple, destination: tuple, file_name: str) -> None:
    """Create a flight route map image and save it as a PNG.

    Args:
        origin: (latitude, longitude) of the departure airport.
        destination: (latitude, longitude) of the arrival airport.
        file_name: Output PNG file path.
    """
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    origin_ll = staticmaps.create_latlng(origin[0], origin[1])
    destination_ll = staticmaps.create_latlng(destination[0], destination[1])

    flight_line = staticmaps.Line([destination_ll, origin_ll], color=staticmaps.BLUE, width=4)
    context.add_object(flight_line)

    heading = flight_line.calculate_final_bearing()
    shape_info = get_shape_from_marker([MARKER_SHAPE, 1])
    sprite_image = generate_modded_sprite(shape_info, MARKER_COLOR, heading)
    image_stream = save_image_to_stream(sprite_image)
    width, height = sprite_image.size
    context.add_object(
        staticmaps.ImageMarker(destination_ll, image_stream, origin_x=height // 2, origin_y=width // 2)
    )

    image = context.render_cairo(RENDER_SIZE, RENDER_SIZE)
    image.write_to_png(file_name)
