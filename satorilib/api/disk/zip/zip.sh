#!/bin/bash

# Function to zip selected files and folders
zip_selected_files() {
  folder_path=$1
  output_path=$2
  shift 2
  selected_files=("$@")

  echo "Folder path: $folder_path"
  echo "Output path: $output_path"
  echo "Selected files: ${selected_files[*]}"

  # Create a temporary directory
  temp_dir=$(mktemp -d)
  echo "Temporary directory created at $temp_dir"

  # Copy selected files and folders to the temporary directory
  for file in "${selected_files[@]}"; do
    src_path="$folder_path/$file"
    dest_path="$temp_dir/$file"
    echo "Processing $src_path"
    if [ -f "$src_path" ]; then
      mkdir -p "$(dirname "$dest_path")"
      cp "$src_path" "$dest_path"
      echo "Copied file $src_path to $dest_path"
    elif [ -d "$src_path" ]; then
      mkdir -p "$dest_path"
      cp -r "$src_path" "$dest_path"
      echo "Copied directory $src_path to $dest_path"
    else
      echo "Warning: $src_path does not exist"
    fi
  done

  # Ensure the output directory exists
  output_dir=$(dirname "$output_path")
  mkdir -p "$output_dir"

  # Create the zip archive
  (cd "$temp_dir" && zip -r "$output_path" .)
  echo "Zip archive creation attempted at $output_path"

  # Check if the zip file was created
  if [ -f "$output_path" ]; then
    echo "Zip archive successfully created at $output_path"
  else
    echo "Failed to create zip archive at $output_path"
  fi

  # Remove the temporary directory
  rm -rf "$temp_dir"
  echo "Temporary directory $temp_dir removed"
}

# Main
zip_selected_files "$@"
