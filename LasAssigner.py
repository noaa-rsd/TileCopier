import os
from shutil import copyfile
import arcpy


def main():
    shp = arcpy.GetParameter(0)
    reviewer = arcpy.GetParameter(1)

    dir_from = arcpy.GetParameterAsText(2)
    dir_to = arcpy.GetParameterAsText(3)

    assigned_tiles = []
    with arcpy.da.SearchCursor("FL1806_Block_01_AOIs", ['reviewer', 'Tile_ID']) as tiles:
        for tile in tiles:
            if tile[0] == reviewer:
                assigned_tiles.append(tile)

    num_tiles = len(assigned_tiles)

    arcpy.AddMessage(shp)
    arcpy.AddMessage(r"{}, you've got {} tiles assigned to you.".format(reviewer, num_tiles))

    num_not_copied = 0

    for i, tile in enumerate(assigned_tiles, 1):
        las_name = tile[1] + '.las'
        tile_path_from = os.path.join(dir_from, las_name)
        tile_path_to = os.path.join(dir_to, las_name)
        arcpy.AddMessage('copying {} ({} of {})...'.format(tile[1], i, num_tiles))
        try:
            copyfile(tile_path_from, tile_path_to)
        except Exception as e:
            arcpy.AddError(e)
            num_not_copied += 1

    arcpy.AddMessage('{} of {} las files copied'.format(num_tiles - num_not_copied, num_tiles))

if __name__ == '__main__':
    main()
