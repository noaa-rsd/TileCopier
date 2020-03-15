import os
from shutil import copyfile
import arcpy
import datetime
import subprocess
import collections


class TileCopier:

    def __init__(self):
        self.shp = arcpy.GetParameter(0)
        self.reviewer = arcpy.GetParameter(1)
        self.las_from = arcpy.GetParameterAsText(2)
        self.las_to = arcpy.GetParameterAsText(3)
        self.to_pyramid = arcpy.GetParameter(4)
        self.thin_factor = arcpy.GetParameter(5)
        self.lp360_path = arcpy.GetParameterAsText(6)
        self.dem_from = arcpy.GetParameterAsText(7)
        self.dem_to = arcpy.GetParameterAsText(8)

        self.shp_srs = arcpy.Describe(self.shp).spatialReference
        self.export_tile_fields = collections.OrderedDict([
            ('reviewer', 'TEXT'), 
            ('tile_id', 'TEXT'), 
            ('las_name', 'TEXT'), 
            ('las_from', 'TEXT'), 
            ('las_to', 'TEXT'), 
            ('las_copied', 'TEXT'), 
            ('pyramid', 'TEXT'),
            ('dem_name', 'TEXT'), 
            ('dem_from', 'TEXT'), 
            ('dem_to', 'TEXT'), 
            ('dem_copied', 'TEXT')
            ])
        self.tile = None
        self.created_pyramid = False
        self.las_copied = False  # default, change if copied
        self.dem_copied = False  # default, change if copied

    def set_current_tile(self, tile, i):
        self.oid = i
        self.tile_geom = tile[0]
        self.reviewer = tile[1]
        self.tile_id = tile[2]
        self.las_name = tile[3] + '.las'
        self.dem_name = tile[4] + '.img'

    def get_tiles(self):
        assigned_tiles = []
        fields = ['SHAPE@WKT', 'reviewer', 'Tile_ID', 'LAS_Name', 'DEM_Name']
        with arcpy.da.SearchCursor(self.shp, fields) as tiles:
            for tile in tiles:
                if tile[1] == self.reviewer:
                    assigned_tiles.append(tile)

        num_tiles = len(assigned_tiles)
        arcpy.AddMessage(r"{}, you've got {} tiles assigned to you.".format(self.reviewer, num_tiles))
        return assigned_tiles, num_tiles

    def create_copied_tile_status_shp(self):
        shp_processed_dir = os.path.dirname(self.shp.value)
        shp_processed_name = os.path.basename(self.shp.value).replace('.shp', '_TileCopierResults.shp')
        arcpy.CreateFeatureclass_management(shp_processed_dir, 
                                            shp_processed_name,
                                            spatial_reference=self.shp_srs)

        shp_processed_path = os.path.join(shp_processed_dir, shp_processed_name)
        for field, dtype in self.export_tile_fields.items():
            arcpy.AddField_management(shp_processed_path, field, dtype)

        insert_cursor_fields = ['SHAPE@', 'OID@'] + list(self.export_tile_fields.keys())
        self.tile_cursor = arcpy.da.InsertCursor(shp_processed_path, insert_cursor_fields)

    @staticmethod
    def run_console_cmd(cmd, las_tile):
        process = subprocess.Popen(cmd.split('|'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        return output, error
    
    @staticmethod
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
 
    def copy_las(self):
        las_path_from = os.path.join(self.las_from, self.las_name)
        las_path_to = os.path.join(self.las_to, self.las_name)
        try:
            if self.las_from and self.las_to:
                copyfile(las_path_from, las_path_to)
                self.las_copied = True
                if self.to_pyramid:
                    tile_status = 'pyramiding {} ({} of {})'.format(las_name, i, num_tiles)
                    arcpy.SetProgressorLabel(tile_status)
                    self.created_pyramid = create_las_pyramids(thin_factor, las_path_to, lp360_path)
        except Exception as e:
            arcpy.AddError(e)

    def copy_dem(self):
        dem_path_from = os.path.join(self.dem_from, self.dem_name)
        dem_path_to = os.path.join(self.dem_to, self.dem_name)
        try:
            if self.dem_from and self.dem_to:
                copyfile(dem_path_from, dem_path_to)
                self.dem_copied = True
        except Exception as e:
            arcpy.AddError(e)

    def update_status_shp(self):
        tile_data = (arcpy.FromWKT(self.tile_geom, self.shp_srs), 
                     self.oid, self.reviewer, self.tile_id, 
                     self.las_name, self.las_from, self.las_to, 
                     str(self.las_copied), str(self.created_pyramid), 
                     self.dem_name, self.dem_from, self.dem_to, 
                     str(self.dem_copied))
        self.tile_cursor.insertRow(tile_data)


def main():
    tile_copier = TileCopier()
    assigned_tiles, num_tiles = tile_copier.get_tiles()
    tile_copier.create_copied_tile_status_shp()
    arcpy.SetProgressor("step", "Copying tile data...", 0, num_tiles, 1)

    for i, tile in enumerate(assigned_tiles, 1):
        tile_copier.set_current_tile(tile, i)
        tile_status = 'tile {} ({} of {})'.format(tile_copier.tile_id, i, num_tiles)
        arcpy.SetProgressorLabel(tile_status)

        tile_copier.copy_las()
        tile_copier.copy_dem()

        arcpy.SetProgressorPosition()
        tile_copier.update_status_shp()

    del tile_copier.tile_cursor
    arcpy.ResetProgressor()


if __name__ == '__main__':
    main()
