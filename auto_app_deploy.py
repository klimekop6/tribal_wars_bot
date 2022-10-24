import pathlib
import shutil
import subprocess
from itertools import chain

import pysftp

from config import PYTHON_ANYWHERE_PASSWORD, PYTHON_ANYWHERE_USERNAME

APP_VERSION = "1.0.70"

pyupdater_path = pathlib.Path(r".venv_tribal_wars\Scripts\pyupdater")
# Build app using pyupdater and win.spec file
subprocess.run(
    [pyupdater_path, "build", "--clean", f"--app-version={APP_VERSION}", "win.spec"],
)
# Created and sign package file to update app
subprocess.run([pyupdater_path, "pkg", "--process", "--sign"])

# Create paths to all needed files
keys = pathlib.Path(r"pyu-data\deploy\keys.gz")
versions = pathlib.Path(r"pyu-data\deploy\versions.gz")
app_pkg = max(
    pathlib.Path(r"pyu-data\deploy").glob("*.zip"),
    key=lambda file: file.stat().st_ctime,
)
update_pkg = max(
    chain(
        pathlib.Path(r"pyu-data\deploy").glob("*stable*"),
        pathlib.Path(r"pyu-data\deploy").glob("*beta*"),
    ),
    key=lambda file: file.stat().st_ctime,
)

# Copy files from local storage to ftp server
shutil.copyfile(update_pkg, pathlib.Path(rf"\\Srv-01\ftp\{update_pkg.name}"))
shutil.copyfile(app_pkg, pathlib.Path(rf"\\Srv-01\ftp\{app_pkg.name}"))
shutil.copyfile(keys, pathlib.Path(rf"\\Srv-01\ftp\{keys.name}"))
shutil.copyfile(versions, pathlib.Path(rf"\\Srv-01\ftp\{versions.name}"))

# Copy files from local storage to pythonanywhere server
with pysftp.Connection(
    "ssh.eu.pythonanywhere.com",
    username=PYTHON_ANYWHERE_USERNAME,
    password=PYTHON_ANYWHERE_PASSWORD,
) as sftp:
    # Set working directory on the remote
    sftp.chdir("mysite/tribalwarsbot/download/")
    sftp.put(update_pkg)
    sftp.put(app_pkg)
    sftp.put(keys)
    sftp.put(versions)
