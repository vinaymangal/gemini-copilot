# Gemini Copilot

Gemini Copilot is a beginner-friendly Windows desktop application that integrates a Gemini-powered assistant into your workflow. The application allows users to interact with local files and folders using natural language commands, making it easier to summarize, analyze, and manage documents.

## Features

- **Global Hotkey**: Launch the assistant with a simple keyboard shortcut.
- **File Interaction**: Drag and drop files or right-click to ask the assistant about specific documents.
- **Multi-File Support**: Read and process various file types, including .txt, .pdf, .docx, .xlsx, and more.
- **Gemini API Integration**: Utilize the Gemini API for intelligent responses and insights.
- **User-Friendly Interface**: A minimalistic popup window for easy interaction.
- **System Tray Icon**: Stay connected with the assistant while working on other tasks.
- **Batch Processing**: Analyze multiple files simultaneously.
- **Memory & Context**: Remember past interactions and provide smart suggestions.

## Setup Instructions

1. **Install Python**: Ensure you have Python installed on your Windows machine. You can download it from the official Python website.

2. **Clone the Repository**: Clone this repository to your local machine using Git:
   ```
   git clone https://github.com/yourusername/gemini-copilot.git
   ```

3. **Navigate to the Project Directory**:
   ```
   cd gemini-copilot
   ```

4. **Install Required Libraries**: Install the necessary Python libraries by running:
   ```
   pip install -r requirements.txt
   ```

5. **Set Up Your Gemini API Key**: Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

6. **Run the Application**: Start the application by executing the main script:
   ```
   python src/main.py
   ```

## Usage Guidelines

- Press the designated global hotkey (e.g., Ctrl + Space) to open the assistant.
- Drag and drop files into the popup window or right-click on a file in File Explorer and select "Ask Gemini about this file."
- Use the provided buttons to summarize, extract information, or perform other actions on the selected files.

## Milestones

The project is structured into several milestones, each adding new features and enhancements. The core milestones include:

1. **Setup & Safe Folder**: Initial project setup and GitHub integration.
2. **Hello Popup Window**: Basic UI with a functional window.
3. **Global Hotkey + System Tray**: Hotkey functionality and tray icon integration.
4. **File Reading**: Ability to read and display file contents.
5. **Connect to Gemini API**: Integration with the Gemini API for responses.
6. **Explorer Right-Click Menu**: Context menu integration for file interactions.
7. **Packaging**: Create a standalone executable for easy distribution.
8. **Auto-Start & Updates**: Enable the application to start with Windows and check for updates.

## Contribution

Contributions are welcome! If you have suggestions or improvements, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.