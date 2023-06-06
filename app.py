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

def apply_formula(image):
        formula = "exp(-2*image/1-image)"
        ndvi = image.select('NDVI')
        new_ndvi = ndvi.expression(formula, {"image": ndvi})
        return image.addBands(new_ndvi.rename('New_NDVI'))

# Define a function to calculate NDVI
def calculate_ndvi(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return image.addBands(ndvi)
    
def get_values_from_descriptions(descriptions, class_list):
    values = []
    for description in descriptions:
        for item in class_list:
            if item['description'] == description:
                values.append(item['value'])
                break
    return values

def ls(aoi):
    # Load a digital elevation model (DEM) as an example
    dem = ee.Image("USGS/SRTMGL1_003")
    # Calculate the slope in radians
    slope_rad = ee.Terrain.slope(dem).multiply(3.14159 / 180.0)
    # Calculate the LS factor using the formula
    ls = slope_rad.tan().divide(0.0896).pow(1.097)
    return ls

def Factor_r(aoi,start_date,end_date):
    # Load the Sentinel-2 image collection
    collection = ee.ImageCollection('COPERNICUS/S2')


    # Create a list of month start dates
    months = ee.List.sequence(1, 12)

    # Filter the collection and calculate NDVI for each month
    ndvi_collection = months.map(lambda month: 
                                 calculate_ndvi(collection
                                                .filterDate(start_date.format(month), end_date.format(month))
                                                .filterBounds(aoi)
                                                .mean()))

    # Convert the collection to an ImageCollection
    ndvi_collection = ee.ImageCollection(ndvi_collection)

    # Select the NDVI band from the collection
    ndvi = ndvi_collection.select('NDVI')
    
    # Apply the formula to every image in the collection
    new_collection = ndvi_collection.map(apply_formula)

    # Calculate the mean of the new collection
    factor_c = new_collection.select('New_NDVI').mean().float()
    return factor_c




def Factor_c(aoi,start_date,end_date):
    # Load the precipitation image collection
    collection = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .select("precipitation") \
        .filterDate(start_date, end_date)

    # Calculate the sum of precipitation within the date range
    precipitation_sum = collection.sum()

    # Modify the expression to match Earth Engine syntax
    expression = "(precipitation < 850) ? (0.0483 * (precipitation ** 1.610)) : (587.8 - 1.219 * precipitation + 0.004105 * (precipitation ** 2))"
    
    # Create a new image from the expression
    new_image = precipitation_sum.expression(expression, {"precipitation": precipitation_sum}).divide(10)

    return new_image

def Factor_k(aoi):
    soil_texture = ee.Image('OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02')
    classes = [
        {'value': 1, 'color': '#d5c36b', 'description': 'Cl'},
        {'value': 2, 'color': '#b96947', 'description': 'SiCl'},
        {'value': 3, 'color': '#9d3706', 'description': 'SaCl'},
        {'value': 4, 'color': '#ae868f', 'description': 'ClLo'},
        {'value': 5, 'color': '#f86714', 'description': 'SiClLo'},
        {'value': 6, 'color': '#46d143', 'description': 'SaClLo'},
        {'value': 7, 'color': '#368f20', 'description': 'Lo'},
        {'value': 8, 'color': '#3e5a14', 'description': 'SiLo'},
        {'value': 9, 'color': '#ffd557', 'description': 'SaLo'},
        {'value': 10, 'color': '#fff72e', 'description': 'Si'},
        {'value': 11, 'color': '#ff5a9d', 'description': 'LoSa'},
        {'value': 12, 'color': '#ff005b', 'description': 'Sa'}
    ]

    descriptions = ['Sa', 'LoSa', 'SaCl', 'ClLo', 'SiClLo', 'SaClLo', 'Cl', 'SiCl', 'Lo', 'Si', 'SaLo', 'SiLo']
    texture_classes = get_values_from_descriptions(descriptions, classes)


    # Define the corresponding K factor values
    K_factor_values = [0.12, 0.18, 0.276, 0.25, 0.281, 0.1, 0.05, 0.055, 0.155, 0.08, 0.06,0.3]

    # Remap the soil texture image to the K factor values
    k_factor_image = soil_texture.remap(texture_classes, K_factor_values)

    return k_factor_image
    

def ls(aoi):
    # Load a digital elevation model (DEM) as an example
    dem = ee.Image("USGS/SRTMGL1_003")
    # Calculate the slope in radians
    slope_rad = ee.Terrain.slope(dem).multiply(3.14159 / 180.0)
    # Calculate the LS factor using the formula
    ls = slope_rad.tan().divide(0.0896).pow(1.097)
    return ls
def ruslee(aoi,start_date,end_date):
    constant = 0.9
    image_ls=ls(aoi)
    image_c=Factor_c(aoi,start_date,end_date)
    image_r=Factor_r(aoi,start_date,end_date)
    image_k=Factor_k(aoi)

    # Multiply the images and the constant
    rusel = image_ls.multiply(image_c).multiply(image_k).multiply(image_r).multiply(0.9).clip(aoi)
    return rusel

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




app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/2018')
def index2018():
    return render_template('2018.html')

@app.route('/2019')
def index2019():
    return render_template('2019.html')

@app.route('/2050')
def index2050():
    return render_template('2050.html')

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
    # Download the TIFF image from the Google Drive link
    geoJSON={
    "type": "FeatureCollection",
    "features": [
        {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "coordinates": [
            [
                [
                -1.1707247623846513,
                31.900522645249836
                ],
                [
                -1.1707247623846513,
                36.01296943222077
                ],
                [
                -9.23660848613946,
                36.01296943222077
                ],
                [
                -9.23660848613946,
                31.900522645249836
                ],
                [
                -1.1707247623846513,
                31.900522645249836
                ]
            ]
            ],
            "type": "Polygon"
        }
        }
    ]
    }
    coords = geoJSON['features'][0]['geometry']['coordinates']
    aoi = ee.Geometry.Polygon(coords[0])

    # Add the topography layer to the map with the "terrain" palette
    palette_ls = ["#000000", "#0000FF", "#00FFFF", "#00FF00"] 
    my_map.addLayer(ls(aoi), {'min': 0, 'max': 1, 'palette': palette_ls}, 'LS')

    # Add the topography layer to the map with the "R" palette
    palette_r = ['0000FF', '00FF00', 'FF0000']  # Replace with your desired colors
    
    start_date='2018-01-01'
    end_date='2018-12-31'

    my_map.addLayer(Factor_r(aoi,start_date,end_date), {'min': 0, 'max': 100, 'palette': palette_r}, "R")

    # Add the topography layer to the map with the "R" palette
    palette_c = ["#FFFFFF", "#D9E6FF", "#A6C8FF", "#73AAFF", "#408CFF", "#0D6EFF", "#0058E6", "#003CB4", "#002782", "#001051"]  # Adjust the shades of blue as desired
    my_map.addLayer(Factor_c(aoi,start_date,end_date), {'min': 0, 'max': 2, 'palette': palette_c}, "C")

     # Add the topography layer to the map with the "R" palette
    palette_k = ["#FFFFFF", "#D9E6FF", "#A6C8FF", "#73AAFF", "#408CFF", "#0D6EFF", "#0058E6", "#003CB4", "#002782", "#001051"]  # Adjust the shades of blue as desired
    my_map.addLayer(Factor_k(aoi), {'palette': palette_k}, "K")

     # Add the topography layer to the map with the "R" palette
    palette_ru = ["#FFFFFF", "#FFD9D9", "#FFA6A6", "#FF7373", "#FF4040", "#FF0D0D", "#E60000", "#B40000", "#820000", "#510000"]  # Adjust the shades of red as desired
    my_map.addLayer(ruslee(aoi,start_date,end_date), {'min': 0, 'max': 200,'palette': palette_ru}, "RUSELE")

    


    url = 'https://www.zupimages.net/up/22/39/h8au.png'
    FloatImage(url, bottom=10, left=20).add_to(my_map)
    folium.LayerControl().add_to(my_map)
    # Add EE drawing method to folium.
    folium.Map.add_ee_layer = add_ee_layer
    # TIFF image link
    
    my_map.save('templates/yourmap2018.html')
    print("hello")
    return render_template('index.html')



if __name__ == '__main__':
    app.run(debug=True)