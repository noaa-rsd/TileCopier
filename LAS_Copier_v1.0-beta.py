import os
from shutil import copyfile
import arcpy
import datetime


def main():
    shp = arcpy.GetParameter(0)
    reviewer = arcpy.GetParameter(1)

    dir_from = arcpy.GetParameterAsText(2)
    dir_to = arcpy.GetParameterAsText(3)

    assigned_tiles = []
    with arcpy.da.SearchCursor(shp, ['reviewer', 'Tile_ID']) as tiles:
        for tile in tiles:
            if tile[0] == reviewer:
                assigned_tiles.append(tile)

    num_tiles = len(assigned_tiles)

    arcpy.AddMessage(shp)
    arcpy.AddMessage(r"{}, you've got {} tiles assigned to you.".format(reviewer, num_tiles))

    num_not_copied = 0

    arcpy.SetProgressor("step", "Copying LAS files...", 0, num_tiles, 1)

    mean_dt = '?'
    time_remaining = 'calculating initial guess...'
    las_status = None
    time_status = None
    tic = datetime.datetime.now()

    for i, tile in enumerate(assigned_tiles, 1):
        las_name = tile[1] + '.las'
        tile_path_from = os.path.join(dir_from, las_name)
        tile_path_to = os.path.join(dir_to, las_name)
        
        try:
            las_status = 'copying {} ({} of {})'.format(las_name, i, num_tiles)
            time_status = 'Est. Time Remaining: {}'.format(str(time_remaining).split('.')[0])
            mean_dt_status = 'Mean Time per LAS: {}'.format(str(mean_dt).split('.')[0])

            arcpy.SetProgressorLabel('{}\n{} ({})'.format(las_status, time_status, mean_dt_status))
            copyfile(tile_path_from, tile_path_to)
            arcpy.SetProgressorPosition()

            if i > 5:
                mean_dt = (datetime.datetime.now() - tic) / i
                time_remaining = mean_dt * (num_tiles - i)

        except Exception as e:
            arcpy.AddError(e)
            num_not_copied += 1

    arcpy.AddMessage('{} of {} las files copied'.format(num_tiles - num_not_copied, num_tiles))

    arcpy.ResetProgressor()

if __name__ == '__main__':
    main()
