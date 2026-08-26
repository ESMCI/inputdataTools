# inputdataTools
Tools used for publishing CESM input data.

## Process to publish data
1. Place your datafile(s) in `/glade/campaign/cesm/cesmdata/inputdata/` (`$CESMDATAROOT`) following the input data naming conventions (see below).
2. When you have tested on derecho and are ready to share the new file(s) publically, run the `rimport` script. This will ask you for a password and 2FA login before it can copy the files from this "input data" directory" to the "publication" or "staging" directory. (This authentication should be possible for any member of the `cseg` group.)
3. Once that's done, `rimport` will replace the original with a link to the copy.
4. Sometime in the next 24 hours, your file should be uploaded to the GDEX server and available for download during CESM runs.

Notes:
- Use `rimport --check` if you'd like to see the current status of a file, including whether it's available for download.
- The `relink.py` script was previously used for step 3 above, but that functionality is now built into `rimport`. It's still there if you want to use it by itself.
- A relative filename passed to `rimport` directly (via `--file` or as a positional argument) is always resolved against your current directory — never against the inputdata root, and it doesn't matter whether you're running from inside or outside the inputdata tree. Pass an absolute path if you want to name a file without regard to your current directory.
- A relative entry in a `--list` file is always resolved against that list file's own directory — again never against the inputdata root, wherever the list file itself lives. Pass absolute entries in the list if you want them independent of the list file's location.
- Before staging anything, `rimport` validates every file it's about to process (all `--file`/`--list`/positional entries together). If any of them fail — missing, a directory, a broken symlink, outside the inputdata root, etc. — none of them are touched, and every failing path is reported at once so you can fix them all in one pass. This is a promise about rejected input, not about success: pre-flight passing doesn't guarantee the whole batch will finish, since a file can still fail later for a reason pre-flight can't see (e.g. a runtime/relink failure partway through).
- `--check` is gated by the same pre-flight validation as a real run: if any file in the batch fails validation, `rimport` reports the failures and exits without checking (or reporting on) any of the other files. This is deliberate, not a bug — fix the bad entries and re-run to see the rest.
- Exit codes: `0` means everything succeeded (or, under `--check`, everything checked cleanly); `2` means the run was rejected before touching anything (bad arguments, a missing/empty list file, or a pre-flight validation failure); `1` means pre-flight passed but something failed for real while actually being staged or relinked.

## Filenames and metadata:

There is a good description of metadata that should be included in inputdata files here:  https://www.cesm.ucar.edu/models/cam/metadata

Filenames should be descriptive and should contain the date the file was created. Other information in the filename is also useful to keep as shown in the list below. Files published in inputdata should never be overwritten.

Replacement files should be different at least by creation date. Files that come from CESM simualtions should normally follow the output naming conventions from https://www.cesm.ucar.edu/models/cesm2/naming-conventions#modelOutputFilenames

Files should be placed under the appropriate directory for the component it's used or applicable for (so under `lnd/clm2/` for data that applies to the CLM/CTSM land model). Subdirectories under those levels should be used to seperate data by general types as needed for that component.

Some suggestions on things to include in the filename:
- Spatial resolution of the gridded data
- Year (or years) for which the data was observed or applicable to
- Institution or project source of the data
- Creation date in the form of `_cMMDDYY.nc`
- CESM casename that was used to create the data (also simulation date for it) (see output file naming conventions above)
- Things needed to distinquish it from other similar input files (e.g., number of vertical levels, land mask, number of Plant Functional Types, etc.)
