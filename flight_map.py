def create_flight_map(origin, destination, file_name):
    import staticmaps

    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    origin = staticmaps.create_latlng(origin[0], origin[1])
    destination = staticmaps.create_latlng(destination[0], destination[1])


    context.add_object(staticmaps.Line([destination, origin], color=staticmaps.BLUE, width=4))
    context.add_object(staticmaps.ImageMarker(destination, "ac.png", origin_x=37, origin_y=37))
    context.add_object(staticmaps.Marker(origin, color=staticmaps.RED, size=12))


    # render anti-aliased png (this only works if pycairo is installed)
    image = context.render_cairo(1080, 1080)
    image.write_to_png(file_name)


def test_map():
    origin = (50.110644, 8.682092)
    destination = (40.712728, -74.006015)

    create_flight_map(origin, destination, "test_map.png")

#test_map()