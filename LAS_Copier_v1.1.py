import os
from shutil import copyfile
import arcpy
import datetime
import subprocess


def run_console_cmd(cmd, las_tile):
    process = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    arcpy.AddMessage(output)
    error_msg = 'ERROR: Failed in getting valid license'
    error = error.strip().decode('utf-8')
    if error == error_msg:
        arcpy.AddWarning('{}|{}'.format(las_tile, error))
    return output, error


def create_las_pyramids(las_tile):
    exe = r'C:\Program Files\Common Files\LP360\LDPyramid.exe'
    thin_factor = 12
    cmd_str = '{} -f {} {}'.format(exe, thin_factor, las_tile)
    try:
        output, error = run_console_cmd(cmd_str, las_tile)
        if output == 'COMPLETE: Finished pyramiding all files.':
            return True
        else:
            return False
    except Exception as e:
         arcpy.AddMessage(e)
         return False


def main():
    shp = arcpy.GetParameter(0)
    reviewer = arcpy.GetParameter(1)

    dir_from = arcpy.GetParameterAsText(2)
    dir_to = arcpy.GetParameterAsText(3)
    to_pyramid = arcpy.GetParameter(4)

    assigned_tiles = []
    with arcpy.da.SearchCursor(shp, ['reviewer', 'Tile_ID']) as tiles:
        for tile in tiles:
            if tile[0] == reviewer:
                assigned_tiles.append(tile)

    num_tiles = len(assigned_tiles)

    arcpy.AddMessage(shp)
    arcpy.AddMessage(r"{}, you've got {} tiles assigned to you.".format(reviewer, num_tiles))

    num_not_copied = 0
    no_pyramids = []

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

            if to_pyramid:
                las_status = 'pyramiding {} ({} of {})'.format(las_name, i, num_tiles)
                arcpy.SetProgressorLabel('{}\n{} ({})'.format(las_status, time_status, mean_dt_status))
                created_pyramid = create_las_pyramids(tile_path_to)

                if not created_pyramid:
                    no_pyramids.append(tile_path_to)

            if i > 5:
                mean_dt = (datetime.datetime.now() - tic) / i
                time_remaining = mean_dt * (num_tiles - i)

        except Exception as e:
            arcpy.AddError(e)
            num_not_copied += 1

    arcpy.AddMessage('{} of {} las files copied'.format(num_tiles - num_not_copied, num_tiles))

    if no_pyramids:
        arcpy.AddWarning('Pyramids for the following {} Las tiles were not generated:'.format(len(no_pyramids)))
        for tile in no_pyramids:
            arcpy.AddMessage(tile)

    arcpy.ResetProgressor()


if __name__ == '__main__':
    main()
