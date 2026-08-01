Examples and Use Cases
======================

Generate Password Examples
--------------------------

Basic Password Generation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate a 20-character password (default):

.. code-block:: bash

   python3 scripts/generate_password.py

Expected output:

.. code-block:: text

   Generated password: aB3@kL9!mQ2$rT5^zX8%
   Password copied to clipboard!

Custom Length Password
~~~~~~~~~~~~~~~~~~~~~~

Generate a 32-character password:

.. code-block:: bash

   python3 scripts/generate_password.py -l 32

Use in Scripts
~~~~~~~~~~~~~~

Use the generated password in another script:

.. code-block:: bash

   PASSWORD=$(python3 scripts/generate_password.py 2>&1 | grep "Generated password" | awk '{print $NF}')
   echo "Your password: $PASSWORD"

PHP Switch Examples
-------------------

List Available Versions
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python3 scripts/php_switch.py

This will show:

.. code-block:: text

   Installed PHP versions:
   1. PHP 8.3 (/usr/bin/php8.3)
   2. PHP 8.2 (/usr/bin/php8.2)
   3. PHP 7.4 (/usr/bin/php7.4)
   Select the PHP version to switch to (by number): _

Switch to Specific Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Switch to PHP 8.3:

.. code-block:: bash

   python3 scripts/php_switch.py -v 8.3

Development Setup Examples
---------------------------

Create Feature Branch
~~~~~~~~~~~~~~~~~~~~~

Set up a new branch for feature development:

.. code-block:: bash

   python3 scripts/dev_setup.py --number 123 --name "Add user authentication"

This will:

1. Show available branches
2. Let you select a base branch
3. Create branch: ``issues/123_add_user_authentication``
4. Copy commit message to clipboard

Complete Workflow
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create the branch
   python3 scripts/dev_setup.py --number 456 --name "Fix database connection"

   # Output:
   # Based on issues [#456](https://github.com/username/repo/issues/456)
   # refs: #456 Fix database connection

   # Now make your commits
   git add src/database.py
   git commit  # Paste the copied message

CV Generator Example
--------------------

Create ``cv.md`` in the project root:

.. code-block:: markdown

   # Candidate Name

   candidate@example.com | +381 11 555 0100 | Belgrade, Serbia

   ## Experience

   ### [Senior Engineer](https://example.com) / **Example Co** | *2022–Present*

   - Built and operated reliable services.

Configure the source and output in ``.env``:

.. code-block:: text

   MARKDOWN_FILE_URL="cv.md"
   PDF_OUTPUT_LOCATION="cv.pdf"

Generate the PDF:

.. code-block:: bash

   python3 scripts/cv_generator.py

The generated PDF contains selectable text and is written only after a
single-page render succeeds.

Backup Examples
---------------

Daily Backup
~~~~~~~~~~~~

Backup system configuration and projects:

.. code-block:: bash

   python3 scripts/backup.py

Setup with cron for daily backups:

.. code-block:: bash

   # Edit crontab
   crontab -e

   # Add this line to run backup daily at 2 AM:
   0 2 * * * cd /home/username/python_scripts && python3 scripts/backup.py

Verify Backup
~~~~~~~~~~~~~

Check if backup was successful:

.. code-block:: bash

   ls -lah /path/to/backup/location/

Example .env configuration:

.. code-block:: bash

   BACKUP_LOCATION="/home/user/Documents/backups"
   SYSTEM_SOURCE_PATHS="/home/user/.bashrc,/home/user/.gitconfig"
   SYSTEM_DESTINATION_FOLDER_NAME="system"
   PROJECTS_SOURCE_PATHS="/var/www/project1,/var/www/project2"
   PROJECTS_DESTINATION_FOLDER_NAME="projects"

Git Copy Examples
-----------------

Copy Recent Changes
~~~~~~~~~~~~~~~~~~~

Copy files changed in the last commit:

.. code-block:: bash

   python3 scripts/git_copy.py

This creates a timestamped zip file with all changed files.

Copy Between Two Commits
~~~~~~~~~~~~~~~~~~~~~~~~~

Copy files changed between specific commits:

.. code-block:: bash

   python3 scripts/git_copy.py abc123def456 xyz789uvw012 /tmp/changes

This will create ``/tmp/changes_YYYYMMDD_HHMMSS.zip``

Distribute Changes
~~~~~~~~~~~~~~~~~~

After running git_copy, share the zip file:

.. code-block:: bash

   # Find the created zip file
   ls -la /path/to/target/directory/*.zip

   # Send to colleague or backup location
   scp /path/to/changes_20260311_143022.zip user@server:/backups/

Hash Filenames Examples
-----------------------

Hash Images in Directory
~~~~~~~~~~~~~~~~~~~~~~~~~

Hash all JPG files in a directory:

.. code-block:: bash

   python3 scripts/hash_filenames.py -d /home/user/Downloads -v

Example configuration in .env:

.. code-block:: bash

   HASH_FILENAMES_FILE_EXTENSIONS=.jpg,.jpeg,.png,.gif

Organize Files into Batches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hash files and organize into batch folders:

.. code-block:: bash

   python3 scripts/hash_filenames.py -d /path/to/media -m -v

This creates:

.. code-block:: text

   hashed_001/  (100 files)
   hashed_002/  (100 files)
   hashed_003/  (50 files)
   ...

Splice Images Examples
----------------------

Create Image Collage
~~~~~~~~~~~~~~~~~~~~

Splice random images together:

.. code-block:: bash

   cd /path/to/images
   python3 /path/to/scripts/splice_images.py -n 5

This will:

1. Select 5 random images
2. Splice them horizontally
3. Save result to ``spliced_images/``
4. Move originals to ``standalone_images/``

Splice Specific Images
~~~~~~~~~~~~~~~~~~~~~~

Combine specific images:

.. code-block:: bash

   python3 scripts/splice_images.py -i photo1.jpg photo2.jpg photo3.jpg -o collage.jpg

Set Custom Dimensions
~~~~~~~~~~~~~~~~~~~~~

Splice with specific height:

.. code-block:: bash

   python3 scripts/splice_images.py -n 3 --height 600 -o result.jpg

Splice Videos Examples
----------------------

Create Highlight Reel
~~~~~~~~~~~~~~~~~~~~~

Extract 30 seconds of random 3-second clips:

.. code-block:: bash

   python3 scripts/splice_videos.py -i input_video.mp4 -d 30 -s 3

This creates:

.. code-block:: text

   assets/spliced/output_from_input_video.mp4

Extract Longer Segment
~~~~~~~~~~~~~~~~~~~~~~

Create a 60-second video from 5-second clips:

.. code-block:: bash

   python3 scripts/splice_videos.py -i source.mp4 -d 60 -s 5

Monitor Progress
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Watch the assets/random_clips directory
   watch -n 1 'ls -la assets/random_clips/'

Restore VS Code Examples
------------------------

Initial Setup
~~~~~~~~~~~~~

After installing VS Code settings on a new machine:

.. code-block:: bash

   cd /path/to/project
   python3 scripts/restore_vscode_folder.py

Setup with cron for regular restoration:

.. code-block:: bash

   # Create a backup
   python3 scripts/backup.py

   # Later, restore in new clone
   git clone <repo>
   cd <repo>
   python3 scripts/restore_vscode_folder.py

Verify Restoration
~~~~~~~~~~~~~~~~~~

Check if .vscode folder was restored:

.. code-block:: bash

   ls -la .vscode/
   cat .vscode/settings.json

Advanced Examples
-----------------

Combining Scripts
~~~~~~~~~~~~~~~~~

Create and backup a project setup:

.. code-block:: bash

   # 1. Set up new feature branch
   python3 ../python_scripts/scripts/dev_setup.py --number 789 --name "New feature"

   # 2. Make changes
   # ... edit files ...

   # 3. Generate build number
   BUILD_NUM=$(python3 -c "import random, string; print(''.join(random.choices(string.digits, k=4)))")

   # 4. Backup project
   python3 ../python_scripts/scripts/backup.py

   # 5. Copy changes
   python3 ../python_scripts/scripts/git_copy.py

Daily Automation Script
~~~~~~~~~~~~~~~~~~~~~~~

Create a shell script that runs multiple tasks:

.. code-block:: bash

   #!/bin/bash

   SCRIPTS_DIR="/home/user/python_scripts"

   echo "Running daily automation tasks..."

   # 1. Backup system files
   cd $SCRIPTS_DIR
   python3 scripts/backup.py

   # 2. Clean up old clips
   cd $SCRIPTS_DIR
   rm -rf assets/random_clips/*

   # 3. Generate summary
   echo "Backup completed at $(date)" >> /tmp/automation.log

   echo "Automation complete!"

Workflow Integration
~~~~~~~~~~~~~~~~~~~~

Integrate with your development workflow:

.. code-block:: bash

   # Upon starting work
   python3 scripts/dev_setup.py --number ${ISSUE_NUM} --name "${FEATURE_NAME}"

   # Before committing work
   python3 -m pytest tests/
   python3 -m mypy src/
   python3 -m black .
   python3 -m isort .

Password Manager Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate and store password:

.. code-block:: bash

   # Generate password
   NEW_PASS=$(python3 scripts/generate_password.py | tail -1)

   # Store in password manager (example with pass)
   echo "$NEW_PASS" | pass insert myproject/new_password

Tips and Tricks
---------------

Running Multiple Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Process multiple video files:

.. code-block:: bash

   for video in videos/*.mp4; do
       python3 scripts/splice_videos.py -i "$video" -d 30 -s 3
   done

Parallel Execution
~~~~~~~~~~~~~~~~~~~

Run multiple scripts in parallel:

.. code-block:: bash

   python3 scripts/backup.py &
   python3 scripts/hash_filenames.py -d /media &
   wait
   echo "All tasks completed"

Logging Output
~~~~~~~~~~~~~~

Save script output for review:

.. code-block:: bash

   python3 scripts/backup.py > backup.log 2>&1
   python3 scripts/hash_filenames.py -v > hash_operations.log 2>&1
