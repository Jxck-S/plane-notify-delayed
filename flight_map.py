def create_flight_map(origin, destination, file_name):
    import staticmaps
    from flight_static_maps.markers import get_shape_from_marker, generate_modded_sprite
    from flight_static_maps.image_stream import save_image_to_stream

    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    origin = staticmaps.create_latlng(origin[0], origin[1])
    destination = staticmaps.create_latlng(destination[0], destination[1])


 

    flight_line = staticmaps.Line([destination, origin], color=staticmaps.BLUE, width=4)
    context.add_object(flight_line)

    heading = flight_line.calculate_final_bearing()
    shape = ["jet_swept", 1]
    shape_info = get_shape_from_marker(shape)
    sprite_image = generate_modded_sprite(shape_info, "#000000", heading)
    image_stream = save_image_to_stream(sprite_image)
    width, height = sprite_image.size
    context.add_object(staticmaps.ImageMarker(destination, image_stream, origin_x=height/2, origin_y=width/2))


    # render anti-aliased png (this only works if pycairo is installed)
    image = context.render_cairo(1080, 1080)
    image.write_to_png(file_name)


def test_map():
    KAUS = (30.1945272,-97.6698761)
    KTIX = (28.5148056,-80.7992222)
    KJFK = (40.6399281,-73.7786922)
    origin = (50.110644, 8.682092)
    destination = (40.712728, -74.006015)

    create_flight_map(KTIX, KAUS, "test_map.png")

#test_map()