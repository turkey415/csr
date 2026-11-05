"""Raw log archive (fork addition): keep a copy of every finished session log.

Star Citizen prunes old files from logbackups. CSR's session archive already keeps the
parsed numbers, but a session whose log is gone can't be re-read when the parser learns
something new. So each scan copies finished logs into raw_logs/<channel>/ next to the
archive, and scans read that folder too (duplicates collapse by file name).
"""
import os
import shutil

DIR = "raw_logs"


def merge(channel_folder, files, app_dir):
    """Copy new or grown logbackups files into the raw archive and return the scan list:
    the original files plus archived ones the game has since deleted."""
    dest = os.path.join(app_dir, DIR, os.path.basename(os.path.normpath(channel_folder)).upper() or "LIVE")
    try:
        os.makedirs(dest, exist_ok=True)
    except OSError:
        return files
    have = {os.path.basename(f) for f in files}
    for src in files:
        dst = os.path.join(dest, os.path.basename(src))
        try:
            if not os.path.exists(dst) or os.path.getsize(dst) < os.path.getsize(src):
                shutil.copy2(src, dst)
        except OSError:
            pass
    try:
        kept = [os.path.join(dest, n) for n in os.listdir(dest) if n.endswith(".log") and n not in have]
    except OSError:
        kept = []
    return files + kept
