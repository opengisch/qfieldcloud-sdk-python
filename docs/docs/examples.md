# Real Use Case: Automating QFieldCloud Project Management

## CLI Example Usage

Here it is typical user story, for **Bash** (Linux/macOS) and **PowerShell** (Windows):

### **Install QFieldCloud SDK**

To interact with the QFieldCloud API, start by installing the official QFieldCloud SDK. The installation command is the same for both Bash and PowerShell:

```shell
pip install qfieldcloud-sdk
```

Once installed, you're ready to manage your projects directly from the command line.
> Note: All values are enclosed in quotes, with single quotes (`'`) recommended for Bash (_but not mandatory_) and double quotes (`"`) for PowerShell.

### **Log in to QFieldCloud and Create a New Project**

First, log in to your QFieldCloud account.

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli login 'ninjamaster' 'secret_password123'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli login "ninjamaster" "secret_password123"
    ```

After signing in, the QFieldCloud CLI will output the value of the authentication token.
The authentication token will be sent to QFieldCloud API to authorize you instead of sending the username and password.
You can explicitly pass the authentication token via passing `--token` CLI argument for every command.

The easier approach is to set an environment variable with your token:

=== ":material-linux: Linux"

    ```bash
    export QFIELDCLOUD_TOKEN='123abcXYZ987exampleToken'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    $env:QFIELDCLOUD_TOKEN = "123abcXYZ987exampleToken"
    ```

#### Create a project

Create a project called `Tree_Survey` within your organization:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli create-project --owner 'My_Organization_Clan' --description 'Daily work project' --is-private 'Tree_Survey'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli create-project --owner "My_Organization_Clan" --description "Daily work project" --is-private "Tree_Survey"
    ```

The project is now created in your QFieldCloud organization, and its project ID (e.g., `123e4567-e89b-12d3-a456-426614174000`) is returned.
You’re now ready for file uploads.

### **Upload Local Files to QFieldCloud**

Prepare your local project files and upload them to QFieldCloud:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli upload-files '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/QField/cloud/Tree_survey'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\QField\cloud\Tree_survey"
    ```

You can also upload specific files by using the `--filter` option. For instance, to upload only `.gpkg` files:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli upload-files '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/QField/cloud/Tree_survey' --filter '*.gpkg'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\QField\cloud\Tree_survey" --filter "*.gpkg"
    ```

### **Schedule and Trigger a Package Job**

Suppose your company packages the project every morning at 8:47 AM.:

=== ":material-linux: Linux"

    ```bash
    47 8 * * * qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package
    ```

    This triggers the package job daily at the specified time. For more information about [cronjob](https://crontab.guru/)

=== ":material-microsoft-windows: Windows"

    ```powershell
    schtasks /create /tn "QFieldCloud Job Trigger" /tr "qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package" /sc daily /st 08:47
    ```

    This triggers the package job daily at the specified time. For more information about [schtasks](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks)

To manually trigger a package job at any time and force if require:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli job-trigger '123e4567-e89b-12d3-a456-426614174000' package --force
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli job-trigger "123e4567-e89b-12d3-a456-426614174000" package --force
    ```

### **Monitor Job Status**

After triggering a job, monitor its status to ensure successful completion:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli list-jobs '123e4567-e89b-12d3-a456-426614174000' --type package
    qfieldcloud-cli job-status '321e4567-e89b-12d3-a456-426614174987'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli list-jobs "123e4567-e89b-12d3-a456-426614174000" --type package
    qfieldcloud-cli job-status "321e4567-e89b-12d3-a456-426614174987"
    ```

### **Download Files for Backup**

Once the package job is complete, download the project files for backup. To download all files or filter specific ones (e.g., `.jpg` files):

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli package-download '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/backup_folder/DCIM/2024-11-10/' --filter '*.jpg'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\backup_folder\DCIM\2024-11-10\" --filter "*.jpg"
    ```

If files already exist locally and you want to overwrite them, use the `--force-download` option:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli package-download '123e4567-e89b-12d3-a456-426614174000' '/home/ninjamaster/backup_folder/DCIM/2024-11-10/' --force-download
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "C:\Users\ninjamaster\backup_folder\DCIM\2024-11-10\" --force-download
    ```

### **Delete Files to Save Space**

To free up storage on QFieldCloud, you can delete unnecessary files, such as `.jpg` files:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli delete-files '123e4567-e89b-12d3-a456-426614174000' --filter '*.jpg'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" --filter "*.jpg"
    ```

You can also delete specific files by specifying their exact path:

=== ":material-linux: Linux"

    ```bash
    qfieldcloud-cli delete-files '123e4567-e89b-12d3-a456-426614174000' 'DCIM/tree-202411202334943.jpg'
    ```

=== ":material-microsoft-windows: Windows"

    ```powershell
    qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" "DCIM\tree-202411202334943.jpg"
    ```

### **Other Useful QFieldCloud CLI Commands**

#### **List Your Projects**

To list all projects associated with your account:

```shell
qfieldcloud-cli list-projects
```

To include public projects in the list:

```shell
qfieldcloud-cli list-projects --include-public
```

#### **List Files in a Project**

To view all files in a specific project:

```shell
qfieldcloud-cli list-files "123e4567-e89b-12d3-a456-426614174000"
```

#### **Delete a Project**

To permanently delete a project (be cautious—this action cannot be undone):

```shell
qfieldcloud-cli delete-project "123e4567-e89b-12d3-a456-426614174000"
```

#### **Manage Collaborators**

You can add, remove, or change the roles of collaborators on your project.

- **Add a Collaborator:**

```shell
qfieldcloud-cli collaborators-add "123e4567-e89b-12d3-a456-426614174000" "ninja007" admin
```

- **Remove a Collaborator:**

```shell
qfieldcloud-cli collaborators-remove "123e4567-e89b-12d3-a456-426614174000" "ninja007"
```

- **Change a Collaborator’s Role:**

```shell
qfieldcloud-cli collaborators-patch "123e4567-e89b-12d3-a456-426614174000" "ninja001" editor
```
