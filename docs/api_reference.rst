API Reference
=============

Helper Modules
--------------

src.helpers.wrapper_helper
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.helpers.wrapper_helper
   :members:
   :undoc-members:
   :show-inheritance:

src.helpers.arguments_helper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.helpers.arguments_helper
   :members:
   :undoc-members:
   :show-inheritance:

Scripts
-------

scripts.generate_password
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.generate_password
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``generate_password(minimum_password_length, number_of_chunks, length)`` - Generates a random password
- ``parse_arguments(minimum_password_length, number_of_chunks)`` - Parses command-line arguments

**Environment Variables:** None required

**Usage:**

.. code-block:: bash

   python3 -m scripts.generate_password -l 32

scripts.php_switch
~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.php_switch
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_installed_php_versions()`` - Returns list of installed PHP versions
- ``extract_version_from_path(php_path)`` - Extracts version number from PHP path
- ``switch_php_version(php_path)`` - Switches to specified PHP version

**Environment Variables:** None required

**Usage:**

.. code-block:: bash

   python3 -m scripts.php_switch -v 8.3

scripts.dev_setup
~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.dev_setup
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``issue_name_for_branch(issue_name)`` - Converts issue name to branch-friendly format
- ``get_git_branches()`` - Lists available Git branches
- ``create_and_checkout_new_branch(branch_name, source_branch)`` - Creates and checks out new branch

**Environment Variables:**

- ``BRANCH_PREFIX`` - Prefix for branch names (default: ``issues``)
- ``REQUEST_PREFIX`` - Prefix for commit messages (default: ``refs:``)
- ``ISSUE_BASE_PATH`` - Base URL for issue links (optional)

**Usage:**

.. code-block:: bash

   python3 -m scripts.dev_setup --number 123 --name "Feature name"

scripts.backup
~~~~~~~~~~~~~~~

.. automodule:: scripts.backup
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_env(var_name, is_list)`` - Gets environment variable value(s)
- ``do_simple_backup(backup_destination, env_prefixes)`` - Performs simple backup
- ``do_projects_backup(backup_location)`` - Backs up project files
- ``do_deployments_backup(backup_location)`` - Backs up deployment files

**Environment Variables:**

- ``BACKUP_LOCATION`` - Destination directory for backups
- ``SYSTEM_SOURCE_PATHS`` - Comma-separated system files to backup
- ``PROJECTS_SOURCE_PATHS`` - Comma-separated project directories
- ``DEPLOYMENTS_SOURCE_PATHS`` - Comma-separated deployment directories

**Usage:**

.. code-block:: bash

   python3 -m scripts.backup

scripts.git_copy
~~~~~~~~~~~~~~~~

.. automodule:: scripts.git_copy
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_last_two_git_hashes()`` - Gets last two commit hashes
- ``do_copy_files_and_folders(src_list, dest)`` - Copies files between locations
- ``zip_copied_files(directory_path)`` - Creates zip archive of copied files

**Environment Variables:**

- ``TARGET_DIRECTORY_PATH`` - Base directory for git copy operations

**Usage:**

.. code-block:: bash

   python3 -m scripts.git_copy [start_hash] [end_hash] [target_dir]

scripts.restore_vscode_folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.restore_vscode_folder
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``read_environment_variables()`` - Reads backup configuration
- ``do_restore_operation(vscode_folder, current_dir, ...)`` - Performs restoration

**Environment Variables:**

- ``BACKUP_LOCATION`` - Base backup directory
- ``PROJECTS_DESTINATION_FOLDER_NAME`` - Project backup folder name

**Usage:**

.. code-block:: bash

   python3 -m scripts.restore_vscode_folder

scripts.hash_filenames
~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.hash_filenames
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_file_extensions()`` - Gets target file extensions from environment
- ``hash_files(directory, verbose)`` - Hashes filenames in directory
- ``is_hashed(filename, length)`` - Checks if filename is already hashed
- ``load_mapping(mapping_file)`` - Loads filename mapping from file

**Environment Variables:**

- ``HASH_FILENAMES_FILE_EXTENSIONS`` - Target file extensions (e.g., ``.jpg,.png``)

**Usage:**

.. code-block:: bash

   python3 -m scripts.hash_filenames -d /path -v -m

scripts.splice_images
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.splice_images
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_valid_extensions()`` - Gets valid image extensions
- ``get_random_images_from_directory(directory, count)`` - Selects random images
- ``splice_images(images, output, width, height)`` - Splices images horizontally
- ``move_images(src_dir, dest_dir)`` - Moves images to destination

**Environment Variables:**

- ``SPLICE_IMAGES_FILE_EXTENSIONS`` - Valid image extensions

**Usage:**

.. code-block:: bash

   python3 -m scripts.splice_images -n 5 -o result.jpg

scripts.splice_videos
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: scripts.splice_videos
   :members:
   :undoc-members:
   :show-inheritance:

**Key Functions:**

- ``get_video_duration(video_path)`` - Gets video duration
- ``calculate_number_of_random_clips(total_duration, target_duration, segment_duration)`` - Calculates clip count
- ``create_random_clips(num_segments, segment_duration, ...)`` - Creates random clips
- ``concatenate_clips(clips, output_path)`` - Concatenates clips into final video

**Environment Variables:** None required

**Usage:**

.. code-block:: bash

   python3 -m scripts.splice_videos -i input.mp4 -d 30 -s 3

Data Types and Constants
------------------------

Common Return Types
~~~~~~~~~~~~~~~~~~~~

Most functions return:

- ``str`` - Single string values
- ``list[str]`` - Lists of strings
- ``dict`` - Mapping dictionaries
- ``None`` - Functions with side effects (file operations)

Exceptions
~~~~~~~~~~

Scripts raise:

- ``ValueError`` - Invalid input values or missing variables
- ``FileNotFoundError`` - Missing files or directories
- ``PermissionError`` - Insufficient permissions
- ``subprocess.CalledProcessError`` - External command failures

Type Hints
----------

All scripts use Python type hints. Examples:

.. code-block:: python

   def generate_password(
       minimum_password_length: int,
       number_of_chunks: int,
       length: int = 20
   ) -> str:
       """Generate a random password."""
       ...

   def get_env(var_name: str, is_list: bool = False) -> str | list[str]:
       """Get environment variable value(s)."""
       ...

See also :doc:`../usage_guide` for usage patterns and :doc:`../examples` for detailed examples.
