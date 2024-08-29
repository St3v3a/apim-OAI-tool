# AI Chat Application

![Application Demo](picture1.gif)

## Description

This AI Chat Application is a lightweight, user-friendly interface for interacting with an AI model via Azure APIM with subscription keys.

- Simple and intuitive chat interface for front end testing
- Two modes basic and advanced with different iterations from provided .csv file 
- Real-time AI responses (only displays first sentance") with headers captured
- Lightweight implementation using basic language features and standard library

## Getting Started

### Prerequisites

- Git
- Python 3.7 or higher

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-chat-app.git
   cd ai-chat-app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. Ensure the `config.json` file is properly set up with your Azure API credentials.

2. Run the main application script:
   ```bash
   python main.py
   ```

3. The application window should open, allowing you to start chatting with the AI.

### First-Time Setup

When running the application for the first time, you'll need to configure the settings:

1. Launch the application:
   ```bash
   python main.py
   ```

2. Click on the "Settings" button or menu option.

3. In the Settings window:
   - Enter your Azure API endpoint URL
   - Input your Azure API key
   - Select the appropriate API version
   - Choose the AI model you want to use (if applicable)

4. Click "Save" to store your settings.

5. Restart the application for the changes to take effect.

Note: Your settings will be saved in the `config.json` file. This file is gitignored to prevent accidental commits of sensitive information.

## Usage

1. Type your message in the input field at the bottom of the window.
2. Press Enter or click the Send button to submit your message.
3. The AI's response will appear in the chat history above.

## Configuration

An example `config.json` file is provided with placeholders for the necessary API credentials:
