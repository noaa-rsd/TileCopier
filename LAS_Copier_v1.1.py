import os
from shutil import copyfile
import pandas as pd
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

        self.source_fields = ['SHAPE@WKT', 
                              'reviewer', 
                              'Tile_ID', 
                              'LAS_Name', 
                              'DEM_Name']

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

        self.assigned_tiles = []
        self.copied_tiles = []
        self.num_tiles = 0
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

    def get_assigned_tiles(self):
        with arcpy.da.SearchCursor(self.shp, self.source_fields) as tiles:
            for tile in tiles:
                if tile[1] == self.reviewer:
                    self.assigned_tiles.append(tile)

        self.num_tiles = len(self.assigned_tiles)
        arcpy.AddMessage(r"{} has {} assigned tiles".format(self.reviewer, self.num_tiles))

    def create_results_shp(self):
        shp_processed_dir = os.path.dirname(self.shp.value)
        shp_basename = os.path.basename(self.shp.value)
        shp_processed_name = shp_basename.replace('.shp', '_TileCopierResults.shp')

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
        process = subprocess.Popen(cmd.split('|'), stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, shell=True)
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
                    arcpy.AddMessage('pyramiding...')
                    self.created_pyramid = create_las_pyramids(thin_factor, 
                                                               las_path_to, 
                                                               lp360_path)
        except Exception as e:
            arcpy.AddMessage(e)
            self.las_copied = False

    def copy_dem(self):
        dem_path_from = os.path.join(self.dem_from, self.dem_name)
        dem_path_to = os.path.join(self.dem_to, self.dem_name)
        try:
            if self.dem_from and self.dem_to:
                copyfile(dem_path_from, dem_path_to)
                self.dem_copied = True
        except Exception as e:
            arcpy.AddMessage(e)
            self.dem_copied = False

    def update_status_shp(self):
        tile_data = (arcpy.FromWKT(self.tile_geom, self.shp_srs), 
                     self.oid, self.reviewer, self.tile_id, 
                     self.las_name, self.las_from, self.las_to, 
                     self.las_copied, self.created_pyramid, 
                     self.dem_name, self.dem_from, self.dem_to, 
                     self.dem_copied)

        self.tile_cursor.insertRow(tile_data)
        self.copied_tiles.append(tile_data[2:])  # don't add wkt or oid to pandas df

    def summary(self):
        df = pd.DataFrame(self.copied_tiles, columns=self.export_tile_fields)
        num_las_copied = (df['las_copied'].astype('bool').sum())
        num_dem_copied = (df['dem_copied'].astype('bool').sum())
        arcpy.AddMessage('-------------------- SUMMARY --------------------')
        arcpy.AddMessage(r'Number of Assigned Tiles:    {}'.format(self.num_tiles))
        arcpy.AddMessage(r'Number of Copied LAS files:  {}'.format(num_las_copied))
        arcpy.AddMessage(r'Number of Copied DEM files:  {}'.format(num_dem_copied))


def main():
    tile_copier = TileCopier()
    tile_copier.get_assigned_tiles()
    tile_copier.create_results_shp()

    for i, tile in enumerate(tile_copier.assigned_tiles, 1):
        tile_copier.set_current_tile(tile, i)
        tile_status = 'copying data from tile {} ({} of {})'.format(
            tile_copier.tile_id, i, tile_copier.num_tiles)
        arcpy.AddMessage(tile_status)

        tile_copier.copy_las()
        tile_copier.copy_dem()
        tile_copier.update_status_shp()

    del tile_copier.tile_cursor


if __name__ == '__main__':
    main()
