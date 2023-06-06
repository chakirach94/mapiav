from flask import Flask, render_template
import folium
from folium.plugins import FloatImage
from folium import plugins
import geemap.foliumap as geemap
from folium.plugins import FloatImage
import numpy as np
from folium import plugins
from folium.plugins import HeatMap
import ee

def getNLCD(year):
    # Import the NLCD collection.
    dataset = ee.ImageCollection("USGS/NLCD_RELEASES/2019_REL/NLCD")

    # Filter the collection by year.
    nlcd = dataset.filter(ee.Filter.eq("system:index", year)).first()

    # Select the land cover band.
    landcover = nlcd.select("landcover")
    return landcover

def getNDVI(year):
    # Import the NLCD collection.
    dataset = ee.ImageCollection("MODIS/MOD09GA_006_NDVI")

    # Filter the collection by year.
    ndvi = dataset.max()

    # Select the land cover band.
    myndvi = ndvi.select('NDVI')
    return myndvi

# Define a method for displaying Earth Engine image tiles on a folium map.
def add_ee_layer(self, ee_object, vis_params, name):
    
    try:    
        # display ee.Image()
        if isinstance(ee_object, ee.image.Image):    
            map_id_dict = ee.Image(ee_object).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
            ).add_to(self)

        # display ee.ImageCollection()
        elif isinstance(ee_object, ee.imagecollection.ImageCollection):    
            ee_object_new = ee_object.mosaic()
            map_id_dict = ee.Image(ee_object_new).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
            ).add_to(self)

        # display ee.Geometry()
        elif isinstance(ee_object, ee.geometry.Geometry):    
            folium.GeoJson(
            data = ee_object.getInfo(),
            name = name,
            overlay = True,
            control = True
        ).add_to(self)

        # display ee.FeatureCollection()
        elif isinstance(ee_object, ee.featurecollection.FeatureCollection):  
            ee_object_new = ee.Image().paint(ee_object, 0, 2)
            map_id_dict = ee.Image(ee_object_new).getMapId(vis_params)
            folium.raster_layers.TileLayer(
            tiles = map_id_dict['tile_fetcher'].url_format,
            attr = 'Google Earth Engine',
            name = name,
            overlay = True,
            control = True
        ).add_to(self)
    
    except:
        print("Could not display {}".format(name))


# Add EE drawing method to folium.
folium.Map.add_ee_layer = add_ee_layer


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/map')
def map():
    my_map=geemap.Map(
            basemap="HYBRID",
            plugin_Draw=False,
            Draw_export=False,
            locate_control=False,
            plugin_LatLngPopup=False,
        )

        

    # Add custom base maps to folium
    basemaps = {
        'Google Maps': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Maps',
            overlay = True,
            control = True
        ),
        'Google Satellite': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Google Terrain': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Terrain',
            overlay = True,
            control = True
        ),
        'Google Satellite Hybrid': folium.TileLayer(
            tiles = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ),
        'Esri Satellite': folium.TileLayer(
            tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr = 'Esri',
            name = 'Esri Satellite',
            overlay = True,
            control = True
        )
    }

    # Add custom basemaps
    basemaps['Google Satellite Hybrid'].add_to(my_map)
    
    data = (
    np.random.normal(size=(100, 3)) *
    np.array([[1, 1, 1]]) +
    np.array([[48, 5, 1]])
).tolist()
    #fullscreen
    plugins.Fullscreen().add_to(my_map)
    HeatMap(data).add_to(folium.FeatureGroup(name='Heat Map').add_to(my_map))

    year="2013"
    my_map.addLayer(getNLCD(year), {}, "NLCD " + year)
    """my_map.addLayer(getNLCD(year), {}, "getjrc " + year)"""
    legend_dict = {
    '11 Open Water': '466b9f',
    '12 Perennial Ice/Snow': 'd1def8',
    '21 Developed, Open Space': 'dec5c5',
    '22 Developed, Low Intensity': 'd99282',
    '23 Developed, Medium Intensity': 'eb0000',
    '24 Developed High Intensity': 'ab0000',
    '31 Barren Land (Rock/Sand/Clay)': 'b3ac9f',
    '41 Deciduous Forest': '68ab5f',
    '42 Evergreen Forest': '1c5f2c',
    '43 Mixed Forest': 'b5c58f',
    '51 Dwarf Scrub': 'af963c',
    '52 Shrub/Scrub': 'ccb879',
    '71 Grassland/Herbaceous': 'dfdfc2',
    '72 Sedge/Herbaceous': 'd1d182',
    '73 Lichens': 'a3cc51',
    '74 Moss': '82ba9e',
    '81 Pasture/Hay': 'dcd939',
    '82 Cultivated Crops': 'ab6c28',
    '90 Woody Wetlands': 'b8d9eb',
    '95 Emergent Herbaceous Wetlands': '6c9fb8',
}
    year="2013"
    my_map.addLayer(getNDVI(year), {}, "NDVI " + year)


    url = 'https://www.zupimages.net/up/22/39/h8au.png'
    FloatImage(url, bottom=10, left=20).add_to(my_map)
    folium.LayerControl().add_to(my_map)
    my_map.save('templates/yourmap.html')

    return render_template('index.html')



if __name__ == '__main__':
    app.run(debug=True)