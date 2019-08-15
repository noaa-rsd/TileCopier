import os
from shutil import copyfile
import arcpy
import datetime
import subprocess


def run_console_cmd(cmd, las_tile):
    process = subprocess.Popen(cmd.split('|'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output, error


def create_las_pyramids(thin_factor, las_tile, lp360_path):
    exe = r'{}\LDPyramid.exe'.format(lp360_path)
    cmd_str = '{}|-f|{}|{}'.format(exe, thin_factor, las_tile)

    try:
        output, error = run_console_cmd(cmd_str, las_tile)

        error_msg = 'ERROR: Failed in getting valid license'
        output_msg = 'COMPLETE: Finished pyramiding all files.'

        error = error.strip().decode('utf-8')
        output = output.strip().decode('utf-8')

        #arcpy.AddMessage(output)
        arcpy.AddMessage(error)

        if output == output_msg:
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
    thin_factor = arcpy.GetParameter(5)
    lp360_path = arcpy.GetParameterAsText(6)

    assigned_tiles = []
    with arcpy.da.SearchCursor(shp, ['reviewer', 'Tile_ID']) as tiles:
        for tile in tiles:
            if tile[0] == reviewer:
                assigned_tiles.append(tile)

    num_tiles = len(assigned_tiles)
    num_pyramids = 0

    arcpy.AddMessage(shp)
    arcpy.AddMessage(r"{}, you've got {} tiles assigned to you.".format(reviewer, num_tiles))

    num_copied_tiles = 0
    num_not_copied = 0

    tiles_not_pyramided = []

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
            num_copied_tiles += 1
            arcpy.SetProgressorPosition()

            if to_pyramid:
                las_status = 'pyramiding {} ({} of {})'.format(las_name, i, num_tiles)
                arcpy.SetProgressorLabel('{}\n{} ({})'.format(las_status, time_status, mean_dt_status))
                created_pyramid = create_las_pyramids(thin_factor, tile_path_to, lp360_path)
                num_pyramids += 1

                if not created_pyramid:
                    tiles_not_pyramided.append(tile_path_to)

            if i > 5:
                mean_dt = (datetime.datetime.now() - tic) / i
                time_remaining = mean_dt * (num_tiles - i)

        except Exception as e:
            arcpy.AddError(e)
            num_not_copied += 1

    arcpy.AddMessage('{} Summary {}'.format('-' * 20, '-' * 20))
    arcpy.AddMessage('{} of {} las files copied'.format(num_copied_tiles, num_tiles))

    if to_pyramid:
        arcpy.AddMessage('{} tiles pyramided'.format(num_pyramids))    

        if not tiles_not_pyramided:
            arcpy.AddWarning('Pyramids for the following {} Las tiles were not generated:'.format(len(tiles_not_pyramided)))
            for tile in tiles_not_pyramided:
                arcpy.AddMessage(tile)

    arcpy.ResetProgressor()


if __name__ == '__main__':
    main()
