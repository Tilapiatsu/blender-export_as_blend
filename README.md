# Export as Blend for Blender

### Description
This addon allow you to export data to a new blend file.
Usually we would neeed to create a new Blend file first then Link or Append data from the file you want the data from.
With this addon **you can just export objects dirrectly from the file you have the data into**.

This addon works with objects or scene only at the moment. 

*It has been tested with Blender 3.1.2 on Windows 11*

***
### Usage
1- Install and enable the Addon like any regular Addons in `Edit` > `Preferences`,

2- Then you can select one or more objects and go to `File` > `Export` > `Export as Blend (.blend)`

3- In the export dialog you have many options in the `n` pannel

| Setting | Description |
|-----------:|-----------|
|**source**| let you choose what to export : `Selected Objects` only export current object selection, `Current Scene` will export the entire current scene.|
|**mode**|`Append` will append data to the exported blend file , and `Link` will Link data to the exported blend file.|
|**Pack External Data**| Any external data will be written into Blend file ( Textures etc...). It will drastically increase saving time and file size, but make the file easier to transfer.|
|**Export to Clean File**|If enable, the data will be exported to a clean file without any data except from your source objects. Otherwise the data will be exported in a scene with your Startup file as a starting point that can contain many data depending on your configuration.|
|**Create Collection Hierarchy**| The collection hierarchy of the selected objects will be recreated in the exported file. If disable, all objects will be exported in the root collection.|
|**Export objects in root collection**|If enable everything will be place under a collection named defined by `Root collection Name`|
|**Root Collection name**|Name of the collection |
|**Export dependencies in dedicated collection**| If enable any object dependencies will be exported in a collection named "Dependencies". Otherwise, the collection hierarchy will be recreated for each dependencies. ( An object dependency is any data neeeded for the selected objects to be evaluated correctly. For exemple, an object that is used in the modifier or a driver used in by the exported object. ) |
|**Open Exported Blend**| After export, the file is exported.|


### Feedback
***
Feel free to send me feedback or to report any issues or bugs if you found one.