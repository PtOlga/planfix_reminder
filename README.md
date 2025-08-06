# Planfix Reminder

A desktop notification system for Planfix tasks with modular architecture and advanced diagnostic capabilities.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![Stars](https://img.shields.io/github/stars/PtOlga/planfix_reminder.svg)
![Issues](https://img.shields.io/github/issues/PtOlga/planfix_reminder.svg)

## ✨ Features

- 🏗️ **Modular Architecture** - clean separation of concerns
- 🔔 **Toast Notifications** - beautiful animated popup windows
- 🎯 **Task Categorization** - overdue, urgent, and current tasks
- ⏰ **Flexible Settings** - intervals, limits, notification types
- 🎵 **Sound Alerts** - different sounds for different task types
- 💤 **Snooze Functionality** - 15 minutes or 1 hour delays
- 🖱️ **Draggable Windows** - customizable positioning
- 📊 **System Tray** - management and statistics
- 🔄 **Smart Tracking** - prevents duplicate notifications
- 📝 **Advanced Logging** - detailed logs for diagnostics
- 🔧 **Built-in Diagnostics** - automatic system health checks
- 📦 **Executable Build** - ready-to-use tools for creating exe files

## 📁 Project Structure

```
planfix_reminder/
├── main.py                       # Main application entry point
├── config_manager.py             # Configuration management
├── planfix_api.py                # Planfix API integration
├── task_tracker.py               # Task state tracking
├── ui_components.py              # Toast notifications and system tray
├── file_logger.py                # File logging system
├── diagnostic_module.py          # System diagnostic module
├── config.ini                    # Configuration file (not in git!)
├── config.ini.example            # Configuration template
├── requirements.txt              # Python dependencies
├── build.bat                     # Build batch file
├── md/                           # Documentation files
│   ├── BUILD_INSTRUCTIONS.md     # Build instructions
│   └── DIAGNOSTIC_INTEGRATION.md # Diagnostic documentation
├── planfix_reminder_help.html    # User help file
├── README.md                     # Documentation
└── tools/                        # Development tools
    ├── build_exe.py              # Executable build script
    ├── planfix_reminder.spec     # PyInstaller configuration
    ├── debug_utils.py            # Debug utilities
    └── test_diagnostic_integration.py # Integration tests
```

## 🚀 Installation and Setup

### Option 1: Pre-built Executable (Recommended)

1. **Download** the latest release or build yourself (see "Building exe" section)
2. **Extract** the archive to any folder
3. **Copy** `config.ini.example` to `config.ini`
4. **Edit** `config.ini` with your Planfix API credentials
5. **Run** `PlanfixReminder.exe`

### Option 2: Run from Source Code

#### 1. Clone the Repository
```bash
git clone https://github.com/PtOlga/planfix_reminder.git
cd planfix_reminder
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Configure Settings
```bash
# Windows
copy config.ini.example config.ini

# Linux/macOS
cp config.ini.example config.ini

# Edit config.ini
notepad config.ini  # Windows
nano config.ini     # Linux/macOS
```

#### 4. Get Planfix API Token
1. Log in to Planfix as administrator
2. Navigate to **Settings → API**
3. Create a new API key
4. Copy the token to `config.ini`

#### 5. Run Application
```bash
python main.py
```

## ⚙️ Configuration

### Main Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api_token` | Planfix API token | - |
| `account_url` | Account URL (with `/rest`) | - |
| `filter_id` | Pre-built filter ID | - |
| `user_id` | User ID | 1 |
| `check_interval` | Check interval (seconds) | 300 |
| `max_total_windows` | Max total windows | 10 |
| `max_windows_per_category` | Max windows per category | 5 |

### Example config.ini
```ini
[Planfix]
api_token = your_api_token_here
account_url = https://your-account.planfix.com/rest
filter_id =
user_id = 4

[Settings]
check_interval = 300
notify_current = true
notify_urgent = true
notify_overdue = true
max_windows_per_category = 5
max_total_windows = 10
debug_mode = false

[Roles]
include_assignee = true
include_assigner = true
include_auditor = true
```

## 🎯 Usage

### Notification Types

- 🔴 **Overdue Tasks** - red with critical sound alerts
- 🟡 **Urgent Tasks** - orange with warning sound alerts
- 📋 **Current Tasks** - blue with no sound

### Notification Controls

- **Open** - opens task in browser
- **15min** - snooze for 15 minutes (urgent/overdue only)
- **1h** - snooze for 1 hour
- **Done** - mark as viewed (won't show again)
- **✕** - close (will reappear after interval)
- **📌** - pin/unpin window

### System Tray

Right-click the tray icon:
- 📊 **Check Now** - force immediate check
- ⏸️ **Pause** - temporarily disable notifications (1 hour / until tomorrow)
- ▶️ **Resume** - enable notifications after pause
- 🌐 **Open Planfix** - open in browser
- 📖 **Help** - open user guide
- 🔧 **Diagnostics** - run system diagnostics
- ❌ **Exit** - close application

### Tray Icon Colors
- 🔴 **Red** - overdue tasks present
- 🟠 **Orange** - urgent tasks present
- 🟢 **Green** - all good
- ⚫ **Gray** - application paused

## 🔧 Diagnostics and Troubleshooting

### Built-in Diagnostics
Run diagnostics from tray menu (🔧 Diagnostics) or via command:
```bash
python diagnostic_module.py
```

Diagnostics check:
- ✅ **System** - OS, architecture, user permissions
- ✅ **Security** - antivirus, UAC, SmartScreen
- ✅ **Notifications** - Windows notification settings
- ✅ **Services** - critical Windows services
- ✅ **Network** - internet, DNS, firewall
- ✅ **Files** - folder access permissions
- ✅ **Display** - resolution, scaling settings
- ✅ **Performance** - CPU, memory, conflicting processes

### Logging
Enable debug mode in `config.ini`:
```ini
[Settings]
debug_mode = true
```

Logs are saved to `logs/` folder with detailed application activity.

### Module Testing
Each module can be tested independently:

```bash
# Test configuration loading
python config_manager.py

# Test API and task retrieval
python planfix_api.py

# Test task tracking
python task_tracker.py

# Test UI components
python ui_components.py

# Test diagnostics
python tools/test_diagnostic_integration.py
```

## 📦 Building Executable

### Automatic Build (Recommended)
```bash
# Windows
build.bat

# Or directly via Python
python tools/build_exe.py
```

### Manual Build
```bash
# Install PyInstaller
pip install pyinstaller

# Build using spec file
pyinstaller --clean tools/planfix_reminder.spec
```

Detailed instructions available in [md/BUILD_INSTRUCTIONS.md](md/BUILD_INSTRUCTIONS.md)

## 🛠️ Architecture

### Core Modules

- **`main.py`** - application entry point and main class
- **`ConfigManager`** - settings loading and validation
- **`PlanfixAPI`** - API integration and task retrieval
- **`TaskProcessor`** - task categorization and formatting
- **`TaskTracker`** - notification state tracking
- **`ToastManager`** - popup notification management
- **`SystemTray`** - system tray and menu
- **`FileLogger`** - file-based logging system
- **`DiagnosticModule`** - system diagnostics

### Development Tools (`tools/` folder)

- **`build_exe.py`** - automated executable building
- **`planfix_reminder.spec`** - PyInstaller configuration
- **`debug_utils.py`** - debugging utilities
- **`test_diagnostic_integration.py`** - integration tests

### Modular Architecture Benefits

- ✅ **Readability** - each module handles specific functionality
- ✅ **Testability** - modules can be tested independently
- ✅ **Reusability** - modules can be used in other projects
- ✅ **Extensibility** - easy to add new features
- ✅ **Maintainability** - easier to locate and fix issues
- ✅ **Diagnostics** - built-in tools for problem resolution

## 📋 System Requirements

### For Executable (Recommended)
- **Windows 10/11** (primary support)
- **Windows 7/8.1** (limited support)
- **4 GB RAM** (minimum 2 GB)
- **50 MB** free disk space
- **Internet connection** for Planfix API access

### For Source Code Execution
- **Python 3.8+** (recommended 3.10+)
- **pip** for dependency installation
- Libraries from `requirements.txt`

#### Windows
```bash
# Python usually includes tkinter
python --version
pip install -r requirements.txt
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk python3-pip
pip3 install -r requirements.txt

# CentOS/RHEL/Fedora
sudo dnf install python3-tkinter python3-pip
pip3 install -r requirements.txt
```

#### macOS
```bash
# Via Homebrew
brew install python-tk
pip3 install -r requirements.txt
```

## 🚨 Security

- ⚠️ **Never commit `config.ini` to git!**
- 🔒 API tokens should be stored locally only
- 📝 Use `config.ini.example` as template

## 🐛 Troubleshooting

### 🔧 First Step - Run Diagnostics
**Always start with diagnostics!**
1. Run diagnostics from tray menu (🔧 Diagnostics)
2. Review the HTML report with recommendations
3. Send report to support if needed

### ❌ Configuration Won't Load
- Verify `config.ini` exists in application folder
- Ensure API token is correct (no extra spaces)
- URL must end with `/rest`
- Check file encoding (should be UTF-8)

### 🌐 Can't Connect to API
- Run diagnostics - it checks internet and DNS
- Verify token and URL correctness in config.ini
- Ensure Planfix server is accessible
- Check proxy and firewall settings

### 🔔 No Notifications Appearing
- Verify user has active tasks
- Ensure tasks aren't closed/completed
- Check `notify_*` settings in config
- Diagnostics will show Windows notification service status

### 🖥️ Interface Issues
- Diagnostics will check display and scaling settings
- Try running as administrator
- Verify no multiple application instances are running

### 📝 Enable Debug Mode for Detailed Analysis
```ini
[Settings]
debug_mode = true
```
Logs are saved to `logs/` folder - send them with support requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Usage and Attribution

When using this code, please include:
- **Author:** PtOlga
- **Project:** Planfix Reminder  
- **Repository:** https://github.com/PtOlga/planfix_reminder

**Example code attribution:**
```python
# Based on Planfix Reminder by PtOlga
# https://github.com/PtOlga/planfix_reminder
```

**For web projects:**
```html
<!-- Powered by Planfix Reminder - https://github.com/PtOlga/planfix_reminder -->
```

## 🌟 If This Project Helped You

- ⭐ **Star the repository** on GitHub
- 🔗 **Share the link** with colleagues
- 📝 **Create issues** with suggestions or bug reports
- 🤝 **Contribute** improvements via Pull Requests

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Create a Pull Request

## 📈 Roadmap

- [ ] Support for other task management systems
- [ ] Web-based configuration interface
- [ ] Mobile push notifications
- [ ] Telegram bot integration
- [ ] Multi-language support

## 📊 Monitoring and Statistics

### System Tray Information
- **Total task count**
- **Overdue task count**
- **Last check time**
- **Application status** (active/paused)

### Logging Categories
The application maintains detailed logs:
- **Startup** - initialization and startup events
- **Config** - configuration loading and changes
- **API** - Planfix API requests and responses
- **UI** - interface events and notifications
- **Error** - errors and exceptions

## 🔄 Updates

### Version Check
Current version is displayed in application title and logs.

### Installing Updates
1. **For exe version** - download new version and replace file
2. **For source code** - run `git pull` and restart application

### Release History
- ✅ **v2.0** - Modular architecture, diagnostics, improved logging
- ✅ **v1.5** - System tray, pause management
- ✅ **v1.0** - Basic notification functionality

## 📞 Support

### Self-Service Problem Resolution
1. **Run diagnostics** from tray menu (🔧 Diagnostics)
2. **Review HTML report** with recommendations
3. **Check troubleshooting section** in this README
4. **Enable debug_mode** and examine logs

### Contacting Support
When creating support requests, please include:
1. **Diagnostic HTML report**
2. **Log files** from `logs/` folder
3. **Problem description** and steps to reproduce
4. **Application version** and operating system

### Contact Information
- 🐛 **Issues:** https://github.com/PtOlga/planfix_reminder/issues
- 📧 **Email:** Available via GitHub profile
- 💬 **Discussions:** Use GitHub Discussions for questions

---

**Made with ❤️ for the Planfix community**