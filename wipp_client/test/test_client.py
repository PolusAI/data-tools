from wipp_client import Wipp, WippPlugin

w = Wipp()

# Search image collections
collections = w.search_image_collections("ratBrain")
for c in collections:
    print(c)

# Get list of images in the image collection
images = w.get_image_collections_images(collections[0].id)
for i in images:
    print(i)

# Search CSV collections
csv_collections = w.search_csv_collections("covid")
for csvc in csv_collections:
    print(csvc)

# Get list of CSV files in the CSV collection
w.get_csv_collections_csv_files(csv_collections[0].id)

# Crerate plugin object
plugin = {
  "name": "WIPP API Test",
  "version": "0.0.0",
  "containerId": "ktaletsk/noop",
  "title": "Test Plugin Created by Python WIPP API client 0.2.0",
  "description": "This plugin does nothing",
  "author": "Konstantin Taletskiy (konstantin.taletskiy@labshare.org)",
  "institution": "National Center for Advancing Translational Sciences, National Institutes of Health",
  "repository": "https://github.com/labshare/polus-plugins",
  "website": "",
  "citation": "",
  "inputs": [
    {
      "name": "inpImageDir",
      "description": "Input Image collection to make predictions on",
      "type": "collection",
      "required": True
    },
    {
      "name": "inpBaseDir",
      "description": "Input SplineDist Model that contains weights",
      "type": "genericData",
      "required": True
    },
    {
      "name": "imagePattern",
      "description": "Pattern of the images in Input",
      "type": "string",
      "required": False
    }
  ],
  "outputs": [
    {
      "name": "outDir",
      "description": "Output Directory for Predicted Images",
      "type": "genericData",
      "required": True
    }
  ],
  "ui": [
    {
      "key": "inputs.inpImageDir",
      "title": "Input Image Directory: ",
      "description": "Collection name that contains intensity based images"
    },
    {
      "key": "inputs.inpBaseDir",
      "title": "Model Directory: ",
      "description": "Directory containing the model weights and config file"
    },
    {
      "key": "inputs.imagePattern",
      "title": "Image Pattern: ",
      "description": "Pattern of images in input collection (image_r{rrr}_c{ccc}_z{zzz}.ome.tif). "
    }
  ]
}

wp = WippPlugin(plugin)
print(wp)

# Register plugin
np = w.create_plugin(wp)
print(np.id)

# Delete plugin
w.delete_plugin(np.id)