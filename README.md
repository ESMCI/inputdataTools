# inputdataTools
rimport used for publishing inputdata
relink.py used to remove files from $CESMDATAROOT and replace with links.

Process to publish data:
The first step is to place your datafile(s) in /glade/campaign/cesm/cesmdata/inputdata following the inputdata naming convention.
When you have tested on derecho and are ready to share the new file(s) publically:

As user cesmdata run the rimport script.  This requires a 2FA login, everyone in cseg should have access to the account, you will need to
contact cislhelp and request access if you are new to the group.

As owner of the files in /glade/campaign/cesm/cesmdata/inputdata run script relink.py, this will remove the files from /glade/campaign/cesm/cesmdata/inputdata
and replace them with links to the published data location.  /glade/campaign/collections/gdex/data/d651077/cesmdata/inputdata/

Filenames and metadata:

There is a good description of metadata that should be included in inputdata files here:  https://www.cesm.ucar.edu/models/cam/metadata

Filenames should be descriptive and should contain the date the file was created. Other information in the filename is also useful to keep as shown in the list below. Files published in inputdata should never be overwritten.
Replacement files should be different at least by creation date. Files that come from CESM simualtions should normally follow the output naming conventions from https://www.cesm.ucar.edu/models/cesm2/naming-conventions#modelOutputFilenames

Files should be placed under the appropriate directory for the component it's used or applicable for (so under lnd/clm2 for data that applies to the CLM/CTSM land model). Subdirectories under those levels should be used to seperate data by general types as needed for that component.

Some suggestions on things to include in the filename:
- Spatial resolution of the gridded data
- Year (or years) for which the data was observed or applicable to
- Institution or project source of the data
- Creation date in the form of _cMMDDYY.nc
- CESM casename that was used to create the data (also simulation date for it) (see output file naming conventions above)
- Things needed to distinquish it from other similar files in inputdata (i.e. things like number of vertical levels, land-mask, number of Plant Functional Types, etc.)
