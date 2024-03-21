# Gmail Email Automation

This project automates the processing of emails in a Gmail account based on predefined rules.

## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/your-username/gmail-email-automation.git
    ```

2. Navigate to the project directory:

    ```bash
    cd gmail-email-automation
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up Google API credentials:
   
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project (or select an existing one).
   - Enable the Gmail API for your project.
   - Create credentials (OAuth client ID) and download the credentials.json file.
   - Place the credentials.json file in the project directory.

5. Run the script:

    ```bash
    python script.py
    ```
6. To Run the Test cases :

   ```bash
    pytest pytests.py
    ```

## Usage

This script fetches emails from the Gmail inbox, applies predefined rules to filter and process emails, and performs actions such as marking emails as read, moving them to specific folders, etc.

## Configuration

- Ensure that the `token.pickle` file (containing user access and refresh tokens) is present in the project directory. This file is generated during the authentication process.
- Define email processing rules in the `rules.json` file. Each rule consists of conditions and actions to be performed on matching emails.


## Credits

- [Google Developers Documentation](https://developers.google.com/gmail/api) - Official documentation for the Gmail API.
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/14/) - Documentation for SQLAlchemy, used for database interaction.
