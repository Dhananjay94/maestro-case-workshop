"""Builds MotorClaims_Workshop_Participant_Kit.zip: only what an attendee needs (no build sources).
Usage: python make_participant_zip.py"""
import os
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
KIT = os.path.join(ROOT, "WorkshopKit")
OUT = os.path.join(ROOT, "MotorClaims_Workshop_Participant_Kit.zip")

START = """MOTOR CLAIMS WORKSHOP: START HERE

You need only a UiPath Community account. Nothing to install.

1. Open Studio Web and press Import (next to Create New).
   Choose the file  MotorClaimsWorkshop_Setup.uis  from this folder.
2. Open the solution MotorClaimsWorkshop_Setup, then the project SetupWorkshop.
   Press Debug. Set  Action = InstallWorkshop  and leave every other field empty.
   Wait for the result. The last line says Done and gives your Intake App address.
3. Follow the Setup guide: Setup_Guide.html (open it in a browser) or Setup_Guide.md. It covers connecting Gmail and
   Data Fabric, running Setup, and running Rahul's claim. The full build guide is in Guide/index.html.

If the screen looks stuck: run SetupWorkshop again with  Action = Status.
Sample customer documents: Sample_Documents/   Claim values for the Intake App: claims_intake_values.csv
"""

FILES = [
    (os.path.join(KIT, "Starter_Solution", "MotorClaimsWorkshop_Setup.uis"), "MotorClaimsWorkshop_Setup.uis"),
    (os.path.join(KIT, "Setup_Guide.md"), "Setup_Guide.md"),
    (os.path.join(KIT, "Guide_Site", "Setup_Guide.html"), "Setup_Guide.html"),
    (os.path.join(KIT, "Participant_Build_Guide.md"), "Participant_Build_Guide.md"),
    (os.path.join(KIT, "01_Data", "claims_intake_values.csv"), "claims_intake_values.csv"),
]
TREES = [(os.path.join(KIT, "Guide_Site"), "Guide"), (os.path.join(KIT, "02_Documents"), "Sample_Documents")]

if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("START_HERE.txt", START)
    for src, arc in FILES:
        z.write(src, arc)
    for base, arc_root in TREES:
        for root, _, files in os.walk(base):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.join(arc_root, os.path.relpath(full, base)).replace(os.sep, "/"))
with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
print(f"{os.path.basename(OUT)}: {len(names)} files, {os.path.getsize(OUT)//1024} KB")
for n in names[:14]:
    print("  ", n)
