# inputdataTools
rimport used for publishing inputdata
relink.py used to remove files from $CESMDATAROOT and replace with links.

Process to publish data:
The first step is to place your datafile(s) in /glade/campaign/cesm/cesmdata/inputdata following the inputdata naming convention.
When you have tested on derecho and are ready to share the new file(s) publically:

As user cesmdata run the rimport script.  This requires a 2FA login, everyone in cseg should have access to the account, you will need to
contact cislhelp and request access if you are new to the group.

As owner of the files in /glade/campaign/cesm/cesmdata/inputdata run script relink.py, this will remove the files from /glade/campaign/cesm/cesmdata/inputdata
and replace them with links to the published data location.  /glade/campaign/cesm/cesmdata/inputdata
