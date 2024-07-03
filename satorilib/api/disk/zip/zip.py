import os


def zipFolder(folderPath: str, outputPath: str) -> None:
    import shutil
    shutil.make_archive(outputPath, 'zip', folderPath)


def zipSelected(folderPath, outputPath, selectedFiles):
    import zipfile
    with zipfile.ZipFile(outputPath, 'w') as zipf:
        for file in selectedFiles:
            filepath = os.path.join(folderPath, file)
            if os.path.isfile(filepath):
                zipf.write(filepath, os.path.relpath(filepath, folderPath))
            elif os.path.isdir(filepath):
                for root, _, files in os.walk(filepath):
                    for f in files:
                        full_path = os.path.join(root, f)
                        zipf.write(full_path, os.path.relpath(
                            full_path, folderPath))


def zipByBash(folderPath, outputPath, selectedFiles):
    ''' requires RUN apt-get install -y zip '''
    import subprocess
    # Construct the command with the arguments
    command = ['/Satori/Lib/satorilib/api/disk/zip/zip.sh',
               folderPath, outputPath] + selectedFiles
    # Run the command
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    # Print output and errors for debugging
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)
    # Check if the command was successful
    if result.returncode == 0:
        print(f"Successfully created zip file at {outputPath}")
    else:
        print(f"Error: {result.stderr}")
    # >>> folder_path = '/Satori/Lib/satorilib/api'
    # >>> output_path = '/Satori/Lib/satorilib/api/archive.zip'
    # >>> selected_files = ['__init__.py', 'disk', 'hash.py']
    # >>> zipByBash(folder_path, output_path, selected_files)
