# Real Use Case: Automating QFieldCloud Project Management

## CLI Example Usage

### **1. Install QFieldCloud SDK**

To interact with the QFieldCloud API, start by installing the official QFieldCloud SDK:

```bash
pip install qfieldcloud-sdk
```

Once installed, you're ready to manage your projects directly from the command line.

### **2. Log in to QFieldCloud and Create a New Project**

First, log in to your QFieldCloud account.
Note that all values are enclosed in single or double quote characters, depending on your operating system's shell.

```bash
qfieldcloud-cli login "ninjamaster" "secret_password123"
```

After signing in, the QFieldCloud CLI will output the value of the authentication token.
The authentication token will be sent to QFieldCloud API to authorize you instead of sending the username and password.
You can explicitly pass the authentication token via passing `--token` CLI argument for every command.
The easier approach is to set an environment variable with your token:

```bash
export QFIELDCLOUD_TOKEN="123abcXYZ987exampleToken"
```

#### Create a project

Create a project called "Tree_Survey" within your organization:

```bash
qfieldcloud-cli create-project --owner "My_Organization_Clan" --description "Daily work project" --is-private "Tree_Survey"
```

The project is now created in your QFieldCloud organization, and its project ID (e.g., `123e4567-e89b-12d3-a456-426614174000`) is returned.
You’re now ready for file uploads.

### **3. Upload Local Files to QFieldCloud**

Prepare your local project files and upload them to QFieldCloud. For example, if your files are located in `/home/ninjamaster/QField/cloud/Tree_survey`:

```bash
qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "/home/ninjamaster/QField/cloud/Tree_survey"
```

You can also upload specific files by using the `--filter` option. For instance, to upload only `.gpkg` files:

```bash
qfieldcloud-cli upload-files "123e4567-e89b-12d3-a456-426614174000" "/home/ninjamaster/QField/cloud/Tree_survey" --filter "*.gpkg"
```

### **4. Schedule and Trigger a Package Job**

Suppose your company packages the project every morning at 8:47 AM. You can automate this process using a cron job:

```bash
47 8 * * * qfieldcloud-cli job-trigger "123e4567-e89b-12d3-a456-426614174000" package
```

This command triggers the package job daily at the specified time. Here's what the cron job format means:

- `47`: Minute (47th minute).
- `8`: Hour (8 AM).
- `*`: Every day of the month.
- `*`: Every month.
- `*`: Every day of the week.

To manually trigger a package job at any time:

```bash
qfieldcloud-cli job-trigger "123e4567-e89b-12d3-a456-426614174000" package
```

You can force the job to re-run even if one is already queued:

```bash
qfieldcloud-cli job-trigger "123e4567-e89b-12d3-a456-426614174000" package --force
```

### **5. Monitor Job Status**

After triggering a job, monitor its status to ensure successful completion:

```bash
qfieldcloud-cli list-jobs "123e4567-e89b-12d3-a456-426614174000" --type package
qfieldcloud-cli job-status "321e4567-e89b-12d3-a456-426614174987"
```

### **6. Download Files for Backup**

Once the package job is complete, download the project files for backup. To download all files or filter specific ones (e.g., `.jpg` files):

```bash
qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "/home/ninjamaster/backup_folder/DCIM/2024-11-10/" --filter "*.jpg"
```

If files already exist locally and you want to overwrite them, use the `--force-download` option:

```bash
qfieldcloud-cli package-download "123e4567-e89b-12d3-a456-426614174000" "/home/ninjamaster/backup_folder/DCIM/2024-11-10/" --force-download
```

### **7. Delete Files to Save Space**

To free up storage on QFieldCloud, you can delete unnecessary files, such as `.jpg` files:

```bash
qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" --filter "*.jpg"
```

You can also delete specific files by specifying their exact path:

```bash
qfieldcloud-cli delete-files "123e4567-e89b-12d3-a456-426614174000" DCIM/tree-202411202334943.jpg
```

### **Other Useful QFieldCloud CLI Commands**

#### **List Your Projects**

To list all projects associated with your account:

```bash
qfieldcloud-cli list-projects
```

To include public projects in the list:

```bash
qfieldcloud-cli list-projects --include-public
```

#### **List Files in a Project**

To view all files in a specific project:

```bash
qfieldcloud-cli list-files "123e4567-e89b-12d3-a456-426614174000"
```

#### **Delete a Project**

To permanently delete a project (be cautious—this action cannot be undone):

```bash
qfieldcloud-cli delete-project "123e4567-e89b-12d3-a456-426614174000"
```

#### **Manage Collaborators**

You can add, remove, or change the roles of collaborators on your project.

- **Add a Collaborator:**

```bash
qfieldcloud-cli collaborators-add "123e4567-e89b-12d3-a456-426614174000" "ninja007" admin
```

- **Remove a Collaborator:**

```bash
qfieldcloud-cli collaborators-remove "123e4567-e89b-12d3-a456-426614174000" "ninja007"
```

- **Change a Collaborator’s Role:**

```bash
qfieldcloud-cli collaborators-patch "123e4567-e89b-12d3-a456-426614174000" "ninja001" editor
```
