# Automating QFieldCloud Project Management via the SDK

This document presents some of the common tasks solved by using QFieldCloud SDK.
The examples are prepared for both **Bash** (Linux/macOS) and **PowerShell** (Windows).

### Install QFieldCloud SDK

To interact with the QFieldCloud API, start by installing the official QFieldCloud SDK.
The installation command is the same for both Bash and PowerShell:

```shell
pip install qfieldcloud-sdk
```

Once installed, you're ready to manage your projects directly from the command line.

> Note: All values are enclosed in quotes, with single quotes (`'`) recommended for Bash (_but not mandatory_) and double quotes (`"`) for PowerShell.

### Log in to QFieldCloud

First, log in to your QFieldCloud account.

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli login 'ninjamaster' 'secret_password123'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli login "ninjamaster" "secret_password123"
    ```

After signing in, the QFieldCloud CLI will output the value of the authentication token.
The authentication token will be sent to QFieldCloud API to authorize you instead of sending the username and password.
You can explicitly pass the authentication token via passing `--token` CLI argument for every command.

The easier approach is to set an environment variable with your token:

=== ":material-bash: Bash"

    ```bash
    export QFIELDCLOUD_TOKEN='123abcXYZ987exampleToken'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    $env:QFIELDCLOUD_TOKEN = "123abcXYZ987exampleToken"
    ```

You may want to extract the session token directly from the JSON output of the `qfieldcloud-cli` login command.
This is especially useful if you're automating tasks or chaining multiple commands.

In this example, we'll use the `jq` tool to parse the JSON response and retrieve the session token.

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli --json login 'ninjamaster' 'secret_password123' | jq .session_token
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli --json login "ninjamaster" "secret_password123" | jq ".session_token"
    ```

This command will output only the session token, which can be stored in an environment variable for future use:

=== ":material-bash: Bash"

    ```bash
    export QFIELDCLOUD_TOKEN=$(qfieldcloud-cli --json login 'ninjamaster' 'secret_password123' | jq -r .session_token)
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    $env:QFIELDCLOUD_TOKEN = (qfieldcloud-cli --json login "ninjamaster" "secret_password123" | jq ".session_token")
    ```

### Create a project

Create a project called `Tree_Survey` within your organization:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli create-project --owner 'My_Organization_Clan' --description 'Daily work project' --is-private 'Tree_Survey'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli create-project --owner "My_Organization_Clan" --description "Daily work project" --is-private "Tree_Survey"
    ```

The project is now created in your QFieldCloud organization, and its project ID (e.g., `123e4567-e89b-12d3-a456-426614174000`) is returned.
You’re now ready for file uploads.

If you forgot to copy your project ID, you can always check the list of all the projects on QFieldCloud.

### List Your Projects

To list all projects associated with your account:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli list-projects
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli list-projects
    ```

To include public projects in the list:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli list-projects --include-public
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli list-projects --include-public
    ```

### Upload Local Files to QFieldCloud

Prepare your local project files and upload them to QFieldCloud:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli upload-files '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/QField/cloud/Tree_survey'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\QField\cloud\Tree_survey"
    ```

You can also upload specific files by using the `--filter` option.
For instance, to upload only `.gpkg` files:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli upload-files '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/QField/cloud/Tree_survey' --filter '*.gpkg'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\QField\cloud\Tree_survey" --filter "*.gpkg"
    ```

Now you can upload and check your files on QFieldCloud.

### List Files in a Project

To view all files in a specific project:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli list-files '123e4567-e89b-12d3-a456-426614174000'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli list-files "123e4567-e89b-12d3-a456-426614174000"
    ```

### Manage Members and Collaborators

The collaborative nature of QFieldCloud naturally involves other people in the fieldwork.

You can add, remove, or change the members on your Organization.

#### Add a Member to an Organization

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli members-add 'My_Organization_Clan' 'ninja007' admin
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli members-add "My_Organization_Clan" "ninja007" admin
    ```

#### Change a Member's Role

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli members-patch 'My_Organization_Clan' 'ninja007' member
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli members-patch "My_Organization_Clan" "ninja007" member
    ```

#### Remove a Member in an Organization

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli members-remove 'My_Organization_Clan' 'ninja007'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli members-remove "My_Organization_Clan" "ninja007"
    ```

You can add, remove, or change the roles of collaborators on your project.

#### Add a Collaborator in a project

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli collaborators-add '123e4567-e89b-12d3-a456-426614174000' 'ninja007' admin
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli collaborators-add "123e4567-e89b-12d3-a456-426614174000" "ninja007" admin
    ```

#### Change a Collaborator’s Role in a project

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli collaborators-patch '123e4567-e89b-12d3-a456-426614174000' 'ninja001' editor
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli collaborators-patch "123e4567-e89b-12d3-a456-426614174000" "ninja001" editor
    ```

#### Remove a Collaborator in a project

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli collaborators-remove '123e4567-e89b-12d3-a456-426614174000' 'ninja007'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli collaborators-remove "123e4567-e89b-12d3-a456-426614174000" "ninja007"
    ```

### Create and monitor jobs

#### Trigger job

To manually trigger a package job at any time and force if require:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package --force
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli job-trigger "123e4567-e89b-12d3-a456-426614174000" package --force
    ```

After triggering a job, monitor job's status to ensure successful completion:

#### List all jobs for a specific project

Before checking the status of a job, you can list all jobs associated with a project by using the `list-jobs` command.

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli list-jobs '123e4567-e89b-12d3-a456-426614174000' --type package
    ```

=== ":material-powershell: PowerShell"

   ```powershell
   qfieldcloud-cli list-jobs "123e4567-e89b-12d3-a456-426614174000" --type package
   ```

#### Check the status of a specific job

Once you have the job ID, you can check its status using the `job-status` command:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli job-status '321e4567-e89b-12d3-a456-426614174987'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli job-status "321e4567-e89b-12d3-a456-426614174987"
    ```

#### Wait for job completion

To automate the process of checking a job's status until it is finished, you can use a loop that will keep checking the status until the job either succeeds or fails.

=== ":material-bash: Bash"

    ```bash
    JOB_STATUS=$(qfieldcloud-cli --json job-status '321e4567-e89b-12d3-a456-426614174987' | jq '.output' -r)
    while [[ "$JOB_STATUS" != "success" && "$JOB_STATUS" != "failed" ]]; do
    echo "Job is still running... Status: $JOB_STATUS"
    sleep 10  # Wait for 10 seconds before checking again
    JOB_STATUS=$(qfieldcloud-cli --json job-status '321e4567-e89b-12d3-a456-426614174987' | jq '.output' -r)
    done
    echo "Job finished with status: $JOB_STATUS"
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    $JOB_STATUS = (qfieldcloud-cli --json job-status "321e4567-e89b-12d3-a456-426614174987" | jq ".output" -r)
    while ($JOB_STATUS -ne "success" -and $JOB_STATUS -ne "failed") {
        Write-Host "Job is still running... Status: $JOB_STATUS"
        Start-Sleep -Seconds 10  # Wait for 10 seconds before checking again
        $JOB_STATUS = (qfieldcloud-cli --json job-status "321e4567-e89b-12d3-a456-426614174987" | jq ".output" -r)
    }
    Write-Host "Job finished with status: $JOB_STATUS"
    ```

#### Schedule and Trigger a Package Job

A more advanced example where the trigger of the job is automated.

Suppose your company packages the project every morning at 8:47 AM.:

=== ":material-bash: Bash"

    ```bash
    47 8 * * * qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package
    ```

    This triggers the package job daily at the specified time. For more information about [cronjob](https://crontab.guru/).

=== ":material-powershell: PowerShell"

    ```powershell
    schtasks /create /tn "QFieldCloud Job Trigger" /tr "qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package" /sc daily /st 08:47
    ```

    This triggers the package job daily at the specified time. For more information about [schtasks](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks).


### Download Files for Backup

Once the package job is complete, download the project files for backup. To download all files or filter specific ones (e.g., `.jpg` files):

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli package-download '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/backup_folder/DCIM/2024-11-10/' --filter '*.jpg'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\backup_folder\DCIM\2024-11-10\" --filter "*.jpg"
    ```

If files already exist locally and you want to overwrite them, use the `--force-download` option:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli package-download '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/backup_folder/DCIM/2024-11-10/' --force-download
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\backup_folder\DCIM\2024-11-10\" --force-download
    ```

### Delete Files to Save Space

To free up storage on QFieldCloud, you can delete unnecessary files, such as `.jpg` files:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli delete-files '123e4567-e89b-12d3-a456-426614174000' --filter '*.jpg'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" --filter "*.jpg"
    ```

You can also delete specific files by specifying their exact path:

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli delete-files '123e4567-e89b-12d3-a456-426614174000' 'DCIM/tree-202411202334943.jpg'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" "DCIM\tree-202411202334943.jpg"
    ```

### Delete a Project

To permanently delete a project (be cautious—this action cannot be undone):

=== ":material-bash: Bash"

    ```bash
    qfieldcloud-cli delete-project '123e4567-e89b-12d3-a456-426614174000'
    ```

=== ":material-powershell: PowerShell"

    ```powershell
    qfieldcloud-cli delete-project "123e4567-e89b-12d3-a456-426614174000"
    ```
